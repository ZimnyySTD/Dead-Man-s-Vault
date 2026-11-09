from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Library.GameMetadata.metadata_service import MetadataService, RetrievedMetadata


def test_clean_game_name():
    assert MetadataService.clean_game_name("Hollow.Knight.[v1.5.78]-(Portable)") == "Hollow Knight"
    assert MetadataService.clean_game_name("Dead_Cells.zip") == "Dead Cells"
    assert MetadataService.clean_game_name("Doom_Eternal") == "Doom Eternal"


def test_fallback_metadata(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    service = MetadataService(storage)
    fallback = service.generate_fallback_metadata("My_Custom_Game [Build 10]")
    assert fallback.title == "My Custom Game"
    assert "My Custom Game" in fallback.description


def test_metadata_caching(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    service = MetadataService(storage)

    meta = RetrievedMetadata(
        title="Test Game",
        description="Epic test game description.",
        developer="Test Dev",
        publisher="Test Pub",
        genres=["Action", "RPG"],
        cover_url="https://example.com/cover.jpg",
    )

    cached_path = service.cache_metadata("game-test-1", meta)
    assert cached_path.exists()

    loaded = service.get_cached_metadata("game-test-1")
    assert loaded is not None
    assert loaded.title == "Test Game"
    assert loaded.developer == "Test Dev"
    assert loaded.genres == ["Action", "RPG"]


@patch("requests.Session.get")
def test_search_metadata_mocked(mock_get, tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    service = MetadataService(storage)

    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "items": [{"id": 12345, "name": "Dark Souls"}]
    }

    mock_details_resp = MagicMock()
    mock_details_resp.status_code = 200
    mock_details_resp.json.return_value = {
        "12345": {
            "success": True,
            "data": {
                "name": "Dark Souls",
                "short_description": "Prepare to Die.",
                "genres": [{"description": "Action RPG"}],
                "header_image": "https://example.com/ds.jpg",
                "developers": ["FromSoftware"],
                "publishers": ["Bandai Namco"],
                "release_date": {"date": "Sep 22, 2011"},
            },
        }
    }

    def side_effect(url, *args, **kwargs):
        if "storesearch" in url:
            return mock_search_resp
        elif "appdetails" in url:
            return mock_details_resp
        return MagicMock(status_code=404)

    mock_get.side_effect = side_effect

    results = service.search_metadata("Dark Souls")
    assert len(results) >= 1
    assert results[0].title == "Dark Souls"
    assert results[0].description == "Prepare to Die."
    assert "FromSoftware" in results[0].developer
