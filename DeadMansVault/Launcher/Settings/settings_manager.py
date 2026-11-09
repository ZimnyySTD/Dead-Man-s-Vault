"""Settings management for Dead Man's Vault."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager


@dataclass
class GeneralSettings:
    appearance: str = "dark_metallic"
    confirm_uninstall: bool = True
    start_minimized: bool = False


@dataclass
class StorageSettings:
    default_install_dir: str = ""
    download_temp_dir: str = ""
    cache_dir: str = ""


@dataclass
class DownloadsSettings:
    max_concurrent_downloads: int = 3
    retry_attempts: int = 3
    auto_cleanup_temp: bool = True


@dataclass
class LibrarySettings:
    default_layout: str = "grid"
    sort_by: str = "name"
    sort_order: str = "asc"
    enable_metadata_retrieval: bool = True


@dataclass
class DeveloperSettings:
    developer_mode_unlocked: bool = False
    debug_overlay_enabled: bool = False
    verbose_logging: bool = False


@dataclass
class SettingsModel:
    general: GeneralSettings = field(default_factory=GeneralSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    downloads: DownloadsSettings = field(default_factory=DownloadsSettings)
    library: LibrarySettings = field(default_factory=LibrarySettings)
    developer: DeveloperSettings = field(default_factory=DeveloperSettings)


class SettingsManager:
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.settings = SettingsModel()
        self.settings.storage.default_install_dir = str(storage_manager.games_install_dir)
        self.settings.storage.download_temp_dir = str(storage_manager.downloads_temp_dir)
        self.settings.storage.cache_dir = str(storage_manager.cache_dir)
        self.load()

    def load(self) -> None:
        path = self.storage_manager.settings_path
        if not path.exists():
            self.save()
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "general" in data:
                self.settings.general = GeneralSettings(**data["general"])
            if "storage" in data:
                stored_storage = data["storage"]
                self.settings.storage.default_install_dir = stored_storage.get(
                    "default_install_dir", str(self.storage_manager.games_install_dir)
                )
                self.settings.storage.download_temp_dir = stored_storage.get(
                    "download_temp_dir", str(self.storage_manager.downloads_temp_dir)
                )
                self.settings.storage.cache_dir = stored_storage.get(
                    "cache_dir", str(self.storage_manager.cache_dir)
                )
            if "downloads" in data:
                self.settings.downloads = DownloadsSettings(**data["downloads"])
            if "library" in data:
                self.settings.library = LibrarySettings(**data["library"])
            if "developer" in data:
                self.settings.developer = DeveloperSettings(**data["developer"])
        except Exception:
            self.save()

    def save(self) -> None:
        path = self.storage_manager.settings_path
        data = {
            "general": asdict(self.settings.general),
            "storage": asdict(self.settings.storage),
            "downloads": asdict(self.settings.downloads),
            "library": asdict(self.settings.library),
            "developer": asdict(self.settings.developer),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "general": asdict(self.settings.general),
            "storage": asdict(self.settings.storage),
            "downloads": asdict(self.settings.downloads),
            "library": asdict(self.settings.library),
            "developer": asdict(self.settings.developer),
        }
