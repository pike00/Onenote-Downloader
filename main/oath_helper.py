import datetime
import json
from os import makedirs
import re
import threading
import webbrowser
from urllib.parse import quote_plus

import requests
import yaml
from authlib.integrations.requests_client import OAuth2Session
from dateutil import parser
from furl import furl

from OAuth.OAuthHTTPRequestHandler import OAuthHTTPRequestHandler
from OAuth.OAuthHTTPServer import OAuthHTTPServer
from definitions import *
import main.helpers
from main.helpers import download_and_save_json_to_file, get_graph_page, download_and_write_binary_to_file

config_file = open(CONFIG_PATH, 'r')
config = yaml.safe_load(config_file.read())

client_id = config['oauth']['client_id']
client_secret = config['oauth']['client_secret']
scope = config['oauth']['scope']

authorization_endpoint = config['oauth']['urls']['authorization_endpoint']
token_endpoint = config['oauth']['urls']['token_endpoint']

graph_url = config['graph_url']

has_valid_token = False

# GET TOKEN

# If the token file exists, just load that
if os.path.exists(TOKEN_PATH):
    with open(TOKEN_PATH, "r") as file:
        token_js = json.loads(file.read())

    if 'expiration' in token_js:
        expiration_datetime = parser.parse(token_js['expiration'])
        if expiration_datetime > datetime.datetime.now():
            has_valid_token = True
        else:
            has_valid_token = False
    else:
        has_valid_token = False

    # If there isn't a valid token/expiration has passed, remove the token
    if not has_valid_token:
        os.remove(TOKEN_PATH)
    # if token_js.get("expiration")

if not has_valid_token:  # Otherwise get a new token
    client = OAuth2Session(client_id, client_secret, scope=scope)

    uri, state = client.create_authorization_url(authorization_endpoint)
    webbrowser.open(uri, new=2)

    httpd = OAuthHTTPServer(('localhost', 80), OAuthHTTPRequestHandler)

    t = threading.Thread(target=httpd.serve_forever)
    t.start()

    while not httpd.has_authorization_code():
        pass

    httpd.shutdown()

    code = quote_plus(httpd.get_code())

    token_request_url = furl(token_endpoint)
    token_request_url.args['redirect_uri'] = "http://localhost/onenote_downloader"

    data = {
        "scope": scope,
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "client_secret": client_secret
        # "redirect_url": "http://localhost/onenote_downloader"
    }

    token_js = requests.post(token_request_url.url, data=data).content

    token_js = json.loads(token_js.decode("utf-8"))

    expiration = datetime.datetime.now() + datetime.timedelta(hours=1)

    token_js['expiration'] = str(expiration)

    with open(TOKEN_PATH, "w") as file:
        file.write(json.dumps(token_js))

# noinspection PyUnboundLocalVariable
token = token_js['access_token']
headers_auth = {"Authorization": f"Bearer {token}"}
main.helpers.headers_auth = headers_auth

# Notebooks
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
