#!/usr/bin/env python3
"""Proxy: serves twitch-sync.html and remuxes Streamlink MPEG-TS to live HLS via ffmpeg.

HLS is required for iOS Safari (which rejects continuous fMP4 progressive). On other
browsers (Firefox / Chrome) the front-end uses hls.js to play the same playlist.
"""

from __future__ import annotations

import http.server
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

STREAMLINK_URL = "http://127.0.0.1:8888/"
PORT = 8765
DIR = os.path.dirname(os.path.abspath(__file__))

HLS_DIR = os.path.join(tempfile.gettempdir(), "twitch-sync-hls")
HLS_PLAYLIST = "playlist.m3u8"
HLS_SEGMENT_PATTERN = "seg-%05d.ts"
HLS_SEGMENT_RE = re.compile(r"^seg-\d+\.ts$")
HLS_TIME_SEC = 2
HLS_LIST_SIZE = 60  # 60 * 2s = 120s seekable window — matches the UI's max delay.
HLS_READY_TIMEOUT = 12.0  # how long the playlist endpoint waits for ffmpeg to write the m3u8

STDERR_TAIL_MAX = 8192
IDLE_KILL_SEC = 15.0  # HLS clients reconnect/poll; give them more headroom than fMP4 streaming.
WATCHDOG_INTERVAL_SEC = 2.0


