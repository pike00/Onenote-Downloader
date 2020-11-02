import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from furl import furl
import threading

logging.basicConfig(level = logging.ERROR)


class OAuthHTTPRequestHandler(BaseHTTPRequestHandler):



    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()

        f = furl(self.path)

        if f.path == furl('/onenote_downloader'):
            self.server.set_code(f.args['code'])
