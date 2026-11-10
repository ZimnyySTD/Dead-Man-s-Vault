"""Metadata retrieval, caching, and fallback management for Dead Man's Vault."""

import hashlib
import json
import logging
import re
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager

logger = logging.getLogger("DeadMansVault.GameMetadata")


@dataclass
class RetrievedMetadata:
    title: str
    description: str = ""
    release_date: str = ""
    developer: str = ""
    publisher: str = ""
    genres: List[str] = field(default_factory=list)
    cover_url: str = ""
    background_url: str = ""
    logo_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievedMetadata":
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            release_date=data.get("release_date", ""),
            developer=data.get("developer", ""),
            publisher=data.get("publisher", ""),
            genres=data.get("genres", []),
            cover_url=data.get("cover_url", ""),
            background_url=data.get("background_url", ""),
            logo_url=data.get("logo_url", ""),
        )


class MetadataService:
    def __init__(self, storage_manager: StorageManager, session: Optional[requests.Session] = None):
        self.storage_manager = storage_manager
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "DeadMansVault/1.0.0 (Windows NT 10.0; Win64; x64) Desktop Game Launcher"
        })

    def search_metadata(self, game_name: str, timeout: int = 5) -> List[RetrievedMetadata]:
        clean_name = self.clean_game_name(game_name)
        if not clean_name:
            return []

        results: List[RetrievedMetadata] = []
        try:
            url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(clean_name)}&l=english&cc=US"
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("items", [])[:5]:
                    appid = item.get("id")
                    meta = self._fetch_steam_app_details(appid, timeout=timeout)
                    if meta:
                        results.append(meta)
                    else:
                        results.append(
                            RetrievedMetadata(
                                title=item.get("name", clean_name),
                                cover_url=item.get("tiny_image", ""),
                            )
                        )
        except Exception as e:
            logger.warning(f"Metadata search failed for '{game_name}': {e}")

        if not results:
            results.append(self.generate_fallback_metadata(game_name))

        return results

    def _fetch_steam_app_details(self, appid: int, timeout: int = 5) -> Optional[RetrievedMetadata]:
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                app_data = data.get(str(appid), {})
                if app_data.get("success"):
                    d = app_data.get("data", {})
                    raw_desc = d.get("short_description", "")
                    clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()

                    genres = [g.get("description", "") for g in d.get("genres", [])]
                    devs = ", ".join(d.get("developers", []))
                    pubs = ", ".join(d.get("publishers", []))

                    cover = (
                        d.get("header_image")
                        or f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg"
                    )
                    bg = d.get("background") or d.get("background_raw", "")

                    return RetrievedMetadata(
                        title=d.get("name", ""),
                        description=clean_desc,
                        release_date=d.get("release_date", {}).get("date", ""),
                        developer=devs,
                        publisher=pubs,
                        genres=genres,
                        cover_url=cover,
                        background_url=bg,
                        logo_url="",
                    )
        except Exception as e:
            logger.debug(f"Failed to fetch Steam app details for {appid}: {e}")
        return None

    @staticmethod
    def clean_game_name(name: str) -> str:
        cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", name)
        cleaned = re.sub(r"\.(zip|rar|7z|tar|gz|exe)$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[_.-]", " ", cleaned)
        return cleaned.strip()

    def generate_fallback_metadata(self, name: str) -> RetrievedMetadata:
        clean_name = self.clean_game_name(name)
        return RetrievedMetadata(
            title=clean_name,
            description=f"Local game entry for {clean_name}.",
            genres=["Action / Adventure"],
        )

    def cache_metadata(self, game_id: str, metadata: RetrievedMetadata) -> Path:
        path = self.storage_manager.metadata_cache_dir / f"{game_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        return path

    def get_cached_metadata(self, game_id: str) -> Optional[RetrievedMetadata]:
        path = self.storage_manager.metadata_cache_dir / f"{game_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return RetrievedMetadata.from_dict(data)
        except Exception:
            return None

    def cache_artwork_from_url(self, image_url: str, category: str = "cover") -> Optional[Path]:
        if not image_url or not image_url.startswith("http"):
            return None

        url_hash = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:16]
        ext = ".jpg"
        if ".png" in image_url.lower():
            ext = ".png"
        elif ".webp" in image_url.lower():
            ext = ".webp"

        cached_file = self.storage_manager.artwork_cache_dir / f"{category}_{url_hash}{ext}"
        if cached_file.exists() and cached_file.stat().st_size > 0:
            return cached_file

        try:
            resp = self.session.get(image_url, timeout=10, stream=True)
            if resp.status_code == 200:
                with open(cached_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return cached_file
        except Exception as e:
            logger.warning(f"Failed to cache artwork from {image_url}: {e}")

        return None
