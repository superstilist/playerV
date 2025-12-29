from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFormLayout, QCheckBox, QFrame, QSlider
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

        title = QLabel("Settings")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        settings_frame = QFrame()
        settings_frame.setObjectName("settingsFrame")
        form_layout = QFormLayout(settings_frame)
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        form_layout.setContentsMargins(20, 20, 20, 20)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(settings.value("theme", "Dark", type=str).capitalize())
        self.theme_combo.currentTextChanged.connect(self.update_theme)
        form_layout.addRow("Theme:", self.theme_combo)

        self.show_cover_check = QCheckBox("Show cover art")
        self.show_cover_check.setChecked(settings.value("show_cover", True, type=bool))
        self.show_cover_check.stateChanged.connect(self.update_show_cover)
        form_layout.addRow("", self.show_cover_check)

        self.show_sidebar_check = QCheckBox("Show sidebar")
        self.show_sidebar_check.setChecked(settings.value("show_sidebar", True, type=bool))
        self.show_sidebar_check.stateChanged.connect(self.update_show_sidebar)
        form_layout.addRow("", self.show_sidebar_check)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(settings.value("volume", 80, type=int))
        self.volume_slider.valueChanged.connect(self.update_volume)
        form_layout.addRow("Volume:", self.volume_slider)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Українська"])
        self.language_combo.setCurrentText(settings.value("language", "English", type=str))
        self.language_combo.currentTextChanged.connect(self.update_language)
        form_layout.addRow("Language:", self.language_combo)

        self.auto_scan_check = QCheckBox("Auto scan on startup")
        self.auto_scan_check.setChecked(settings.value("auto_scan", True, type=bool))
        self.auto_scan_check.stateChanged.connect(self.update_auto_scan)
        form_layout.addRow("", self.auto_scan_check)

        layout.addWidget(settings_frame)
        layout.addStretch()

    def update_theme(self, text):
        self.settings.setValue("theme", text.lower())
        self.apply_callback()

    def update_show_sidebar(self, state):
        self.settings.setValue("show_sidebar", state == Qt.Checked)
        self.apply_callback()

    def update_show_cover(self, state):
        self.settings.setValue("show_cover", state == Qt.Checked)
        self.apply_callback()

    def update_volume(self, value):
        self.settings.setValue("volume", value)
        self.apply_callback()

    def update_language(self, text):
        self.settings.setValue("language", text)
        self.apply_callback()

    def update_auto_scan(self, state):
        self.settings.setValue("auto_scan", state == Qt.Checked)
        self.apply_callback()

    def apply_settings(self, settings):
        self.settings = settings
        self.theme_combo.setCurrentText(settings.value("theme", "dark", type=str).capitalize())
        self.show_cover_check.setChecked(settings.value("show_cover", True, type=bool))
        self.show_sidebar_check.setChecked(settings.value("show_sidebar", True, type=bool))
        self.volume_slider.setValue(settings.value("volume", 80, type=int))
        self.language_combo.setCurrentText(settings.value("language", "English", type=str))
        self.auto_scan_check.setChecked(settings.value("auto_scan", True, type=bool))