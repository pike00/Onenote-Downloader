import datetime
import json
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
import onenote_dl.helpers
from definitions import TOKEN_URL, AUTHORIZATION_URL

config_file = open(CONFIG_PATH, 'r')
config = yaml.safe_load(config_file.read())

client_id = config['oauth']['client_id']
client_secret = config['oauth']['client_secret']
scope = config['oauth']['scope']

has_valid_token = False


def _get_token(force=False):
    # If the token file exists, just load that
    global has_valid_token
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

    if not has_valid_token or force:  # Otherwise get a new token
        client = OAuth2Session(client_id, client_secret, scope=scope)

        uri, state = client.create_authorization_url(AUTHORIZATION_URL)
        webbrowser.open(uri, new=2)

        httpd = OAuthHTTPServer(('localhost', 80), OAuthHTTPRequestHandler)

        t = threading.Thread(target=httpd.serve_forever)
        t.start()

        while not httpd.has_authorization_code():
            pass

        httpd.shutdown()

        code = quote_plus(httpd.get_code())

        token_request_url = furl(TOKEN_URL)
        token_request_url.args['redirect_uri'] = "http://localhost/onenote_downloader"

        data = {
            "scope": scope,
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "client_secret": client_secret
        }

        token_js = requests.post(token_request_url.url, data=data).content

        token_js = json.loads(token_js.decode("utf-8"))

        expiration = datetime.datetime.now() + datetime.timedelta(hours=1)

        token_js['expiration'] = str(expiration)

        with open(TOKEN_PATH, "w") as file:
            file.write(json.dumps(token_js))

    # noinspection PyUnboundLocalVariable
    # Set headers_auth to access_token from token_js
    onenote_dl.helpers.headers_auth = {"Authorization": f"Bearer {token_js['access_token']}"}


def refresh_token(force=False):
    if has_valid_token and not force:
        return
    else:
        _get_token(force)
