# wabridge

Python client for [WABridge](https://github.com/marketcalls/wabridge) - send WhatsApp messages from Python via a simple REST API bridge.

## Prerequisites

**1. Install and link WhatsApp (one-time setup):**

```bash
npx wabridge
```

Scan the QR code with WhatsApp (Settings > Linked Devices > Link a Device). Auth is saved to `~/.wabridge/` — you only need to link once.

**2. Start the API server:**

```bash
npx wabridge start
```

Or on a custom port:

```bash
npx wabridge start 8080
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

One function. Three ways to use it.

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
        await wa.send([
            ("919876543210", "Alert 1"),
            ("919876543211", "Alert 2"),
        ])

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

| Usage | Description | Returns |
|-------|-------------|---------|
| `wa.send("Hello!")` | Send to yourself | `{"success": True, "to": "self"}` |
| `wa.send("919876543210", "Hello!")` | Send to a phone number | `{"success": True, "to": "919876543210"}` |
| `wa.send([("91...", "msg"), ...])` | Send to many in parallel | `[{"success": True, "to": "91..."}, ...]` |

Phone numbers must include the country code (e.g. `91` for India, `1` for US) followed by the number — digits only, no `+` or spaces.

#### Utility Methods

| Method | Description |
|--------|-------------|
| `wa.status()` | Returns `{"status": "open", "user": "91...@s.whatsapp.net"}` |
| `wa.is_connected()` | Returns `True` if WhatsApp is connected |
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
    print("WhatsApp is not connected. Run: npx wabridge start")
except ValidationError as e:
    print(f"Bad request: {e.message}")
```

## Use Cases

**Trading alerts:**
```python
wa = WABridge()
wa.send("BUY NIFTY 24000 CE @ 150")
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

**Cron job notifications:**
```python
wa = WABridge()
wa.send("Backup completed successfully")
```

## How It Works

This package is a thin Python wrapper over the [WABridge](https://github.com/marketcalls/wabridge) HTTP API. WABridge runs as a local Node.js server that connects to WhatsApp via the Baileys library. This Python client sends HTTP requests to that server using [httpx](https://www.python-httpx.org/).

```
Python App  -->  wabridge (Python)  -->  WABridge Server (Node.js)  -->  WhatsApp
```

## Requirements

- Python >= 3.8
- WABridge server running (`npx wabridge start`)
- Node.js >= 20.0.0 (for the WABridge server)

## License

[MIT](LICENSE)
