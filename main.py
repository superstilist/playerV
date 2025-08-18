import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox, QStyle
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

        # Load window state
        self.restoreGeometry(self.settings.value("window_geometry", b""))

        # Initialize UI
        self.init_sidebar()
        self.init_pages()

        # Apply initial settings
        self.apply_settings()

        # Set initial page
        self.show_page("home")

    def init_sidebar(self):
        # Create sidebar
        self.sidebar = Sidebar(self, self.settings)

        # Set sidebar position
        sidebar_position = Qt.DockWidgetArea(
            int(self.settings.value("sidebar_position", Qt.LeftDockWidgetArea))
        )
        self.addDockWidget(sidebar_position, self.sidebar)

        # Set sidebar visibility
        self.sidebar.setVisible(self.settings.value("show_sidebar", True, type=bool))

    def init_pages(self):
        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)

        self.page_home = HomePage(self.settings)
        self.page_library = LibraryPage(self.settings)
        self.page_settings = SettingsPage(self.settings, self.apply_settings)

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_library)
        self.pages.addWidget(self.page_settings)

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
            # Update sidebar position
            sidebar_position = Qt.DockWidgetArea(
                int(self.settings.value("sidebar_position", Qt.LeftDockWidgetArea))
            )
            self.removeDockWidget(self.sidebar)
            self.addDockWidget(sidebar_position, self.sidebar)

            # Update sidebar visibility
            self.sidebar.setVisible(self.settings.value("show_sidebar", True, type=bool))

            # Apply theme
            self.apply_theme()

            # Apply settings to pages
            self.page_home.apply_settings(self.settings)
            self.page_library.apply_settings(self.settings)

            # Save settings
            self.settings.sync()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        try:
            if theme == "dark":
                # Dark theme
                palette = QPalette()
                palette.setColor(QPalette.Window, QColor(30, 30, 30))
                palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
                palette.setColor(QPalette.Base, QColor(20, 20, 20))
                palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
                palette.setColor(QPalette.ToolTipBase, QColor(40, 40, 40))
                palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
                palette.setColor(QPalette.Text, QColor(220, 220, 220))
                palette.setColor(QPalette.Button, QColor(50, 50, 50))
                palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
                palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
                palette.setColor(QPalette.Highlight, QColor(100, 100, 200))
                palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
                palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
                QApplication.setPalette(palette)

                # Additional styling
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #1e1e1e;
                    }
                    QDockWidget {
                        background-color: #252525;
                        border: 1px solid #333;
                        titlebar-close-icon: url(close_light.png);
                        titlebar-normal-icon: url(float_light.png);
                    }
                    QDockWidget::title {
                        background: #252525;
                        padding: 4px;
                    }
                    QListWidget {
                        background-color: #252525;
                        border: 1px solid #333;
                        border-radius: 4px;
                    }
                    QListWidget::item {
                        padding: 10px;
                        border-bottom: 1px solid #333;
                    }
                    QListWidget::item:selected {
                        background-color: #3a3a3a;
                    }
                    QLineEdit {
                        background-color: #353535;
                        color: #e0e0e0;
                        padding: 8px 15px;
                        border-radius: 20px;
                        font-size: 14px;
                        border: 1px solid #444;
                    }
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
                palette.setColor(QPalette.Highlight, QColor(100, 150, 230))
                palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
                palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
                QApplication.setPalette(palette)

                # Additional styling
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #f5f5f5;
                    }
                    QDockWidget {
                        background-color: #ffffff;
                        border: 1px solid #ddd;
                    }
                    QDockWidget::title {
                        background: #ffffff;
                        padding: 4px;
                    }
                    QListWidget {
                        background-color: #ffffff;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    QListWidget::item {
                        padding: 10px;
                        border-bottom: 1px solid #eee;
                    }
                    QListWidget::item:selected {
                        background-color: #e0e0e0;
                    }
                    QLineEdit {
                        background-color: #ffffff;
                        color: #333333;
                        padding: 8px 15px;
                        border-radius: 20px;
                        font-size: 14px;
                        border: 1px solid #ddd;
                    }
                """)

            # Apply theme to sidebar
            self.sidebar.apply_theme(theme)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply theme: {str(e)}")

    def closeEvent(self, event):
        # Save window state
        self.settings.setValue("window_geometry", self.saveGeometry())

        # Save settings
        self.settings.sync()

        # Clean up resources
        self.page_home.cleanup()

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application icon
    if os.path.exists("app_icon.png"):
        app.setWindowIcon(QIcon("app_icon.png"))

    win = MainWindow()
    win.show()

    # Handle application exit
    ret = app.exec()
    sys.exit(ret)