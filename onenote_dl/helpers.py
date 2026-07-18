import json
import time
from os.path import join, exists
import random

import requests
from furl import furl

from OAuth.oath_helper import refresh_token

headers_auth = ""
LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 8.0  # start highly conservative to avoid 429 penalty box
SUCCESS_STREAK = 0
SESSION = requests.Session()


def get_html(filename, req_url, forceDownload=False):
    refresh_token()

    if exists(filename) and not forceDownload:
        # print(f"Loaded {filename} (From saved file)")
        with open(filename, "r", encoding="utf-8") as file:
            return file.read().replace("\n", "")
    else:  # Otherwise download it

        req = download(req_url)
        content = req.content.decode("utf-8")

        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)

        # print(f"Loaded {filename} (Downloaded + Saved)")

        return content


def get_json_notebook_section(filename: str, req_url: str, forceDownload: bool = False) -> json:
    if ".json" not in filename:
        filename += ".json"

    refresh_token()

    # Check if the file already exists and you don't want to overwrite
    if exists(filename) and not forceDownload:
        # print(f"Loaded {filename} (From saved file)")
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    req = download(req_url)

    json_to_save = req.json().get("value")

    with open(filename, "w", encoding="utf-8") as file:
        file.write(json.dumps(json_to_save, indent=2, sort_keys=True))

    return json_to_save


# Returns json_content and Saves to file
def get_json_page(filename, req_url, forceDownload=False) -> json:
    # Append ".json" if not already in filename
    if ".json" not in filename:
        filename += ".json"

    refresh_token()

    # Check if the file already exists and you don't want to overwrite
    if exists(filename) and not forceDownload:
        # print(f"Loaded {filename} (From saved file)")
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    # Otherwise, check the request URL and download the appropriate data
    json_to_save = None
    f = furl(req_url)
    f.args['select'] = 'id,title,contentUrl'
    f.args['orderby'] = 'title'

    req_url = f.url

    json_to_save = []

    while True:
        req = download(req_url)

        if len(req.json().get("value")) != 0:
            json_to_save += req.json().get("value")
        else:  # No more values present
            break

        if "@odata.nextLink" in req.json():
            f = furl(req.json().get("@odata.nextLink"))
            req_url = f.url
        else:
            break

    # if json_content is None:  # Error of some type
    #     return json.loads("{}")

    str_content = json.dumps(json_to_save, indent=2, sort_keys=True)

    with open(filename, "w", encoding="utf-8") as file:
        file.write(str_content)

    # print(f"Loaded {filename} (Downloaded + Saved)")

    return json_to_save


def get_binary_file(filename, req_url, forceDownload=False):
    refresh_token()

    if exists(filename) and not forceDownload:
        # print(f"\tAsset {filename} already downloaded")
        return
    else:
        req = download(req_url)
        with open(filename, "wb") as file:
            file.write(req.content)

        # print(f"\tLoaded {filename} (Downloaded)")
        return


def download(request_url):
    global LAST_REQUEST_TIME, MIN_REQUEST_INTERVAL, SUCCESS_STREAK
    req = None
    backoff = 10

    while True:
        # Respect rate limits by maintaining a minimum interval between requests
        now = time.time()
        elapsed = now - LAST_REQUEST_TIME
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        refresh_token()

        try:
            LAST_REQUEST_TIME = time.time()
            req = SESSION.get(request_url, headers=headers_auth)
        except Exception as e:
            print(f"\nRequest failed: {e}. Retrying in {backoff} seconds...", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if req.status_code == 200:
            SUCCESS_STREAK += 1
            # If we run successfully for 30 requests, slowly attempt to decrease interval
            if SUCCESS_STREAK >= 30:
                MIN_REQUEST_INTERVAL = max(1.0, MIN_REQUEST_INTERVAL - 0.1)
                SUCCESS_STREAK = 0
            return req

        if req.status_code == 429:
            SUCCESS_STREAK = 0
            # Increase delay interval dynamically on throttle to back off
            MIN_REQUEST_INTERVAL = min(15.0, MIN_REQUEST_INTERVAL + 1.0)

            retry_after = req.headers.get("Retry-After")
            if retry_after:
                try:
                    sleep_time = int(retry_after)
                except ValueError:
                    sleep_time = max(1800, backoff)
            else:
                sleep_time = max(1800, backoff)

            print(f"\nThrottle limit reached (429) for URL: {request_url}\nResponse body: {req.text}\nHeaders: {dict(req.headers)}\nIncreasing request interval to {MIN_REQUEST_INTERVAL:.1f}s. Pausing for {sleep_time // 60} minutes...", flush=True)
            time.sleep(sleep_time)
            backoff = min(backoff * 2, 1800)
        elif req.status_code == 401:
            print(f"\nRequest returned status code 401. Refreshing token...", flush=True)
            refresh_token(True)
        else:
            print(f"\nRequest returned status code {req.status_code}. Retrying in {backoff} seconds...", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
