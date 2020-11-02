import requests



# Get Notebooks URL
from furl import furl

f = furl(graph_url)
f /= "notebooks"

# Download and write the notebooks json to the main json folder
notebooks_js = download_and_save_json_to_file([OUT_DIR, "notebooks.json"], f.url)

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
            for asset_url in asset_urls:
                uuid = asset_url.split("/")[7]
                asset_filename = join(page_dir, uuid)

                # Download asset if doesn't exist
                if not os.path.exists(asset_filename):
                    asset = download_and_write_binary_to_file(asset_filename, asset_url)

                # Replace the page html that has the asset_urls with the filenames for local loading
                page_html = page_html.replace(asset_url, asset_filename)

            # Now save page html to page folder
            with open(join(page_dir, "page.html"), "w") as file:
                file.write(page_html)

                # img_tags = re.findall(r'<img (.*) />', content)
            # for img_tag in img_tags:
            #     attrs = img_tag.split(" ")
            #     img_src = ""
            #     for attr in attrs:
            #         if "data-fullres-src-type" in attr:
            #             img_type = re.findall(r'"(.*)"', attr)[0]
            #         elif "data-fullres-src" in attr:
            #             img_src = re.findall(r'"(.*)"', attr)[0]
            #
            #     # print(f"Image: {img_type} \t {img_src}")

            # print(filename)
