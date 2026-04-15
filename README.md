# Twitch Sync

Watch a Twitch stream in your browser with adjustable delay, plus delayed chat — so you can sync it with another broadcast (e.g. a TV feed).

## Why

Streamlink grabs Twitch streams but outputs MPEG-TS, which browsers can't play natively. This project adds a thin proxy (`serve.py`) that remuxes to fragmented MP4 via ffmpeg, making it playable in a plain `<video>` tag. Chat connects over anonymous Twitch IRC — no API keys or login needed.

## Prerequisites

- [Streamlink](https://streamlink.github.io/)
- [ffmpeg](https://ffmpeg.org/)
- Python 3

## Usage

```bash
# 1. Start Streamlink (replace channel/quality as needed)
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/legendofwinning 720p

# 2. Start the proxy (second terminal, from this directory)
python3 serve.py

# 3. Open in browser
open http://127.0.0.1:8765/twitch-sync.html
```

In the app:
- Click **Connect** to start the stream
- Enter a channel name and click **Connect Chat**
- Adjust **Stream delay** and **Chat delay** (0–120s) to sync with your other screen
- **Sync both** sets chat delay = stream delay
