"""Central Installation Manager coordinating downloads, archive extraction, B2Chunks, and registration."""

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional

from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager, DownloadProgress, DownloadStatus
from DeadMansVault.Installer.Extraction.extractor import ArchiveExtractor
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.Storage.Configuration.storage_manager import StorageManager

logger = logging.getLogger("DeadMansVault.Installer")


class InstallationStage(str, Enum):
    INITIALIZING = "initializing"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    EXTRACTING = "extracting"
    EXECUTABLE_SELECTION = "executable_selection"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class InstallationProgress:
    game_id: str
    stage: InstallationStage
    progress_fraction: float = 0.0
    download_speed_bps: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    message: str = ""
    extracted_folder: Optional[Path] = None
    detected_executable: Optional[Path] = None
    error: Optional[str] = None


class InstallationManager:
    def __init__(
        self,
        storage_manager: StorageManager,
        registry: GameRegistry,
        download_manager: DownloadManager,
    ):
        self.storage_manager = storage_manager
        self.registry = registry
        self.download_manager = download_manager
        self.active_installs: Dict[str, InstallationProgress] = {}
        self._cancellation_events: Dict[str, threading.Event] = {}
        self.lock = threading.Lock()

    def install_game(
        self,
        game_def: GameDefinition,
        custom_install_dir: Optional[Path] = None,
        callback: Optional[Callable[[InstallationProgress], None]] = None,
    ) -> threading.Thread:
        thread = threading.Thread(
            target=self._run_installation,
            args=(game_def, custom_install_dir, callback),
            daemon=True,
        )
        thread.start()
        return thread

    def cancel_installation(self, game_id: str) -> None:
        with self.lock:
            if game_id in self._cancellation_events:
                self._cancellation_events[game_id].set()
            self.download_manager.cancel(f"download_{game_id}")

    def get_progress(self, game_id: str) -> Optional[InstallationProgress]:
        with self.lock:
            return self.active_installs.get(game_id)

    def _notify(
        self,
        progress: InstallationProgress,
        callback: Optional[Callable[[InstallationProgress], None]],
    ) -> None:
        with self.lock:
            self.active_installs[progress.game_id] = progress
        if callback:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in installation callback: {e}")

    def _run_installation(
        self,
        game_def: GameDefinition,
        custom_install_dir: Optional[Path],
        callback: Optional[Callable[[InstallationProgress], None]],
    ) -> None:
        game_id = game_def.id
        cancel_event = threading.Event()
        with self.lock:
            self._cancellation_events[game_id] = cancel_event

        progress = InstallationProgress(
            game_id=game_id,
            stage=InstallationStage.INITIALIZING,
            message="Initializing installation...",
        )
        self._notify(progress, callback)

        if not game_def.source:
            progress.stage = InstallationStage.FAILED
            progress.error = "No download source configured for this game."
            self._notify(progress, callback)
            return

        install_root = custom_install_dir or (self.storage_manager.games_install_dir / game_def.id)
        install_root.mkdir(parents=True, exist_ok=True)

        try:
            source_type = game_def.source.type.lower()
            if source_type in ["archive", "zip", "direct"]:
                self._install_archive(game_def, install_root, progress, cancel_event, callback)
            elif source_type in ["b2", "b2chunks"]:
                from DeadMansVault.Installer.B2ChunksInstaller.b2chunks_installer import B2ChunksInstaller
                b2_installer = B2ChunksInstaller(
                    storage_manager=self.storage_manager,
                    download_manager=self.download_manager,
                )
                b2_installer.install(
                    game_def=game_def,
                    target_dir=install_root,
                    progress_obj=progress,
                    cancel_event=cancel_event,
                    notify_fn=lambda p: self._notify(p, callback),
                )
            else:
                raise ValueError(f"Unknown source type: {source_type}")

            if cancel_event.is_set():
                progress.stage = InstallationStage.CANCELLED
                progress.message = "Installation cancelled by user."
                self._notify(progress, callback)
                return

            detected_exe = None
            if game_def.executable:
                candidate = (install_root / game_def.executable).resolve()
                if candidate.exists():
                    detected_exe = candidate

            if not detected_exe:
                detected_exe = self.registry.detect_executable_in_folder(install_root)

            progress.extracted_folder = install_root
            progress.detected_executable = detected_exe

            if detected_exe:
                rel_path = ""
                try:
                    rel_path = str(detected_exe.resolve().relative_to(install_root.resolve())).replace("\\", "/")
                except ValueError:
                    rel_path = detected_exe.name

                self.registry.register_installation(
                    game_id=game_id,
                    install_dir=install_root,
                    executable_path=detected_exe,
                    relative_executable=rel_path,
                )
                progress.stage = InstallationStage.COMPLETED
                progress.progress_fraction = 1.0
                progress.message = "Installation completed successfully."
                self._notify(progress, callback)
            else:
                progress.stage = InstallationStage.EXECUTABLE_SELECTION
                progress.message = "Please select game executable."
                self._notify(progress, callback)

        except Exception as e:
            logger.error(f"Installation failed for {game_id}: {e}", exc_info=True)
            progress.stage = InstallationStage.FAILED
            progress.error = str(e)
            progress.message = f"Installation failed: {e}"
            self._notify(progress, callback)

    def _install_archive(
        self,
        game_def: GameDefinition,
        install_root: Path,
        progress: InstallationProgress,
        cancel_event: threading.Event,
        callback: Optional[Callable[[InstallationProgress], None]],
    ) -> None:
        url = game_def.source.url
        if not url:
            raise ValueError("Direct archive download URL is missing.")

        filename = Path(url.split("?")[0]).name or f"{game_def.id}.zip"
        archive_path = self.storage_manager.downloads_temp_dir / f"{game_def.id}_{filename}"

        progress.stage = InstallationStage.DOWNLOADING
        progress.message = "Downloading game archive..."
        self._notify(progress, callback)

        def on_dl_progress(dl_p: DownloadProgress):
            if cancel_event.is_set():
                return
            progress.download_speed_bps = dl_p.speed_bps
            progress.downloaded_bytes = dl_p.bytes_downloaded
            progress.total_bytes = dl_p.total_bytes
            progress.progress_fraction = dl_p.progress_fraction * 0.7
            progress.message = f"Downloading: {dl_p.bytes_downloaded / (1024*1024):.1f} MB / {dl_p.total_bytes / (1024*1024):.1f} MB"
            self._notify(progress, callback)

        task = self.download_manager.download(
            task_id=f"download_{game_def.id}",
            url=url,
            destination=archive_path,
            expected_sha256=game_def.source.checksum,
            callback=on_dl_progress,
        )

        while task.progress.status == DownloadStatus.DOWNLOADING:
            if cancel_event.is_set():
                task.cancel()
                return
            task.join(timeout=0.2)

        if task.progress.status != DownloadStatus.COMPLETED:
            raise IOError(f"Archive download failed: {task.progress.error_message or 'Unknown error'}")

        if cancel_event.is_set():
            return

        progress.stage = InstallationStage.EXTRACTING
        progress.message = "Extracting files..."
        self._notify(progress, callback)

        def on_extract(cur, total):
            if cancel_event.is_set():
                return
            frac = 0.7 + 0.3 * (cur / max(1, total))
            progress.progress_fraction = frac
            progress.message = f"Extracting files ({cur}/{total})..."
            self._notify(progress, callback)

        ArchiveExtractor.extract_archive(archive_path, install_root, progress_callback=on_extract)

        if self.storage_manager.downloads_temp_dir in archive_path.parents:
            archive_path.unlink(missing_ok=True)
