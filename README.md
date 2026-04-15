# Twitch Sync

A single-file local webapp ([`twitch-sync.html`](twitch-sync.html)) for watching a Twitch stream from Streamlink with **adjustable video delay**, plus **delayed Twitch chat**, so you can line the stream up with another broadcast (for example, a TV feed) and match chat timing separately.

## Prerequisites

- [Streamlink](https://streamlink.github.io/) installed and available in your shell
- A modern desktop browser (Firefox is recommended for native Picture-in-Picture on the video)

## Quick start

### 1. Start the local HTTP stream

In a terminal, run Streamlink with external HTTP playback on port **8888**. Replace the channel with any live channel; this example uses [legendofwinning](https://www.twitch.tv/legendofwinning):

```bash
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/legendofwinning best
```

Leave this running. Streamlink prints the exact URLs; use the loopback one in the app (often `http://127.0.0.1:8888/` — a trailing slash is fine).

### 2. Open the app

- **Double-click** `twitch-sync.html`, or open it via **File → Open** in your browser, **or**
- Serve the folder with any static HTTP server and open the page (optional; either works).

### 3. Connect video and chat

1. In **Stream URL**, set the same URL Streamlink showed (prefer `http://127.0.0.1:8888` if `localhost` misbehaves) and click **Connect**.
2. In **Channel**, enter the chat channel name (for the example above: `legendofwinning`) and click **Connect Chat**.
3. Use **Stream delay** and **Chat delay** (0–120 seconds) to match your other screen. **Sync both** sets chat delay to match stream delay in one click.

### 4. Picture-in-Picture (Firefox)

Hover the video and use Firefox’s Picture-in-Picture control (typically bottom-right on the player) to float the stream over your other content.

## Files

| File | Purpose |
|------|---------|
| `twitch-sync.html` | Full app (HTML, CSS, and JS in one file) |
| `specs.md` | Original product specification |

## Notes

- No Twitch login or API keys are required; chat uses anonymous IRC access as documented in the app.

## If Streamlink says “Stream ended” right away

Your log shows Streamlink **did** find the channel, **did** accept a request from Firefox, and **started** the `1080p` HLS stream — then the Twitch side or the HLS pipeline stopped. That usually is **not** a bug in `twitch-sync.html`.

Try these in order:

1. **Confirm the channel is live** — open [legendofwinning](https://www.twitch.tv/legendofwinning) in a normal tab. If they are offline, hosting, or the stream died, Streamlink will end immediately.

2. **Smoke-test Streamlink without the HTTP server** — if this fails too, fix Streamlink/Twitch before the web app:
   ```bash
   streamlink twitch.tv/legendofwinning best
   ```
   (Uses your default player; proves the plugin and stream work.)

3. **Match the URL Streamlink prints** — use `http://127.0.0.1:8888` in the app if `http://localhost:8888` fails (some systems resolve `localhost` to IPv6 while Streamlink listens on IPv4, or the reverse).

4. **Update Streamlink** — older Twitch plugin behavior can break after API changes:
   ```bash
   pip install -U streamlink
   ```
   (Or upgrade however you installed it — Homebrew, etc.)

5. **Stale Twitch tokens** — if playback fails with integrity or API errors in the log, try purging the cached client-integrity token once, then retry:
   ```bash
   streamlink --twitch-purge-client-integrity twitch.tv/legendofwinning best
   ```
   (Then run your usual `--player-external-http` command again.)

6. **Try another quality** — e.g. `720p` instead of `best`, to rule out a bad run for one rendition.

7. **Open the app over HTTP** — if anything is odd with `file://` and media, serve this folder and open the page:
   ```bash
   python3 -m http.server 8765
   ```
   Then visit `http://127.0.0.1:8765/twitch-sync.html`.

If the plain `streamlink twitch.tv/... best` test plays reliably but `--player-external-http` still ends instantly, check [Streamlink issues](https://github.com/streamlink/streamlink/issues) for Twitch + external HTTP (known edge cases include playlist reload failures and ad-related segment handling).