class StreamHub:
    """One ffmpeg writes the HLS playlist; HTTP handlers serve files from HLS_DIR.

    Lifecycle: any GET to /stream/* refreshes `_last_access`; a watchdog kills ffmpeg
    after IDLE_KILL_SEC of no access. Restarted on the next request.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._stderr_lock = threading.Lock()
        self._stderr_tail = bytearray()
        self._last_access = 0.0
        self._watchdog_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        os.makedirs(HLS_DIR, exist_ok=True)

    def touch(self) -> None:
        self._last_access = time.monotonic()

    def _ffmpeg_cmd(self) -> list[str]:
        playlist_path = os.path.join(HLS_DIR, HLS_PLAYLIST)
        segment_path = os.path.join(HLS_DIR, HLS_SEGMENT_PATTERN)
        return [
            "ffmpeg",
            "-loglevel", "warning",
            "-fflags", "+genpts",
            "-avoid_negative_ts", "make_zero",
            "-i", STREAMLINK_URL,
            "-c:v", "copy",
            "-c:a", "aac",
            "-f", "hls",
            "-hls_time", str(HLS_TIME_SEC),
            "-hls_list_size", str(HLS_LIST_SIZE),
            "-hls_flags", "delete_segments+append_list+omit_endlist+independent_segments",
            "-hls_segment_type", "mpegts",
            "-hls_segment_filename", segment_path,
            playlist_path,
        ]

    def _purge_hls_dir(self) -> None:
        try:
            for name in os.listdir(HLS_DIR):
                if name == HLS_PLAYLIST or HLS_SEGMENT_RE.match(name):
                    try:
                        os.remove(os.path.join(HLS_DIR, name))
                    except OSError:
                        pass
        except FileNotFoundError:
            os.makedirs(HLS_DIR, exist_ok=True)

    def _kill_proc_unlocked(self) -> None:
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass
        self._log_ffmpeg_exit(proc)

    def _append_stderr(self, data: bytes) -> None:
        if not data:
            return
        with self._stderr_lock:
            self._stderr_tail.extend(data)
            if len(self._stderr_tail) > STDERR_TAIL_MAX:
                del self._stderr_tail[: len(self._stderr_tail) - STDERR_TAIL_MAX]

    def _stderr_drain_loop(self, pipe) -> None:
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    break
                self._append_stderr(chunk)
        except Exception:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def _log_ffmpeg_exit(self, proc: subprocess.Popen | None) -> None:
        if proc is None:
            return
        rc = proc.returncode
        with self._stderr_lock:
            text = bytes(self._stderr_tail).decode("utf-8", errors="replace").strip()
        clean_exit = rc in (0, None, -9)  # -9 is our own SIGKILL via watchdog
        if clean_exit and not text:
            return
        lines = text.splitlines() if text else []
        tail = "\n".join(lines[-25:]) if len(lines) > 25 else text
        suffix = f"\n{tail}" if tail else ""
        print(f"[ffmpeg] returncode={rc}{suffix}", file=sys.stderr, flush=True)

    def _ensure_watchdog(self) -> None:
        if self._watchdog_thread is not None and self._watchdog_thread.is_alive():
            return
        self._stop_event.clear()
        t = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread = t
        t.start()

    def _watchdog_loop(self) -> None:
        while not self._stop_event.wait(WATCHDOG_INTERVAL_SEC):
            with self._lock:
                if self._proc is None:
                    return
                if self._proc.poll() is not None:
                    self._kill_proc_unlocked()
                    return
                idle = time.monotonic() - self._last_access
                if idle >= IDLE_KILL_SEC:
                    self._kill_proc_unlocked()
                    return

    def _start_ffmpeg_locked(self) -> None:
        with self._stderr_lock:
            self._stderr_tail.clear()
        self._purge_hls_dir()
        cmd = self._ffmpeg_cmd()
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Cannot start ffmpeg: {e}") from e
        assert self._proc.stderr is not None
        threading.Thread(
            target=self._stderr_drain_loop,
            args=(self._proc.stderr,),
            daemon=True,
        ).start()
        self.touch()
        self._ensure_watchdog()

    def ensure_playlist_ready(self) -> str:
        """Start ffmpeg if needed and wait until the playlist file exists. Returns its path."""
        self.touch()
        playlist_path = os.path.join(HLS_DIR, HLS_PLAYLIST)
        with self._lock:
            running = self._proc is not None and self._proc.poll() is None
            if not running:
                self._start_ffmpeg_locked()
        deadline = time.monotonic() + HLS_READY_TIMEOUT
        while time.monotonic() < deadline:
            try:
                st = os.stat(playlist_path)
                if st.st_size > 0:
                    return playlist_path
            except FileNotFoundError:
                pass
            with self._lock:
                if self._proc is None or self._proc.poll() is not None:
                    raise RuntimeError("ffmpeg exited before producing a playlist")
            time.sleep(0.15)
        raise TimeoutError("playlist did not appear in time")

    def file_path(self, name: str) -> str | None:
        """Return absolute path for an HLS asset name, or None if invalid/missing."""
        if name == HLS_PLAYLIST or HLS_SEGMENT_RE.match(name):
            return os.path.join(HLS_DIR, name)
        return None


HUB = StreamHub()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def log_message(self, format, *args):  # quieter logs for HLS chatter
        if isinstance(args, tuple) and args and isinstance(args[0], str):
            msg = args[0]
            if "/stream/seg-" in msg or "/stream/playlist.m3u8" in msg:
                return
        super().log_message(format, *args)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/stream/") or self.path == "/stream":
            self._serve_hls()
        else:
            super().do_GET()

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")

    def _serve_hls(self):
        # /stream → /stream/playlist.m3u8 (back-compat; UI now requests the playlist directly)
        path = self.path
        if path == "/stream" or path == "/stream/":
            self.send_response(302)
            self.send_header("Location", f"/stream/{HLS_PLAYLIST}")
            self._send_cors()
            self.end_headers()
            return

        name = path[len("/stream/"):].split("?", 1)[0]
        local = HUB.file_path(name)
        if local is None:
            self.send_error(404, "Not found")
            return

        is_playlist = name == HLS_PLAYLIST
        if is_playlist:
            try:
                HUB.ensure_playlist_ready()
            except FileNotFoundError:
                self.send_error(500, "ffmpeg not found — install it with: brew install ffmpeg")
                return
            except TimeoutError:
                self.send_error(504, "Stream not ready yet — make sure Streamlink is running")
                return
            except Exception as e:
                self.send_error(502, str(e))
                return
        else:
            HUB.touch()

        try:
            with open(local, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            self.send_error(404, "Segment expired or not yet written")
            return

        if is_playlist:
            ctype = "application/vnd.apple.mpegurl"
        else:
            ctype = "video/mp2t"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._send_cors()
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://127.0.0.1:{port}/twitch-sync.html")
    print(f"HLS playlist: http://127.0.0.1:{port}/stream/{HLS_PLAYLIST} (ffmpeg HLS from {STREAMLINK_URL})")
    print(f"HLS cache dir: {HLS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        with HUB._lock:
            HUB._kill_proc_unlocked()
        try:
            shutil.rmtree(HLS_DIR, ignore_errors=True)
        except Exception:
            pass
