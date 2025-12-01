
import os
import hashlib
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QScrollArea, \
    QPushButton
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QPixmap, QLinearGradient
from mutagen.id3 import ID3
from mutagen.mp3 import MP3


class MusicScanner(QThread):
    progress = Signal(int, int)
    finished = Signal(list)

    def __init__(self, music_folder="music"):
        super().__init__()
        self.music_folder = music_folder

    def run(self):
        songs = []
        if not os.path.exists(self.music_folder):
            self.finished.emit(songs)
            return

        files = [f for f in os.listdir(self.music_folder)
                 if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg'))]

        self.progress.emit(0, len(files))

        for i, filename in enumerate(files):
            try:
                filepath = os.path.join(self.music_folder, filename)
                song_info = self.get_song_info(filepath)
                songs.append(song_info)

            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue

            self.progress.emit(i + 1, len(files))

        self.finished.emit(songs)

    def get_song_info(self, filepath):
        song = {
            'title': os.path.splitext(os.path.basename(filepath))[0],
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'cover_data': None
        }

        try:
            if filepath.lower().endswith('.mp3'):
                audio = ID3(filepath)

                # Отримання метаданих
                if 'TIT2' in audio:
                    song['title'] = str(audio['TIT2'])
                if 'TPE1' in audio:
                    song['artist'] = str(audio['TPE1'])
                if 'TALB' in audio:
                    song['album'] = str(audio['TALB'])

                # Отримання обкладинки
                for key in audio.keys():
                    if key.startswith('APIC'):
                        apic = audio[key]
                        song['cover_data'] = apic.data
                        break

        except Exception as e:
            # Якщо не вдалося прочитати ID3 теги, використовуємо ім'я файлу
            print(f"Could not read ID3 tags for {filepath}: {e}")

        return song


class HomePage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.songs = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Cover art section - зберігаємо оригінальний дизайн
        self.cover_container = QWidget()
        cover_layout = QVBoxLayout(self.cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        self.cover_frame = QFrame()
        self.cover_frame.setMinimumSize(320, 320)
        self.cover_frame.setMaximumSize(400, 400)

        # Напівпрозорий фон
        self.cover_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
                border-radius: 20px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.cover_frame)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.cover_frame.setGraphicsEffect(shadow)

        # Label для обкладинки
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignCenter)
        cover_layout.addWidget(self.cover_label)
        cover_layout.addWidget(self.cover_frame)
        layout.addWidget(self.cover_container, 0, Qt.AlignCenter)

        # Track info - буде оновлюватись при виборі пісні
        track_layout = QVBoxLayout()
        track_layout.setSpacing(8)

        self.track_title = QLabel("Select a Song")
        self.track_title.setFont(QFont("Arial", 24, QFont.Bold))
        self.track_title.setAlignment(Qt.AlignCenter)
        self.track_title.setStyleSheet("color: white;")

        self.track_artist = QLabel("From Your Library")
        self.track_artist.setFont(QFont("Arial", 18))
        self.track_artist.setAlignment(Qt.AlignCenter)
        self.track_artist.setStyleSheet("color: #b3b3b3;")

        self.track_album = QLabel("Click any song to play")
        self.track_album.setFont(QFont("Arial", 16))
        self.track_album.setAlignment(Qt.AlignCenter)
        self.track_album.setStyleSheet("color: #b3b3b3;")

        track_layout.addWidget(self.track_title)
        track_layout.addWidget(self.track_artist)
        track_layout.addWidget(self.track_album)
        layout.addLayout(track_layout)

        # Кнопка оновлення бібліотеки
        self.refresh_btn = QPushButton("🔄 Refresh Music Library")
        self.refresh_btn.setFixedHeight(40)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)
        self.refresh_btn.clicked.connect(self.scan_music)
        layout.addWidget(self.refresh_btn, alignment=Qt.AlignCenter)

        # Music Library section замість Recommendations
        self.add_music_library_section(layout)
        layout.addStretch()

        # Сканування музики при запуску
        self.scan_music()

    def add_music_library_section(self, layout):
        rec_title = QLabel("Your Music Library")
        rec_title.setFont(QFont("Arial", 18, QFont.Bold))
        rec_title.setStyleSheet("color: white; margin-top: 20px;")
        layout.addWidget(rec_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(700)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                background-color: transparent; 
                border: none; 
            }
            QScrollBar:horizontal { 
                background: #404040; 
                height: 10px; 
                border-radius: 5px; 
            }
            QScrollBar::handle:horizontal { 
                background: #606060; 
                border-radius: 5px; 
            }
            QScrollBar::handle:horizontal:hover { 
                background: #808080; 
            }
        """)

        self.songs_container = QWidget()
        self.songs_layout = QGridLayout(self.songs_container)
        self.songs_layout.setContentsMargins(5, 5, 5, 5)
        self.songs_layout.setSpacing(15)

        scroll_area.setWidget(self.songs_container)
        layout.addWidget(scroll_area)

    def scan_music(self):
        self.scanner = MusicScanner("music")
        self.scanner.finished.connect(self.display_songs)
        self.scanner.start()

    def display_songs(self, songs):
        self.songs = songs

        # Очищаємо контейнер
        for i in reversed(range(self.songs_layout.count())):
            widget = self.songs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Додаємо пісні
        for i, song in enumerate(songs):
            card = self.create_song_card(song)
            row = i // 4
            col = i % 4
            self.songs_layout.addWidget(card, row, col)

    def create_song_card(self, song):
        card = QFrame()
        card.setFixedSize(180, 220)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
                border-radius: 20px;
            }
            QFrame:hover {
                background-color: rgba(40, 40, 40, 0.85);
            }
        """)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 120))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Іконка з обкладинкою пісні
        icon_size = QSize(160, 160)
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size)
        icon_label.setAlignment(Qt.AlignCenter)

        if song['cover_data']:
            pixmap = QPixmap()
            pixmap.loadFromData(song['cover_data'])
            if not pixmap.isNull():
                pixmap = pixmap.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                # Обрізаємо до квадрата
                if pixmap.width() > pixmap.height():
                    crop_x = (pixmap.width() - icon_size.width()) // 2
                    pixmap = pixmap.copy(crop_x, 0, icon_size.width(), icon_size.height())
                else:
                    crop_y = (pixmap.height() - icon_size.height()) // 2
                    pixmap = pixmap.copy(0, crop_y, icon_size.width(), icon_size.height())
            else:
                pixmap = self.create_default_cover(song['title'], icon_size)
        else:
            pixmap = self.create_default_cover(song['title'], icon_size)

        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # Назва пісні
        name_label = QLabel(song['title'])
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # Виконавець
        artist_label = QLabel(song['artist'])
        artist_label.setFont(QFont("Arial", 11))
        artist_label.setStyleSheet("color: #b3b3b3;")
        artist_label.setWordWrap(True)
        artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(artist_label)

        # Подія кліку на картку
        card.mousePressEvent = lambda event, s=song: self.on_song_clicked(s, icon_label.pixmap())

        return card

    def create_default_cover(self, title, size):
        """Створює обкладинку за замовчуванням"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Генеруємо колір на основі хешу назви
        hash_obj = hashlib.md5(title.encode())
        hash_num = int(hash_obj.hexdigest()[:6], 16)
        r = (hash_num & 0xFF0000) >> 16
        g = (hash_num & 0x00FF00) >> 8
        b = hash_num & 0x0000FF

        # Градієнт фону
        gradient = QLinearGradient(0, 0, size.width(), size.height())
        gradient.setColorAt(0, QColor(r, g, b))
        gradient.setColorAt(1, QColor(r // 2, g // 2, b // 2))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, size.width(), size.height(), 12, 12)

        # Нотка
        note_color = QColor(255, 255, 255, 200)
        painter.setBrush(QBrush(note_color))

        # Більша нотка для кращого відображення
        center_x, center_y = size.width() // 2, size.height() // 2

        painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)
        painter.drawRect(center_x - 5, center_y + 20, 10, 40)
        painter.drawEllipse(center_x - 30, center_y - 30, 20, 20)
        painter.drawRect(center_x - 35, center_y - 10, 25, 10)

        painter.end()
        return pixmap

    def on_song_clicked(self, song, cover_pixmap):
        """Обробка кліку по пісні"""
        self.track_title.setText(song['title'])
        self.track_artist.setText(song['artist'])
        self.track_album.setText(song['album'])

        # Оновлюємо обкладинку
        self.update_cover(cover_pixmap)

    def update_cover(self, pixmap):
        """Оновлення обкладинки на верхній панелі"""
        if pixmap:
            scaled_pixmap = pixmap.scaled(
                self.cover_frame.size() - QSize(20, 20),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(scaled_pixmap)
        else:
            self.cover_label.clear()

    def apply_settings(self, settings):
        try:
            self.settings = settings
            show_cover = settings.value("show_cover", True, type=bool)
            self.cover_container.setVisible(show_cover)

            theme = settings.value("theme", "dark", type=str)
            if theme == "dark":
                self.track_title.setStyleSheet("color: white;")
                self.track_artist.setStyleSheet("color: #b3b3b3;")
                self.track_album.setStyleSheet("color: #b3b3b3;")
            else:
                self.track_title.setStyleSheet("color: black;")
                self.track_artist.setStyleSheet("color: #555555;")
                self.track_album.setStyleSheet("color: #555555;")

            # Оновлюємо кольори карток
            for i in range(self.songs_layout.count()):
                widget = self.songs_layout.itemAt(i).widget()
                if widget:
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
        except Exception as e:
            print(f"Error applying settings to home page: {str(e)}")

    def cleanup(self):
        if hasattr(self, 'scanner') and self.scanner.isRunning():
            self.scanner.terminate()
            self.scanner.wait()

