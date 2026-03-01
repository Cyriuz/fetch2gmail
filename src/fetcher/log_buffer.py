"""In-memory ring buffer of recent log records for UI."""

import logging
from collections import deque
from typing import Deque

# Keep last 500 lines
MAX_LINES = 500


class LogBufferHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._lines: Deque[str] = deque(maxlen=MAX_LINES)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._lines.append(msg)
        except Exception:  # noqa: BLE001
            pass

    def get_recent(self, n: int = 100) -> list[str]:
        return list(self._lines)[-n:]


_buffer_handler: LogBufferHandler | None = None


def install_log_buffer() -> LogBufferHandler:
    """Attach a buffer handler to the root logger; return it for reading."""
    global _buffer_handler
    if _buffer_handler is None:
        _buffer_handler = LogBufferHandler()
        _buffer_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logging.getLogger().addHandler(_buffer_handler)
    return _buffer_handler


def get_recent_logs(n: int = 100) -> list[str]:
    if _buffer_handler is None:
        install_log_buffer()
    return (_buffer_handler or install_log_buffer()).get_recent(n)
