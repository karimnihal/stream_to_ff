#!/usr/bin/env python3
"""Proxy: serves twitch-sync.html and remuxes Streamlink MPEG-TS to fMP4 via ffmpeg."""

import http.server
import subprocess
import sys
import os
import signal

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
        # ffmpeg reads MPEG-TS from Streamlink and outputs fragmented MP4 (browser-native)
        cmd = [
            "ffmpeg",
            "-i", STREAMLINK_URL,
            "-c:v", "copy",
            "-c:a", "aac",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-blocksize", "8192",
            "-flush_packets", "1",
            "pipe:1",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except FileNotFoundError:
            self.send_error(500, "ffmpeg not found — install it with: brew install ffmpeg")
            return
        except Exception as e:
            self.send_error(502, f"Cannot start ffmpeg: {e}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                chunk = proc.stdout.read(16384)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://127.0.0.1:{port}/twitch-sync.html")
    print(f"Stream proxy: http://127.0.0.1:{port}/stream (ffmpeg remux from {STREAMLINK_URL})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
