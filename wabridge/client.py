from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Union

import httpx

from .exceptions import ConnectionError, ValidationError, WABridgeError


class WABridge:
    """Sync client for WABridge - WhatsApp HTTP API.

    Usage:
        wa = WABridge()
        wa.send("Hello!")                              # send to self
        wa.send("919876543210", "Hello!")               # send to contact
        wa.send([("91...", "Hi"), ("91...", "Hey")])    # send to many
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

    def send(
        self,
        phone_or_message: Union[str, List[Tuple[str, str]]],
        message: str = None,
        max_workers: int = 5,
    ) -> Union[dict, List[dict]]:
        """Send a WhatsApp message.

        Usage:
            wa.send("Hello!")                                  # send to self
            wa.send("919876543210", "Hello!")                   # send to a number
            wa.send([("919876543210", "Hi"), ("91...", "Hey")]) # send to many in parallel

        Args:
            phone_or_message: A phone number (str), a message to self (str), or
                              a list of (phone, message) tuples for parallel sends.
            message: Text message (required when first arg is a phone number).
            max_workers: Max concurrent threads for parallel sends (default 5).

        Returns:
            dict for single sends, list of dicts for parallel sends.
        """
        # List of tuples -> parallel send
        if isinstance(phone_or_message, list):
            return self._send_many(phone_or_message, max_workers)

        # Single string, no message -> send to self
        if message is None:
            return self._send_self(phone_or_message)

        # Phone + message -> send to contact
        return self._send_to(phone_or_message, message)

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

    async def send(
        self,
        phone_or_message: Union[str, List[Tuple[str, str]]],
        message: str = None,
    ) -> Union[dict, List[dict]]:
        """Send a WhatsApp message.

        Usage:
            await wa.send("Hello!")                                  # send to self
            await wa.send("919876543210", "Hello!")                   # send to a number
            await wa.send([("919876543210", "Hi"), ("91...", "Hey")]) # send to many

        Args:
            phone_or_message: A phone number (str), a message to self (str), or
                              a list of (phone, message) tuples for parallel sends.
            message: Text message (required when first arg is a phone number).

        Returns:
            dict for single sends, list of dicts for parallel sends.
        """
        if isinstance(phone_or_message, list):
            return await self._send_many(phone_or_message)

        if message is None:
            return await self._send_self(phone_or_message)

        return await self._send_to(phone_or_message, message)

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
