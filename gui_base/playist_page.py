from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QLinearGradient

class Playlist(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Заголовок
        title = QLabel("Your Library")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title)

        # Панель пошуку
        search_field = QLineEdit()
        search_field.setPlaceholderText("Search playlists, artists, albums...")
        search_field.setMinimumHeight(30)
        main_layout.addWidget(search_field)

        # Прокрутка
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        playlists_container = QWidget()
        self.playlists_layout = QVBoxLayout(playlists_container)
        self.playlists_layout.setContentsMargins(0, 0, 0, 0)
        self.playlists_layout.setSpacing(10)

        scroll_area.setWidget(playlists_container)
        main_layout.addWidget(scroll_area)

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
            {"name": "Electronic Dance", "count": 45, "color": (180, 100, 220)},
        ]

        for playlist in playlists:
            item = QFrame()
            item.setStyleSheet("""
                QFrame {
                    background-color: rgba(24, 24, 24, 0.7);  /* напівпрозорий темний фон */
                    border-radius: 20px;                       /* округлі кути */
                }
                QFrame:hover {
                    background-color: rgba(40, 40, 40, 0.85); /* трохи темніший при наведенні */
                }
            """)
            item.setFixedHeight(60)
            layout = QHBoxLayout(item)
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(10)

            # Іконка плейлисту з градієнтом
            icon_size = QSize(50, 50)
            icon_label = QLabel()
            icon_label.setFixedSize(icon_size)

            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            gradient = QLinearGradient(0, 0, icon_size.width(), icon_size.height())
            gradient.setColorAt(0, QColor(*playlist["color"]))
            gradient.setColorAt(1, QColor(playlist["color"][0]//2, playlist["color"][1]//2, playlist["color"][2]//2))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, icon_size.width(), icon_size.height(), 10, 10)

            # Нотка
            note_color = QColor(255, 255, 255, 200)
            painter.setBrush(QBrush(note_color))
            painter.drawEllipse(15, 15, 20, 20)
            painter.end()

            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)

            # Назва і кількість треків
            text_layout = QVBoxLayout()
            name_label = QLabel(playlist["name"])
            name_label.setFont(QFont("Arial", 12, QFont.Bold))
            name_label.setStyleSheet("color: white;")
            text_layout.addWidget(name_label)

            count_label = QLabel(f"{playlist['count']} tracks")
            count_label.setFont(QFont("Arial", 10))
            count_label.setStyleSheet("color: #b3b3b3;")
            text_layout.addWidget(count_label)

            layout.addLayout(text_layout)

            self.playlists_layout.addWidget(item)

    def apply_settings(self, settings):
        pass
