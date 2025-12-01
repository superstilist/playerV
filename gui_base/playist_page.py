
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QScrollArea, QPushButton, \
    QInputDialog, QMessageBox
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QLinearGradient
import json
import os
import random


class Playlist(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.playlists_file = "playlists.json"
        self.playlists = self.load_playlists()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Заголовок і кнопка
        title_layout = QHBoxLayout()
        title = QLabel("Your Playlists")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)
        title_layout.addWidget(title)

        # Кнопка нового плейлиста
        self.new_playlist_btn = QPushButton("+ New Playlist")
        self.new_playlist_btn.setFixedHeight(30)
        self.new_playlist_btn.clicked.connect(self.create_new_playlist)
        self.new_playlist_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)
        title_layout.addWidget(self.new_playlist_btn)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # Панель пошуку
        search_field = QLineEdit()
        search_field.setPlaceholderText("Search playlists...")
        search_field.setMinimumHeight(30)
        main_layout.addWidget(search_field)

        # Прокрутка
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.playlists_container = QWidget()
        self.playlists_layout = QVBoxLayout(self.playlists_container)
        self.playlists_layout.setContentsMargins(0, 0, 0, 0)
        self.playlists_layout.setSpacing(10)

        scroll_area.setWidget(self.playlists_container)
        main_layout.addWidget(scroll_area)

        self.populate_playlists()

    def load_playlists(self):
        """Завантаження плейлистів з JSON файлу"""
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading playlists: {e}")
                return self.get_default_playlists()
        else:
            return self.get_default_playlists()

    def get_default_playlists(self):
        """Стандартні плейлисти"""
        return [
            {"name": "Favorite Tracks", "count": 0, "color": [220, 20, 60], "tracks": []},
            {"name": "Workout Mix", "count": 0, "color": [30, 144, 255], "tracks": []},
            {"name": "Chill Vibes", "count": 0, "color": [50, 205, 50], "tracks": []},
            {"name": "Study Focus", "count": 0, "color": [138, 43, 226], "tracks": []},
            {"name": "Road Trip", "count": 0, "color": [255, 140, 0], "tracks": []},
        ]

    def save_playlists(self):
        """Збереження плейлистів у JSON файл"""
        try:
            with open(self.playlists_file, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save playlists: {e}")

    def create_new_playlist(self):
        """Створення нового плейлиста"""
        name, ok = QInputDialog.getText(self, "New Playlist", "Enter playlist name:")
        if ok and name:
            if any(p['name'].lower() == name.lower() for p in self.playlists):
                QMessageBox.warning(self, "Error", "Playlist with this name already exists!")
                return

            # Генерація випадкового кольору
            color = [random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)]

            new_playlist = {
                "name": name,
                "count": 0,
                "color": color,
                "tracks": []
            }

            self.playlists.append(new_playlist)
            self.save_playlists()
            self.populate_playlists()

            QMessageBox.information(self, "Success", f"Playlist '{name}' created!")

    def populate_playlists(self):
        """Відображення плейлистів"""
        # Очищення контейнера
        while self.playlists_layout.count():
            child = self.playlists_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for playlist in self.playlists:
            item = self.create_playlist_item(playlist)
            self.playlists_layout.addWidget(item)

    def create_playlist_item(self, playlist):
        item = QFrame()
        item.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
                border-radius: 15px;
            }
            QFrame:hover {
                background-color: rgba(40, 40, 40, 0.85);
            }
        """)
        item.setFixedHeight(60)
        item.setCursor(Qt.PointingHandCursor)

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

        # Градієнт на основі кольору плейлиста
        gradient = QLinearGradient(0, 0, icon_size.width(), icon_size.height())
        gradient.setColorAt(0, QColor(*playlist["color"]))
        gradient.setColorAt(1, QColor(playlist["color"][0] // 2,
                                      playlist["color"][1] // 2,
                                      playlist["color"][2] // 2))
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
        layout.addStretch()

        return item

    def apply_settings(self, settings):
        self.settings = settings
        theme = settings.value("theme", "dark", type=str)

        # Оновлення стилів відповідно до теми
        for i in range(self.playlists_layout.count()):
            widget = self.playlists_layout.itemAt(i).widget()
            if widget:
                # Оновлення кольору тексту
                for label in widget.findChildren(QLabel):
                    if label.font().bold():
                        if theme == "dark":
                            label.setStyleSheet("color: white;")
                        else:
                            label.setStyleSheet("color: black;")
                    else:
                        if theme == "dark":
                            label.setStyleSheet("color: #b3b3b3;")
                        else:
                            label.setStyleSheet("color: #555555;")

