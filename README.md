# Twitch Sync

Watch any Twitch stream in your browser, with adjustable stream and chat delay, to sync with another broadcast source (like TV).

- Lets you set and hold a fixed stream delay (Twitch’s player always drifts to live)
- Add a separate chat delay to match your video
- Runs Streamlink and a local Python proxy that serves a **live HLS** stream — **Safari / iOS Safari** use native HLS; **Firefox / Chrome** use [hls.js](https://github.com/video-dev/hls.js/) (loaded from a CDN in the page)

Just what you need for easy manual sync with external feeds.

## Prerequisites

- [Streamlink](https://streamlink.github.io/)
- [ffmpeg](https://ffmpeg.org/)
- Python 3
- A network connection for the CDN script (hls.js) on non-Safari browsers; Safari/iPad can play without it

## Usage — start the backend (always on the Mac)

Run Streamlink and the proxy in **two terminals** from this repo:

```bash
# Terminal 1 — replace channel and quality as needed
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/[channel] best

# Terminal 2
python3 serve.py
```

Available stream qualities: `audio_only`, `160p` (worst), `360p`, `480p`, `720p`, `1080p` (`best`). Default in docs is `best`.

---

## Open the app — local vs another device

Everything heavy (**Streamlink**, **ffmpeg**, **`serve.py`**) runs on the **Mac**. The phone/tablet/PC browser is only a **client**.

### On the same machine (local)

Open:

```text
http://127.0.0.1:8765/twitch-sync.html
```

On macOS you can run:

```bash
open http://127.0.0.1:8765/twitch-sync.html
```

### On another device (iPad, phone, laptop on the same Wi‑Fi)

1. Find the Mac’s **LAN IP** (Terminal on the Mac):

   ```bash
   # Wi‑Fi (most Macs)
   ipconfig getifaddr en0

   # Ethernet, if en0 is empty
   ipconfig getifaddr en1
   ```

2. On the **other device**, open (replace the IP with yours):

   ```text
   http://192.168.1.50:8765/twitch-sync.html
   ```

3. **Firewall**: the first time another device connects, macOS may prompt to allow **incoming** connections for **Python**. Allow it, or add a rule in **System Settings → Network → Firewall → Options**, or testing will fail even though `127.0.0.1` works on the Mac.

4. **Same network**: the Mac and the other device must be on the same LAN/VLAN (guest Wi‑Fi often blocks device-to-device traffic).

You do **not** run Streamlink or `serve.py` on the iPad — only open that URL.

---

## In the app

- Click **Connect** to start the stream (required for autoplay rules on mobile).
- Enter a channel name and click **Connect Chat**.
- Adjust **Stream delay** and **Chat delay** (0–120s) to sync with your other screen.
  - When setting a stream delay, the HLS buffer must cover at least that much time behind the live edge (the server keeps about **120s** of sliding window). If you ask for more delay than is buffered, wait for more buffer or lower the delay.
  - Chat delay holds messages before they appear (e.g. 30s chat delay → messages show 30s after receipt).
- **Sync both** sets chat delay equal to stream delay.
