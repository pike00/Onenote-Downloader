import re
from os import makedirs

# Get Notebooks URL
from os.path import join, exists

from furl import furl
from sqlalchemy.orm import Session
from tqdm import tqdm

from definitions import GRAPH_URL, OUT_DIR
# from onenote_dl.db_helper import *
from onenote_dl.db_helper import parseJSON, OneNoteType, update_row
from onenote_dl.helpers import get_json, get_graph_page, download_and_write_binary_to_file

f = furl(GRAPH_URL)
f /= "notebooks"

# Download and write the notebooks json to the onenote_dl json folder
notebooks_js = get_json(join(OUT_DIR, "notebooks.json"), f.url)

for notebook_js in notebooks_js:
    notebook = parseJSON(json_content=notebook_js, objectType=OneNoteType.NOTEBOOK)
    update_row(notebook)

    # Create notebook directory within JSON directory
    notebook_dir = join(OUT_DIR, notebook.id)
    makedirs(notebook_dir, exist_ok=True)

    # Download and save each subsection url and related json
    sections_js = get_json(join(notebook_dir, "sections.json"),
                           notebook_js['sectionsUrl'])

    #Loop over each section
    for section_js in sections_js:
        section = parseJSON(section_js, OneNoteType.SECTION)
        update_row(section)

        # Create section directory within each notebook directory
        section_dir = join(notebook_dir, section.id)
        makedirs(section_dir, exist_ok=True)

        # Download and Save pages json for each section
        pages_js = get_json(join(section_dir, "pages.json"), section_js['pagesUrl'])

        # Loop over each page within each section
        for page_js in pages_js:
            page = parseJSON(page_js, OneNoteType.PAGE)
            update_row(page)
            # Download page_html
            contentUrl = page_js['contentUrl']
#
            # noinspection SpellCheckingInspection
            page_html = get_graph_page(contentUrl + f"?includeinkML=true")
            # Don't save yet - must replace asset urls with filenames

            # Create a page directory for assets
            page_dir = join(section_dir, page.id)
            makedirs(page_dir, exist_ok=True)

            # Find resource urls within each page
            # Includes images
            asset_urls = re.findall(r'"(https?://.+?\$value)"', page_html)
            print(f"Downloading assets for {page.id}")
            for asset_url in tqdm(asset_urls):
                uuid = asset_url.split("/")[7]
                asset_filename = join(page_dir, uuid)

                # Download asset if doesn't exist
                if not exists(asset_filename):
                    asset = download_and_write_binary_to_file(asset_filename, asset_url)

                # Replace the page html that has the asset_urls with the filenames for local loading
                page_html = page_html.replace(asset_url, asset_filename.split("\\")[-1])

            # Now save page html to page folder

            page_filename = join(page_dir, "page.html")
            if not exists(page_filename):
                with open(page_filename, "w", encoding='utf-8') as file:
                    file.write(page_html)
                    print(f"Wrote {page.id}.html")
