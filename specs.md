# Twitch Sync — specs

## What it does
Watch a Twitch stream in a browser with adjustable delay, alongside delayed Twitch chat. Use case: sync a Streamlink feed with a separate broadcast (e.g. TV).

## Architecture

```
Twitch CDN
   │ HLS
   ▼
Streamlink (--player-external-http, port 8888)
   │ MPEG-TS over HTTP
   ▼
serve.py (port 8765)
   │ ffmpeg remux: MPEG-TS → fragmented MP4
   │ + CORS headers + static file serving
   ▼
Browser (<video> plays fMP4 natively)
   + Twitch IRC chat via WebSocket (wss://irc-ws.chat.twitch.tv)
```

### Why the proxy exists
Browsers can't play raw MPEG-TS. Streamlink's HTTP server also doesn't send CORS headers, so JS-based decoders (mpegts.js) fail too. `serve.py` solves both: ffmpeg remuxes to fragmented MP4 (browser-native) and adds CORS headers.

### Why fragmented MP4
Regular MP4 needs the `moov` atom at the end of the file, which doesn't work for live streams. Fragmented MP4 (`-movflags frag_keyframe+empty_moov+default_base_moof`) writes the moov atom first (empty) and streams fragments as they arrive. Browsers play this natively with `<video src>`.

## Files

| File | Role |
|------|------|
| `twitch-sync.html` | Single-file app (HTML + CSS + JS) |
| `serve.py` | Python proxy — serves HTML, remuxes stream via ffmpeg |

## serve.py

- Serves static files from its own directory (for the HTML)
- `/stream` endpoint: spawns `ffmpeg -i http://127.0.0.1:8888/ -c:v copy -c:a aac -f mp4 ...` and pipes stdout to the HTTP response
- Video is copied (`-c:v copy`), audio is re-encoded to AAC (`-c:a aac`) for browser compat
- Kills ffmpeg subprocess when the client disconnects
- Default port: 8765

## twitch-sync.html

### Stream
- `<video>` element loads `/stream` (the proxy endpoint)
- Stream delay: pauses and seeks back from the live edge by N seconds
- Delay controls: slider (0.5s steps), number input (0.5s steps), nudge buttons, keyboard shortcuts (`[` / `]`)

### Chat
- Connects to Twitch IRC via anonymous WebSocket (`justinfanNNNNNNNN` nick, no auth needed)
- Parses PRIVMSG with IRCv3 tags for display name, color, badges (sub/mod)
- Messages are queued with timestamps; a 250ms interval timer releases them after the configured chat delay
- Auto-scrolls unless the user has scrolled up
- Max 200 messages in DOM; oldest removed on overflow
- Auto-reconnects with exponential backoff on disconnect

### Delay controls
- Stream delay and chat delay are independent (0–120s)
- "Sync both" sets chat delay = stream delay
- All delay values persist in localStorage

### Keyboard shortcuts
- `[` / `]` — stream delay ±0.5s
- `{` / `}` — chat delay ±0.5s

## Dependencies
- Streamlink (CLI)
- ffmpeg (CLI, called by serve.py)
- Python 3 (serve.py)
- No npm, no build step, no JS libraries
