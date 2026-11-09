import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.Installer.Extraction.extractor import ArchiveExtractor, ExtractionError
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import (
    InstallationManager,
    InstallationStage,
)


def test_extractor_safe_zip(tmp_path):
    zip_path = tmp_path / "test_game.zip"
    dest_dir = tmp_path / "extracted"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Game.exe", b"fake binary executable")
        zf.writestr("Data/levels.dat", b"level 1, level 2")

    ArchiveExtractor.extract_archive(zip_path, dest_dir)
    assert (dest_dir / "Game.exe").exists()
    assert (dest_dir / "Data" / "levels.dat").exists()


def test_extractor_zip_slip_protection(tmp_path):
    zip_path = tmp_path / "malicious.zip"
    dest_dir = tmp_path / "safe_zone"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", b"escaped payload")

    with pytest.raises(ExtractionError):
        ArchiveExtractor.extract_archive(zip_path, dest_dir)


def test_installation_manager_archive_flow(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)

    mock_zip_buf = io.BytesIO()
    with zipfile.ZipFile(mock_zip_buf, "w") as zf:
        zf.writestr("MyGame.exe", b"MZ dummy executable")
        zf.writestr("config.ini", b"[Settings]\nVolume=100")
    zip_bytes = mock_zip_buf.getvalue()

    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": str(len(zip_bytes))}
    mock_response.iter_content = lambda chunk_size=8192: [zip_bytes]
    mock_session.get.return_value = mock_response

    dl_manager = DownloadManager(session=mock_session)
    install_mgr = InstallationManager(storage, registry, dl_manager)

    game_def = GameDefinition(
        id="portable-runner",
        name="Portable Runner",
        source=GameSource(type="archive", url="https://example.com/runner.zip"),
    )
    registry.add_or_update_game(game_def)

    t = install_mgr.install_game(game_def)
    t.join(timeout=5)

    progress = install_mgr.get_progress("portable-runner")
    assert progress is not None
    assert progress.stage == InstallationStage.COMPLETED
    assert progress.detected_executable is not None

    entry = registry.get_game("portable-runner")
    assert entry.is_installed
    assert Path(entry.installation.executable_path).name == "MyGame.exe"
