"""
Centralized Styling System for PlayerV

This module provides a unified styling system for the entire application,
including theme management, style generation, and the upper toolbar.
"""

from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QGroupBox, QMenu, QDialog, QVBoxLayout as DialogLayout,
    QComboBox, QSlider, QCheckBox
)

# Settings organization
SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


class SettingsDialog(QDialog):
    """Floating settings dialog window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowTitle("PlayerV Settings")
        self.setFixedSize(400, 500)
        self.setModal(True)
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        layout = DialogLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Theme selection
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(self.settings.value("theme", "Dark", type=str).capitalize())
        self.theme_combo.currentTextChanged.connect(self.update_theme)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        # Volume control
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.settings.value("volume", 80, type=int))
        self.volume_slider.valueChanged.connect(self.update_volume)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addStretch()
        layout.addLayout(volume_layout)
        
        # Language selection
        lang_label = QLabel("Language:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Ukrainian"])
        self.lang_combo.setCurrentText(self.settings.value("language", "English", type=str))
        self.lang_combo.currentTextChanged.connect(self.update_language)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Auto scan checkbox
        self.auto_scan_check = QCheckBox("Auto scan music library on startup")
        self.auto_scan_check.setChecked(self.settings.value("auto_scan", True, type=bool))
        self.auto_scan_check.stateChanged.connect(self.update_auto_scan)
        layout.addWidget(self.auto_scan_check)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedHeight(35)
        layout.addWidget(close_btn)
    
    def update_theme(self, text):
        self.settings.setValue("theme", text.lower())
        if self.parent() and hasattr(self.parent(), 'apply_settings'):
            self.parent().apply_settings()
        self.apply_theme()
    
    def update_volume(self, value):
        self.settings.setValue("volume", value)
        if self.parent() and hasattr(self.parent(), 'apply_settings'):
            self.parent().apply_settings()
    
    def update_language(self, text):
        self.settings.setValue("language", text)
        if self.parent() and hasattr(self.parent(), 'apply_settings'):
            self.parent().apply_settings()
    
    def update_auto_scan(self, state):
        self.settings.setValue("auto_scan", state == Qt.Checked)
        if self.parent() and hasattr(self.parent(), 'apply_settings'):
            self.parent().apply_settings()
    
    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        
        if theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #2a2a2a;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QComboBox {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                }
                QComboBox:hover {
                    background-color: #4a4a4a;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #555555;
                    height: 8px;
                    background: #3a3a3a;
                    margin: 2px 0;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #1DB954;
                    border: 1px solid #179944;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #555555;
                    border-radius: 4px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #1DB954;
                    border-color: #1DB954;
                }
                QPushButton {
                    background-color: #1DB954;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                    border-radius: 3px;
                }
                QComboBox:hover {
                    background-color: #f0f0f0;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #cccccc;
                    height: 8px;
                    background: #f5f5f5;
                    margin: 2px 0;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #1DB954;
                    border: 1px solid #179944;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }
                QCheckBox {
                    color: #333333;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #999999;
                    border-radius: 4px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #1DB954;
                    border-color: #1DB954;
                }
                QPushButton {
                    background-color: #1DB954;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
            """)


