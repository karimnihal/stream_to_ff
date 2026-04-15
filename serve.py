#!/usr/bin/env python3
"""Tiny proxy: serves twitch-sync.html and proxies /stream to Streamlink with CORS."""

import http.server
import urllib.request
import sys
import os

STREAMLINK_URL = "http://127.0.0.1:8888/"
PORT = 8765
DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/stream"):
            self._proxy_stream()
        else:
            super().do_GET()

    def _proxy_stream(self):
        try:
            req = urllib.request.urlopen(STREAMLINK_URL)
        except Exception as e:
            self.send_error(502, f"Cannot reach Streamlink: {e}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp2t")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                chunk = req.read(16384)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            req.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://127.0.0.1:{port}/twitch-sync.html")
    print(f"Stream proxy: http://127.0.0.1:{port}/stream -> {STREAMLINK_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
