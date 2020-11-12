import json
from os.path import join, exists

import requests

from OAuth.oath_helper import refresh_token

headers_auth = ""


def get_graph_page(req_url):
    refresh_token()
    return requests.get(req_url, headers=headers_auth).content.decode("utf-8")


# Returns json_content
def get_json(filename, req_url, forceDownload=False) -> json:
    refresh_token()
    json_content = json.loads(get_graph_page(req_url))['value']

    # Append ".json" if not already in filename
    if ".json" not in filename:
        filename += ".json"

    # Check if the file already exists and you don't want to overwrite
    if exists(filename) and not forceDownload:

        with open(filename, "r") as file:
            return json.load(file)



    return json_content


def write_json(filename_array, json_content):
    # Otherwise, write the json formatting nicely
    str_content = json.dumps(json_content, indent=2, sort_keys=True)
    with open(filename, "w") as file:
        file.write(str_content)

    print(f"Wrote {filename}")

def download_and_write_binary_to_file(filename, req_url):
    refresh_token()
    with open(filename, "wb") as file:
        result = requests.get(req_url, headers=headers_auth)

        file.write(result.content)

    print(f"Wrote {filename}")
