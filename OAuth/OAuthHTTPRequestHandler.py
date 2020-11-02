import logging
import re
from http.server import BaseHTTPRequestHandler

from furl import furl

logging.basicConfig(level=logging.ERROR)


class OAuthHTTPRequestHandler(BaseHTTPRequestHandler):


    def log_message(self, format, *args):
        pass

    def do_GET(self):
        response = """Content-type: text/html

            <html>
            <head>
            <title>Authorization Complete</title>
            </head>

            <body>
            Authorization with OneNote Downloader complete. You can close this page.
            <br/><br/><br/>
            </body>
            </html>
            """
        self.send_response(200)
        self.end_headers()

        f = furl(self.path)

        code = ""

        if f.path == furl('/onenote_downloader'):
            code = f.args['code']
            self.server.set_code(code)

        self.send_response(200)
        self.send_header("Content-type", "text/html")

        response = re.sub("<code>", self.server.get_code(), response)

        self.wfile.write(str.encode(response))
