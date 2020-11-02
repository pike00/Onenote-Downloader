import os
from os.path import join, exists

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

KEYS_DIR = join(ROOT_DIR, "keys")

CONFIG_PATH = join(KEYS_DIR, "config.yaml")
TOKEN_PATH = join(KEYS_DIR, "token.json")


OUT_DIR = join(ROOT_DIR, "out/")

os.makedirs(OUT_DIR, exist_ok = True)
TOKEN_URL = "https://login.microsoftonline.com/organizations/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0/me/onenote/"
AUTHORIZATION_URL = "https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize"