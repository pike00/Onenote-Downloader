import re
import time
from os import makedirs


# Get Notebooks URL
from furl import furl
from tqdm import tqdm

from definitions import *
from onenote_dl.helpers import *

f = furl(GRAPH_URL)
f /= "notebooks"

# Download and write the notebooks json to the onenote_dl json folder
notebooks_js = download_and_save_json_to_file([OUT_DIR, "notebooks.json"], f.url)

while True:

    try:
        # Loop over each notebook
        for notebook_js in notebooks_js:
            notebook_id = notebook_js['id']

            # Create notebook directory within JSON directory
            notebook_dir = join(OUT_DIR, notebook_id)
            makedirs(notebook_dir, exist_ok=True)

            # Download and save each subsection url and related json
            sections_js = download_and_save_json_to_file([notebook_dir, "sections.json"],
                                                         notebook_js['sectionsUrl'])

            # Loop over each section
            for section_js in sections_js:

                section_id = section_js['id']

                # Create section directory within each notebook directory
                section_dir = join(notebook_dir, section_id)
                makedirs(section_dir, exist_ok=True)

                # Download and Save pages json for each section
                pages_js = download_and_save_json_to_file([section_dir, "pages.json"], section_js['pagesUrl'])

                # Loop over each page within each section
                for page_js in pages_js:

                    page_id = page_js['id']

                    # Download page_html
                    contentUrl = page_js['contentUrl']

                    # noinspection SpellCheckingInspection
                    page_html = get_graph_page(contentUrl + f"?includeinkML=true")
                    # Don't save yet - must replace asset urls with filenames

                    # Create a page directory for assets
                    page_dir = join(section_dir, page_id)
                    makedirs(page_dir, exist_ok=True)

                    # Find resource urls within each page
                    # Includes images
                    asset_urls = re.findall(r'"(https?://.+?\$value)"', page_html)
                    for asset_url in tqdm(asset_urls):
                        uuid = asset_url.split("/")[7]
                        asset_filename = join(page_dir, uuid)

                        # Download asset if doesn't exist
                        if not os.path.exists(asset_filename):
                            asset = download_and_write_binary_to_file(asset_filename, asset_url)

                        # Replace the page html that has the asset_urls with the filenames for local loading
                        page_html = page_html.replace(asset_url, asset_filename.split("\\")[-1])

                    # Now save page html to page folder

                    page_filename = join(page_dir, "page.html")
                    if not os.path.exists(page_filename):
                        with open(page_filename, "w", encoding='utf-8') as file:
                            file.write(page_html)
                            print(f"Wrote {page_id}.html")

    except:
        print("exception caught. Waiting 60 seconds")

    time.sleep(600)