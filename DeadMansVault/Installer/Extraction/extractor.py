"""Secure archive extraction backend with Zip Slip / traversal protection."""

import logging
import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("DeadMansVault.Extractor")


class ExtractionError(Exception):
    pass


class ArchiveExtractor:
    @classmethod
    def is_path_safe(cls, target_dir: Path, path: Path) -> bool:
        try:
            target_resolved = target_dir.resolve()
            dest_resolved = (target_dir / path).resolve()
            return dest_resolved.is_relative_to(target_resolved)
        except Exception:
            return False

    @classmethod
    def extract_archive(
        cls,
        archive_path: Path,
        destination_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        archive_path = Path(archive_path)
        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        suffix = archive_path.suffix.lower()

        if suffix in [".zip"]:
            cls._extract_zip(archive_path, destination_dir, progress_callback)
        elif suffix in [".tar", ".gz", ".bz2", ".xz"] or archive_path.name.endswith(".tar.gz"):
            cls._extract_tar(archive_path, destination_dir, progress_callback)
        elif suffix in [".7z"]:
            cls._extract_7z(archive_path, destination_dir, progress_callback)
        else:
            if zipfile.is_zipfile(archive_path):
                cls._extract_zip(archive_path, destination_dir, progress_callback)
            elif tarfile.is_tarfile(archive_path):
                cls._extract_tar(archive_path, destination_dir, progress_callback)
            else:
                raise ExtractionError(f"Unsupported archive format: {archive_path.name}")

        return destination_dir

    @classmethod
    def _extract_zip(
        cls,
        archive_path: Path,
        destination_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> None:
        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                members = zf.infolist()
                total = len(members)

                for index, member in enumerate(members):
                    member_path = Path(member.filename)
                    if not cls.is_path_safe(destination_dir, member_path):
                        raise ExtractionError(
                            f"Path traversal detected in archive member: {member.filename}"
                        )

                    zf.extract(member, destination_dir)
                    if progress_callback:
                        progress_callback(index + 1, total)
        except zipfile.BadZipFile as e:
            raise ExtractionError(f"Corrupt or invalid ZIP archive: {e}")

    @classmethod
    def _extract_tar(
        cls,
        archive_path: Path,
        destination_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> None:
        try:
            with tarfile.open(archive_path, "r:*") as tf:
                members = tf.getmembers()
                total = len(members)

                for index, member in enumerate(members):
                    member_path = Path(member.name)
                    if not cls.is_path_safe(destination_dir, member_path):
                        raise ExtractionError(
                            f"Path traversal detected in archive member: {member.name}"
                        )

                    tf.extract(member, destination_dir, filter="data" if hasattr(tarfile, "data_filter") else None)
                    if progress_callback:
                        progress_callback(index + 1, total)
        except Exception as e:
            raise ExtractionError(f"Error extracting TAR archive: {e}")

    @classmethod
    def _extract_7z(
        cls,
        archive_path: Path,
        destination_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]],
    ) -> None:
        try:
            import py7zr
            with py7zr.SevenZipFile(archive_path, mode="r") as sz:
                sz.extractall(path=destination_dir)
                if progress_callback:
                    progress_callback(100, 100)
        except ImportError:
            import subprocess
            if shutil.which("7z"):
                res = subprocess.run(
                    ["7z", "x", str(archive_path), f"-o{destination_dir}", "-y"],
                    capture_output=True,
                )
                if res.returncode != 0:
                    raise ExtractionError(f"7z extraction failed: {res.stderr.decode()}")
                if progress_callback:
                    progress_callback(100, 100)
            else:
                raise ExtractionError("7z extraction requires 'py7zr' or system '7z' utility.")
