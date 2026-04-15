# Twitch Sync Webapp

## Overview

Build a self-contained local webapp for syncing a Twitch stream with a live sports broadcast. The user runs a local HTTP stream via streamlink (piped from Twitch), opens this app in Firefox, and uses Firefox's native Picture-in-Picture to float the video while watching the game. The app provides independent delay controls for both the video stream and chat, allowing the user to manually match game clocks between the two broadcasts.

---

## Problem Being Solved

Twitch's web player aggressively re-syncs to live when paused. This makes it impossible to hold a delayed position in the stream to match an external broadcast (e.g., a cable TV game feed). Additionally, Twitch chat has no viewer-side delay feature. This app solves both problems by:

1. Playing the stream via a `<video>` tag fed by a local streamlink HTTP server (pause-safe, no re-sync)
2. Consuming Twitch chat directly via IRC WebSocket and buffering messages with an adjustable delay
3. Providing separate delay sliders for video and chat independently

---

## Tech Stack

- **Single HTML file** — no build step, no framework, no dependencies beyond browser APIs
- Opens directly in Firefox (or any modern browser)
- All logic in vanilla JS
- Twitch IRC via native browser WebSocket API
- No backend required beyond the streamlink local HTTP server the user runs separately

---

## User Setup (document in the app's UI)

Before opening the app, the user runs:

```bash
streamlink --player-external-http --player-external-http-port 8888 twitch.tv/CHANNEL_NAME best
```

This serves the stream at `http://localhost:8888`. The app connects to this URL in its `<video>` tag.

---

## Layout

Two-column layout, full viewport height:

```
┌─────────────────────────────┬──────────────────┐
│                             │  Chat header      │
│       Video Player          │  [messages...]    │
│       (left, ~70% width)    │                   │
│                             │  (right, ~30%)    │
├─────────────────────────────┴──────────────────┤
│  Controls bar (full width, bottom)              │
└─────────────────────────────────────────────────┘
```

### Video pane (left)
- `<video>` element, fills the pane, `controls` attribute enabled
- Native browser controls so Firefox PiP button appears on hover
- Stream URL input field (pre-filled with `http://localhost:8888`)
- "Connect" button to load/reload stream
- Video delay slider (0–120 seconds, default 0)
- Video delay numeric display (e.g., "▶ +34s delay")

### Chat pane (right)
- Channel name input field
- "Connect Chat" button
- Scrolling message list, auto-scrolls to bottom
- Each message shows: colored username, message text, optional badges (subscriber, mod icons as simple colored dots)
- Chat delay slider (0–120 seconds, default 0)
- Chat delay numeric display (e.g., "💬 +34s delay")
- Connection status indicator (connecting / connected / disconnected)

### Controls bar (bottom strip)
- Both sliders visible side-by-side for quick adjustment
- "Sync both" button: sets chat delay to match video delay with one click
- Current delay values shown numerically next to each slider
- Small label: "Stream delay" | "Chat delay"

---

## Video Delay Logic

The `<video>` element connects to the local streamlink HTTP server. Since it's a direct video element (not the Twitch embed), pausing does not trigger re-sync — this is the core benefit.

To implement a delay offset:

- When the user sets a video delay of N seconds, implement this by seeking the video back N seconds from its current buffered position after the stream loads
- Use the `<video>` element's `buffered` property to determine how much content is available
- Provide a "buffer" loading indicator — the app should wait until enough buffer is available before applying the delay
- If the user increases delay while watching, pause, seek back, then resume
- Display a warning if the requested delay exceeds available buffer

**Important:** The goal is a stable delayed position, not a real-time sync algorithm. Keep it simple — manual adjustment by the user is fine and expected.

---

## Chat Delay Logic

- Connect to Twitch IRC anonymously via WebSocket:
  - URL: `wss://irc-ws.chat.twitch.tv:443`
  - Send: `PASS SCHMOOPIIE` (anonymous)
  - Send: `NICK justinfan12345` (anonymous justinfan account, no auth needed)
  - Send: `CAP REQ :twitch.tv/tags twitch.tv/commands` (for metadata like colors, badges)
  - Send: `JOIN #channelname`
- Parse incoming `PRIVMSG` lines for: username, message text, display color (from tags), badge info
- Store each message in a buffer array as: `{ timestamp: Date.now(), username, color, text, badges }`
- A `setInterval` loop (every ~250ms) checks the buffer and renders messages where `(Date.now() - timestamp) >= chatDelayMs`
- Changing the delay slider immediately takes effect — messages already in the buffer either appear sooner or stay hidden longer

### Chat message rendering
- Render as a scrolling div
- Username in their Twitch color (default to a readable hue if none provided)
- Message text in normal body color
- Simple badge dots: gold dot for subscriber, green dot for mod — no images needed
- Max ~200 messages visible before trimming oldest
- Auto-scroll to bottom unless user has manually scrolled up (detect scroll position)

---

## Delay Sliders — Specification

Both sliders:
- Range: 0 to 120 seconds
- Step: 1 second
- Default: 0
- Real-time display of value in seconds next to slider
- Slider label: "Stream delay" and "Chat delay"
- Visually distinct (different accent colors — e.g., blue for stream, purple for chat)

"Sync Both" button sets chat delay = stream delay instantly.

---

## Connection States & Error Handling

### Video
- If `http://localhost:8888` is unreachable, show a friendly error: "Stream not found. Make sure streamlink is running."
- Include the exact streamlink command the user should run, copyable
- Show a reconnect button

### Chat
- If WebSocket fails to connect, show "Chat disconnected — retrying..." and attempt reconnect with backoff
- If the channel name is invalid or has no chat activity, show a "Waiting for messages..." placeholder

---

## Style & Visual Design

- Dark theme only (appropriate for watching streams)
- Background: near-black (`#0e0e10` — Twitch-style)
- Chat pane: slightly lighter card surface
- Accent colors: blue for stream controls, purple for chat controls
- Clean, minimal — no decorative elements
- Readable at browser zoom levels (don't use tiny font sizes)
- Video pane should be as large as possible to make Firefox's PiP button easy to hit

---

## Firefox PiP Note (document in UI)

Include a small tooltip or help text near the video:

> "Hover over the video to reveal Firefox's Picture-in-Picture button (bottom-right corner), then pop it out to float the stream over your game broadcast."

---

## Stretch Goals (implement if straightforward, skip if complex)

- Emote rendering: replace known Twitch emote names in messages with their text representation (no image fetching needed — just preserve the text)
- Keyboard shortcut: `[` and `]` to decrease/increase stream delay by 1s, `{` and `}` for chat delay
- A "nudge" button (+1s / -1s) next to each slider for fine-tuning without dragging
- Save channel name and last-used delay values to `localStorage`

---

## What NOT to Build

- No Twitch OAuth, no API keys, no login
- No stream recording or downloading
- No multi-stream support
- No mobile layout (desktop only)
- No Electron wrapper — plain HTML file that runs in a browser

---

## Deliverable

A single `twitch-sync.html` file the user can download and open in Firefox. All CSS and JS inline. No external dependencies or CDN links required (use only browser-native APIs). Should work by double-clicking the file or serving it via any local HTTP server.