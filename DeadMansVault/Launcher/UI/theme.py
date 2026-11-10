"""Dark charcoal, metallic, muted amber styling stylesheets for Dead Man's Vault."""

DARK_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #121316;
    color: #E0E2E6;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

#Sidebar {
    background-color: #0E0F12;
    border-right: 1px solid #1E2127;
    min-width: 220px;
    max-width: 220px;
}

#AppTitle {
    color: #F59E0B;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 1px;
}

#BuildLabel {
    color: #64748B;
    font-size: 11px;
}
#BuildLabel:hover {
    color: #F59E0B;
}

QPushButton {
    background-color: #1C1E24;
    border: 1px solid #2A2E38;
    border-radius: 6px;
    color: #D1D5DB;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #262932;
    border-color: #3E4352;
    color: #FFFFFF;
}
QPushButton:pressed {
    background-color: #17191E;
}

QPushButton.nav-button {
    text-align: left;
    padding: 10px 18px;
    font-size: 14px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: #9CA3AF;
}
QPushButton.nav-button:hover {
    background-color: #1E2129;
    color: #F3F4F6;
}
QPushButton.nav-button:checked, QPushButton.nav-button.active {
    background-color: #27231B;
    color: #F59E0B;
    border-left: 3px solid #F59E0B;
    font-weight: bold;
}

QPushButton.primary {
    background-color: #D97706;
    border: 1px solid #B45309;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton.primary:hover {
    background-color: #F59E0B;
    border-color: #D97706;
}

QLineEdit, QTextEdit, QComboBox {
    background-color: #181A20;
    border: 1px solid #282C37;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F3F4F6;
    selection-background-color: #D97706;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #F59E0B;
}

QListWidget, QTableWidget {
    background-color: #14161B;
    border: 1px solid #20242D;
    border-radius: 6px;
}
QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px 4px;
}
QListWidget::item:hover {
    background-color: #1F232D;
}
QListWidget::item:selected {
    background-color: #2E271D;
    border-left: 2px solid #F59E0B;
    color: #F59E0B;
}

QProgressBar {
    background-color: #1A1D24;
    border: 1px solid #2A2F3D;
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #D97706;
    border-radius: 3px;
}

QScrollBar:vertical {
    border: none;
    background: #121316;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2D313D;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #474E61;
}

#DebugOverlay {
    background-color: rgba(15, 17, 21, 230);
    border: 1px solid #F59E0B;
    border-radius: 8px;
    color: #10B981;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 10px;
}
"""
