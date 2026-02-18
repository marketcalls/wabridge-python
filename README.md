# wabridge

Python client for [WABridge](https://github.com/marketcalls/wabridge) - send WhatsApp messages from Python via a simple REST API bridge. Supports text, images, video, audio, documents — to individuals, groups, and channels.

## Prerequisites

**Node.js** (>= 20.0.0) must be installed on your system. Download it from [nodejs.org](https://nodejs.org/).

**1. Install WABridge globally:**

```bash
npm install -g wabridge
```

**2. Link WhatsApp (one-time setup):**

```bash
wabridge
```

Scan the QR code with WhatsApp (Settings > Linked Devices > Link a Device). Auth is saved to `~/.wabridge/` — you only need to link once.

**3. Start the API server:**

```bash
wabridge start
```

Or on a custom port:

```bash
wabridge start 8080
```

## Install

```bash
pip install wabridge
```

## Quick Start

```python
from wabridge import WABridge

wa = WABridge()

# Send to yourself
wa.send("Hello!")

# Send to a contact (phone number with country code)
wa.send("919876543210", "Hello!")

# Send to multiple contacts in parallel
wa.send([
    ("919876543210", "Alert 1"),
    ("919876543211", "Alert 2"),
    ("919876543212", "Alert 3"),
])
```

## Media Messages

```python
wa = WABridge()

# Image to self
wa.send(image="https://example.com/photo.jpg", caption="Check this out")

# Image to a contact
wa.send("919876543210", image="https://example.com/photo.jpg", caption="Hello!")

# Video
wa.send("919876543210", video="https://example.com/video.mp4", caption="Watch this")

# Voice note
wa.send("919876543210", audio="https://example.com/voice.ogg")

# Audio file (not voice note)
wa.send("919876543210", audio="https://example.com/song.mp3", ptt=False)

# Document
wa.send("919876543210", document="https://example.com/report.pdf", mimetype="application/pdf", filename="report.pdf")
```

## Groups

```python
wa = WABridge()

# List all groups
groups = wa.groups()
for g in groups:
    print(f"{g['subject']} - {g['id']}")

# Send text to group
wa.send_group("120363012345@g.us", "Hello group!")

# Send image to group
wa.send_group("120363012345@g.us", image="https://example.com/photo.jpg", caption="Check this")
```

## Channels

```python
wa = WABridge()

# Send text to channel
wa.send_channel("120363098765@newsletter", "Channel update!")

# Send image to channel
wa.send_channel("120363098765@newsletter", image="https://example.com/photo.jpg")
```

## Configuration

```python
# Default - connects to localhost:3000
wa = WABridge()

# Custom port
wa = WABridge(port=8080)

# Custom host and port (e.g. WABridge running on another machine)
wa = WABridge(host="192.168.1.100", port=4000)

# Custom timeout (default 30 seconds)
wa = WABridge(timeout=60.0)
```

## Async Support

```python
import asyncio
from wabridge import AsyncWABridge

async def main():
    async with AsyncWABridge() as wa:
        await wa.send("Hello!")
        await wa.send("919876543210", "Hello!")
        await wa.send("919876543210", image="https://example.com/photo.jpg")
        await wa.send_group("120363012345@g.us", "Hello group!")
        await wa.send_channel("120363098765@newsletter", "Update!")

asyncio.run(main())
```

## Context Manager

```python
# Sync
with WABridge() as wa:
    wa.send("Hello!")

# Async
async with AsyncWABridge() as wa:
    await wa.send("Hello!")
```

## API Reference

### `WABridge(host="localhost", port=3000, timeout=30.0)`

#### `wa.send(...)`

| Usage | Description |
|-------|-------------|
| `wa.send("Hello!")` | Text to self |
| `wa.send("919876543210", "Hello!")` | Text to a number |
| `wa.send([("91...", "msg"), ...])` | Text to many in parallel |
| `wa.send(image="https://...")` | Image to self |
| `wa.send("919876543210", image="https://...", caption="Hi")` | Image to a number |
| `wa.send("919876543210", video="https://...")` | Video to a number |
| `wa.send("919876543210", audio="https://...")` | Voice note to a number |
| `wa.send("919876543210", document="https://...", mimetype="application/pdf")` | Document to a number |

#### `wa.send_group(group_id, ...)`

| Usage | Description |
|-------|-------------|
| `wa.send_group("id@g.us", "Hello!")` | Text to group |
| `wa.send_group("id@g.us", image="https://...")` | Image to group |

#### `wa.send_channel(channel_id, ...)`

| Usage | Description |
|-------|-------------|
| `wa.send_channel("id@newsletter", "Update!")` | Text to channel |
| `wa.send_channel("id@newsletter", image="https://...")` | Image to channel |

#### Media Keyword Arguments

| Kwarg | Type | Description |
|-------|------|-------------|
| `image` | str (URL) | Image URL |
| `video` | str (URL) | Video URL |
| `audio` | str (URL) | Audio URL |
| `document` | str (URL) | Document URL |
| `caption` | str | Caption for image/video/document |
| `mimetype` | str | MIME type (required for document) |
| `filename` | str | File name for document |
| `ptt` | bool | True for voice note (default), False for audio file |

Phone numbers must include the country code (e.g. `91` for India, `1` for US) followed by the number — digits only, no `+` or spaces.

#### Utility Methods

| Method | Description |
|--------|-------------|
| `wa.status()` | Returns `{"status": "open", "user": "91...@s.whatsapp.net"}` |
| `wa.is_connected()` | Returns `True` if WhatsApp is connected |
| `wa.groups()` | Returns list of groups with `id`, `subject`, `size`, `desc` |
| `wa.close()` | Close the HTTP client |

### `AsyncWABridge(host="localhost", port=3000, timeout=30.0)`

Same methods as `WABridge`, but all are `async`. Supports `async with` context manager.

### Exceptions

| Exception | When |
|-----------|------|
| `WABridgeError` | Base exception for all errors |
| `ConnectionError` | WhatsApp is not connected (server returned 500) |
| `ValidationError` | Invalid phone number or missing fields (server returned 400) |

```python
from wabridge import WABridge, ConnectionError, ValidationError

wa = WABridge()

try:
    wa.send("919876543210", "Hello!")
except ConnectionError:
    print("WhatsApp is not connected. Run: wabridge start")
except ValidationError as e:
    print(f"Bad request: {e.message}")
```

## Use Cases

**Trading alerts:**
```python
wa = WABridge()
wa.send("BUY NIFTY 24000 CE @ 150")
```

**Send chart image:**
```python
wa = WABridge()
wa.send("919876543210", image="https://charts.example.com/nifty.png", caption="NIFTY Chart")
```

**Group notification:**
```python
wa = WABridge()
wa.send_group("120363012345@g.us", "Market closed. P&L: +5000")
```

**Server monitoring:**
```python
wa = WABridge()
if cpu_usage > 90:
    wa.send("919876543210", f"CPU at {cpu_usage}%")
```

**Broadcast to multiple numbers:**
```python
wa = WABridge()
numbers = ["919876543210", "919876543211", "919876543212"]
wa.send([(n, "Server maintenance at 10 PM") for n in numbers])
```

## How It Works

This package is a thin Python wrapper over the [WABridge](https://github.com/marketcalls/wabridge) HTTP API. WABridge runs as a local Node.js server that connects to WhatsApp via the Baileys library. This Python client sends HTTP requests to that server using [httpx](https://www.python-httpx.org/).

```
Python App  -->  wabridge (Python)  -->  WABridge Server (Node.js)  -->  WhatsApp
```

## Requirements

- [Node.js](https://nodejs.org/) >= 20.0.0 (required for the WABridge server)
- WABridge installed globally (`npm install -g wabridge`) and running (`wabridge start`)
- Python >= 3.8

## License

[MIT](LICENSE)
