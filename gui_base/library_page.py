from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QFrame, \
    QLineEdit, QGridLayout, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QLinearGradient


class LibraryPage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Title
        title = QLabel("Your Library")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Search bar
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search playlists, artists, albums...")
        self.search_field.setMinimumHeight(40)
        search_layout.addWidget(self.search_field)

        layout.addWidget(search_container)

        # Scroll area for playlists
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Playlist grid container
        playlists_container = QWidget()
        self.playlists_layout = QGridLayout(playlists_container)
        self.playlists_layout.setContentsMargins(10, 10, 10, 10)
        self.playlists_layout.setSpacing(20)

        scroll_area.setWidget(playlists_container)
        layout.addWidget(scroll_area)

        # Add sample playlists
        self.populate_playlists()

    def populate_playlists(self):
        playlists = [
            {"name": "Chill Vibes", "count": 24, "color": (80, 120, 200)},
            {"name": "Workout Mix", "count": 18, "color": (200, 80, 100)},
            {"name": "Focus Time", "count": 32, "color": (80, 180, 120)},
            {"name": "Road Trip", "count": 42, "color": (180, 120, 80)},
            {"name": "Throwbacks", "count": 56, "color": (160, 100, 200)},
            {"name": "Summer Hits", "count": 38, "color": (240, 180, 60)},
            {"name": "Relaxing Jazz", "count": 28, "color": (100, 160, 180)},
            {"name": "Electronic Dance", "count": 45, "color": (180, 100, 220)}
        ]

        for i, playlist in enumerate(playlists):
            # Create playlist widget
            playlist_widget = QFrame()
            playlist_widget.setMinimumSize(180, 220)
            playlist_widget.setMaximumSize(200, 240)
            playlist_widget.setStyleSheet("""
                QFrame {
                    background-color: #181818;
                    border-radius: 8px;
                }
                QFrame:hover {
                    background-color: #282828;
                }
            """)

            playlist_layout = QVBoxLayout(playlist_widget)
            playlist_layout.setContentsMargins(10, 10, 10, 10)
            playlist_layout.setSpacing(10)

            # Create playlist icon
            icon_size = QSize(160, 160)
            icon_label = QLabel()
            icon_label.setFixedSize(icon_size)
            icon_label.setAlignment(Qt.AlignCenter)

            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw background with gradient
            gradient = QLinearGradient(0, 0, icon_size.width(), icon_size.height())
            gradient.setColorAt(0, QColor(playlist["color"][0], playlist["color"][1], playlist["color"][2]))
            gradient.setColorAt(1,
                                QColor(playlist["color"][0] // 2, playlist["color"][1] // 2, playlist["color"][2] // 2))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, icon_size.width(), icon_size.height(), 8, 8)

            # Draw musical note
            note_color = QColor(255, 255, 255, 200)
            painter.setBrush(QBrush(note_color))

            # Draw note body
            painter.drawEllipse(60, 50, 40, 40)
            painter.drawRect(75, 90, 10, 50)

            # Draw note stem
            painter.drawRect(45, 35, 10, 40)
            painter.drawRect(35, 75, 30, 10)

            painter.end()

            icon_label.setPixmap(pixmap)
            playlist_layout.addWidget(icon_label)

            # Playlist info
            name_label = QLabel(playlist["name"])
            name_label.setFont(QFont("Arial", 14, QFont.Bold))
            name_label.setStyleSheet("color: white;")
            name_label.setWordWrap(True)
            playlist_layout.addWidget(name_label)

            count_label = QLabel(f"{playlist['count']} tracks")
            count_label.setFont(QFont("Arial", 12))
            count_label.setStyleSheet("color: #b3b3b3;")
            playlist_layout.addWidget(count_label)

            # Add to grid
            row = i // 4
            col = i % 4
            self.playlists_layout.addWidget(playlist_widget, row, col)

    def apply_settings(self, settings):
        # Theme is now handled globally in MainWindow
        pass