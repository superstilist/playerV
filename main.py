import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QProgressBar, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, QSize, QSettings, QTimer
from PySide6.QtGui import QIcon, QPalette, QColor, QFont

from gui_base.home_page import HomePage
from gui_base.playist_page import Playlist
from gui_base.settings_page import SettingsPage

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowTitle("PlayerV")
        self.setMinimumSize(QSize(1100, 700))

        # Відновлення збереженої геометрії
        geom = self.settings.value("window_geometry", None)
        if geom:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

        # Стан плеєра
        self._is_playing = False
        self._progress_value = 0

        self.init_ui()
        self.apply_theme()
        self.apply_settings()

        # Таймер для демонстрації прогресу
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self.show_page("home")

    # ---------- UI ----------
    def init_ui(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(14, 14, 14, 14)
        central_layout.setSpacing(12)

        
        row = QHBoxLayout()
        row.setSpacing(12)


        self.left_container = QFrame()
        self.left_container.setObjectName("leftPanel")
        self.left_container.setFixedWidth(320)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title = QLabel("Плейлисти")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_layout.addWidget(left_title)

        self.left_playlist = Playlist(self.settings)
        left_layout.addWidget(self.left_playlist)
        row.addWidget(self.left_container)

        # Панель сторінок
        self.pages_container = QFrame()
        self.pages_container.setObjectName("pagesPanel")
        pages_layout = QVBoxLayout(self.pages_container)
        pages_layout.setContentsMargins(10, 10, 10, 10)
        pages_layout.setSpacing(8)

        self.pages = QStackedWidget()
        self.page_home = HomePage(self.settings)
        self.page_playlist_page = Playlist(self.settings)
        self.page_settings = SettingsPage(self.settings, self.apply_settings)

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_playlist_page)
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

        self.btn_prev.clicked.connect(self.on_prev)
        self.btn_play.clicked.connect(self.on_play_pause)
        self.btn_next.clicked.connect(self.on_next)

        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)

        bottom_layout.addLayout(controls)

        central_layout.addWidget(self.bottom_container)
        self.setCentralWidget(central)

        self.setStyleSheet(self.build_stylesheet())

    # ---------- логіка кнопок ----------
    def on_play_pause(self):
        if self._is_playing:
            self._timer.stop()
            self._is_playing = False
            self.btn_play.setText("▶")
        else:
            self._timer.start()
            self._is_playing = True
            self.btn_play.setText("⏸")

    def on_prev(self):
        self._progress_value = 0
        self.progress_bar.setValue(self._progress_value)

    def on_next(self):
        self._progress_value = 0
        self.progress_bar.setValue(self._progress_value)

    def _on_tick(self):
        self._progress_value += 5
        if self._progress_value > 100:
            self._progress_value = 0
        self.progress_bar.setValue(self._progress_value)

    # ---------- Теми ----------
    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        pal = QPalette()
        if theme == "dark":
            pal.setColor(QPalette.Window, QColor(18, 18, 18))
            pal.setColor(QPalette.WindowText, QColor(230, 230, 230))
        else:
            pal.setColor(QPalette.Window, QColor(245, 245, 245))
            pal.setColor(QPalette.WindowText, QColor(30, 30, 30))
        QApplication.setPalette(pal)

    def build_stylesheet(self) -> str:
        return """
        QWidget {
            background: transparent;
            color: #e8e8e8;
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 12px;
        }

        QFrame#leftPanel {
            background: rgba(30,30,32,180);
            border-radius: 16px;
        }
        QFrame#pagesPanel {
            background: rgba(24,24,26,180);
            border-radius: 16px;
        }
        QFrame#bottomPanel {
            background: rgba(18,18,20,200);
            border-radius: 16px;
        }

        QProgressBar {
            background: rgba(255,255,255,10);
            border-radius: 8px;
            min-height: 12px;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 #1DB954, stop:1 #179944);
            border-radius: 8px;
        }
        """

    # ---------- Сторінки ----------
    def show_page(self, page: str):
        if page == "home":
            self.pages.setCurrentWidget(self.page_home)
        elif page == "library":
            self.pages.setCurrentWidget(self.page_playlist_page)
        elif page == "settings":
            self.pages.setCurrentWidget(self.page_settings)
            try:
                self.page_settings.apply_settings(self.settings)
            except Exception:
                pass

    def apply_settings(self):
        try:
            self.page_home.apply_settings(self.settings)
        except Exception:
            pass
        try:
            self.page_playlist_page.apply_settings(self.settings)
        except Exception:
            pass
        try:
            self.left_playlist.apply_settings(self.settings)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.sync()
        except Exception:
            pass
        try:
            self.page_home.cleanup()
        except Exception:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if os.path.exists("app_icon.png"):
        app.setWindowIcon(QIcon("app_icon.png"))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
