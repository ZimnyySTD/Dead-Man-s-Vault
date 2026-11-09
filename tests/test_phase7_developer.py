import time
from pathlib import Path
import pytest

from DeadMansVault.Storage.Configuration.storage_manager import StorageManager
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.DeveloperMode.Diagnostics.developer_controller import DeveloperController
from DeadMansVault.DeveloperMode.Monitoring.system_monitor import SystemMonitor


def test_system_monitor():
    monitor = SystemMonitor()
    metrics = monitor.get_metrics()
    assert metrics.total_system_ram_mb > 0
    assert metrics.available_system_ram_mb > 0
    assert metrics.app_memory_rss_mb > 0
    assert metrics.platform_name != ""


def test_developer_triple_click_unlock(tmp_path):
    storage = StorageManager(base_dir=tmp_path)
    settings = SettingsManager(storage)
    dev_ctrl = DeveloperController(settings)

    assert not dev_ctrl.is_unlocked
    assert not dev_ctrl.is_overlay_enabled

    assert not dev_ctrl.register_build_click()
    assert not dev_ctrl.is_unlocked

    assert not dev_ctrl.register_build_click()
    assert not dev_ctrl.is_unlocked

    assert dev_ctrl.register_build_click()
    assert dev_ctrl.is_unlocked

    enabled = dev_ctrl.toggle_overlay(True)
    assert enabled
    assert dev_ctrl.is_overlay_enabled

    new_settings = SettingsManager(storage)
    assert new_settings.settings.developer.developer_mode_unlocked
    assert new_settings.settings.developer.debug_overlay_enabled
