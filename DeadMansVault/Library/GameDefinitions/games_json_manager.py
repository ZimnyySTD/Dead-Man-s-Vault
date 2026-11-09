"""Parser, validator, and serializer for the shareable games.json format."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition

CURRENT_SCHEMA_FORMAT = "DMV"
CURRENT_SCHEMA_VERSION = 1


class GamesJsonManager:
    @staticmethod
    def validate_schema(data: Any) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Root of games.json must be an object/dict."
        if data.get("format") != CURRENT_SCHEMA_FORMAT:
            return False, f"Unsupported or missing format tag. Expected '{CURRENT_SCHEMA_FORMAT}'."
        if not isinstance(data.get("version"), int):
            return False, "Missing or invalid 'version' field. Expected integer."
        if "games" not in data or not isinstance(data["games"], list):
            return False, "Missing or invalid 'games' array."

        for i, game_data in enumerate(data["games"]):
            if not isinstance(game_data, dict):
                return False, f"Game entry at index {i} must be an object."
            if "name" not in game_data or not str(game_data["name"]).strip():
                return False, f"Game entry at index {i} is missing a valid 'name'."

        return True, "Valid"

    @classmethod
    def load_from_file(cls, filepath: Path) -> List[GameDefinition]:
        path = Path(filepath)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        valid, error = cls.validate_schema(data)
        if not valid:
            raise ValueError(f"Invalid games.json schema in {filepath}: {error}")

        games: List[GameDefinition] = []
        for g_dict in data["games"]:
            games.append(GameDefinition.from_dict(g_dict))
        return games

    @classmethod
    def save_to_file(cls, filepath: Path, games: List[GameDefinition]) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {
            "format": CURRENT_SCHEMA_FORMAT,
            "version": CURRENT_SCHEMA_VERSION,
            "games": [g.to_dict() for g in games],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def export_library(cls, export_path: Path, games: List[GameDefinition]) -> None:
        cls.save_to_file(export_path, games)

    @classmethod
    def import_library(cls, import_path: Path) -> List[GameDefinition]:
        return cls.load_from_file(import_path)
