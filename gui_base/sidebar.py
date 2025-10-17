from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QStyle
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush
import os


class Sidebar(QDockWidget):
    def __init__(self, main_window, settings):
        super().__init__("Menu")
        self.main_window = main_window
        self.settings = settings

        # ---- Dock config ----
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)  # прибирає можливість рухати/закривати
        self.setTitleBarWidget(QWidget(self))  # без заголовка
        self.setFixedWidth(200)  # фіксована ширина панелі

        # ---- Content ----
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # Header
        header = QLabel("PlayerV")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Navigation buttons
        icon_map = {
            "Home": QStyle.SP_DirHomeIcon,
            "Discover": QStyle.SP_FileDialogContentsView,
            "Library": QStyle.SP_DirIcon,
            "Settings": QStyle.SP_ComputerIcon
        }
        self.btn_home = self.create_nav_button("Home", "home_icon.png", "home", icon_map["Home"])
        self.btn_library = self.create_nav_button("Library", "library_icon.png", "library", icon_map["Library"])
        self.btn_settings = self.create_nav_button("Settings", "settings_icon.png", "settings", icon_map["Settings"])

        layout.addWidget(self.btn_home)
        layout.addWidget(self.btn_library)
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        # User Profile
        user_frame = QFrame()
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(5, 10, 5, 10)
        user_layout.setSpacing(6)

        avatar = QLabel()
        avatar.setFixedSize(50, 50)
        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(80, 120, 200)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 50, 50)
        painter.setFont(QFont("Arial", 20))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "U")
        painter.end()
        avatar.setPixmap(pixmap)
        avatar.setAlignment(Qt.AlignCenter)

        user_name = QLabel("User Profile")
        user_name.setAlignment(Qt.AlignCenter)
        user_name.setFont(QFont("Arial", 10, QFont.Bold))

        user_layout.addWidget(avatar, 0, Qt.AlignCenter)
        user_layout.addWidget(user_name)
        layout.addWidget(user_frame)

        self.setWidget(widget)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)  # тільки зліва

        # Apply theme
        self.apply_theme(self.settings.value("theme", "dark", type=str))

    def create_nav_button(self, text, icon_path, page, fallback_icon):
        btn = QPushButton(text)
        btn.setMinimumHeight(40)


        # Icon
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        else:
            btn.setIcon(self.main_window.style().standardIcon(fallback_icon))
        btn.setIconSize(QSize(20, 20))

        btn.clicked.connect(lambda: self.main_window.show_page(page))
        return btn

    def apply_theme(self, theme):
        if theme == "dark":
            self.setStyleSheet("""
                QDockWidget {
                    background-color: #252525;
                    border: 1px solid #333;
                }
                QPushButton {
                    background-color: #2e2e2e;
                    color: #e0e0e0;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    padding: 6px 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
                QPushButton:pressed {
                    background-color: #1f1f1f;
                }
                QPushButton:checked {
                    background-color: #2a5a7a;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QFrame {
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QDockWidget {
                    background-color: #ffffff;
                    border: 1px solid #ddd;
                }
                QPushButton {
                    background-color: #f5f5f5;
                    color: #333;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    padding: 6px 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #eaeaea;
                }
                QPushButton:pressed {
                    background-color: #d9d9d9;
                }
                QPushButton:checked {
                    background-color: #c0d8f0;
                }
                QLabel {
                    color: #333333;
                }
                QFrame {
                    background-color: transparent;
                }
            """)
