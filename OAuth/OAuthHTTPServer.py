from http.server import HTTPServer


class OAuthHTTPServer(HTTPServer):
    code = ''

    def get_code(self):
        return self.code

    def has_authorization_code(self):
        if self.code == "":
            return False
        else:
            return True

    def set_code(self, code):
        self.code = code
