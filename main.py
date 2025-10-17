import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QIcon, QPalette, QColor

from gui_base.sidebar import Sidebar
from gui_base.home_page import HomePage
from gui_base.library_page import LibraryPage
from gui_base.settings_page import SettingsPage

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

        self.setWindowTitle("PlayerV")
        self.setMinimumSize(QSize(900, 600))

        # Load window geometry only
        self.restoreGeometry(self.settings.value("window_geometry", b""))

        # Initialize UI
        self.init_sidebar()
        self.init_pages()

        # Apply initial settings
        self.apply_settings()

        # Set initial page
        self.show_page("home")

    def init_sidebar(self):
        self.sidebar = Sidebar(self, self.settings)

        # Завжди додаємо sidebar зліва (фіксовано)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)
        self.sidebar.setVisible(True)  # завжди показуємо

    def closeEvent(self, event):
        # Save window geometry only
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.sync()

        # Clean up resources
        self.page_home.cleanup()
        super().closeEvent(event)

    def init_pages(self):
        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)

        self.page_home = HomePage(self.settings)
        self.page_library = LibraryPage(self.settings)
        self.page_settings = SettingsPage(self.settings, self.apply_settings)

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_library)
        self.pages.addWidget(self.page_settings)
        pages_layout.addWidget(self.pages)
        row.addWidget(self.pages_container, 1)

        central_layout.addLayout(row)

        # Нижня панель
        self.bottom_container = QFrame()
        self.bottom_container.setObjectName("bottomPanel")
        bottom_layout = QHBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(10)

        # Прогрес-бар зліва
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self._progress_value)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        bottom_layout.addWidget(self.progress_bar, 1, Qt.AlignVCenter)

        # Кнопки по центру
        controls = QHBoxLayout()
        controls.setSpacing(12)

        self.btn_prev = QPushButton("⏮")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("⏭")

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,10);
                    border: 1px solid rgba(255,255,255,15);
                    border-radius: 22px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,20);
                }
                QPushButton:pressed {
                    background: rgba(255,255,255,5);
                }
            """)

    def show_page(self, page):
        if page == "home":
            self.pages.setCurrentWidget(self.page_home)
        elif page == "library":
            self.pages.setCurrentWidget(self.page_library)
        elif page == "settings":
            self.pages.setCurrentWidget(self.page_settings)
            self.page_settings.apply_settings(self.settings)

    def apply_settings(self):
        try:
            # Тепер не рухаємо/не ховаємо sidebar
            self.apply_theme()

            # Apply settings to pages
            self.page_home.apply_settings(self.settings)
            self.page_library.apply_settings(self.settings)

            self.settings.sync()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        try:
            if theme == "dark":
                # Dark theme
                palette = QPalette()
                palette.setColor(QPalette.Window, QColor(18, 18, 18))
                palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
                palette.setColor(QPalette.Base, QColor(24, 24, 24))
                palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
                palette.setColor(QPalette.ToolTipBase, QColor(40, 40, 40))
                palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
                palette.setColor(QPalette.Text, QColor(255, 255, 255))
                palette.setColor(QPalette.Button, QColor(30, 30, 30))
                palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
                palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
                palette.setColor(QPalette.Highlight, QColor(29, 185, 84))
                palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
                palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
                QApplication.setPalette(palette)

                self.setStyleSheet("""
                    QMainWindow { background-color: #121212; }
                    QDockWidget { background-color: #000000; border: 1px solid #333; }
                    QDockWidget::title { background: #000000; padding: 4px; color: white; }
                """)
            else:
                # Light theme
                palette = QPalette()
                palette.setColor(QPalette.Window, QColor(240, 240, 240))
                palette.setColor(QPalette.WindowText, QColor(30, 30, 30))
                palette.setColor(QPalette.Base, QColor(255, 255, 255))
                palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
                palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
                palette.setColor(QPalette.ToolTipText, QColor(30, 30, 30))
                palette.setColor(QPalette.Text, QColor(30, 30, 30))
                palette.setColor(QPalette.Button, QColor(240, 240, 240))
                palette.setColor(QPalette.ButtonText, QColor(30, 30, 30))
                palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
                palette.setColor(QPalette.Highlight, QColor(29, 185, 84))
                palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
                palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
                QApplication.setPalette(palette)

                self.setStyleSheet("""
                    QMainWindow { background-color: #f5f5f5; }
                    QDockWidget { background-color: #ffffff; border: 1px solid #ddd; }
                    QDockWidget::title { background: #ffffff; padding: 4px; color: black; }
                """)

            # Apply theme to sidebar
            self.sidebar.apply_theme(theme)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply theme: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if os.path.exists("app_icon.png"):
        app.setWindowIcon(QIcon("app_icon.png"))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
