"""Full desktop user interface implementation for Dead Man's Vault."""

import os
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from DeadMansVault.DeveloperMode.Diagnostics.developer_controller import DeveloperController
from DeadMansVault.DownloadManager.Queue.download_manager import DownloadManager
from DeadMansVault.GameRunner.game_runner import GameRunner
from DeadMansVault.Installer.ArchiveInstaller.archive_installer import (
    InstallationManager,
    InstallationProgress,
    InstallationStage,
)
from DeadMansVault.Launcher.Settings.settings_manager import SettingsManager
from DeadMansVault.Launcher.UI.theme import DARK_THEME_QSS
from DeadMansVault.Library.GameDefinitions.game_model import GameDefinition, GameEntry, GameSource
from DeadMansVault.Library.GameDefinitions.games_json_manager import GamesJsonManager
from DeadMansVault.Library.GameMetadata.metadata_service import MetadataService
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry
from DeadMansVault.Storage.Configuration.storage_manager import APP_BUILD, APP_NAME, APP_VERSION, StorageManager


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class GameCardWidget(QFrame):
    game_selected = Signal(str)

    def __init__(self, game_entry: GameEntry, parent=None):
        super().__init__(parent)
        self.game_entry = game_entry
        self.setObjectName("GameCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            #GameCard {
                background-color: #16181E;
                border: 1px solid #232733;
                border-radius: 8px;
            }
            #GameCard:hover {
                border: 1px solid #F59E0B;
                background-color: #1D2028;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(160, 210)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #0E0F12; border-radius: 4px; color: #475569;")

        if game_entry.definition.cover_image and Path(game_entry.definition.cover_image).exists():
            pix = QPixmap(game_entry.definition.cover_image).scaled(
                160, 210, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.setText(game_entry.name[:2].upper())
            self.cover_label.setFont(QFont("Arial", 24, QFont.Bold))

        layout.addWidget(self.cover_label)

        self.title_label = QLabel(game_entry.name)
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #E2E8F0;")
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumWidth(160)
        layout.addWidget(self.title_label)

        status_text = "READY TO PLAY" if game_entry.is_installed else "NOT INSTALLED"
        status_color = "#10B981" if game_entry.is_installed else "#94A3B8"
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.status_label)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.game_selected.emit(self.game_entry.id)
        super().mousePressEvent(event)


