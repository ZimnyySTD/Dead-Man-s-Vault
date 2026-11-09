"""Storage paths and persistence management for Dead Man's Vault."""

import os
import sys
from pathlib import Path

APP_NAME = "DeadMansVault"
APP_VERSION = "1.0.0"
APP_BUILD = "2025.10.1"


class StorageManager:
    """Manages storage directories for portable or standard installation modes."""

    def __init__(self, base_dir: Path | None = None, portable: bool = False):
        if base_dir is not None:
            self.root = Path(base_dir).resolve()
        elif portable or (Path.cwd() / "portable.txt").exists() or (Path.cwd() / "data").exists():
            self.root = (Path.cwd() / "data").resolve()
        else:
            if sys.platform == "win32":
                appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
                self.root = (Path(appdata) / APP_NAME).resolve()
            else:
                self.root = (Path.home() / f".{APP_NAME.lower()}").resolve()

        self.config_dir = self.root / "config"
        self.cache_dir = self.root / "cache"
        self.artwork_cache_dir = self.cache_dir / "artwork"
        self.metadata_cache_dir = self.cache_dir / "metadata"
        self.downloads_temp_dir = self.root / "temp_downloads"
        self.games_install_dir = self.root / "installed_games"
        self.db_dir = self.root / "database"
        self.logs_dir = self.root / "logs"

        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Create storage directories if they do not exist."""
        for directory in [
            self.root,
            self.config_dir,
            self.cache_dir,
            self.artwork_cache_dir,
            self.metadata_cache_dir,
            self.downloads_temp_dir,
            self.games_install_dir,
            self.db_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def settings_path(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def local_library_path(self) -> Path:
        return self.db_dir / "local_games.json"

    @property
    def active_games_definition_path(self) -> Path:
        return self.config_dir / "games.json"
