from pathlib import Path
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager, APP_NAME
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.DeveloperMode.Logging.logger import setup_logging, get_log_buffer


def test_storage_manager_initialization(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    assert storage.root == tmp_path
    assert storage.config_dir.exists()
    assert storage.cache_dir.exists()
    assert storage.artwork_cache_dir.exists()
    assert storage.metadata_cache_dir.exists()
    assert storage.downloads_temp_dir.exists()
    assert storage.games_install_dir.exists()
    assert storage.db_dir.exists()
    assert storage.logs_dir.exists()


def test_settings_manager_save_and_load(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    settings = SettingsManager(storage)

    settings.settings.general.appearance = "cyber_amber"
    settings.settings.downloads.max_concurrent_downloads = 5
    settings.save()

    new_settings = SettingsManager(storage)
    assert new_settings.settings.general.appearance == "cyber_amber"
    assert new_settings.settings.downloads.max_concurrent_downloads == 5


def test_logging_and_buffer(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    logger = setup_logging(storage.logs_dir, verbose=True)
    buffer = get_log_buffer()

    test_msg = "Dead Mans Vault Phase 1 initialized"
    logger.info(test_msg)

    logs = buffer.get_logs()
    assert any(test_msg in log for log in logs)
    assert (storage.logs_dir / "launcher.log").exists()
