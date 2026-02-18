class WABridgeError(Exception):
    """Base exception for wabridge."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ConnectionError(WABridgeError):
    """WhatsApp is not connected."""


class ValidationError(WABridgeError):
    """Invalid request parameters."""
