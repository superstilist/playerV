from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QStyle
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QLinearGradient, QColor, QBrush
import os

class Sidebar(QDockWidget):
    def __init__(self, main_window, settings):
        super().__init__("Menu")
        self.main_window = main_window
        self.settings = settings

        # Configure dock widget
        self.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.setTitleBarWidget(QWidget(self))  # Custom title bar

        # Create main content widget
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(12)

        # App header
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

        # User profile section
        user_frame = QFrame()
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(10, 15, 10, 10)
        user_layout.setSpacing(10)

        # User avatar placeholder
        avatar = QLabel()
        avatar.setFixedSize(60, 60)
        avatar.setAlignment(Qt.AlignCenter)

        # Draw a placeholder avatar
        pixmap = QPixmap(60, 60)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(80, 120, 200)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(5, 5, 50, 50)
        painter.setFont(QFont("Arial", 24))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "U")
        painter.end()
        avatar.setPixmap(pixmap)
        avatar.setAlignment(Qt.AlignCenter)

        # User info
        user_name = QLabel("User Profile")
        user_name.setAlignment(Qt.AlignCenter)
        user_name.setFont(QFont("Arial", 10, QFont.Bold))

        user_layout.addWidget(avatar, 0, Qt.AlignCenter)
        user_layout.addWidget(user_name)
        layout.addWidget(user_frame)

        self.setWidget(widget)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Apply initial theme
        self.apply_theme(self.settings.value("theme", "dark", type=str))

    def create_nav_button(self, text, icon_path, page, fallback_icon):
        btn = QPushButton(text)
        btn.setMinimumHeight(45)

        # Set icon if available
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        else:
            # Use fallback standard icon
            btn.setIcon(self.main_window.style().standardIcon(fallback_icon))

        btn.setIconSize(QSize(24, 24))
        btn.clicked.connect(lambda: self.main_window.show_page(page))
        return btn

    def apply_theme(self, theme):
        try:
            if theme == "dark":
                # Dark theme styling
                self.setStyleSheet("""
                    QDockWidget {
                        background-color: #252525;
                        border: 1px solid #333;
                    }
                    QPushButton {
                        background-color: #353535;
                        color: #e0e0e0;
                        border: none;
                        border-radius: 4px;
                        padding: 12px 15px;
                        text-align: left;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;
                    }
                    QPushButton:pressed {
                        background-color: #2a2a2a;
                    }
                    QPushButton:checked {
                        background-color: #2a5a7a;
                    }
                    QLabel {
                        color: #e0e0e0;
                    }
                    QFrame {
                        background-color: #2a2a2a;
                        border-radius: 8px;
                    }
                """)
            else:
                # Light theme styling
                self.setStyleSheet("""
                    QDockWidget {
                        background-color: #ffffff;
                        border: 1px solid #ddd;
                    }
                    QPushButton {
                        background-color: #f5f5f5;
                        color: #333333;
                        border: none;
                        border-radius: 4px;
                        padding: 12px 15px;
                        text-align: left;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #eaeaea;
                    }
                    QPushButton:pressed {
                        background-color: #e0e0e0;
                    }
                    QPushButton:checked {
                        background-color: #c0d8f0;
                    }
                    QLabel {
                        color: #333333;
                    }
                    QFrame {
                        background-color: #f0f0f0;
                        border-radius: 8px;
                    }
                """)
        except Exception as e:
            print(f"Error applying theme to sidebar: {str(e)}")