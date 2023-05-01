import json
import time
from os.path import join, exists
import random

import requests
from furl import furl
from tqdm import tqdm

from OAuth.oath_helper import refresh_token

headers_auth = ""


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
    req = None

    iteration = 60

    while req is None or req.status_code != 200:
        req = requests.get(request_url, headers=headers_auth)

        if req.status_code == 429:
            print(f"\nThrottle limit reached. Pausing briefly fonr {iteration} minutes")
            time.sleep(60 * iteration)
            # for i in tqdm(range(iteration)):
            #     time.sleep(60)

            iteration *= 2

            refresh_token(True)

    return req
