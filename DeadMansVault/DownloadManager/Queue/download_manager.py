"""Asynchronous, multi-threaded download manager with speed tracking, retry, and cancellation."""

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

logger = logging.getLogger("DeadMansVault.DownloadManager")


class DownloadStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    task_id: str
    url: str
    destination: Path
    bytes_downloaded: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    status: DownloadStatus = DownloadStatus.QUEUED
    error_message: str = ""

    @property
    def progress_fraction(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(1.0, max(0.0, self.bytes_downloaded / self.total_bytes))

    @property
    def progress_percentage(self) -> float:
        return self.progress_fraction * 100.0


class DownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        destination: Path,
        expected_sha256: Optional[str] = None,
        chunk_size: int = 65536,
        retry_limit: int = 3,
        callback: Optional[Callable[[DownloadProgress], None]] = None,
        session: Optional[requests.Session] = None,
    ):
        self.task_id = task_id
        self.url = url
        self.destination = Path(destination)
        self.expected_sha256 = expected_sha256
        self.chunk_size = chunk_size
        self.retry_limit = retry_limit
        self.callback = callback
        self.session = session or requests.Session()

        self._cancelled = threading.Event()
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.progress = DownloadProgress(
            task_id=task_id,
            url=url,
            destination=self.destination,
        )

    def cancel(self) -> None:
        self._cancelled.set()
        self.progress.status = DownloadStatus.CANCELLED
        self._notify()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _notify(self) -> None:
        if self.callback:
            try:
                self.callback(self.progress)
            except Exception as e:
                logger.error(f"Error in download progress callback: {e}")

    def _run(self) -> None:
        self.progress.status = DownloadStatus.DOWNLOADING
        self._notify()

        self.destination.parent.mkdir(parents=True, exist_ok=True)
        part_file = self.destination.with_suffix(self.destination.suffix + ".part")

        attempt = 0
        while attempt <= self.retry_limit and not self._cancelled.is_set():
            attempt += 1
            try:
                headers = {}
                existing_bytes = 0
                if part_file.exists():
                    existing_bytes = part_file.stat().st_size
                    if existing_bytes > 0:
                        headers["Range"] = f"bytes={existing_bytes}-"

                resp = self.session.get(self.url, headers=headers, stream=True, timeout=15)

                if resp.status_code == 416:
                    total = existing_bytes
                    mode = "ab"
                elif resp.status_code == 206:
                    content_range = resp.headers.get("Content-Range", "")
                    if "/" in content_range:
                        total = int(content_range.split("/")[-1])
                    else:
                        total = existing_bytes + int(resp.headers.get("Content-Length", 0))
                    mode = "ab"
                elif resp.status_code == 200:
                    existing_bytes = 0
                    total = int(resp.headers.get("Content-Length", 0))
                    mode = "wb"
                else:
                    raise IOError(f"HTTP server returned status {resp.status_code}")

                self.progress.total_bytes = total
                self.progress.bytes_downloaded = existing_bytes

                speed_sample_time = time.time()
                speed_sample_bytes = 0

                with open(part_file, mode) as f:
                    for chunk in resp.iter_content(chunk_size=self.chunk_size):
                        if self._cancelled.is_set():
                            part_file.unlink(missing_ok=True)
                            return

                        if chunk:
                            f.write(chunk)
                            self.progress.bytes_downloaded += len(chunk)
                            speed_sample_bytes += len(chunk)

                            now = time.time()
                            elapsed = now - speed_sample_time
                            if elapsed >= 0.5:
                                self.progress.speed_bps = speed_sample_bytes / elapsed
                                speed_sample_time = now
                                speed_sample_bytes = 0
                                self._notify()

                if self.expected_sha256:
                    hasher = hashlib.sha256()
                    with open(part_file, "rb") as f:
                        while chunk := f.read(65536):
                            hasher.update(chunk)
                    computed = hasher.hexdigest().lower()
                    if computed != self.expected_sha256.lower():
                        part_file.unlink(missing_ok=True)
                        raise ValueError(f"Checksum mismatch: expected {self.expected_sha256}, got {computed}")

                part_file.replace(self.destination)
                self.progress.status = DownloadStatus.COMPLETED
                self.progress.speed_bps = 0.0
                self._notify()
                return

            except Exception as e:
                logger.warning(f"Download attempt {attempt} failed for {self.url}: {e}")
                if attempt > self.retry_limit:
                    self.progress.status = DownloadStatus.FAILED
                    self.progress.error_message = str(e)
                    self._notify()
                    return
                time.sleep(1.0)


class DownloadManager:
    def __init__(self, max_concurrent: int = 3, session: Optional[requests.Session] = None):
        self.max_concurrent = max_concurrent
        self.session = session or requests.Session()
        self.tasks: Dict[str, DownloadTask] = {}
        self.lock = threading.Lock()

    def download(
        self,
        task_id: str,
        url: str,
        destination: Path,
        expected_sha256: Optional[str] = None,
        callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> DownloadTask:
        with self.lock:
            task = DownloadTask(
                task_id=task_id,
                url=url,
                destination=destination,
                expected_sha256=expected_sha256,
                callback=callback,
                session=self.session,
            )
            self.tasks[task_id] = task
            task.start()
            return task

    def cancel(self, task_id: str) -> None:
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].cancel()

    def get_progress(self, task_id: str) -> Optional[DownloadProgress]:
        with self.lock:
            if task_id in self.tasks:
                return self.tasks[task_id].progress
            return None
