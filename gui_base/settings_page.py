from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFormLayout, QCheckBox, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SettingsPage(QWidget):
    def __init__(self, settings, apply_callback):
        super().__init__()
        self.settings = settings
        self.apply_callback = apply_callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Title
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Settings container
        settings_frame = QFrame()
        settings_frame.setObjectName("settingsFrame")
        form_layout = QFormLayout(settings_frame)
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(settings.value("theme", "Dark", type=str).capitalize())
        self.theme_combo.currentTextChanged.connect(self.update_theme)
        form_layout.addRow("Theme:", self.theme_combo)







        layout.addWidget(settings_frame)
        layout.addStretch()

        # Apply initial styling
        self.apply_styling()

    def apply_styling(self):
        if self.settings.value("theme", "dark", type=str) == "dark":
            self.setStyleSheet("""
                #settingsFrame {
                    background-color: #252525;
                    border-radius: 10px;
                    border: 1px solid #333;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QComboBox, QCheckBox {
                    background-color: #353535;
                    color: #e0e0e0;
                    border: 1px solid #444;
                    padding: 5px;
                    border-radius: 4px;
                }
                QComboBox::drop-down {
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                #settingsFrame {
                    background-color: #ffffff;
                    border-radius: 10px;
                    border: 1px solid #ddd;
                }
                QLabel {
                    color: #333333;
                }
                QComboBox, QCheckBox {
                    background-color: #f5f5f5;
                    color: #333333;
                    border: 1px solid #ddd;
                    padding: 5px;
                    border-radius: 4px;
                }
                QComboBox::drop-down {
                    border: none;
                }
            """)

    def update_sidebar_pos(self, text):
        self.settings.setValue("sidebar_position", Qt.LeftDockWidgetArea if text == "Left" else Qt.RightDockWidgetArea)
        self.apply_callback()

    def update_theme(self, text):
        self.settings.setValue("theme", text.lower())
        self.apply_styling()
        self.apply_callback()

    def update_show_sidebar(self, state):
        self.settings.setValue("show_sidebar", state == Qt.Checked)
        self.apply_callback()

    def update_show_cover(self, state):
        self.settings.setValue("show_cover", state == Qt.Checked)
        self.apply_callback()

    def apply_settings(self, settings):
        self.settings = settings
        self.theme_combo.setCurrentText(settings.value("theme", "dark", type=str).capitalize())
        self.apply_styling()