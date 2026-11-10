import json
import shutil
from pathlib import Path
import pytest

import b2chks
from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import InstallationManager, InstallationStage


def test_b2chunks_installation_flow(tmp_path):
    storage = StorageManager(base_dir=tmp_path / "storage")
    registry = GameRegistry(storage)
    dl_manager = DownloadManager()
    install_mgr = InstallationManager(storage, registry, dl_manager)

    orig_game_dir = tmp_path / "OrigGame"
    orig_game_dir.mkdir()
    (orig_game_dir / "Game.exe").write_bytes(b"B2CHUNKS RUNNER EXECUTABLE DATA")
    (orig_game_dir / "Data").mkdir()
    (orig_game_dir / "Data" / "assets.bin").write_bytes(b"1234567890abcdef" * 1024)

    package_output_dir = tmp_path / "B2Package"
    manifest_path = b2chks.pack(
        source=str(orig_game_dir),
        chunk_size_str="4KB",
        output_dir=str(package_output_dir),
        compression="gzip",
    )

    chunks_dir = manifest_path.parent / "chunks"

    game_def = GameDefinition(
        id="b2-space-game",
        name="Space Combat B2",
        source=GameSource(
            type="b2",
            manifest=str(manifest_path),
            chunks={"*": f"{chunks_dir}/{{hash}}"},
        ),
        executable="Game.exe",
    )
    registry.add_or_update_game(game_def)

    t = install_mgr.install_game(game_def)
    t.join(timeout=10)

    progress = install_mgr.get_progress("b2-space-game")
    assert progress is not None
    assert progress.stage == InstallationStage.COMPLETED, f"Failed with {progress.error}"

    entry = registry.get_game("b2-space-game")
    assert entry.is_installed
    installed_exe = Path(entry.installation.executable_path)
    assert installed_exe.exists()
    assert installed_exe.read_bytes() == b"B2CHUNKS RUNNER EXECUTABLE DATA"
    assert (installed_exe.parent / "Data" / "assets.bin").exists()
