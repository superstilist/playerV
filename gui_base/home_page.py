from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QPixmap


class HomePage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Cover art section
        self.cover_container = QWidget()
        cover_layout = QVBoxLayout(self.cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        # Cover frame with shadow
        self.cover_frame = QFrame()
        self.cover_frame.setMinimumSize(320, 320)
        self.cover_frame.setMaximumSize(400, 400)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self.cover_frame)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.cover_frame.setGraphicsEffect(shadow)

        # Cover placeholder
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setMinimumSize(300, 300)
        self.update_cover_art()

        cover_layout.addWidget(self.cover_frame)
        layout.addWidget(self.cover_container, 0, Qt.AlignCenter)

        # Track info
        track_layout = QVBoxLayout()
        track_layout.setSpacing(8)

        self.track_title = QLabel("Chill Vibes")
        self.track_title.setFont(QFont("Arial", 20, QFont.Bold))
        self.track_title.setAlignment(Qt.AlignCenter)

        self.track_artist = QLabel("Various Artists")
        self.track_artist.setFont(QFont("Arial", 16))
        self.track_artist.setAlignment(Qt.AlignCenter)

        self.track_album = QLabel("Relaxing Tunes Vol. 1")
        self.track_album.setFont(QFont("Arial", 14))
        self.track_album.setAlignment(Qt.AlignCenter)
        self.track_album.setStyleSheet("color: #888;")

        track_layout.addWidget(self.track_title)
        track_layout.addWidget(self.track_artist)
        track_layout.addWidget(self.track_album)
        layout.addLayout(track_layout)

        # Add stretch to fill space
        layout.addStretch()

    def update_cover_art(self):
        # Create a placeholder cover art
        pixmap = QPixmap(300, 300)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        bg_color = QColor(80, 120, 200) if self.settings.value("theme", "dark") == "dark" else QColor(180, 200, 240)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 300, 300, 10, 10)

        # Draw musical note
        note_color = QColor(220, 220, 220, 200)
        painter.setBrush(QBrush(note_color))
        painter.setPen(Qt.NoPen)

        # Draw note body
        painter.drawEllipse(130, 100, 40, 40)
        painter.drawRect(150, 140, 10, 100)

        # Draw note stem
        painter.drawRect(110, 80, 10, 60)
        painter.drawRect(100, 140, 30, 10)

        painter.end()

        self.cover_label.setPixmap(pixmap)
        self.cover_frame.setLayout(QVBoxLayout())
        self.cover_frame.layout().addWidget(self.cover_label)

    def apply_settings(self, settings):
        try:
            self.settings = settings

            # Update visibility
            show_cover = settings.value("show_cover", True, type=bool)
            self.cover_container.setVisible(show_cover)

            # Update cover art
            self.update_cover_art()
        except Exception as e:
            print(f"Error applying settings to home page: {str(e)}")

    def cleanup(self):
        # Clean up resources
        pass