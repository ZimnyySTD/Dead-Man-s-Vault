"""Shared and local game models for Dead Man's Vault."""

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DownloadSourceType(str, Enum):
    ARCHIVE = "archive"
    B2CHUNKS = "b2"
    LOCAL = "local"


@dataclass
class GameSource:
    type: str
    url: Optional[str] = None
    manifest: Optional[str] = None
    signature: Optional[str] = None
    chunks: Optional[Dict[str, str]] = None
    checksum: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameSource":
        return cls(
            type=data.get("type", "archive"),
            url=data.get("url"),
            manifest=data.get("manifest"),
            signature=data.get("signature"),
            chunks=data.get("chunks"),
            checksum=data.get("checksum"),
        )


@dataclass
class GameDefinition:
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    source: Optional[GameSource] = None
    executable: str = ""
    launch_arguments: str = ""
    developer: str = ""
    publisher: str = ""
    release_date: str = ""
    genres: List[str] = field(default_factory=list)
    cover_image: str = ""
    background_image: str = ""
    logo_image: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "executable": self.executable,
        }
        if self.source:
            d["source"] = self.source.to_dict()
        if self.launch_arguments:
            d["launch_arguments"] = self.launch_arguments
        if self.developer:
            d["developer"] = self.developer
        if self.publisher:
            d["publisher"] = self.publisher
        if self.release_date:
            d["release_date"] = self.release_date
        if self.genres:
            d["genres"] = self.genres
        if self.cover_image:
            d["cover_image"] = self.cover_image
        if self.background_image:
            d["background_image"] = self.background_image
        if self.logo_image:
            d["logo_image"] = self.logo_image
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameDefinition":
        game_id = data.get("id") or str(uuid.uuid4())
        source = GameSource.from_dict(data["source"]) if "source" in data and data["source"] else None
        return cls(
            id=game_id,
            name=data.get("name", "Unknown Game"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            source=source,
            executable=data.get("executable", ""),
            launch_arguments=data.get("launch_arguments", ""),
            developer=data.get("developer", ""),
            publisher=data.get("publisher", ""),
            release_date=data.get("release_date", ""),
            genres=data.get("genres", []),
            cover_image=data.get("cover_image", ""),
            background_image=data.get("background_image", ""),
            logo_image=data.get("logo_image", ""),
        )


@dataclass
class LocalInstallationRecord:
    game_id: str
    install_directory: str
    executable_path: str
    working_directory: str = ""
    custom_arguments: str = ""
    installed_at: float = 0.0
    last_played: float = 0.0
    size_bytes: int = 0
    is_installed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalInstallationRecord":
        return cls(
            game_id=data["game_id"],
            install_directory=data.get("install_directory", ""),
            executable_path=data.get("executable_path", ""),
            working_directory=data.get("working_directory", ""),
            custom_arguments=data.get("custom_arguments", ""),
            installed_at=data.get("installed_at", 0.0),
            last_played=data.get("last_played", 0.0),
            size_bytes=data.get("size_bytes", 0),
            is_installed=data.get("is_installed", True),
        )


@dataclass
class GameEntry:
    definition: GameDefinition
    installation: Optional[LocalInstallationRecord] = None
    is_running: bool = False

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def is_installed(self) -> bool:
        return self.installation is not None and self.installation.is_installed
