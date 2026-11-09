import json
from pathlib import Path
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource
from DeadMansVault.Library.GameDefinitions.games_json_manager import GamesJsonManager
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry


def test_games_json_save_load_validation(tmp_path):
    json_path = tmp_path / "games.json"
    game1 = GameDefinition(
        id="cyber-rogue",
        name="Cyber Rogue",
        version="1.2.0",
        description="A stealth game in neon shadows.",
        source=GameSource(type="b2", manifest="https://example.com/manifest.json"),
        executable="Binaries/CyberRogue.exe",
    )
    game2 = GameDefinition(
        id="iron-vault",
        name="Iron Vault",
        version="2.0.0",
        description="Vault exploration.",
        source=GameSource(type="archive", url="https://example.com/vault.zip"),
        executable="Vault.exe",
    )

    GamesJsonManager.save_to_file(json_path, [game1, game2])
    loaded = GamesJsonManager.load_from_file(json_path)

    assert len(loaded) == 2
    assert loaded[0].name == "Cyber Rogue"
    assert loaded[0].source.type == "b2"
    assert loaded[1].name == "Iron Vault"


def test_game_registry_lifecycle(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)

    game = GameDefinition(
        id="game-1",
        name="Alpha Protocol Portable",
        source=GameSource(type="archive", url="http://test.com/alpha.zip"),
    )
    registry.add_or_update_game(game)

    entry = registry.get_game("game-1")
    assert entry is not None
    assert not entry.is_installed

    install_folder = tmp_path / "AlphaProtocol"
    install_folder.mkdir()
    fake_exe = install_folder / "Alpha.exe"
    fake_exe.touch()

    registry.register_installation(
        game_id="game-1",
        install_dir=install_folder,
        executable_path=fake_exe,
    )

    entry = registry.get_game("game-1")
    assert entry.is_installed
    assert entry.installation.executable_path == str(fake_exe.resolve())

    new_reg = GameRegistry(storage)
    reloaded_entry = new_reg.get_game("game-1")
    assert reloaded_entry is not None
    assert reloaded_entry.is_installed


def test_import_local_folder(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)

    game_dir = tmp_path / "MyRetroGame"
    game_dir.mkdir()
    exe = game_dir / "retro.exe"
    exe.touch()

    entry = registry.import_local_folder(game_dir)
    assert entry is not None
    assert entry.name == "MyRetroGame"
    assert entry.is_installed
    assert entry.definition.executable == "retro.exe"
    assert entry.installation.executable_path == str(exe.resolve())


def test_search_and_filter(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    registry = GameRegistry(storage)

    g1 = GameDefinition(id="g1", name="Dark Souls Portable")
    g2 = GameDefinition(id="g2", name="Dead Cells")
    g3 = GameDefinition(id="g3", name="Super Mario")

    registry.add_or_update_game(g1)
    registry.add_or_update_game(g2)
    registry.add_or_update_game(g3)

    results = registry.search_and_filter(query="dead")
    assert len(results) == 1
    assert results[0].name == "Dead Cells"

    results_asc = registry.search_and_filter(sort_by="name", sort_order="asc")
    assert [r.name for r in results_asc] == ["Dark Souls Portable", "Dead Cells", "Super Mario"]

    results_desc = registry.search_and_filter(sort_by="name", sort_order="desc")
    assert [r.name for r in results_desc] == ["Super Mario", "Dead Cells", "Dark Souls Portable"]
