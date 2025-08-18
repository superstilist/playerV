from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QFrame, QLineEdit
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush


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

        # Playlist list
        self.playlist_list = QListWidget()
        self.playlist_list.setIconSize(QSize(60, 60))
        self.playlist_list.setSpacing(12)
        self.playlist_list.setStyleSheet("""
            QListWidget {
                border-radius: 8px;
            }
            QListWidget::item {
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.playlist_list)

        # Add sample playlists
        self.populate_playlists()

        # Add some padding at bottom
        layout.addStretch()

    def populate_playlists(self):
        playlists = [
            {"name": "Chill Vibes", "count": 24, "color": (80, 120, 200)},
            {"name": "Workout Mix", "count": 18, "color": (200, 80, 100)},
            {"name": "Focus Time", "count": 32, "color": (80, 180, 120)},
            {"name": "Road Trip", "count": 42, "color": (180, 120, 80)},
            {"name": "Throwbacks", "count": 56, "color": (160, 100, 200)}
        ]

        for playlist in playlists:
            # Create playlist icon
            icon_size = QSize(60, 60)
            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw background
            bg_color = QColor(*playlist["color"])
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, icon_size.width(), icon_size.height(), 10, 10)

            # Draw musical note
            note_color = QColor(220, 220, 220, 200)
            painter.setBrush(QBrush(note_color))

            # Draw note body
            painter.drawEllipse(15, 15, 30, 30)
            painter.drawRect(25, 45, 10, 10)

            painter.end()

            # Create list item
            item = QListWidgetItem(QIcon(pixmap), f"{playlist['name']}\n{playlist['count']} tracks")
            item.setSizeHint(QSize(100, 80))
            self.playlist_list.addItem(item)

    def apply_settings(self, settings):
        # Theme is now handled globally in MainWindow
        pass