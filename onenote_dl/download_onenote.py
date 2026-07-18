import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import threading
from os import makedirs
from os.path import join

from furl import furl
from tqdm import tqdm

import definitions
from onenote_dl.db_helper import parseJSON, OneNoteType
from onenote_dl.helpers import get_json_notebook_section, get_json_page, get_binary_file, get_html


# tqdm defaults to a multiprocessing.RLock for cross-process write locking.
# That registers a semaphore with multiprocessing.resource_tracker; a SIGTERM
# mid-download (systemd restart / pkill) then warns:
#   resource_tracker: There appear to be 1 leaked semaphore objects...
# We only ever run a single process, so a threading lock is correct and leak-free.
tqdm.set_lock(threading.RLock())


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
        # On ares Mattermost is local; elsewhere hop via ssh.
        if socket.gethostname().split(".")[0] == "ares":
            subprocess.run(["bash", "-s"], input=bash_script.encode("utf-8"), capture_output=True, check=True)
        else:
            subprocess.run(["ssh", "ares", "bash -s"], input=bash_script.encode("utf-8"), capture_output=True, check=True)
    except Exception as e:
        print(f"Failed to send Mattermost notification: {e}", flush=True)


def main(notebook_filter: str = ""):
    # Exit cleanly on systemd stop / Ctrl-C so tqdm can tear down without warnings.
    def _handle_stop(signum, _frame):
        print(f"\nReceived signal {signum}; shutting down cleanly.", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    try:
        f = furl(definitions.GRAPH_URL)
        f /= "notebooks"

        notebooks_js = get_json_notebook_section(join(definitions.OUT_DIR, "notebooks.json"), f.url)

        filt = notebook_filter.strip().lower()

        for notebook_js in notebooks_js:
            notebook = parseJSON(json_content=notebook_js, objectType=OneNoteType.NOTEBOOK)
            if filt and filt not in notebook.displayName.lower():
                continue

            send_mattermost_message(f"🚀 OneNote Downloader: Starting sync for notebook *{notebook.displayName}*")
            print(f"\n\n------NOTEBOOK: {notebook.displayName}------")

            notebook_dir = join(definitions.OUT_DIR, notebook.id)
            makedirs(notebook_dir, exist_ok=True)

            sections_js = get_json_notebook_section(
                join(notebook_dir, "sections.json"),
                notebook_js["sectionsUrl"],
            )

            for section_js in sections_js:
                section = parseJSON(section_js, OneNoteType.SECTION)
                print(f"{notebook.displayName} > {section.displayName} (ID: {section.id})")
                send_mattermost_message(f"🔄 OneNote Downloader: Syncing section *{section.displayName}*")

                section_dir = join(notebook_dir, section.id)
                makedirs(section_dir, exist_ok=True)

                pages_js = get_json_page(join(section_dir, "pages.json"), section_js["pagesUrl"])

                for page_js in pages_js:
                    page = parseJSON(page_js, OneNoteType.PAGE)
                    contentUrl = page_js["contentUrl"]

                    page_dir = join(section_dir, page.id)
                    makedirs(page_dir, exist_ok=True)

                    page_filename = join(page_dir, "page.html")
                    page_html = get_html(page_filename, contentUrl + "?includeinkML=true")

                    asset_urls = re.findall(
                        r'"(https?://graph\.microsoft.com.+?\$value)"',
                        page_html,
                    )

                    if len(asset_urls) == 0:
                        continue

                    for asset_url in tqdm(
                        asset_urls,
                        desc=f"{page.displayName[0:35]:>40}",
                        ncols=100,
                        unit="files",
                    ):
                        uuid = asset_url.split("/")[7]
                        asset_filename = join(page_dir, uuid)
                        get_binary_file(asset_filename, asset_url)

                send_mattermost_message(f"📁 OneNote Downloader: Finished section *{section.displayName}*")

            send_mattermost_message(
                f"✅ OneNote Downloader: Sync successfully completed for *{notebook.displayName}*!"
            )

    except Exception as e:
        send_mattermost_message(f"❌ OneNote Downloader: Sync CRASHED with error: `{e}`")
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync OneNote notebooks from Microsoft Graph.")
    parser.add_argument(
        "--notebook",
        metavar="SUBSTR",
        help="Only sync notebooks whose name contains SUBSTR (overrides ONENOTE_NOTEBOOK_FILTER)",
    )
    args = parser.parse_args()
    filt = os.environ.get("ONENOTE_NOTEBOOK_FILTER", "").strip().lower()
    if args.notebook is not None:
        filt = args.notebook.strip().lower()
    main(notebook_filter=filt)
