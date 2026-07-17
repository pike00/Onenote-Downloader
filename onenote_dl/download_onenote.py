import re
import subprocess
from os import makedirs
from os.path import join

from furl import furl
from tqdm import tqdm

import definitions
from onenote_dl.db_helper import parseJSON, OneNoteType
from onenote_dl.helpers import get_json_notebook_section, get_json_page, get_binary_file, get_html

def send_mattermost_message(message):
    escaped_message = message.replace('"', '\\"')
    bash_script = f"""
JANET_ID="4zauw6phe7g6jfhxxkyqzqsiyo"
WILL_ID="tp1edo6wf3bziydgf8zyrahkuc"

TOKEN_LINE=$(docker exec mattermost mmctl token generate janet temp-notify --local 2>&1)
TOKEN=$(echo "$TOKEN_LINE" | awk '{{print $1}}' | tr -d ':')

MM_URL="http://$(docker inspect mattermost --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' | awk '{{print $1}}'):8065"

CHANNEL_ID=$(curl -s -X POST "$MM_URL/api/v4/channels/direct" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "[\"$JANET_ID\", \"$WILL_ID\"]" | jq -r '.id')

curl -s -X POST "$MM_URL/api/v4/posts" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{{\\"channel_id\\": \\"$CHANNEL_ID\\", \\"message\\": \\"{escaped_message}\\"}}" | jq -r '.id'

TOKEN_ID=$(docker exec mattermost mmctl token list janet --local 2>&1 \
  | grep "temp-notify" | awk '{{print $1}}' | tr -d ':')
[ -n "$TOKEN_ID" ] && docker exec mattermost mmctl token revoke "$TOKEN_ID" --local
"""
    try:
        subprocess.run(["ssh", "ares", "bash -s"], input=bash_script.encode('utf-8'), capture_output=True, check=True)
    except Exception as e:
        print(f"Failed to send Mattermost notification: {e}", flush=True)

try:
    f = furl(definitions.GRAPH_URL)
    f /= "notebooks"

    # Download and write the notebooks json to the onenote_dl json folder
    notebooks_js = get_json_notebook_section(join(definitions.OUT_DIR, "notebooks.json"), f.url)

    for notebook_js in notebooks_js:
        notebook = parseJSON(json_content=notebook_js, objectType=OneNoteType.NOTEBOOK)
        if "01 sfi" not in notebook.displayName.lower():
            continue
            
        send_mattermost_message(f"🚀 OneNote Downloader: Starting sync for notebook *{notebook.displayName}*")
        print(f"\n\n------NOTEBOOK: {notebook.displayName}------")

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
            send_mattermost_message(f"🔄 OneNote Downloader: Syncing section *{section.displayName}*")

            # Create section directory within each notebook directory
            section_dir = join(notebook_dir, section.id)
            makedirs(section_dir, exist_ok=True)

            # Download and Save pages json for each section
            pages_js = get_json_page(join(section_dir, "pages.json"), section_js['pagesUrl'])
            
            # Loop over each page within each section
            for page_js in pages_js:
                page = parseJSON(page_js, OneNoteType.PAGE)
                contentUrl = page_js['contentUrl']

                # Create a page directory for assets
                page_dir = join(section_dir, page.id)
                makedirs(page_dir, exist_ok=True)

                page_filename = join(page_dir, "page.html")
                page_html = get_html(page_filename, contentUrl + f"?includeinkML=true")

                # Find resource urls within each page (Includes images)
                asset_urls = re.findall(r'"(https?://graph\.microsoft.com.+?\$value)"', page_html)

                if len(asset_urls) == 0:
                    continue

                for asset_url in tqdm(asset_urls, desc=f"{page.displayName[0:35]:>40}", ncols=100, unit="files"):
                    uuid = asset_url.split("/")[7]
                    asset_filename = join(page_dir, uuid)
                    get_binary_file(asset_filename, asset_url)

            send_mattermost_message(f"📁 OneNote Downloader: Finished section *{section.displayName}*")

        send_mattermost_message(f"✅ OneNote Downloader: Sync successfully completed for *{notebook.displayName}*!")

except Exception as e:
    send_mattermost_message(f"❌ OneNote Downloader: Sync CRASHED with error: `{e}`")
    raise e
