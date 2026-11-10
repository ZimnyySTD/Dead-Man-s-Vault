"""Application bootstrap and entry point for Dead Man's Vault."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from DeadMansVault.DeveloperMode.Diagnostics.developer_controller import DeveloperController
from DeadMansVault.DeveloperMode.Logging.logger import setup_logging
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.GameRunner.game_runner import GameRunner
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import InstallationManager
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.Launcher.UI.main_window import MainWindow
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameDefinitions.games_json_manager import GamesJsonManager
from DeadMansVault.Library.GameMetadata.metadata_service import MetadataService
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.Storage.Configuration.storage_manager import StorageManager


def create_app(storage_dir: Path | None = None, portable: bool = False) -> tuple[QApplication, MainWindow]:
    storage_mgr = StorageManager(base_dir=storage_dir, portable=portable)
    settings_mgr = SettingsManager(storage_mgr)

    logger = setup_logging(storage_mgr.logs_dir, verbose=settings_mgr.settings.developer.verbose_logging)
    logger.info("Initializing Dead Man's Vault...")

    registry = GameRegistry(storage_mgr)
    metadata_service = MetadataService(storage_mgr)
    dl_mgr = DownloadManager(max_concurrent=settings_mgr.settings.downloads.max_concurrent_downloads)
    installer = InstallationManager(storage_mgr, registry, dl_mgr)
    runner = GameRunner(registry)
    dev_ctrl = DeveloperController(settings_mgr)

    if not storage_mgr.active_games_definition_path.exists():
        GamesJsonManager.save_to_file(storage_mgr.active_games_definition_path, [])

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        app.setApplicationName("DeadMansVault")

    window = MainWindow(
        storage_manager=storage_mgr,
        settings_manager=settings_mgr,
        registry=registry,
        metadata_service=metadata_service,
        download_manager=dl_mgr,
        installer=installer,
        runner=runner,
        developer_controller=dev_ctrl,
    )

    return app, window


def main():
    app, window = create_app()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
