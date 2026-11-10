"""Installer integration for the B2Chunks protocol format using the b2chks package."""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import requests
import b2chks

from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager, DownloadStatus
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition
from DeadMansVault.Storage.Configuration.storage_manager import StorageManager

logger = logging.getLogger("DeadMansVault.B2ChunksInstaller")


class B2ChunksInstaller:
    def __init__(
        self,
        storage_manager: StorageManager,
        download_manager: DownloadManager,
        session: Optional[requests.Session] = None,
    ):
        self.storage_manager = storage_manager
        self.download_manager = download_manager
        self.session = session or requests.Session()

    def install(
        self,
        game_def: GameDefinition,
        target_dir: Path,
        progress_obj: Any,
        cancel_event: threading.Event,
        notify_fn: Callable[[Any], None],
    ) -> None:
        source = game_def.source
        if not source or not source.manifest:
            raise ValueError("B2Chunks installation requires a manifest URL or file path.")

        from DeadMansVault.Installer.ArchiveInstaller.archive_installer import InstallationStage

        progress_obj.stage = InstallationStage.INITIALIZING
        progress_obj.message = "Retrieving B2Chunks manifest..."
        notify_fn(progress_obj)

        manifest_data, manifest_path = self._load_manifest(source.manifest, game_def.id)

        pubkey_path = None
        if source.signature:
            progress_obj.stage = InstallationStage.VERIFYING
            progress_obj.message = "Verifying manifest signature..."
            notify_fn(progress_obj)
            if Path(source.signature).exists():
                pubkey_path = str(Path(source.signature).resolve())
            else:
                key_file = self.storage_manager.config_dir / f"{game_def.id}.pub"
                key_file.write_text(source.signature, encoding="utf-8")
                pubkey_path = str(key_file)

        chunks_cache_dir = self.storage_manager.downloads_temp_dir / f"chunks_{game_def.id}"
        chunks_cache_dir.mkdir(parents=True, exist_ok=True)

        chunks_info = manifest_data.get("chunks", [])
        if not chunks_info:
            raise ValueError("Invalid B2Chunks manifest: no chunks listed.")

        total_chunks = len(chunks_info)
        total_uncompressed_bytes = sum(c.get("size", 0) for c in chunks_info)
        progress_obj.total_bytes = total_uncompressed_bytes

        progress_obj.stage = InstallationStage.DOWNLOADING
        progress_obj.message = f"Downloading chunks (0/{total_chunks})..."
        notify_fn(progress_obj)

        chunk_sources: Dict[str, str] = source.chunks or {}

        for idx, chunk_entry in enumerate(chunks_info):
            if cancel_event.is_set():
                return

            chunk_filename = chunk_entry.get("filename", f"chunk_{idx:03d}.bin")
            chunk_sha256 = chunk_entry.get("sha256") or chunk_entry.get("hash")
            chunk_file = chunks_cache_dir / chunk_filename

            if not chunk_file.exists():
                chunk_url = self._resolve_chunk_url(
                    chunk_filename=chunk_filename,
                    chunk_hash=chunk_sha256,
                    manifest_loc=source.manifest,
                    chunk_sources=chunk_sources,
                )

                local_candidate = Path(chunk_url.replace("file://", ""))
                if chunk_url.startswith("file://") or local_candidate.exists():
                    import shutil
                    shutil.copyfile(local_candidate, chunk_file)
                elif not (chunk_url.startswith("http://") or chunk_url.startswith("https://")):
                    manifest_parent = Path(source.manifest.replace("file://", "")).parent
                    candidate_in_parent = manifest_parent / chunk_filename
                    if candidate_in_parent.exists():
                        import shutil
                        shutil.copyfile(candidate_in_parent, chunk_file)
                    else:
                        raise FileNotFoundError(f"Local chunk not found: {chunk_url}")
                else:
                    task = self.download_manager.download(
                        task_id=f"chunk_{game_def.id}_{chunk_filename}",
                        url=chunk_url,
                        destination=chunk_file,
                        expected_sha256=chunk_sha256,
                    )
                    while task.progress.status == DownloadStatus.DOWNLOADING:
                        if cancel_event.is_set():
                            task.cancel()
                            return
                        task.join(timeout=0.2)

                    if task.progress.status != DownloadStatus.COMPLETED:
                        raise IOError(f"Failed downloading chunk {chunk_filename}: {task.progress.error_message}")

            progress_obj.progress_fraction = (idx + 1) / total_chunks * 0.7
            progress_obj.message = f"Downloading chunks ({idx + 1}/{total_chunks})..."
            notify_fn(progress_obj)

        if cancel_event.is_set():
            return

        progress_obj.stage = InstallationStage.EXTRACTING
        progress_obj.message = "Extracting and reconstructing files..."
        notify_fn(progress_obj)

        def b2_progress_cb(current: int, total: int, step_desc: str):
            if total > 0:
                frac = 0.7 + 0.3 * (current / total)
                progress_obj.progress_fraction = frac
            progress_obj.message = f"{step_desc} ({current}/{total})"
            notify_fn(progress_obj)

        success = b2chks.extract(
            manifest_path=str(manifest_path),
            chunks_dir=str(chunks_cache_dir),
            output_dir=str(target_dir),
            public_key_path=pubkey_path,
            progress_callback=b2_progress_cb,
            cancel_token=cancel_event.is_set,
        )

        if not success and not cancel_event.is_set():
            raise IOError("B2Chunks extraction failed or verification check failed.")

        progress_obj.progress_fraction = 1.0
        progress_obj.message = "B2Chunks extraction completed."
        notify_fn(progress_obj)

    def _load_manifest(self, manifest_loc: str, game_id: str) -> tuple[Dict[str, Any], Path]:
        if manifest_loc.startswith("http://") or manifest_loc.startswith("https://"):
            resp = self.session.get(manifest_loc, timeout=10)
            if resp.status_code != 200:
                raise IOError(f"Failed to fetch manifest from {manifest_loc} (HTTP {resp.status_code})")
            data = resp.json()
            local_manifest = self.storage_manager.downloads_temp_dir / f"manifest_{game_id}.b2m"
            local_manifest.write_text(json.dumps(data), encoding="utf-8")
            return data, local_manifest
        else:
            path = Path(manifest_loc.replace("file://", "")).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Manifest file not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f), path

    def _resolve_chunk_url(
        self,
        chunk_filename: str,
        chunk_hash: Optional[str],
        manifest_loc: str,
        chunk_sources: Dict[str, str],
    ) -> str:
        if chunk_filename in chunk_sources:
            return chunk_sources[chunk_filename]
        if chunk_hash and chunk_hash in chunk_sources:
            return chunk_sources[chunk_hash]
        if "*" in chunk_sources:
            template = chunk_sources["*"]
            if "{filename}" in template:
                return template.replace("{filename}", chunk_filename)
            elif "{hash}" in template and chunk_hash:
                return template.replace("{hash}", chunk_hash)
            elif "{hash}" in template:
                return template.replace("{hash}", chunk_filename)
            else:
                return f"{template.rstrip('/')}/{chunk_filename}"

        if manifest_loc.startswith("http://") or manifest_loc.startswith("https://"):
            base_url = manifest_loc.rsplit("/", 1)[0]
            return f"{base_url}/chunks/{chunk_filename}"
        else:
            manifest_dir = Path(manifest_loc.replace("file://", "")).parent
            return str(manifest_dir / "chunks" / chunk_filename)