class UpperToolBar(QFrame):
    """Upper toolbar with app name, add music button, and settings button.
    Reworked to use a slightly darker, panel-like background to match
    left/pages/bottom panels.
    """

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        # Назвaти об'єкта — буде корисно якщо захочете таргетити стилями
        self.setObjectName("upperPanel")

        # Не робимо повну прозорість — використовуємо напівпрозорий фон
        # (але темніший ніж раніше).
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        layout = QHBoxLayout(self)

        layout.setSpacing(15)

        # App name/logo - клікабельний
        self.app_title = QLabel("PlayerV")
        self.app_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        # Кольор тексту встановлюється у apply_theme, сюди ставимо fallback
        self.app_title.setStyleSheet("color: #ffffff;")
        self.app_title.setCursor(Qt.PointingHandCursor)
        self.app_title.mousePressEvent = self.on_app_title_clicked
        layout.addWidget(self.app_title)

        layout.addStretch()

        # Add Music button
        self.btn_add_music = QPushButton("+ Add Music")
        self.btn_add_music.setFixedHeight(35)
        self.btn_add_music.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_add_music)

        # Settings button
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(35, 35)
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setObjectName("settingsButton")
        layout.addWidget(self.btn_settings)

        # Connect signals (main_window має відповідні методи)
        try:
            self.btn_add_music.clicked.connect(self.main_window.add_music_files)
        except Exception:
            pass
        self.btn_settings.clicked.connect(self.show_settings_menu)

    def on_app_title_clicked(self, event):
        """Повернутися на домашню сторінку при кліку на заголовок."""
        if event.button() == Qt.LeftButton:
            try:
                self.main_window.show_page("home")
            except Exception:
                pass
        super().mousePressEvent(event)

    def show_settings_menu(self):
        """Відкрити вікно налаштувань (floating dialog)."""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def toggle_theme(self):
        """Переключити тему та застосувати її збереження."""
        current_theme = self.settings.value("theme", "dark", type=str)
        new_theme = "light" if current_theme == "dark" else "dark"
        self.settings.setValue("theme", new_theme)
        try:
            self.main_window.apply_settings()
        except Exception:
            pass
        self.apply_theme()

    def show_about_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About PlayerV",
                          "PlayerV Music Player\n\nA modern music player application\nbuilt with PySide6.\n\n© 2024 PlayerV Team")

    def apply_theme(self):
        """Застосувати стиль тулбару — темніший фон, округлені кути,
        невелика рамка. Узгоджено з іншими панелями (left/pages/bottom)."""
        theme = self.settings.value("theme", "dark", type=str)

        if theme == "dark":
            self.setStyleSheet("""
                QFrame#upperPanel {
                    background: rgba(24, 24, 26, 220); /* трохи темніше */
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    margin: 6px;
                    
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #1DB954;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
                QPushButton:pressed {
                    background-color: #179944;
                }
                QPushButton#settingsButton {
                    font-size: 16px;
                    padding: 0;
                    min-width: 32px;
                    min-height: 32px;
                    border-radius: 10px;
                }
            """)
        else:
            # Легка тема — також панельного вигляду, але світліше
            self.setStyleSheet("""
                QFrame#upperPanel {
                    background: rgba(250, 250, 250, 230);
                    border-radius: 12px;
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    margin: 6px;
                    padding: 6px;
                }
                QLabel {
                    color: #333333;
                }
                QPushButton {
                    background-color: #1DB954;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    padding: 6px 12px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background-color: #1ed760;
                }
                QPushButton:pressed {
                    background-color: #179944;
                }
                QPushButton#settingsButton {
                    font-size: 16px;
                    padding: 0;
                    min-width: 32px;
                    min-height: 32px;
                    border-radius: 10px;
                }
            """)



