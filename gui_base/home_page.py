import os
import hashlib
import io
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QScrollArea, \
    QPushButton, QHBoxLayout, QMenu, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QPixmap, QLinearGradient, QIcon, QPainterPath

# Для читання вбудованих обкладинок з аудіофайлів
try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


class HomePage(QWidget):
    track_selected = Signal(dict)  # Сигнал при виборі трека
    playlist_selected = Signal(str)  # Сигнал при виборі плейлиста

    def __init__(self, settings, library, main_window):
        super().__init__()
        self.settings = settings
        self.library = library
        self.main_window = main_window
        self.current_playlist = "Recently Added"
        self._temp_cover_files = []  # список тимчасових файлів, які ми створюємо при вилученні обкладинок
        self.context_menu_track = None  # Трек для контекстного меню

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Music Library section
        self.add_music_library_section(layout)
        layout.addStretch()

        # Відображення пісень з поточного плейлиста
        self.refresh_library()

    def add_music_library_section(self, layout):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(800)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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
            QScrollBar:vertical { 
                background: #404040; 
                width: 10px; 
                border-radius: 5px; 
            }
            QScrollBar::handle:vertical { 
                background: #606060; 
                border-radius: 5px; 
            }
            QScrollBar::handle:vertical:hover { 
                background: #808080; 
            }
        """)

        self.songs_container = QWidget()
        self.songs_layout = QGridLayout(self.songs_container)
        self.songs_layout.setContentsMargins(15, 25, 25, 15)
        self.songs_layout.setSpacing(35)

        scroll_area.setWidget(self.songs_container)
        layout.addWidget(scroll_area)

    def refresh_library(self):
        """Оновлює список пісень з поточного плейлиста"""
        # Очищаємо контейнер
        for i in reversed(range(self.songs_layout.count())):
            widget = self.songs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Отримуємо треки з поточного плейлиста
        if self.current_playlist in self.library.playlists:
            tracks = self.library.get_playlist_tracks(self.current_playlist)
        else:
            tracks = self.library.get_all_tracks()

        # Додаємо пісні
        for i, song in enumerate(tracks):
            card = self.create_song_card(song)
            row = i // 3
            col = i % 3
            self.songs_layout.addWidget(card, row, col)

    def create_song_card(self, song):
        card = QFrame()
        card.setFixedSize(220, 270)
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

        def rounded_pixmap(pixmap, radius):
            size = pixmap.size()
            rounded = QPixmap(size)
            rounded.fill(Qt.transparent)

            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            path = QPainterPath()
            path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)

            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            return rounded

        # Іконка з обкладинкою пісні
        icon_size = QSize(200, 200)
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size)
        icon_label.setAlignment(Qt.AlignCenter)

        # Отримуємо QPixmap для обкладинки (з файлу, з вбудованого тега або з дефолтного генератора)
        pixmap = self.get_cover_pixmap_for_song(song, icon_size)
        pixmap = rounded_pixmap(pixmap, radius=10)  # радіус заокруглення

        icon_label.setPixmap(pixmap)

        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # Назва пісні
        name_label = QLabel(song.get('title', 'Unknown')[:20] + ('...' if len(song.get('title', '')) > 20 else ''))
        name_label.setFont(QFont("Arial", 24, QFont.Bold))
        name_label.setStyleSheet("color: white; background-color: rgba(40, 40, 40, 150); border-radius: 10px; padding: 5px;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # Виконавець
        artist_label = QLabel(song.get('artist', 'Unknown')[:20] + ('...' if len(song.get('artist', '')) > 20 else ''))
        artist_label.setFont(QFont("Arial", 16))
        artist_label.setStyleSheet("color: #b3b3b3; background-color: rgba(40, 40, 40, 150); border-radius: 10px; padding: 5px;")
        artist_label.setWordWrap(True)
        artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(artist_label)

        # Обробка кліку
        card.mousePressEvent = lambda event, s=song, p=pixmap: self.on_song_clicked(event, s, p)

        return card

    def get_cover_pixmap_for_song(self, song, icon_size):
        """Повертає QPixmap обкладинки для пісні.
        Послідовність спроб:
         1) Якщо song['cover_path'] існує на диску — завантажити його.
         2) Спробувати витягти вбудований артефакт з аудіофайлу (через mutagen).
         3) Згенерувати дефолтну обкладинку.
        """
        # 1) файл обкладинки явно вказаний
        if 'cover_path' in song and song['cover_path'] and os.path.exists(song['cover_path']):
            pixmap = QPixmap(song['cover_path'])
            if not pixmap.isNull():
                return pixmap.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # 2) Спробувати витягти вбудовану обкладинку з аудіо
        audio_path = song.get('file_path') or song.get('path') or song.get('filepath')
        if audio_path and os.path.exists(audio_path) and MutagenFile is not None:
            try:
                af = MutagenFile(audio_path)
                if af is not None:
                    # mp3 (APIC), or ID3; для mp4/m4a/ogg різні теги
                    pic_data = None
                    if hasattr(af, 'tags') and af.tags is not None:
                        tags = af.tags
                        # APIC frame (mp3)
                        if 'APIC:' in str(tags):
                            for key in tags.keys():
                                if key.startswith('APIC'):
                                    pic = tags.get(key)
                                    if pic and hasattr(pic, 'data'):
                                        pic_data = pic.data
                                        break
                        # For MP4/M4A
                        if pic_data is None and hasattr(af, 'pictures') and af.pictures:
                            pic_data = af.pictures[0].data
                        # For ID3v2 common access
                        if pic_data is None:
                            try:
                                # some containers keep 'covr' or 'metadata_block_picture'
                                if 'covr' in tags:
                                    covr = tags.get('covr')
                                    if covr:
                                        pic_data = covr[0]
                            except Exception:
                                pass

                    if pic_data:
                        qpix = QPixmap()
                        if qpix.loadFromData(pic_data):
                            return qpix.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            except Exception:
                # мовчазно пропускаємо помилки читання метаданих
                pass

        # 3) Фолбек — генеруємо дефолтну обкладинку
        return self.create_default_cover(song.get('title', 'Unknown'), icon_size)

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

        center_x, center_y = size.width() // 2, size.height() // 2
        painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)
        painter.drawRect(center_x - 5, center_y + 20, 10, 40)
        painter.drawEllipse(center_x - 30, center_y - 30, 20, 20)
        painter.drawRect(center_x - 35, center_y - 10, 25, 10)

        painter.end()
        return pixmap

    def on_song_clicked(self, event, song, cover_pixmap):
        """Обробка кліку на пісню"""
        if event.button() == Qt.LeftButton:
            # Лівий клік - відтворення
            self.play_song(song, cover_pixmap)
        elif event.button() == Qt.RightButton:
            # Правий клік - контекстне меню
            self.show_track_context_menu(song, event.globalPos())

    def play_song(self, song, cover_pixmap):
        """Відтворення пісні"""
        # Відправляємо сигнал
        self.track_selected.emit(song)

        # Відтворюємо трек в головному вікні
        if hasattr(self.main_window, 'play_track_by_id'):
            self.main_window.play_track_by_id(song['id'])

    def show_track_context_menu(self, song, global_pos):
        """Показує контекстне меню для трека"""
        self.context_menu_track = song
        menu = QMenu(self)

        # Основний пункт меню
        play_action = menu.addAction("▶ Відтворити")
        menu.addSeparator()

        # Пункти для роботи з плейлистами
        add_to_playlist_action = menu.addAction("➕ Додати до плейлиста...")
        remove_from_playlist_action = menu.addAction("➖ Видалити з плейлиста")

        # Додаткові пункти
        menu.addSeparator()
        show_info_action = menu.addAction("ℹ Інформація про трек")
        delete_action = menu.addAction("🗑 Видалити трек з бібліотеки")

        # Визначаємо, чи це системний плейлист
        system_playlists = ['Favorites', 'Recently Added', 'Most Played']
        is_system_playlist = self.current_playlist in system_playlists
        remove_from_playlist_action.setEnabled(not is_system_playlist)

        # Обробка вибору пунктів меню
        action = menu.exec_(global_pos)

        if action == play_action:
            self.play_song(song, None)  # cover_pixmap не потрібен, оскільки ми вже на картці
        elif action == add_to_playlist_action:
            self.add_track_to_playlist(song)
        elif action == remove_from_playlist_action:
            self.remove_track_from_playlist(song)
        elif action == show_info_action:
            self.show_track_info(song)
        elif action == delete_action:
            self.delete_track_from_library(song)

    def add_track_to_playlist(self, track):
        """Додає трек до плейлиста"""
        # Отримуємо список плейлистів (крім поточного)
        playlists = list(self.library.playlists.keys())
        if self.current_playlist in playlists:
            playlists.remove(self.current_playlist)

        if not playlists:
            QMessageBox.information(self, "Немає плейлистів", "Створіть спочатку новий плейлист!")
            return

        # Діалог вибору плейлиста
        playlist_name, ok = QInputDialog.getItem(
            self, "Додати до плейлиста",
            "Виберіть плейлист:", playlists, 0, False
        )

        if ok and playlist_name:
            if self.library.add_to_playlist(playlist_name, track['id']):
                QMessageBox.information(self, "Успішно", f"Трек додано до '{playlist_name}'")
            else:
                QMessageBox.warning(self, "Помилка", "Трек вже є у цьому плейлисті!")

    def remove_track_from_playlist(self, track):
        """Видаляє трек з поточного плейлиста"""
        reply = QMessageBox.question(
            self, "Видалити з плейлиста",
            f"Видалити '{track['title']}' з '{self.current_playlist}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.library.remove_from_playlist(self.current_playlist, track['id']):
                # Оновлюємо відображення
                self.refresh_library()
                QMessageBox.information(self, "Успішно", "Трек видалено з плейлиста")
            else:
                QMessageBox.warning(self, "Помилка", "Не вдалося видалити трек")

    def show_track_info(self, track):
        """Показує інформацію про трек"""
        info_text = f"""
        <b>Назва:</b> {track.get('title', 'Невідомо')}<br>
        <b>Виконавець:</b> {track.get('artist', 'Невідомо')}<br>
        <b>Альбом:</b> {track.get('album', 'Невідомо')}<br>
        <b>Тривалість:</b> {self.format_duration(track.get('duration', 0))}<br>
        <b>Жанр:</b> {track.get('genre', 'Невідомо')}<br>
        <b>Рік:</b> {track.get('year', 'Невідомо')}<br>
        <b>Кількість відтворень:</b> {track.get('play_count', 0)}<br>
        <b>Шлях до файлу:</b><br>{track.get('file_path', 'Невідомо')}
        """

        QMessageBox.information(self, "Інформація про трек", info_text)

    def delete_track_from_library(self, track):
        """Видаляє трек з бібліотеки"""
        reply = QMessageBox.question(
            self, "Видалити трек",
            f"Ви впевнені, що хочете видалити '{track['title']}' з бібліотеки?<br><br>"
            f"<i>Ця дія також видалить трек з усіх плейлистів!</i>",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Видаляємо трек з усіх плейлистів
            for playlist_name in list(self.library.playlists.keys()):
                self.library.remove_from_playlist(playlist_name, track['id'])

            # Видаляємо трек з основного списку
            self.library.tracks = [t for t in self.library.tracks if t['id'] != track['id']]
            self.library.save_library()

            # Оновлюємо відображення
            self.refresh_library()
            QMessageBox.information(self, "Успішно", "Трек видалено з бібліотеки")

    def format_duration(self, seconds):
        """Форматує тривалість у секундах у читабельний формат"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def on_playlist_changed(self, playlist_name):
        """Обробляє зміну плейлиста"""
        self.current_playlist = playlist_name
        self.refresh_library()

    def apply_settings(self, settings):
        try:
            self.settings = settings
            show_cover = settings.value("show_cover", True, type=bool)

            theme = settings.value("theme", "dark", type=str)
            if theme == "dark":
                # Оновлюємо кольори карток
                for i in range(self.songs_layout.count()):
                    widget = self.songs_layout.itemAt(i).widget()
                    if widget:
                        for label in widget.findChildren(QLabel):
                            if label.font().bold():
                                label.setStyleSheet("color: white;")
                            else:
                                label.setStyleSheet("color: #b3b3b3;")
            else:
                # Оновлюємо кольори карток
                for i in range(self.songs_layout.count()):
                    widget = self.songs_layout.itemAt(i).widget()
                    if widget:
                        for label in widget.findChildren(QLabel):
                            if label.font().bold():
                                label.setStyleSheet("color: black;")
                            else:
                                label.setStyleSheet("color: #555555;")
        except Exception as e:
            print(f"Error applying settings to home page: {str(e)}")

    def cleanup(self):
        """Очищає тимчасові файли, створені при витягуванні обкладинок"""
        for p in self._temp_cover_files:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self._temp_cover_files.clear()