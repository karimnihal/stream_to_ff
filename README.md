# Twitch Sync

Watch any Twitch stream in your browser, with adjustable stream and chat delay, to sync with another broadcast source (like TV).

- Lets you set and hold a fixed stream delay (Twitch’s player always drifts to live)
- Add a separate chat delay to match your video
- Runs Streamlink and a local Python proxy for browser playback; works in Firefox

Just what you need for easy manual sync with external feeds.

## Prerequisites

- [Streamlink](https://streamlink.github.io/)
- [ffmpeg](https://ffmpeg.org/)
- Python 3

## Usage

```bash
# 1. Start Streamlink (replace channel/quality as needed)
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/[channel] best

# 2. Start the proxy (second terminal, from this directory)
python3 serve.py

# 3. Open in browser
open http://127.0.0.1:8765/twitch-sync.html
```

Available stream qualities: audio_only, 160p (worst), 360p, 480p, 720p, 1080p (best). By default, "best" is used.

In the app:
- Click **Connect** to start the stream.
- Enter a channel name and click **Connect Chat**.
- Adjust **Stream delay** and **Chat delay** (0–120s) to sync with your other screen.
  - Note: When setting a stream delay, Streamlink must buffer at least as much video as your chosen delay time. For example, a 30s delay requires at least 30 seconds of stream to buffer before playback can start at that offset.
  - Setting a chat delay will cause a corresponding pause before new chat messages appear (for example, with a 30s chat delay, incoming chat will be held for 30 seconds before showing).
- **Sync both** sets chat delay equal to stream delay.
