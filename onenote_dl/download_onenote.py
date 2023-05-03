import re
from os import makedirs
from os.path import join

from furl import furl
from tqdm import tqdm

import definitions
# from onenote_dl.db_helper import *
from onenote_dl.db_helper import parseJSON, OneNoteType
from onenote_dl.helpers import get_json_notebook_section, get_json_page, get_binary_file, get_html

f = furl(definitions.GRAPH_URL)
f /= "notebooks"

# Download and write the notebooks json to the onenote_dl json folder
notebooks_js = get_json_notebook_section(join(definitions.OUT_DIR, "notebooks.json"), f.url)

for notebook_js in notebooks_js:
    notebook = parseJSON(json_content=notebook_js, objectType=OneNoteType.NOTEBOOK)
    # if notebook.id != '1-957d9a86-d5f9-4a39-83c9-cf7415928045':
    #     continue
    print(f"\n\n------NOTEBOOK: {notebook.displayName}------")
    # update_row(notebook)

    # Create notebook directory within JSON directory
    notebook_dir = join(definitions.OUT_DIR, notebook.id)
    makedirs(notebook_dir, exist_ok=True)

    # Download and save each subsection url and related json
    sections_js = get_json_notebook_section(join(notebook_dir, "sections.json"),
                                            notebook_js['sectionsUrl'])

    # Loop over each section
    for section_js in sections_js:
        section = parseJSON(section_js, OneNoteType.SECTION)
        print(f"{notebook.displayName} > {section.displayName} (ID: {section.id})")

        # update_row(section)

        # Create section directory within each notebook directory
        section_dir = join(notebook_dir, section.id)
        makedirs(section_dir, exist_ok=True)

        # Download and Save pages json for each section
        pages_js = get_json_page(join(section_dir, "pages.json"), section_js['pagesUrl'])
        #
        # Loop over each page within each section
        for page_js in pages_js:
            page = parseJSON(page_js, OneNoteType.PAGE)
            # update_row(page)
            # Download page_html
            contentUrl = page_js['contentUrl']

            # Create a page directory for assets
            page_dir = join(section_dir, page.id)
            makedirs(page_dir, exist_ok=True)

            page_filename = join(page_dir, "page.html")

            page_html = get_html(page_filename, contentUrl + f"?includeinkML=true")

            # Find resource urls within each page
            # Includes images
            asset_urls = re.findall(r'"(https?://graph\.microsoft.com.+?\$value)"', page_html)

            if len(asset_urls) == 0:
                continue

            # print(f"Loading assets for {page.id}")
            # print(f"\t\t\tLoading {len(asset_urls)} assets")
            # asset_urls_iter.set_description(f"\t{page.displayName}: ")
            for asset_url in tqdm(asset_urls, desc=f"{page.displayName[0:35]:>40}", ncols=100, unit="files"):
                uuid = asset_url.split("/")[7]
                asset_filename = join(page_dir, uuid)

                # Thread(target=get_binary_file, args=(asset_filename, asset_url)).start()

                get_binary_file(asset_filename, asset_url)
