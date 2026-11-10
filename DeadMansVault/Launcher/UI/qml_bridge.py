"""QML Application Bridge integrating Python backend engines with Qt 6 QML desktop frontend."""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from DeadMansVault.DeveloperMode.Diagnostics.developer_controller import DeveloperController
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.GameRunner.game_runner import GameRunner
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import InstallationManager
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition
from DeadMansVault.Library.GameMetadata.metadata_service import MetadataService
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry


class LauncherQmlBridge(QObject):
    gamesUpdated = Signal()
    developerUnlocked = Signal()

    def __init__(
        self,
        registry: GameRegistry,
        runner: GameRunner,
        installer: InstallationManager,
        metadata_service: MetadataService,
        developer_controller: DeveloperController,
        settings_manager: SettingsManager,
        parent=None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.runner = runner
        self.installer = installer
        self.metadata_service = metadata_service
        self.developer_controller = developer_controller
        self.settings_manager = settings_manager

        self.developer_controller.add_unlock_listener(lambda _: self.developerUnlocked.emit())

    @Slot(result="QVariantList")
    def getGames(self):
        games = self.registry.get_all_games()
        return [
            {
                "id": g.id,
                "name": g.name,
                "version": g.definition.version,
                "is_installed": g.is_installed,
                "cover_image": g.definition.cover_image,
                "description": g.definition.description,
            }
            for g in games
        ]

    @Slot(str)
    def launchGame(self, game_id: str):
        self.runner.launch_game(game_id)

    @Slot(str)
    def stopGame(self, game_id: str):
        self.runner.stop_game(game_id)

    @Slot()
    def registerBuildClick(self):
        if self.developer_controller.register_build_click():
            self.developerUnlocked.emit()


def create_qml_engine(
    app: QApplication,
    registry: GameRegistry,
    runner: GameRunner,
    installer: InstallationManager,
    metadata_service: MetadataService,
    developer_controller: DeveloperController,
    settings_manager: SettingsManager,
) -> tuple[QQmlApplicationEngine, LauncherQmlBridge]:
    engine = QQmlApplicationEngine()
    bridge = LauncherQmlBridge(
        registry=registry,
        runner=runner,
        installer=installer,
        metadata_service=metadata_service,
        developer_controller=developer_controller,
        settings_manager=settings_manager,
    )
    engine.rootContext().setContextProperty("launcherBridge", bridge)
    engine.rootContext().setContextProperty("devBridge", bridge)

    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))
    return engine, bridge
