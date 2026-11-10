"""Game Registry coordinating games.json definitions with machine-specific local installations."""

import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from DeadMansVault.Library.GameDefinitions.game_model import (
    GameDefinition,
    GameEntry,
    GameSource,
    LocalInstallationRecord,
)
from DeadMansVault.Library.GameDefinitions.games_json_manager import GamesJsonManager
from DeadMansVault.Storage.Configuration.storage_manager import StorageManager

logger = logging.getLogger("DeadMansVault.GameRegistry")


class GameRegistry:
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.definitions: Dict[str, GameDefinition] = {}
        self.installations: Dict[str, LocalInstallationRecord] = {}
        self.load_all()

    def load_all(self) -> None:
        self.definitions.clear()
        self.installations.clear()

        games_json_file = self.storage_manager.active_games_definition_path
        if games_json_file.exists():
            try:
                loaded = GamesJsonManager.load_from_file(games_json_file)
                for g in loaded:
                    self.definitions[g.id] = g
            except Exception as e:
                logger.error(f"Failed loading games.json: {e}")

        local_db_file = self.storage_manager.local_library_path
        if local_db_file.exists():
            try:
                with open(local_db_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("installations", []):
                        rec = LocalInstallationRecord.from_dict(item)
                        if Path(rec.install_directory).exists():
                            self.installations[rec.game_id] = rec
                        else:
                            rec.is_installed = False
                            self.installations[rec.game_id] = rec
            except Exception as e:
                logger.error(f"Failed loading local installations: {e}")

    def save_definitions(self) -> None:
        GamesJsonManager.save_to_file(
            self.storage_manager.active_games_definition_path,
            list(self.definitions.values()),
        )

    def save_installations(self) -> None:
        path = self.storage_manager.local_library_path
        data = {
            "version": 1,
            "installations": [inst.to_dict() for inst in self.installations.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_or_update_game(self, definition: GameDefinition, save: bool = True) -> GameEntry:
        self.definitions[definition.id] = definition
        if save:
            self.save_definitions()
        return self.get_game(definition.id)

    def register_installation(
        self,
        game_id: str,
        install_dir: Path,
        executable_path: Path,
        relative_executable: Optional[str] = None,
        custom_arguments: str = "",
        size_bytes: int = 0,
    ) -> LocalInstallationRecord:
        record = LocalInstallationRecord(
            game_id=game_id,
            install_directory=str(install_dir.resolve()),
            executable_path=str(executable_path.resolve()),
            working_directory=str(install_dir.resolve()),
            custom_arguments=custom_arguments,
            size_bytes=size_bytes,
            is_installed=True,
        )
        self.installations[game_id] = record
        self.save_installations()

        if game_id in self.definitions:
            defn = self.definitions[game_id]
            if relative_executable:
                defn.executable = relative_executable
                self.save_definitions()
            elif not defn.executable:
                try:
                    rel = executable_path.resolve().relative_to(install_dir.resolve())
                    defn.executable = str(rel).replace("\\", "/")
                    self.save_definitions()
                except ValueError:
                    pass

        return record

    def remove_game(self, game_id: str, delete_files: bool = False) -> None:
        if game_id in self.installations:
            inst = self.installations[game_id]
            if delete_files and Path(inst.install_directory).exists():
                import shutil
                try:
                    shutil.rmtree(inst.install_directory)
                except Exception as e:
                    logger.error(f"Error deleting files for {game_id}: {e}")
            del self.installations[game_id]
            self.save_installations()

        if game_id in self.definitions:
            del self.definitions[game_id]
            self.save_definitions()

    def get_game(self, game_id: str) -> Optional[GameEntry]:
        if game_id not in self.definitions:
            return None
        return GameEntry(
            definition=self.definitions[game_id],
            installation=self.installations.get(game_id),
        )

    def get_all_games(self) -> List[GameEntry]:
        entries: List[GameEntry] = []
        for g_id, defn in self.definitions.items():
            entries.append(
                GameEntry(
                    definition=defn,
                    installation=self.installations.get(g_id),
                )
            )
        return entries

    def import_local_folder(
        self, folder_path: Path, game_name: Optional[str] = None, executable_path: Optional[Path] = None
    ) -> GameEntry:
        folder = Path(folder_path).resolve()
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"Folder does not exist or is not a directory: {folder}")

        name = game_name or folder.name
        game_id = str(uuid.uuid4())

        if executable_path is None:
            executable_path = self.detect_executable_in_folder(folder)

        rel_exec = ""
        if executable_path is not None:
            try:
                rel_exec = str(executable_path.resolve().relative_to(folder)).replace("\\", "/")
            except ValueError:
                rel_exec = executable_path.name

        defn = GameDefinition(
            id=game_id,
            name=name,
            executable=rel_exec,
            source=GameSource(type="local"),
        )
        self.add_or_update_game(defn, save=True)

        if executable_path:
            self.register_installation(
                game_id=game_id,
                install_dir=folder,
                executable_path=executable_path,
                relative_executable=rel_exec,
            )

        return self.get_game(game_id)

    @staticmethod
    def detect_executable_in_folder(folder: Path) -> Optional[Path]:
        patterns = ["*.exe", "*.bat", "*.cmd", "*.sh", "*.bin"]
        candidates: List[Path] = []

        for pattern in patterns:
            candidates.extend(folder.glob(pattern))

        if not candidates:
            for sub in folder.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    for pattern in patterns:
                        candidates.extend(sub.glob(pattern))

        if not candidates:
            return None

        non_installers = [
            c for c in candidates
            if not any(k in c.name.lower() for k in ["unins", "setup", "install", "crash", "helper"])
        ]
        if non_installers:
            return non_installers[0]
        return candidates[0]

    def search_and_filter(
        self,
        query: str = "",
        filter_status: str = "all",
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> List[GameEntry]:
        games = self.get_all_games()

        if query.strip():
            q = query.strip().lower()
            games = [g for g in games if q in g.name.lower() or q in g.definition.description.lower()]

        if filter_status == "installed":
            games = [g for g in games if g.is_installed]
        elif filter_status == "not_installed":
            games = [g for g in games if not g.is_installed]

        reverse = (sort_order.lower() == "desc")
        if sort_by == "name":
            games.sort(key=lambda g: g.name.lower(), reverse=reverse)
        elif sort_by == "installed":
            games.sort(key=lambda g: (1 if g.is_installed else 0, g.name.lower()), reverse=reverse)
        elif sort_by == "recent":
            games.sort(
                key=lambda g: g.installation.last_played if g.installation else 0.0,
                reverse=reverse,
            )

        return games