class LibraryView(QWidget):
    open_game_details = Signal(str)

    def __init__(self, registry: GameRegistry, runner: GameRunner, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.runner = runner

        self.layout_mode = "grid"
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        header_bar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search games...")
        self.search_input.textChanged.connect(self.refresh_library)
        header_bar.addWidget(self.search_input, stretch=3)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Games", "Installed", "Available"])
        self.filter_combo.currentIndexChanged.connect(self.refresh_library)
        header_bar.addWidget(self.filter_combo, stretch=1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name (A-Z)", "Name (Z-A)", "Installed First", "Recently Played"])
        self.sort_combo.currentIndexChanged.connect(self.refresh_library)
        header_bar.addWidget(self.sort_combo, stretch=1)

        self.layout_toggle_btn = QPushButton("Grid")
        self.layout_toggle_btn.clicked.connect(self._toggle_layout)
        header_bar.addWidget(self.layout_toggle_btn)

        main_layout.addLayout(header_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda item: self.open_game_details.emit(item.data(Qt.UserRole)))

        self.container_layout.addWidget(self.grid_widget)
        self.container_layout.addWidget(self.list_widget)
        self.list_widget.hide()

        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)

        self.refresh_library()

    def _toggle_layout(self):
        if self.layout_mode == "grid":
            self.layout_mode = "list"
            self.layout_toggle_btn.setText("List")
            self.grid_widget.hide()
            self.list_widget.show()
        else:
            self.layout_mode = "grid"
            self.layout_toggle_btn.setText("Grid")
            self.list_widget.hide()
            self.grid_widget.show()
        self.refresh_library()

    def refresh_library(self):
        q = self.search_input.text()
        f_idx = self.filter_combo.currentIndex()
        filter_status = "all" if f_idx == 0 else ("installed" if f_idx == 1 else "not_installed")

        s_idx = self.sort_combo.currentIndex()
        if s_idx == 0:
            sort_by, sort_order = "name", "asc"
        elif s_idx == 1:
            sort_by, sort_order = "name", "desc"
        elif s_idx == 2:
            sort_by, sort_order = "installed", "desc"
        else:
            sort_by, sort_order = "recent", "desc"

        games = self.registry.search_and_filter(
            query=q,
            filter_status=filter_status,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.list_widget.clear()

        cols = 4
        for i, game in enumerate(games):
            card = GameCardWidget(game)
            card.game_selected.connect(self.open_game_details.emit)
            self.grid_layout.addWidget(card, i // cols, i % cols)

        for game in games:
            status = "Installed" if game.is_installed else "Available"
            item = QListWidgetItem(f"{game.name}  [{status}] - v{game.definition.version}")
            item.setData(Qt.UserRole, game.id)
            self.list_widget.addItem(item)


class GameDetailsView(QWidget):
    back_to_library = Signal()
    game_state_changed = Signal()

    def __init__(
        self,
        registry: GameRegistry,
        runner: GameRunner,
        installer: InstallationManager,
        metadata_service: MetadataService,
        parent=None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.runner = runner
        self.installer = installer
        self.metadata_service = metadata_service
        self.current_game_id: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        back_btn = QPushButton("← Back to Library")
        back_btn.setFixedWidth(140)
        back_btn.clicked.connect(self.back_to_library.emit)
        layout.addWidget(back_btn)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(220, 310)
        self.cover_label.setStyleSheet("background-color: #15171D; border: 1px solid #232734; border-radius: 8px;")
        self.cover_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        self.title_label = QLabel("Game Title")
        self.title_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(self.title_label)

        self.meta_label = QLabel("Developer • Publisher • Genre")
        self.meta_label.setStyleSheet("color: #94A3B8; font-size: 13px;")
        info_layout.addWidget(self.meta_label)

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(120)
        self.desc_text.setStyleSheet("background-color: transparent; border: none; color: #CBD5E1;")
        info_layout.addWidget(self.desc_text)

        btn_bar = QHBoxLayout()
        self.action_btn = QPushButton("PLAY")
        self.action_btn.setProperty("class", "primary")
        self.action_btn.setFixedHeight(40)
        self.action_btn.setFixedWidth(160)
        self.action_btn.clicked.connect(self._on_action_clicked)
        btn_bar.addWidget(self.action_btn)

        self.edit_btn = QPushButton("Edit Metadata")
        self.edit_btn.setFixedHeight(40)
        self.edit_btn.clicked.connect(self._edit_metadata)
        btn_bar.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setFixedHeight(40)
        self.remove_btn.clicked.connect(self._remove_game)
        btn_bar.addWidget(self.remove_btn)
        btn_bar.addStretch()

        info_layout.addLayout(btn_bar)

        self.path_info = QLabel()
        self.path_info.setStyleSheet("color: #64748B; font-size: 11px;")
        info_layout.addWidget(self.path_info)

        content_layout.addLayout(info_layout)
        layout.addLayout(content_layout)
        layout.addStretch()

    def load_game(self, game_id: str):
        self.current_game_id = game_id
        entry = self.registry.get_game(game_id)
        if not entry:
            return

        self.title_label.setText(entry.name)
        meta_str = f"{entry.definition.developer or 'Unknown'} | {entry.definition.publisher or 'Independent'} | {', '.join(entry.definition.genres) if entry.definition.genres else 'General'}"
        self.meta_label.setText(meta_str)
        self.desc_text.setText(entry.definition.description or "No description provided.")

        if entry.definition.cover_image and Path(entry.definition.cover_image).exists():
            pix = QPixmap(entry.definition.cover_image).scaled(
                220, 310, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.setText(entry.name[:2].upper())
            self.cover_label.setFont(QFont("Arial", 36, QFont.Bold))

        is_running = self.runner.is_game_running(game_id)
        if is_running:
            self.action_btn.setText("STOP")
            self.action_btn.setStyleSheet("background-color: #DC2626; color: white;")
            self.path_info.setText(f"Status: RUNNING (PID active)")
        elif entry.is_installed:
            self.action_btn.setText("PLAY")
            self.action_btn.setStyleSheet("background-color: #D97706; color: white;")
            self.path_info.setText(f"Installed at: {entry.installation.install_directory}")
        else:
            self.action_btn.setText("INSTALL")
            self.action_btn.setStyleSheet("background-color: #2563EB; color: white;")
            self.path_info.setText("Status: Not installed locally")

    def _on_action_clicked(self):
        if not self.current_game_id:
            return

        entry = self.registry.get_game(self.current_game_id)
        if not entry:
            return

        if self.runner.is_game_running(self.current_game_id):
            self.runner.stop_game(self.current_game_id)
            self.load_game(self.current_game_id)
            self.game_state_changed.emit()
            return

        if entry.is_installed:
            try:
                self.runner.launch_game(self.current_game_id)
                self.load_game(self.current_game_id)
                self.game_state_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Launch Error", str(e))
        else:
            self.installer.install_game(
                entry.definition,
                callback=lambda p: QTimer.singleShot(0, lambda: self.load_game(self.current_game_id)),
            )
            QMessageBox.information(
                self, "Installation", f"Installation started for {entry.name}. Track progress in Downloads tab."
            )

    def _edit_metadata(self):
        if not self.current_game_id:
            return
        entry = self.registry.get_game(self.current_game_id)
        if not entry:
            return

        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Edit Game Name", "Title:", text=entry.name)
        if ok and new_name.strip():
            entry.definition.name = new_name.strip()
            self.registry.add_or_update_game(entry.definition)
            self.load_game(self.current_game_id)
            self.game_state_changed.emit()

    def _remove_game(self):
        if not self.current_game_id:
            return
        res = QMessageBox.question(
            self,
            "Remove Game",
            "Are you sure you want to remove this game from your library?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.registry.remove_game(self.current_game_id, delete_files=False)
            self.game_state_changed.emit()
            self.back_to_library.emit()


class AddGameView(QWidget):
    game_added = Signal(str)

    def __init__(
        self,
        registry: GameRegistry,
        installer: InstallationManager,
        metadata_service: MetadataService,
        parent=None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.installer = installer
        self.metadata_service = metadata_service

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Add Game to Vault")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        method_bar = QHBoxLayout()
        self.folder_btn = QPushButton("📁 Local Folder")
        self.archive_btn = QPushButton("📦 Archive Download")
        self.b2_btn = QPushButton("⚡ B2Chunks Manifest")

        for btn in [self.folder_btn, self.archive_btn, self.b2_btn]:
            btn.setCheckable(True)
            method_bar.addWidget(btn)
        method_bar.addStretch()
        layout.addLayout(method_bar)

        self.stack = QStackedWidget()

        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        self.folder_path_input = QLineEdit()
        self.folder_path_input.setPlaceholderText("Select folder on disk...")
        browse_f_btn = QPushButton("Browse Folder")
        browse_f_btn.clicked.connect(self._browse_folder)
        row1 = QHBoxLayout()
        row1.addWidget(self.folder_path_input)
        row1.addWidget(browse_f_btn)
        l1.addLayout(row1)

        self.folder_game_name = QLineEdit()
        self.folder_game_name.setPlaceholderText("Game Name (Optional)")
        l1.addWidget(self.folder_game_name)

        import_f_btn = QPushButton("Import Local Folder")
        import_f_btn.setProperty("class", "primary")
        import_f_btn.clicked.connect(self._import_folder)
        l1.addWidget(import_f_btn)
        l1.addStretch()
        self.stack.addWidget(p1)

        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        self.archive_url_input = QLineEdit()
        self.archive_url_input.setPlaceholderText("Archive URL (http://... .zip / .7z / .tar.gz)")
        l2.addWidget(self.archive_url_input)

        self.archive_name_input = QLineEdit()
        self.archive_name_input.setPlaceholderText("Game Name")
        l2.addWidget(self.archive_name_input)

        import_a_btn = QPushButton("Download and Install Archive")
        import_a_btn.setProperty("class", "primary")
        import_a_btn.clicked.connect(self._import_archive)
        l2.addWidget(import_a_btn)
        l2.addStretch()
        self.stack.addWidget(p2)

        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        self.b2_manifest_input = QLineEdit()
        self.b2_manifest_input.setPlaceholderText("B2Chunks Manifest URL or File Path...")
        browse_b2_btn = QPushButton("Browse Manifest")
        browse_b2_btn.clicked.connect(self._browse_manifest)
        row3 = QHBoxLayout()
        row3.addWidget(self.b2_manifest_input)
        row3.addWidget(browse_b2_btn)
        l3.addLayout(row3)

        self.b2_name_input = QLineEdit()
        self.b2_name_input.setPlaceholderText("Game Name")
        l3.addWidget(self.b2_name_input)

        import_b2_btn = QPushButton("Import and Install B2Chunks")
        import_b2_btn.setProperty("class", "primary")
        import_b2_btn.clicked.connect(self._import_b2)
        l3.addWidget(import_b2_btn)
        l3.addStretch()
        self.stack.addWidget(p3)

        layout.addWidget(self.stack)

        self.folder_btn.clicked.connect(lambda: self._set_method(0))
        self.archive_btn.clicked.connect(lambda: self._set_method(1))
        self.b2_btn.clicked.connect(lambda: self._set_method(2))

        self.folder_btn.setChecked(True)

    def _set_method(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.folder_btn.setChecked(idx == 0)
        self.archive_btn.setChecked(idx == 1)
        self.b2_btn.setChecked(idx == 2)

    def _browse_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Select Game Folder")
        if f:
            self.folder_path_input.setText(f)
            if not self.folder_game_name.text():
                self.folder_game_name.setText(Path(f).name)

    def _browse_manifest(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Manifest", filter="B2Chunks Manifest (*.b2m *.json)")
        if f:
            self.b2_manifest_input.setText(f)
            if not self.b2_name_input.text():
                self.b2_name_input.setText(Path(f).stem)

    def _import_folder(self):
        path = self.folder_path_input.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Error", "Please provide a valid folder path.")
            return

        name = self.folder_game_name.text().strip() or Path(path).name
        entry = self.registry.import_local_folder(Path(path), game_name=name)

        self._lookup_metadata_async(entry.id, name)
        self.game_added.emit(entry.id)
        QMessageBox.information(self, "Success", f"Game '{name}' imported into library!")

    def _import_archive(self):
        url = self.archive_url_input.text().strip()
        name = self.archive_name_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please provide a download URL.")
            return

        import uuid
        game_id = str(uuid.uuid4())
        name = name or Path(url.split("?")[0]).stem

        game_def = GameDefinition(
            id=game_id,
            name=name,
            source=GameSource(type="archive", url=url),
        )
        self.registry.add_or_update_game(game_def)
        self.installer.install_game(game_def)

        self._lookup_metadata_async(game_id, name)
        self.game_added.emit(game_id)
        QMessageBox.information(self, "Downloading", f"Archive download started for '{name}'!")

    def _import_b2(self):
        manifest = self.b2_manifest_input.text().strip()
        name = self.b2_name_input.text().strip()
        if not manifest:
            QMessageBox.warning(self, "Error", "Please provide a manifest path or URL.")
            return

        import uuid
        game_id = str(uuid.uuid4())
        name = name or Path(manifest).stem

        game_def = GameDefinition(
            id=game_id,
            name=name,
            source=GameSource(type="b2", manifest=manifest),
        )
        self.registry.add_or_update_game(game_def)
        self.installer.install_game(game_def)

        self._lookup_metadata_async(game_id, name)
        self.game_added.emit(game_id)
        QMessageBox.information(self, "Installing", f"B2Chunks install started for '{name}'!")

    def _lookup_metadata_async(self, game_id: str, game_name: str):
        import threading
        def worker():
            try:
                results = self.metadata_service.search_metadata(game_name)
                if results:
                    top = results[0]
                    entry = self.registry.get_game(game_id)
                    if entry:
                        entry.definition.description = top.description
                        entry.definition.developer = top.developer
                        entry.definition.publisher = top.publisher
                        entry.definition.genres = top.genres
                        if top.cover_url:
                            cover_p = self.metadata_service.cache_artwork_from_url(top.cover_url, "cover")
                            if cover_p:
                                entry.definition.cover_image = str(cover_p)
                        self.registry.add_or_update_game(entry.definition)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()


class DownloadsView(QWidget):
    def __init__(self, installer: InstallationManager, registry: GameRegistry, parent=None):
        super().__init__(parent)
        self.installer = installer
        self.registry = registry

        self._init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_downloads)
        self.timer.start(500)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Downloads & Installations")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Game", "Stage", "Progress", "Speed", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def _refresh_downloads(self):
        installs = list(self.installer.active_installs.values())
        self.table.setRowCount(len(installs))

        for row, p in enumerate(installs):
            game = self.registry.get_game(p.game_id)
            name = game.name if game else p.game_id

            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(p.stage.value.capitalize()))

            pbar = QProgressBar()
            pbar.setValue(int(p.progress_fraction * 100))
            self.table.setCellWidget(row, 2, pbar)

            speed_mb = p.download_speed_bps / (1024 * 1024)
            speed_text = f"{speed_mb:.1f} MB/s" if p.download_speed_bps > 0 else "-"
            self.table.setItem(row, 3, QTableWidgetItem(speed_text))

            if p.stage in [InstallationStage.DOWNLOADING, InstallationStage.EXTRACTING]:
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(lambda _, gid=p.game_id: self.installer.cancel_installation(gid))
                self.table.setCellWidget(row, 4, cancel_btn)
            else:
                self.table.setItem(row, 4, QTableWidgetItem(p.stage.value))


class SettingsView(QWidget):
    def __init__(
        self,
        settings_manager: SettingsManager,
        developer_controller: DeveloperController,
        registry: GameRegistry,
        parent=None,
    ):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.developer_controller = developer_controller
        self.registry = registry

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Settings")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)

        st_label = QLabel("Storage")
        st_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(st_label)

        inst_row = QHBoxLayout()
        inst_row.addWidget(QLabel("Default Install Directory:"))
        self.inst_dir_input = QLineEdit(self.settings_manager.settings.storage.default_install_dir)
        inst_row.addWidget(self.inst_dir_input)
        layout.addLayout(inst_row)

        dl_label = QLabel("Downloads")
        dl_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(dl_label)

        concur_row = QHBoxLayout()
        concur_row.addWidget(QLabel("Max Concurrent Downloads:"))
        self.concur_spin = QSpinBox()
        self.concur_spin.setRange(1, 10)
        self.concur_spin.setValue(self.settings_manager.settings.downloads.max_concurrent_downloads)
        concur_row.addWidget(self.concur_spin)
        concur_row.addStretch()
        layout.addLayout(concur_row)

        lib_label = QLabel("Library Import / Export")
        lib_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(lib_label)

        btn_row = QHBoxLayout()
        exp_btn = QPushButton("Export games.json")
        exp_btn.clicked.connect(self._export_games_json)
        imp_btn = QPushButton("Import games.json")
        imp_btn.clicked.connect(self._import_games_json)
        btn_row.addWidget(exp_btn)
        btn_row.addWidget(imp_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.dev_section = QWidget()
        dev_l = QVBoxLayout(self.dev_section)
        dev_l.setContentsMargins(0, 10, 0, 0)
        d_lbl = QLabel("Developer Mode Diagnostics")
        d_lbl.setFont(QFont("Arial", 14, QFont.Bold))
        d_lbl.setStyleSheet("color: #F59E0B;")
        dev_l.addWidget(d_lbl)

        self.overlay_chk = QCheckBox("Enable Performance Debug Overlay HUD")
        self.overlay_chk.setChecked(self.developer_controller.is_overlay_enabled)
        self.overlay_chk.toggled.connect(self.developer_controller.toggle_overlay)
        dev_l.addWidget(self.overlay_chk)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(120)
        dev_l.addWidget(self.log_text)

        refresh_logs_btn = QPushButton("Refresh Logs")
        refresh_logs_btn.clicked.connect(self._refresh_logs)
        dev_l.addWidget(refresh_logs_btn)

        layout.addWidget(self.dev_section)
        self.dev_section.setVisible(self.developer_controller.is_unlocked)

        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

    def update_developer_visibility(self):
        self.dev_section.setVisible(self.developer_controller.is_unlocked)
        self.overlay_chk.setChecked(self.developer_controller.is_overlay_enabled)

    def _refresh_logs(self):
        logs = self.developer_controller.get_logs()
        self.log_text.setText("\n".join(logs[-100:]))

    def _save_settings(self):
        self.settings_manager.settings.storage.default_install_dir = self.inst_dir_input.text().strip()
        self.settings_manager.settings.downloads.max_concurrent_downloads = self.concur_spin.value()
        self.settings_manager.save()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _export_games_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export games.json", "games.json", "JSON (*.json)")
        if path:
            GamesJsonManager.export_library(
                Path(path), [e.definition for e in self.registry.get_all_games()]
            )
            QMessageBox.information(self, "Export", f"Successfully exported games to {path}")

    def _import_games_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import games.json", filter="JSON (*.json)")
        if path:
            try:
                imported = GamesJsonManager.import_library(Path(path))
                for g in imported:
                    self.registry.add_or_update_game(g)
                QMessageBox.information(self, "Import", f"Successfully imported {len(imported)} games!")
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", str(e))


class DebugOverlayWidget(QFrame):
    def __init__(self, developer_controller: DeveloperController, parent=None):
        super().__init__(parent)
        self.developer_controller = developer_controller
        self.setObjectName("DebugOverlay")
        self.setFixedSize(220, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header = QLabel("DEV HUD • PERFORMANCE")
        header.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 10px;")
        layout.addWidget(header)

        self.cpu_label = QLabel("CPU: 0.0%")
        self.ram_label = QLabel("RAM: 0 MB")
        self.sys_ram_label = QLabel("SYS: 0 MB")
        self.gpu_label = QLabel("GPU: Active")

        for lbl in [self.cpu_label, self.ram_label, self.sys_ram_label, self.gpu_label]:
            lbl.setStyleSheet("color: #10B981; font-family: monospace; font-size: 11px;")
            layout.addWidget(lbl)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)

    def update_metrics(self):
        if not self.isVisible():
            return
        metrics = self.developer_controller.get_system_metrics()
        self.cpu_label.setText(f"App CPU: {metrics.cpu_usage_percent:.1f}%")
        self.ram_label.setText(f"App RAM: {metrics.app_memory_rss_mb:.1f} MB")
        self.sys_ram_label.setText(f"Sys RAM: {metrics.available_system_ram_mb:.0f}/{metrics.total_system_ram_mb:.0f} MB")
        self.gpu_label.setText(f"GPU: {metrics.gpu_info[:18]}")


class MainWindow(QMainWindow):
    def __init__(
        self,
        storage_manager: StorageManager,
        settings_manager: SettingsManager,
        registry: GameRegistry,
        metadata_service: MetadataService,
        download_manager: DownloadManager,
        installer: InstallationManager,
        runner: GameRunner,
        developer_controller: DeveloperController,
    ):
        super().__init__()
        self.storage_manager = storage_manager
        self.settings_manager = settings_manager
        self.registry = registry
        self.metadata_service = metadata_service
        self.download_manager = download_manager
        self.installer = installer
        self.runner = runner
        self.developer_controller = developer_controller

        self.setWindowTitle("Dead Man's Vault")
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(DARK_THEME_QSS)

        self.developer_controller.add_unlock_listener(self._on_developer_unlocked)

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 18, 14, 18)
        side_layout.setSpacing(12)

        logo_path = self.storage_manager.root.parent / "logo.png"
        if not logo_path.exists():
            logo_path = Path(__file__).parent.parent.parent / "Resources" / "logo.png"

        if logo_path.exists():
            logo_lbl = QLabel()
            pix = QPixmap(str(logo_path)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignCenter)
            side_layout.addWidget(logo_lbl)

        title_lbl = QLabel("DEAD MAN'S VAULT")
        title_lbl.setObjectName("AppTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(title_lbl)

        side_layout.addSpacing(20)

        self.nav_library_btn = QPushButton("🎮  Library")
        self.nav_downloads_btn = QPushButton("📥  Downloads")
        self.nav_add_game_btn = QPushButton("➕  Add Game")
        self.nav_settings_btn = QPushButton("⚙️  Settings")

        self.nav_buttons = [
            self.nav_library_btn,
            self.nav_downloads_btn,
            self.nav_add_game_btn,
            self.nav_settings_btn,
        ]

        for idx, btn in enumerate(self.nav_buttons):
            btn.setProperty("class", "nav-button")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self.switch_page(i))
            side_layout.addWidget(btn)

        side_layout.addStretch()

        self.build_lbl = ClickableLabel(f"v{APP_VERSION} (build {APP_BUILD})")
        self.build_lbl.setObjectName("BuildLabel")
        self.build_lbl.setAlignment(Qt.AlignCenter)
        self.build_lbl.setCursor(Qt.PointingHandCursor)
        self.build_lbl.clicked.connect(self._on_build_clicked)
        side_layout.addWidget(self.build_lbl)

        main_layout.addWidget(sidebar)

        self.stack = QStackedWidget()

        self.library_view = LibraryView(self.registry, self.runner)
        self.library_view.open_game_details.connect(self.show_game_details)

        self.game_details_view = GameDetailsView(
            self.registry, self.runner, self.installer, self.metadata_service
        )
        self.game_details_view.back_to_library.connect(lambda: self.switch_page(0))
        self.game_details_view.game_state_changed.connect(self.library_view.refresh_library)

        self.downloads_view = DownloadsView(self.installer, self.registry)
        self.add_game_view = AddGameView(self.registry, self.installer, self.metadata_service)
        self.add_game_view.game_added.connect(self._on_game_added)

        self.settings_view = SettingsView(
            self.settings_manager, self.developer_controller, self.registry
        )

        self.stack.addWidget(self.library_view)  # 0
        self.stack.addWidget(self.downloads_view)  # 1
        self.stack.addWidget(self.add_game_view)  # 2
        self.stack.addWidget(self.settings_view)  # 3
        self.stack.addWidget(self.game_details_view)  # 4

        main_layout.addWidget(self.stack)

        self.debug_overlay = DebugOverlayWidget(self.developer_controller, self)
        self.debug_overlay.move(self.width() - 240, 20)
        self.debug_overlay.setVisible(self.developer_controller.is_overlay_enabled)

        self.switch_page(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "debug_overlay"):
            self.debug_overlay.move(self.width() - 240, 20)

    def switch_page(self, page_index: int):
        self.stack.setCurrentIndex(page_index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)
            if i == page_index:
                btn.setStyleSheet("background-color: #27231B; color: #F59E0B; border-left: 3px solid #F59E0B; font-weight: bold;")
            else:
                btn.setStyleSheet("")

        if page_index == 0:
            self.library_view.refresh_library()
        elif page_index == 3:
            self.settings_view.update_developer_visibility()

    def show_game_details(self, game_id: str):
        self.game_details_view.load_game(game_id)
        self.stack.setCurrentIndex(4)

    def _on_game_added(self, game_id: str):
        self.library_view.refresh_library()
        self.show_game_details(game_id)

    def _on_build_clicked(self):
        unlocked = self.developer_controller.register_build_click()
        if unlocked:
            QMessageBox.information(
                self,
                "Developer Mode",
                "Developer mode unlocked!\nAccess advanced diagnostics and debug overlay in Settings.",
            )
            self._on_developer_unlocked(True)

    def _on_developer_unlocked(self, unlocked: bool):
        self.settings_view.update_developer_visibility()
        self.debug_overlay.setVisible(self.developer_controller.is_overlay_enabled)
