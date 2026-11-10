"""Unified logging facility for Dead Man's Vault with in-memory buffer for developer mode."""

import logging
from collections import deque
from pathlib import Path
from typing import List


class LogBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.buffer: deque = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.buffer.append(msg)

    def get_logs(self) -> List[str]:
        return list(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()


_LOG_BUFFER_HANDLER = LogBufferHandler()


def setup_logging(logs_dir: Path, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("DeadMansVault")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        _LOG_BUFFER_HANDLER.setFormatter(formatter)
        logger.addHandler(_LOG_BUFFER_HANDLER)

        log_file = logs_dir / "launcher.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        logger.addHandler(console_handler)

    return logger


def get_log_buffer() -> LogBufferHandler:
    return _LOG_BUFFER_HANDLER
