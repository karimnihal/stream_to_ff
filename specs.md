# Twitch Sync — specs

## What it does

Watch a Twitch stream in a browser with adjustable **stream** and **chat** delay. Use case: sync a Streamlink feed with another screen (for example, a TV broadcast).

## Architecture

```text
Twitch CDN
   │ HLS
   ▼
Streamlink (--player-external-http, port 8888)
   │ MPEG-TS over HTTP (single consumer: localhost only)
   ▼
serve.py (ThreadingHTTPServer, port 8765, bind 0.0.0.0)
   │ ffmpeg: MPEG-TS → live HLS (playlist + rolling TS segments on disk)
   │ GET /stream/* reads files; CORS on responses
   ▼
Browser
   │ Safari / iOS: native HLS on <video> (application/vnd.apple.mpegurl)
   │ Firefox / Chrome: hls.js (MSE) loads same playlist URL
   ▼
Twitch IRC chat: WebSocket wss://irc-ws.chat.twitch.tv (anonymous justinfan*)
```

### Why the proxy exists

- Browsers do not play raw MPEG-TS from Streamlink’s HTTP output.
- Streamlink’s external HTTP player does not add CORS headers, which blocks in-browser tooling if you ever needed them.
- **iOS Safari** does not support continuous **fragmented MP4** progressive playback for this live use case; it expects **HLS** for live video. The stack therefore remuxes to **HLS** and serves `playlist.m3u8` plus segment files.

### Why HLS (not fMP4 pipe)

- **Safari / iPad**: native `<video src="/stream/playlist.m3u8">`.
- **Firefox / Chrome**: same URL via **hls.js** (loaded from jsDelivr in `twitch-sync.html`).
- ffmpeg writes a **sliding window** playlist (`hls_list_size` × `hls_time` ≈ **120 s** of media listed) so the UI can seek backward for stream delay (0–120 s) without an unbounded disk cache. Old segments are deleted (`delete_segments`).

### Streamlink single-reader constraint

`--player-external-http` effectively serves **one** MPEG-TS reader. Only **one** ffmpeg process may read `http://127.0.0.1:8888/` at a time. Multiple browser tabs/devices all hit the **same** HLS playlist and segments; they do not open additional Streamlink connections.

## Files

| File | Role |
|------|------|
| `twitch-sync.html` | Single-file app (HTML + CSS + JS); optional hls.js from CDN |
| `serve.py` | Python server: static files + HLS file serving + ffmpeg lifecycle |
| `README.md` | How to run locally vs on another device |

## serve.py

- **Static files**: serves the repo directory (includes `twitch-sync.html`).
- **HLS output directory**: `tempfile.gettempdir()/twitch-sync-hls/` (e.g. `/tmp/twitch-sync-hls` on macOS). Purged when a new ffmpeg run starts.
- **ffmpeg** (one process while stream is “hot”):
  - Input: `http://127.0.0.1:8888/` (Streamlink).
  - Output: `-f hls` with `playlist.m3u8`, `seg-%05d.ts`, `hls_time` 2 s, `hls_list_size` 60, flags `delete_segments+append_list+omit_endlist+independent_segments`.
  - Video: `-c:v copy`. Audio: `-c:a aac` (re-encode for MP4/HLS compatibility).
  - Demuxer hardening: `-fflags +genpts`, `-avoid_negative_ts make_zero`.
- **HTTP routes**:
  - `GET /stream` → `302` → `/stream/playlist.m3u8`.
  - `GET /stream/playlist.m3u8`: starts ffmpeg if needed; waits up to `HLS_READY_TIMEOUT` for a non-empty playlist; returns `application/vnd.apple.mpegurl`.
  - `GET /stream/seg-NNNNN.ts`: returns `video/mp2t` (404 if segment rotated away).
- **Lifecycle / idle**: any `/stream/*` request calls `touch()`. A watchdog thread stops ffmpeg after `IDLE_KILL_SEC` with no access (HLS clients poll; interval must exceed worst-case gap).
- **stderr**: last ~8 KB retained; on ffmpeg exit, a short tail may print to stderr for debugging.
- **Port**: `8765` (override: `python3 serve.py <port>`).
- **Shutdown**: Ctrl+C attempts to kill ffmpeg and remove the HLS cache directory.

## twitch-sync.html

### Stream

- **URL**: `/stream/playlist.m3u8` (not `/stream` raw bytes).
- **Playback**: if `canPlayType` reports HLS support (Safari / iOS), set `video.src` to the playlist. Otherwise construct **hls.js**, `loadSource`, `attachMedia`, destroy on reconnect.
- **Connect flow**: user gesture on **Connect**; defers `video.play()` until `loadeddata` / `canplay` with retries (iOS is strict); does not treat every `play()` rejection as “stream missing”.
- **Stream delay**: seeks backward from the buffered live edge (HLS exposes enough buffer for the configured window).
- **Controls**: slider (0.5 s steps), number input, nudge buttons, `[` / `]` keyboard shortcuts.

### Chat

- Twitch IRC over WebSocket (`wss://irc-ws.chat.twitch.tv:443`), anonymous `justinfan` nick, `CAP REQ` tags/commands, `JOIN #channel`.
- PRIVMSG parsed with IRCv3 tags (display name, color, badges sub/mod).
- Messages queued with timestamps; 250 ms tick applies chat delay before render.
- Auto-scroll when near bottom; max 200 DOM rows; exponential backoff reconnect.

### Persistence

- Channel name, stream delay, chat delay: `localStorage`.

### Keyboard shortcuts

- `[` / `]` — stream delay ±0.5 s  
- `{` / `}` — chat delay ±0.5 s  

## Dependencies

| Component | Notes |
|-----------|--------|
| Streamlink | CLI; must expose HTTP on `127.0.0.1:8888` as in README |
| ffmpeg | CLI; invoked by `serve.py` |
| Python 3 | `http.server.ThreadingHTTPServer` |
| hls.js | Loaded from CDN in HTML; only used where native HLS is unavailable |

No npm, no bundler, no project `package.json`.
