import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from DeadMansVault.Launcher.Application.main import create_app
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameSource


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@patch("PySide6.QtWidgets.QMessageBox.information")
@patch("PySide6.QtWidgets.QMessageBox.warning")
@patch("PySide6.QtWidgets.QMessageBox.question")
def test_main_window_lifecycle_and_pages(mock_question, mock_warning, mock_info, qapp, tmp_path):
    app, window = create_app(storage_dir=tmp_path)
    assert window is not None
    assert window.windowTitle() == "Dead Man's Vault"

    g = GameDefinition(id="test-ui-game", name="Chrono Vault", version="1.0.0")
    window.registry.add_or_update_game(g)

    window.library_view.refresh_library()
    assert window.library_view.grid_layout.count() >= 1

    window.switch_page(1)
    assert window.stack.currentIndex() == 1

    window.switch_page(2)
    assert window.stack.currentIndex() == 2

    window.switch_page(3)
    assert window.stack.currentIndex() == 3

    window.show_game_details("test-ui-game")
    assert window.stack.currentIndex() == 4
    assert window.game_details_view.title_label.text() == "Chrono Vault"

    assert not window.developer_controller.is_unlocked
    window.build_lbl.clicked.emit()
    window.build_lbl.clicked.emit()
    window.build_lbl.clicked.emit()

    assert window.developer_controller.is_unlocked
    assert not window.settings_view.dev_section.isHidden()

    window.close()
