from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Union

import httpx

from .exceptions import ConnectionError, ValidationError, WABridgeError


class WABridge:
    """Sync client for WABridge - WhatsApp HTTP API.

    Usage:
        wa = WABridge()
        wa.send("Hello!")                              # send to self
        wa.send("919876543210", "Hello!")               # send to contact
        wa.send([("91...", "Hi"), ("91...", "Hey")])    # send to many

        # Groups & Channels
        wa.send_group("120363012345@g.us", "Hello group!")
        wa.send_channel("120363098765@newsletter", "Update!")

        # Media
        wa.send("919876543210", image="https://example.com/photo.jpg", caption="Check this")
        wa.send(image="https://example.com/photo.jpg")   # image to self
    """

    def __init__(self, host: str = "localhost", port: int = 3000, timeout: float = 30.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code == 200:
            return
        data = response.json()
        error = data.get("error", "Unknown error")
        if response.status_code == 500:
            raise ConnectionError(error, status_code=500)
        if response.status_code == 400:
            raise ValidationError(error, status_code=400)
        raise WABridgeError(error, status_code=response.status_code)

    def _build_content(
        self,
        message: Optional[str] = None,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Build content payload from media/text kwargs."""
        payload: dict = {}
        if image:
            payload["image"] = image
            if caption:
                payload["caption"] = caption
        elif video:
            payload["video"] = video
            if caption:
                payload["caption"] = caption
        elif audio:
            payload["audio"] = audio
            if ptt is not None:
                payload["ptt"] = ptt
        elif document:
            payload["document"] = document
            if mimetype:
                payload["mimetype"] = mimetype
            if filename:
                payload["fileName"] = filename
            if caption:
                payload["caption"] = caption
        elif message:
            payload["message"] = message
        return payload

    def status(self) -> dict:
        """Check WhatsApp connection status.

        Returns:
            dict with 'status' ('connecting', 'open', 'disconnected')
            and 'user' (JID string or None).
        """
        r = self._client.get("/status")
        self._handle_error(r)
        return r.json()

    def is_connected(self) -> bool:
        """Check if WhatsApp is connected and ready."""
        try:
            return self.status().get("status") == "open"
        except Exception:
            return False

    def groups(self) -> list:
        """List all WhatsApp groups.

        Returns:
            List of dicts with 'id', 'subject', 'size', 'desc'.
        """
        r = self._client.get("/groups")
        self._handle_error(r)
        return r.json().get("groups", [])

    def send(
        self,
        phone_or_message: Union[str, List[Tuple[str, str]]] = None,
        message: Optional[str] = None,
        max_workers: int = 5,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> Union[dict, List[dict]]:
        """Send a WhatsApp message.

        Usage:
            wa.send("Hello!")                                  # text to self
            wa.send("919876543210", "Hello!")                   # text to a number
            wa.send([("919876543210", "Hi"), ("91...", "Hey")]) # text to many

            # Media to self
            wa.send(image="https://example.com/photo.jpg", caption="Nice!")
            wa.send(video="https://example.com/video.mp4")
            wa.send(audio="https://example.com/voice.ogg")

            # Media to a contact
            wa.send("919876543210", image="https://example.com/photo.jpg", caption="Check this")
            wa.send("919876543210", video="https://example.com/video.mp4")
            wa.send("919876543210", document="https://example.com/file.pdf", mimetype="application/pdf")

        Args:
            phone_or_message: A phone number (str), a message to self (str), or
                              a list of (phone, message) tuples for parallel sends.
            message: Text message (required when first arg is a phone number and no media).
            max_workers: Max concurrent threads for parallel sends (default 5).
            image: URL of image to send.
            video: URL of video to send.
            audio: URL of audio to send.
            document: URL of document to send.
            caption: Caption for image/video/document.
            mimetype: MIME type (required for document).
            filename: File name for document.
            ptt: True for voice note (default), False for audio file.

        Returns:
            dict for single sends, list of dicts for parallel sends.
        """
        has_media = any([image, video, audio, document])

        # List of tuples -> parallel send (text only)
        if isinstance(phone_or_message, list):
            return self._send_many(phone_or_message, max_workers)

        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)

        # No first arg -> send to self (media or text must be in kwargs)
        if phone_or_message is None:
            r = self._client.post("/send/self", json=content)
            self._handle_error(r)
            return r.json()

        # Has media -> first arg is phone number
        if has_media:
            payload = {"phone": phone_or_message, **content}
            r = self._client.post("/send", json=payload)
            self._handle_error(r)
            return r.json()

        # Single string, no message -> send to self
        if message is None:
            return self._send_self(phone_or_message)

        # Phone + message -> send to contact
        return self._send_to(phone_or_message, message)

    def send_group(
        self,
        group_id: str,
        message: Optional[str] = None,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Send a message to a WhatsApp group.

        Args:
            group_id: Group JID (e.g. '120363012345@g.us'). Use wa.groups() to list.
            message: Text message.
            image/video/audio/document: URL of media to send.
            caption: Caption for image/video/document.
            mimetype: MIME type (required for document).
            filename: File name for document.
            ptt: True for voice note, False for audio file.
        """
        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)
        payload = {"groupId": group_id, **content}
        r = self._client.post("/send/group", json=payload)
        self._handle_error(r)
        return r.json()

    def send_channel(
        self,
        channel_id: str,
        message: Optional[str] = None,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Send a message to a WhatsApp channel/newsletter.

        Args:
            channel_id: Channel JID (e.g. '120363098765@newsletter').
            message: Text message.
            image/video/audio/document: URL of media to send.
            caption: Caption for image/video/document.
            mimetype: MIME type (required for document).
            filename: File name for document.
            ptt: True for voice note, False for audio file.
        """
        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)
        payload = {"channelId": channel_id, **content}
        r = self._client.post("/send/channel", json=payload)
        self._handle_error(r)
        return r.json()

    def _send_to(self, phone: str, message: str) -> dict:
        r = self._client.post("/send", json={"phone": phone, "message": message})
        self._handle_error(r)
        return r.json()

    def _send_self(self, message: str) -> dict:
        r = self._client.post("/send/self", json={"message": message})
        self._handle_error(r)
        return r.json()

    def _send_many(self, messages: List[Tuple[str, str]], max_workers: int = 5) -> List[dict]:
        results = [None] * len(messages)

        def _do_send(index: int, phone: str, msg: str):
            try:
                r = httpx.post(
                    f"{self.base_url}/send",
                    json={"phone": phone, "message": msg},
                    timeout=self.timeout,
                )
                if r.status_code == 200:
                    return index, r.json()
                data = r.json()
                return index, {"success": False, "error": data.get("error", "Unknown error"), "to": phone}
            except Exception as e:
                return index, {"success": False, "error": str(e), "to": phone}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_do_send, i, phone, msg) for i, (phone, msg) in enumerate(messages)]
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        return results

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncWABridge:
    """Async client for WABridge - WhatsApp HTTP API.

    Usage:
        async with AsyncWABridge() as wa:
            await wa.send("Hello!")                              # send to self
            await wa.send("919876543210", "Hello!")               # send to contact
            await wa.send([("91...", "Hi"), ("91...", "Hey")])    # send to many

            # Groups & Channels
            await wa.send_group("120363012345@g.us", "Hello group!")
            await wa.send_channel("120363098765@newsletter", "Update!")

            # Media
            await wa.send("919876543210", image="https://example.com/photo.jpg")
    """

    def __init__(self, host: str = "localhost", port: int = 3000, timeout: float = 30.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code == 200:
            return
        data = response.json()
        error = data.get("error", "Unknown error")
        if response.status_code == 500:
            raise ConnectionError(error, status_code=500)
        if response.status_code == 400:
            raise ValidationError(error, status_code=400)
        raise WABridgeError(error, status_code=response.status_code)

    def _build_content(
        self,
        message: Optional[str] = None,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Build content payload from media/text kwargs."""
        payload: dict = {}
        if image:
            payload["image"] = image
            if caption:
                payload["caption"] = caption
        elif video:
            payload["video"] = video
            if caption:
                payload["caption"] = caption
        elif audio:
            payload["audio"] = audio
            if ptt is not None:
                payload["ptt"] = ptt
        elif document:
            payload["document"] = document
            if mimetype:
                payload["mimetype"] = mimetype
            if filename:
                payload["fileName"] = filename
            if caption:
                payload["caption"] = caption
        elif message:
            payload["message"] = message
        return payload

    async def status(self) -> dict:
        """Check WhatsApp connection status."""
        r = await self._client.get("/status")
        self._handle_error(r)
        return r.json()

    async def is_connected(self) -> bool:
        """Check if WhatsApp is connected and ready."""
        try:
            s = await self.status()
            return s.get("status") == "open"
        except Exception:
            return False

    async def groups(self) -> list:
        """List all WhatsApp groups."""
        r = await self._client.get("/groups")
        self._handle_error(r)
        return r.json().get("groups", [])

    async def send(
        self,
        phone_or_message: Union[str, List[Tuple[str, str]]] = None,
        message: Optional[str] = None,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> Union[dict, List[dict]]:
        """Send a WhatsApp message.

        Usage:
            await wa.send("Hello!")                                  # text to self
            await wa.send("919876543210", "Hello!")                   # text to a number
            await wa.send([("919876543210", "Hi"), ("91...", "Hey")]) # text to many

            # Media
            await wa.send(image="https://example.com/photo.jpg")
            await wa.send("919876543210", image="https://example.com/photo.jpg", caption="Check this")
        """
        has_media = any([image, video, audio, document])

        if isinstance(phone_or_message, list):
            return await self._send_many(phone_or_message)

        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)

        if phone_or_message is None:
            r = await self._client.post("/send/self", json=content)
            self._handle_error(r)
            return r.json()

        if has_media:
            payload = {"phone": phone_or_message, **content}
            r = await self._client.post("/send", json=payload)
            self._handle_error(r)
            return r.json()

        if message is None:
            return await self._send_self(phone_or_message)

        return await self._send_to(phone_or_message, message)

    async def send_group(
        self,
        group_id: str,
        message: Optional[str] = None,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Send a message to a WhatsApp group."""
        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)
        payload = {"groupId": group_id, **content}
        r = await self._client.post("/send/group", json=payload)
        self._handle_error(r)
        return r.json()

    async def send_channel(
        self,
        channel_id: str,
        message: Optional[str] = None,
        *,
        image: Optional[str] = None,
        video: Optional[str] = None,
        audio: Optional[str] = None,
        document: Optional[str] = None,
        caption: Optional[str] = None,
        mimetype: Optional[str] = None,
        filename: Optional[str] = None,
        ptt: Optional[bool] = None,
    ) -> dict:
        """Send a message to a WhatsApp channel/newsletter."""
        content = self._build_content(message, image, video, audio, document, caption, mimetype, filename, ptt)
        payload = {"channelId": channel_id, **content}
        r = await self._client.post("/send/channel", json=payload)
        self._handle_error(r)
        return r.json()

    async def _send_to(self, phone: str, message: str) -> dict:
        r = await self._client.post("/send", json={"phone": phone, "message": message})
        self._handle_error(r)
        return r.json()

    async def _send_self(self, message: str) -> dict:
        r = await self._client.post("/send/self", json={"message": message})
        self._handle_error(r)
        return r.json()

    async def _send_many(self, messages: List[Tuple[str, str]]) -> List[dict]:
        async def _do_send(phone: str, msg: str) -> dict:
            try:
                r = await self._client.post("/send", json={"phone": phone, "message": msg})
                if r.status_code == 200:
                    return r.json()
                data = r.json()
                return {"success": False, "error": data.get("error", "Unknown error"), "to": phone}
            except Exception as e:
                return {"success": False, "error": str(e), "to": phone}

        return await asyncio.gather(*[_do_send(phone, msg) for phone, msg in messages])

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
