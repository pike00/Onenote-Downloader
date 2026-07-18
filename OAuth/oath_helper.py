import datetime
import json
import threading
import time
import webbrowser

import requests
import yaml
from authlib.integrations.requests_client import OAuth2Session
from dateutil import parser
from furl import furl

from OAuth.OAuthHTTPRequestHandler import OAuthHTTPRequestHandler
from OAuth.OAuthHTTPServer import OAuthHTTPServer
from definitions import *
from definitions import TOKEN_URL, AUTHORIZATION_URL

config_file = open(CONFIG_PATH, 'r')
config = yaml.safe_load(config_file.read())

client_id = config['oauth']['client_id']
client_secret = config['oauth']['client_secret']
scope = config['oauth']['scope']

has_valid_token = False

REDIRECT_URI = "http://localhost:8085/onenote_downloader"


def _load_token():
    if not os.path.exists(TOKEN_PATH):
        return None
    with open(TOKEN_PATH, "r") as file:
        return json.loads(file.read())


def _save_token(token_js):
    expires_in = int(token_js.get('expires_in', 3600))
    # Refresh a minute early so we don't race Graph with an almost-expired token
    token_js['expiration'] = str(
        datetime.datetime.now() + datetime.timedelta(seconds=max(60, expires_in - 60))
    )
    with open(TOKEN_PATH, "w") as file:
        file.write(json.dumps(token_js))
    return token_js


def _apply_token(token_js):
    global has_valid_token
    # Late import avoids circular import with onenote_dl.helpers
    import onenote_dl.helpers as helpers
    helpers.headers_auth = {"Authorization": f"Bearer {token_js['access_token']}"}
    has_valid_token = True


def _access_token_valid(token_js):
    if not token_js or 'access_token' not in token_js or 'expiration' not in token_js:
        return False
    return parser.parse(token_js['expiration']) > datetime.datetime.now()


def _refresh_with_refresh_token(token_js):
    refresh = token_js.get('refresh_token')
    if not refresh:
        return None

    print("\nRefreshing access token silently...", flush=True)
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "scope": scope,
    }
    resp = requests.post(TOKEN_URL, data=data)
    new_token = resp.json()

    if 'access_token' not in new_token:
        print(
            f"Silent refresh failed: {new_token.get('error_description', new_token)}",
            flush=True,
        )
        return None

    # Microsoft may rotate refresh tokens; keep the old one if none returned
    if 'refresh_token' not in new_token:
        new_token['refresh_token'] = refresh

    return _save_token(new_token)


def _authorize_interactively():
    client = OAuth2Session(client_id, client_secret, scope=scope)

    uri, state = client.create_authorization_url(AUTHORIZATION_URL, redirect_uri=REDIRECT_URI)
    print(f"\nAuthorization URL: {uri}\n", flush=True)
    webbrowser.open(uri, new=2)

    httpd = OAuthHTTPServer(('localhost', 8085), OAuthHTTPRequestHandler)

    t = threading.Thread(target=httpd.serve_forever)
    t.start()

    while not httpd.has_authorization_code():
        time.sleep(0.5)

    httpd.shutdown()

    code = httpd.get_code()

    data = {
        "scope": scope,
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
    }

    token_js = requests.post(TOKEN_URL, data=data).json()

    if 'access_token' not in token_js:
        raise ValueError(
            f"Failed to obtain access token from Microsoft Graph API: "
            f"{token_js.get('error_description', token_js)}"
        )

    return _save_token(token_js)


def _get_token(force=False):
    global has_valid_token
    token_js = _load_token()

    if not force and _access_token_valid(token_js):
        _apply_token(token_js)
        return

    # Prefer silent refresh over browser login whenever we have a refresh token
    if token_js and token_js.get('refresh_token'):
        refreshed = _refresh_with_refresh_token(token_js)
        if refreshed:
            _apply_token(refreshed)
            print("Silent refresh succeeded.", flush=True)
            return

    token_js = _authorize_interactively()
    _apply_token(token_js)


def refresh_token(force=False):
    if has_valid_token and not force:
        return
    _get_token(force)
