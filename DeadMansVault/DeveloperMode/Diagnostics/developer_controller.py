"""Developer mode controller, easter egg state, and diagnostic aggregation."""

import time
from typing import Any, Callable, Dict, List, Optional

from DeadMansVault.DeveloperMode.Logging.logger import get_log_buffer
from DeadMansVault.DeveloperMode.Monitoring.system_monitor import SystemMetrics, SystemMonitor
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager


class DeveloperController:
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        self.monitor = SystemMonitor()
        self._click_timestamps: List[float] = []
        self._listeners: List[Callable[[bool], None]] = []

    @property
    def is_unlocked(self) -> bool:
        return self.settings_manager.settings.developer.developer_mode_unlocked

    @property
    def is_overlay_enabled(self) -> bool:
        return self.is_unlocked and self.settings_manager.settings.developer.debug_overlay_enabled

    def add_unlock_listener(self, listener: Callable[[bool], None]) -> None:
        self._listeners.append(listener)

    def register_build_click(self) -> bool:
        now = time.time()
        self._click_timestamps.append(now)
        self._click_timestamps = [t for t in self._click_timestamps if now - t <= 1.5]

        if len(self._click_timestamps) >= 3:
            self.settings_manager.settings.developer.developer_mode_unlocked = True
            self.settings_manager.save()
            for l in self._listeners:
                l(True)
            self._click_timestamps.clear()
            return True
        return False

    def toggle_overlay(self, enabled: Optional[bool] = None) -> bool:
        if not self.is_unlocked:
            return False
        if enabled is None:
            new_state = not self.settings_manager.settings.developer.debug_overlay_enabled
        else:
            new_state = enabled
        self.settings_manager.settings.developer.debug_overlay_enabled = new_state
        self.settings_manager.save()
        return new_state

    def get_system_metrics(self) -> SystemMetrics:
        return self.monitor.get_metrics()

    def get_logs(self) -> List[str]:
        return get_log_buffer().get_logs()

    def clear_logs(self) -> None:
        get_log_buffer().clear()
