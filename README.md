# Twitch Sync

A local webapp for watching a Twitch stream from Streamlink with **adjustable video delay** + **delayed Twitch chat**, so you can sync the stream with another broadcast (e.g. a TV feed).

## Prerequisites

- [Streamlink](https://streamlink.github.io/) installed
- Python 3 (for the CORS proxy)
- A modern desktop browser (Firefox recommended for PiP)

## Quick start

### 1. Start Streamlink

```bash
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/legendofwinning best
```

### 2. Start the proxy server

In a second terminal, from this directory:

```bash
python3 serve.py
```

This serves the app and proxies the stream with CORS headers (required for browser playback of MPEG-TS).

### 3. Open the app

Open **http://127.0.0.1:8765/twitch-sync.html** in your browser.

### 4. Connect video and chat

1. Stream URL defaults to `/stream` — just click **Connect**.
2. In **Channel**, enter the chat channel name (for the example above: `legendofwinning`) and click **Connect Chat**.
3. Use **Stream delay** and **Chat delay** (0–120 seconds) to match your other screen. Sliders move in **0.5 s** steps; use the number fields next to each slider for **0.1 s** precision. **Sync both** sets chat delay to match stream delay in one click.

### 5. Picture-in-Picture (Firefox)

Hover the video and use Firefox’s Picture-in-Picture control (typically bottom-right on the player) to float the stream over your other content.

## Files

| File | Purpose |
|------|---------|
| `twitch-sync.html` | Full app (HTML, CSS, and JS in one file) |
| `serve.py` | Local proxy — serves the app + proxies Streamlink stream with CORS headers |
| `specs.md` | Original product specification |

## Notes

- No Twitch login or API keys are required; chat uses anonymous IRC access as documented in the app.

## Troubleshooting

**”Stream ended” immediately after Connect:**

1. **Confirm the channel is live** — open the channel in a normal browser tab.
2. **Make sure you're using `serve.py`** — opening `twitch-sync.html` via `file://` won't work because the browser blocks CORS requests to Streamlink's HTTP server. You must use `python3 serve.py` and open `http://127.0.0.1:8765/twitch-sync.html`.
3. **Smoke-test Streamlink** without the HTTP server:
   ```bash
   streamlink twitch.tv/legendofwinning best
   ```
4. **Update Streamlink** — `pip install -U streamlink` or via Homebrew.
5. **Try another quality** — e.g. `720p` instead of `best`.
6. **Purge stale Twitch tokens**:
   ```bash
   streamlink --twitch-purge-client-integrity twitch.tv/legendofwinning best
   ```
