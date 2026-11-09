import sys
import time
from pathlib import Path
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.GameRunner.game_runner import GameRunner


def test_game_runner_launch_and_exit(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)
    runner = GameRunner(registry)

    game_dir = tmp_path / "DummyGame"
    game_dir.mkdir()
    launcher_script = game_dir / "start_game.sh"
    launcher_script.write_text("#!/bin/sh\nsleep 0.2\nexit 0\n", encoding="utf-8")
    launcher_script.chmod(0o755)

    game_def = GameDefinition(id="test-run", name="Test Run Game")
    registry.add_or_update_game(game_def)
    registry.register_installation(
        game_id="test-run",
        install_dir=game_dir,
        executable_path=launcher_script,
    )

    state_changes = []
    runner.register_state_change_callback(lambda gid, running: state_changes.append((gid, running)))

    proc = runner.launch_game("test-run")
    assert runner.is_game_running("test-run")
    assert ("test-run", True) in state_changes

    proc.wait(timeout=2.0)
    time.sleep(0.3)

    assert not runner.is_game_running("test-run")
    assert ("test-run", False) in state_changes


def test_game_runner_stop(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)
    runner = GameRunner(registry)

    game_dir = tmp_path / "LongGame"
    game_dir.mkdir()
    launcher_script = game_dir / "start_long.sh"
    launcher_script.write_text("#!/bin/sh\nsleep 60\n", encoding="utf-8")
    launcher_script.chmod(0o755)

    game_def = GameDefinition(id="long-run", name="Long Run Game")
    registry.add_or_update_game(game_def)
    registry.register_installation(
        game_id="long-run",
        install_dir=game_dir,
        executable_path=launcher_script,
    )

    proc = runner.launch_game("long-run")
    assert runner.is_game_running("long-run")

    stopped = runner.stop_game("long-run", timeout=0.5)
    assert stopped
    time.sleep(0.3)
    assert not runner.is_game_running("long-run")
