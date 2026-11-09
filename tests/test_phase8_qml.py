import os
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.Library.GameMetadata.metadata_service import MetadataService
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import InstallationManager
from DeadMansVault.GameRunner.game_runner import GameRunner
from DeadMansVault.DeveloperMode.Diagnostics.developer_controller import DeveloperController
from DeadMansVault.Launcher.UI.qml_bridge import create_qml_engine


def test_qml_desktop_frontend(tmp_path):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication([])

    storage = StorageManager(base_dir=tmp_path)
    settings = SettingsManager(storage)
    registry = GameRegistry(storage)
    meta = MetadataService(storage)
    dl = DownloadManager()
    inst = InstallationManager(storage, registry, dl)
    runner = GameRunner(registry)
    dev = DeveloperController(settings)

    registry.add_or_update_game(GameDefinition(id="qml-game", name="QML Adventure"))

    engine, bridge = create_qml_engine(app, registry, runner, inst, meta, dev, settings)
    assert len(engine.rootObjects()) > 0

    games = bridge.getGames()
    assert len(games) == 1
    assert games[0]["name"] == "QML Adventure"