class StyleManager:
    """Centralized style manager for the entire application"""

    @staticmethod
    def get_theme_stylesheet(theme):
        """Return the complete stylesheet for the given theme"""
        if theme == "dark":
            return StyleManager.get_dark_theme()
        else:
            return StyleManager.get_light_theme()

    @staticmethod
    def get_dark_theme():
        """Return complete dark theme stylesheet"""
        return """
            /* Main application */
            QMainWindow {
                background-color: #121212;
            }

            QWidget {
                background-color: transparent;
                color: #e8e8e8;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 12px;
                selection-background-color: #1DB954;
                selection-color: white;
            }

            /* Left Panel */
            QFrame#leftPanel {
                background: rgba(30, 30, 32, 180);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            /* Pages Panel */
            QFrame#pagesPanel {
                background: rgba(24, 24, 26, 180);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            /* Bottom Panel */
            QFrame#bottomPanel {
                background: rgba(24, 24, 26, 250);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            /* Settings Frame */
            QFrame#settingsFrame {
                background-color: #252525;
                border-radius: 10px;
                border: 1px solid #333;
            }

            /* Scroll Areas */
            QScrollArea {
                background: transparent;
                border: none;
                outline: none;
            }

            QScrollBar:vertical {
                background: rgba(255, 255, 255, 10);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 50);
            }

            QScrollBar:horizontal {
                background: rgba(255, 255, 255, 10);
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 30);
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255, 255, 255, 50);
            }

            /* Buttons */
            QPushButton {
                background: rgba(40, 40, 40, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 16px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background: rgba(60, 60, 60, 0.9);
            }
            QPushButton:pressed {
                background: rgba(30, 30, 30, 0.9);
            }

            /* Player Control Buttons */
            QPushButton#playerButton {
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 22px;
            }
            QPushButton#playerButton:hover {
                background: rgba(255, 255, 255, 20);
                border-color: rgba(255, 255, 255, 25);
            }
            QPushButton#playerButton:pressed {
                background: rgba(255, 255, 255, 5);
            }
            QPushButton#playerButton:checked {
                background: rgba(29, 185, 84, 0.6);
                border-color: rgba(29, 185, 84, 0.8);
            }

            /* Progress Bar */
            QProgressBar {
                background: rgba(60, 60, 60, 200);
                border-radius: 7px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(29, 185, 84, 1), 
                    stop:0.5 rgba(35, 200, 95, 1),
                    stop:1 rgba(29, 185, 84, 1));
                border-radius: 7px;
            }

            /* Labels */
            QLabel {
                color: #e0e0e0;
            }

            /* Frames */
            QFrame {
                background: transparent;
            }

            /* Line Edits */
            QLineEdit {
                background: rgba(60, 60, 60, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
                color: #e0e0e0;
                selection-background-color: #1DB954;
            }
            QLineEdit:focus {
                border: 1px solid #1DB954;
            }

            /* Combo Boxes */
            QComboBox {
                background: rgba(60, 60, 60, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background: rgba(60, 60, 60, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: #1DB954;
                color: #e0e0e0;
            }

            /* Checkboxes */
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 4px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #1DB954;
                border-color: #1DB954;
            }
            QCheckBox::indicator:hover {
                border-color: #888888;
            }

            /* Sliders */
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: #353535;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: 1px solid #179944;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ed760;
            }

            /* Menus */
            QMenu {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1DB954;
                color: white;
            }

            /* Message Boxes */
            QMessageBox {
                background-color: #252525;
                color: #e0e0e0;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QMessageBox QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1ed760;
            }

            /* Tool Tips */
            QToolTip {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #333;
                padding: 5px;
                border-radius: 4px;
            }

            /* Input Dialogs */
            QInputDialog {
                background-color: #252525;
                color: #e0e0e0;
            }
            QInputDialog QLabel {
                color: #e0e0e0;
            }
            QInputDialog QLineEdit {
                background-color: #353535;
                color: #e0e0e0;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 4px;
            }
            QInputDialog QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QInputDialog QPushButton:hover {
                background-color: #1ed760;
            }
        """

    @staticmethod
    def get_light_theme():
        """Return complete light theme stylesheet"""
        return """
            /* Main application */
            QMainWindow {
                background-color: #f0f0f0;
            }

            QWidget {
                background-color: transparent;
                color: #333333;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 12px;
                selection-background-color: #1DB954;
                selection-color: white;
            }

            /* Left Panel */
            QFrame#leftPanel {
                background: rgba(255, 255, 255, 180);
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }

            /* Pages Panel */
            QFrame#pagesPanel {
                background: rgba(255, 255, 255, 180);
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }

            /* Bottom Panel */
            QFrame#bottomPanel {
                background: rgba(255, 255, 255, 250);
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }

            /* Settings Frame */
            QFrame#settingsFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #ddd;
            }

            /* Scroll Areas */
            QScrollArea {
                background: transparent;
                border: none;
                outline: none;
            }

            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.05);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.3);
            }

            QScrollBar:horizontal {
                background: rgba(0, 0, 0, 0.05);
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(0, 0, 0, 0.3);
            }

            /* Buttons */
            QPushButton {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 8px 16px;
                color: #333333;
            }
            QPushButton:hover {
                background: rgba(240, 240, 240, 0.9);
            }
            QPushButton:pressed {
                background: rgba(220, 220, 220, 0.9);
            }

            /* Player Control Buttons */
            QPushButton#playerButton {
                background: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 22px;
            }
            QPushButton#playerButton:hover {
                background: rgba(0, 0, 0, 0.1);
                border-color: rgba(0, 0, 0, 0.15);
            }
            QPushButton#playerButton:pressed {
                background: rgba(0, 0, 0, 0.02);
            }
            QPushButton#playerButton:checked {
                background: rgba(29, 185, 84, 0.6);
                border-color: rgba(29, 185, 84, 0.8);
            }

            /* Progress Bar */
            QProgressBar {
                background: rgba(220, 220, 220, 0.8);
                border-radius: 7px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(29, 185, 84, 1), 
                    stop:0.5 rgba(35, 200, 95, 1),
                    stop:1 rgba(29, 185, 84, 1));
                border-radius: 7px;
            }

            /* Labels */
            QLabel {
                color: #333333;
            }

            /* Frames */
            QFrame {
                background: transparent;
            }

            /* Line Edits */
            QLineEdit {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 6px;
                padding: 8px;
                color: #333333;
                selection-background-color: #1DB954;
            }
            QLineEdit:focus {
                border: 1px solid #1DB954;
            }

            /* Combo Boxes */
            QComboBox {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 6px;
                padding: 8px;
                color: #333333;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #333333;
            }
            QComboBox QAbstractItemView {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.1);
                selection-background-color: #1DB954;
                color: #333333;
            }

            /* Checkboxes */
            QCheckBox {
                color: #333333;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #999999;
                border-radius: 4px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #1DB954;
                border-color: #1DB954;
            }
            QCheckBox::indicator:hover {
                border-color: #666666;
            }

            /* Sliders */
            QSlider::groove:horizontal {
                border: 1px solid #ddd;
                height: 8px;
                background: #f5f5f5;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: 1px solid #179944;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ed760;
            }

            /* Menus */
            QMenu {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1DB954;
                color: white;
            }

            /* Message Boxes */
            QMessageBox {
                background-color: #ffffff;
                color: #333333;
            }
            QMessageBox QLabel {
                color: #333333;
            }
            QMessageBox QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1ed760;
            }

            /* Tool Tips */
            QToolTip {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #ddd;
                padding: 5px;
                border-radius: 4px;
            }

            /* Input Dialogs */
            QInputDialog {
                background-color: #ffffff;
                color: #333333;
            }
            QInputDialog QLabel {
                color: #333333;
            }
            QInputDialog QLineEdit {
                background-color: #f5f5f5;
                color: #333333;
                border: 1px solid #ddd;
                padding: 5px;
                border-radius: 4px;
            }
            QInputDialog QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QInputDialog QPushButton:hover {
                background-color: #1ed760;
            }
        """

    @staticmethod
    def apply_application_theme(app, theme):
        """Apply theme to the entire application"""
        palette = QPalette()

        if theme == "dark":
            palette.setColor(QPalette.Window, QColor(18, 18, 18))
            palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
            palette.setColor(QPalette.Base, QColor(30, 30, 30))
            palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
            palette.setColor(QPalette.ToolTipBase, QColor(26, 26, 26))
            palette.setColor(QPalette.ToolTipText, QColor(230, 230, 230))
            palette.setColor(QPalette.Text, QColor(230, 230, 230))
            palette.setColor(QPalette.Button, QColor(40, 40, 40))
            palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
            palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
            palette.setColor(QPalette.Link, QColor(29, 185, 84))
            palette.setColor(QPalette.Highlight, QColor(29, 185, 84))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        else:
            palette.setColor(QPalette.Window, QColor(240, 240, 240))
            palette.setColor(QPalette.WindowText, QColor(30, 30, 30))
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
            palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipText, QColor(30, 30, 30))
            palette.setColor(QPalette.Text, QColor(30, 30, 30))
            palette.setColor(QPalette.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ButtonText, QColor(30, 30, 30))
            palette.setColor(QPalette.BrightText, QColor(0, 0, 0))
            palette.setColor(QPalette.Link, QColor(29, 185, 84))
            palette.setColor(QPalette.Highlight, QColor(29, 185, 84))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        app.setPalette(palette)
        return StyleManager.get_theme_stylesheet(theme)