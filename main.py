import sys
import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QProgressBar, QPushButton, QLabel, QFrame,
    QFileDialog, QMessageBox, QMenu, QInputDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QThread, Signal, QUrl
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QAction, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui_base.home_page import HomePage
from gui_base.playist_page import Playlist
from gui_base.settings_page import SettingsPage

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


class MusicScanner(QThread):
    scan_progress = Signal(int, int)  # current, total
    scan_complete = Signal(list)

    def __init__(self, music_dir):
        super().__init__()
        self.music_dir = music_dir
        self.music_files = []

    def run(self):
        # Шукаємо музичні файли
        extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']

        all_files = []
        for ext in extensions:
            all_files.extend(list(Path(self.music_dir).rglob(f'*{ext}')))

        self.scan_progress.emit(0, len(all_files))

        music_data = []
        for i, file_path in enumerate(all_files):
            try:
                track_info = self.extract_track_info(file_path)
                music_data.append(track_info)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

            self.scan_progress.emit(i + 1, len(all_files))

        self.scan_complete.emit(music_data)

    def extract_track_info(self, file_path):
        import mutagen
        from mutagen import File as MutagenFile

        file_path = Path(file_path)
        track = {
            'id': hashlib.md5(str(file_path).encode()).hexdigest(),
            'file_path': str(file_path),
            'file_name': file_path.name,
            'title': file_path.stem,
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'duration': 0,
            'track_number': 0,
            'year': '',
            'genre': '',
            'cover_path': None,
            'date_added': datetime.now().isoformat(),
            'play_count': 0,
            'last_played': None
        }

        try:
            audio = MutagenFile(file_path)
            if audio is not None:
                # Читаємо основні теги
                if hasattr(audio, 'tags'):
                    if hasattr(audio, 'get'):
                        # Для MP3 з ID3 тегами
                        try:
                            if 'TIT2' in audio: track['title'] = str(audio['TIT2'][0])
                            if 'TPE1' in audio: track['artist'] = str(audio['TPE1'][0])
                            if 'TALB' in audio: track['album'] = str(audio['TALB'][0])
                            if 'TCON' in audio: track['genre'] = str(audio['TCON'][0])
                            if 'TRCK' in audio: track['track_number'] = str(audio['TRCK'][0])
                            if 'TDRC' in audio: track['year'] = str(audio['TDRC'][0])

                            # Отримуємо обкладинку
                            for key in audio.keys():
                                if key.startswith('APIC'):
                                    apic = audio[key]
                                    if hasattr(apic, 'data'):
                                        cover_data = apic.data
                                        cover_ext = '.jpg' if hasattr(apic,
                                                                      'mime') and apic.mime == 'image/jpeg' else '.png'
                                        cover_filename = f"{track['id']}{cover_ext}"
                                        cover_path = Path('covers') / cover_filename
                                        cover_path.parent.mkdir(exist_ok=True)

                                        with open(cover_path, 'wb') as f:
                                            f.write(cover_data)
                                        track['cover_path'] = str(cover_path)
                                        break
                        except:
                            pass

                    elif hasattr(audio, 'info'):
                        # Для інших форматів
                        if 'title' in audio: track['title'] = str(audio['title'][0])
                        if 'artist' in audio: track['artist'] = str(audio['artist'][0])
                        if 'album' in audio: track['album'] = str(audio['album'][0])
                        if 'genre' in audio: track['genre'] = str(audio['genre'][0])

                # Тривалість
                if hasattr(audio.info, 'length'):
                    track['duration'] = int(audio.info.length)

        except Exception as e:
            print(f"Error reading tags for {file_path}: {e}")

        return track


class MusicLibrary:
    def __init__(self, db_path='music_library.json'):
        self.db_path = db_path
        self.tracks = []
        self.playlists = {}
        self.load_library()

    def load_library(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tracks = data.get('tracks', [])
                    self.playlists = data.get('playlists', {})
            except Exception as e:
                print(f"Error loading library: {e}")
                self.tracks = []
                self.playlists = {}
        else:
            self.tracks = []
            self.playlists = {
                'Favorites': [],
                'Recently Added': [],
                'Most Played': []
            }

    def save_library(self):
        data = {
            'tracks': self.tracks,
            'playlists': self.playlists
        }
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving library: {e}")

    def add_track(self, track_info):
        # Перевіряємо чи не існує вже такий трек
        existing_ids = [t['id'] for t in self.tracks]
        if track_info['id'] not in existing_ids:
            self.tracks.append(track_info)
            # Додаємо до "Recently Added"
            if 'Recently Added' in self.playlists:
                self.playlists['Recently Added'].insert(0, track_info['id'])
                # Обмежуємо до 50 треків
                if len(self.playlists['Recently Added']) > 50:
                    self.playlists['Recently Added'] = self.playlists['Recently Added'][:50]
            self.save_library()
            return True
        return False

    def create_playlist(self, name):
        if name not in self.playlists:
            self.playlists[name] = []
            self.save_library()
            return True
        return False

    def rename_playlist(self, old_name, new_name):
        if old_name in self.playlists and new_name not in self.playlists:
            self.playlists[new_name] = self.playlists.pop(old_name)
            self.save_library()
            return True
        return False

    def delete_playlist(self, name):
        if name in self.playlists and name not in ['Favorites', 'Recently Added', 'Most Played']:
            del self.playlists[name]
            self.save_library()
            return True
        return False

    def add_to_playlist(self, playlist_name, track_id):
        if playlist_name in self.playlists:
            if track_id not in self.playlists[playlist_name]:
                self.playlists[playlist_name].append(track_id)
                self.save_library()
                return True
        return False

    def remove_from_playlist(self, playlist_name, track_id):
        if playlist_name in self.playlists:
            if track_id in self.playlists[playlist_name]:
                self.playlists[playlist_name].remove(track_id)
                self.save_library()
                return True
        return False

    def increment_play_count(self, track_id):
        for track in self.tracks:
            if track['id'] == track_id:
                track['play_count'] = track.get('play_count', 0) + 1
                track['last_played'] = datetime.now().isoformat()

                # Оновлюємо Most Played
                if 'Most Played' in self.playlists:
                    if track_id not in self.playlists['Most Played']:
                        self.playlists['Most Played'].append(track_id)
                    # Сортуємо за play_count
                    most_played_tracks = []
                    for track in self.tracks:
                        if track['id'] in self.playlists['Most Played']:
                            most_played_tracks.append((track['id'], track.get('play_count', 0)))
                    most_played_tracks.sort(key=lambda x: x[1], reverse=True)
                    self.playlists['Most Played'] = [track_id for track_id, _ in most_played_tracks[:50]]

                self.save_library()
                break

    def get_track_by_id(self, track_id):
        for track in self.tracks:
            if track['id'] == track_id:
                return track
        return None

    def get_playlist_tracks(self, playlist_name):
        tracks = []
        if playlist_name in self.playlists:
            for track_id in self.playlists[playlist_name]:
                track = self.get_track_by_id(track_id)
                if track:
                    tracks.append(track)
        return tracks

    def get_all_tracks(self):
        return self.tracks


class MainWindow(QMainWindow):
    playlist_changed = Signal(str)  # Сигнал при зміні плейлиста
    library_updated = Signal()  # Сигнал при оновленні бібліотеки

    def __init__(self):
        super().__init__()

        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowTitle("PlayerV")
        self.setMinimumSize(QSize(1100, 700))

        # Відновлення збереженої геометрії
        geom = self.settings.value("window_geometry", None)
        if geom:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

        # Ініціалізація музичної бібліотеки
        self.music_dir = 'music'
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)

        self.library = MusicLibrary()
        self.current_playlist = []
        self.current_track_index = -1
        self.current_playlist_name = "Recently Added"

        # Стан плеєра
        self._is_playing = False
        self._progress_value = 0

        # Медіа плеєр
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)

        self.init_ui()
        self.apply_theme()
        self.apply_settings()

        # Сканування музики при запуску
        self.scan_music_library()

        # Таймер для демонстрації прогресу
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self.show_page("home")

    # ---------- UI ----------
    def init_ui(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(14, 14, 14, 14)
        central_layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.left_container = QFrame()
        self.left_container.setObjectName("leftPanel")
        self.left_container.setFixedWidth(320)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # Заголовок та кнопка додавання музики
        left_title_layout = QHBoxLayout()
        left_title = QLabel("Плейлисти")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_title_layout.addWidget(left_title)

        # Кнопка додавання музики
        self.btn_add_music = QPushButton("+ Додати музику")
        self.btn_add_music.setFixedHeight(30)
        self.btn_add_music.clicked.connect(self.add_music_files)
        left_title_layout.addWidget(self.btn_add_music)

        left_layout.addLayout(left_title_layout)

        # Список плейлистів
        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self.on_playlist_selected)
        self.playlist_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self.show_playlist_context_menu)
        left_layout.addWidget(self.playlist_list)

        # Список треків у вибраному плейлисті
        self.track_list = QListWidget()
        self.track_list.itemDoubleClicked.connect(self.on_track_double_clicked)
        self.track_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self.show_track_context_menu)
        left_layout.addWidget(self.track_list)

        row.addWidget(self.left_container)

        # Панель сторінок
        self.pages_container = QFrame()
        self.pages_container.setObjectName("pagesPanel")
        pages_layout = QVBoxLayout(self.pages_container)
        pages_layout.setContentsMargins(10, 10, 10, 10)
        pages_layout.setSpacing(8)

        self.pages = QStackedWidget()
        self.page_home = HomePage(self.settings, self.library, self)
        self.page_playlist_page = Playlist(self.settings, self.library, self)
        self.page_settings = SettingsPage(self.settings, self.apply_settings)

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_playlist_page)
        self.pages.addWidget(self.page_settings)
        pages_layout.addWidget(self.pages)
        row.addWidget(self.pages_container, 1)

        central_layout.addLayout(row)

        # Нижня панель
        self.bottom_container = QFrame()
        self.bottom_container.setObjectName("bottomPanel")
        bottom_layout = QHBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(10)

        # Інформація про поточний трек
        self.current_track_info = QLabel("Виберіть трек")
        bottom_layout.addWidget(self.current_track_info, 1)

        # Прогрес-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self._progress_value)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        bottom_layout.addWidget(self.progress_bar, 3)

        # Кнопки по центру
        controls = QHBoxLayout()
        controls.setSpacing(12)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(QIcon('assets/back.png'))
        self.btn_prev.setToolTip("Попередній трек")

        self.btn_play = QPushButton()
        self.btn_play.setIcon(QIcon('assets/play.png'))
        self.btn_play.setToolTip("Відтворити/Пауза")

        self.btn_next = QPushButton()
        self.btn_next.setIcon(QIcon('assets/next.png'))
        self.btn_next.setToolTip("Наступний трек")

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,10);
                    border: 1px solid rgba(255,255,255,15);
                    border-radius: 22px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,20);
                }
                QPushButton:pressed {
                    background: rgba(255,255,255,5);
                }
            """)

        self.btn_prev.clicked.connect(self.on_prev)
        self.btn_play.clicked.connect(self.on_play_pause)
        self.btn_next.clicked.connect(self.on_next)

        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)

        bottom_layout.addLayout(controls)

        central_layout.addWidget(self.bottom_container)
        self.setCentralWidget(central)

        self.setStyleSheet(self.build_stylesheet())
        self.update_playlist_list()
        self.update_track_list('Recently Added')

        # Підключаємо сигнали
        self.playlist_changed.connect(self.page_home.on_playlist_changed)
        self.library_updated.connect(self.page_home.refresh_library)

    def build_stylesheet(self) -> str:
        return """
        QWidget {
            background: transparent;
            color: #e8e8e8;
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 12px;
        }

        QFrame#leftPanel {
            background: rgba(30,30,32,180);
            border-radius: 16px;
        }
        QFrame#pagesPanel {
            background: rgba(24,24,26,180);
            border-radius: 16px;
        }
        QFrame#bottomPanel {
            background: rgba(24,24,26,250);
            border-radius: 16px;
        }

        QProgressBar {
            background: rgba(255,255,255,10);
            border-radius: 8px;
            min-height: 12px;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 #1DB954, stop:1 #179944);
            border-radius: 8px;
        }

        QListWidget {
            background: transparent;
            border: none;
            outline: none;
        }

        QListWidget::item {
            padding: 8px;
            border-radius: 8px;
        }

        QListWidget::item:selected {
            background: rgba(29, 185, 84, 0.3);
        }

        QListWidget::item:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        QPushButton {
            background: rgba(40, 40, 40, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 8px 16px;
        }

        QPushButton:hover {
            background: rgba(60, 60, 60, 0.9);
        }
        """

    # ---------- Музична бібліотека ----------
    def scan_music_library(self):
        self.scanner = MusicScanner(self.music_dir)
        self.scanner.scan_complete.connect(self.on_scan_complete)
        self.scanner.start()

    def on_scan_complete(self, music_data):
        for track in music_data:
            self.library.add_track(track)
        self.update_track_list('Recently Added')
        self.library_updated.emit()


    def add_music_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Виберіть музичні файли",
            "",
            "Музичні файли (*.mp3 *.wav *.flac *.ogg *.m4a *.aac)"
        )

        if files:
            for file_path in files:
                try:
                    dest_path = os.path.join(self.music_dir, os.path.basename(file_path))
                    # Якщо файл вже існує, додаємо індекс
                    if os.path.exists(dest_path):
                        name, ext = os.path.splitext(os.path.basename(file_path))
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(self.music_dir, f"{name}_{counter}{ext}")
                            counter += 1

                    shutil.copy2(file_path, dest_path)

                    # Додаємо до бібліотеки
                    scanner = MusicScanner(self.music_dir)
                    track_info = scanner.extract_track_info(dest_path)
                    if self.library.add_track(track_info):
                        print(f"Додано: {track_info['title']}")

                except Exception as e:
                    QMessageBox.warning(self, "Помилка", f"Не вдалося додати файл: {e}")

            self.update_track_list('Recently Added')
            self.library_updated.emit()
            QMessageBox.information(self, "Файли додано",
                                    f"Додано {len(files)} файлів у бібліотеку")

    # ---------- Плейлисти ----------
    def update_playlist_list(self):
        self.playlist_list.clear()
        for playlist_name in self.library.playlists.keys():
            item = QListWidgetItem(f"📁 {playlist_name}")
            item.setData(Qt.UserRole, playlist_name)
            self.playlist_list.addItem(item)

    def on_playlist_selected(self, item):
        playlist_name = item.data(Qt.UserRole)
        self.current_playlist_name = playlist_name
        self.update_track_list(playlist_name)
        self.playlist_changed.emit(playlist_name)

    def update_track_list(self, playlist_name):
        self.track_list.clear()
        self.current_playlist = []



    def get_track_by_id(self, track_id):
        return self.library.get_track_by_id(track_id)

    def show_playlist_context_menu(self, position):
        menu = QMenu()

        # Додаємо базові дії
        create_action = menu.addAction("Створити новий плейлист")

        # Перевіряємо, чи під курсором є елемент
        item = self.playlist_list.itemAt(position)
        if item:
            playlist_name = item.data(Qt.UserRole)
            rename_action = menu.addAction("Перейменувати плейлист")
            delete_action = menu.addAction("Видалити плейлист")

            # Не дозволяємо видаляти системні плейлисти
            if playlist_name in ['Favorites', 'Recently Added', 'Most Played']:
                delete_action.setEnabled(False)

        # Показуємо меню
        action = menu.exec_(self.playlist_list.mapToGlobal(position))

        # Обробка вибору
        if action == create_action:
            self.create_new_playlist()
        elif item and action == rename_action:
            self.rename_playlist(playlist_name)
        elif item and action == delete_action:
            self.delete_playlist(playlist_name)

    def create_new_playlist(self):
        name, ok = QInputDialog.getText(self, "Новий плейлист", "Введіть назву плейлиста:")
        if ok and name:
            if self.library.create_playlist(name):
                self.update_playlist_list()
                self.library_updated.emit()

    def rename_playlist(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Перейменувати плейлист",
                                            f"Введіть нову назву для '{old_name}':",
                                            text=old_name)
        if ok and new_name and new_name != old_name:
            if self.library.rename_playlist(old_name, new_name):
                self.update_playlist_list()
                self.library_updated.emit()

    def delete_playlist(self, name):
        reply = QMessageBox.question(self, "Видалити плейлист",
                                     f"Ви впевнені, що хочете видалити плейлист '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.library.delete_playlist(name):
                self.update_playlist_list()
                self.update_track_list('Recently Added')
                self.library_updated.emit()

    def show_track_context_menu(self, position):
        menu = QMenu()
        item = self.track_list.itemAt(position)
        if item:
            track_id = item.data(Qt.UserRole)

            add_to_playlist_action = menu.addAction("Додати до плейлиста...")
            menu.addSeparator()
            play_action = menu.addAction("Відтворити")
            remove_action = menu.addAction("Видалити з плейлиста")

            action = menu.exec_(self.track_list.mapToGlobal(position))

            if action == add_to_playlist_action:
                self.add_track_to_playlist(track_id)
            elif action == play_action:
                self.play_track_by_id(track_id)
            elif action == remove_action:
                self.remove_track_from_playlist(track_id)

    def add_track_to_playlist(self, track_id):
        playlists = list(self.library.playlists.keys())
        playlist_name, ok = QInputDialog.getItem(
            self, "Додати до плейлиста",
            "Виберіть плейлист:", playlists, 0, False
        )
        if ok and playlist_name:
            if self.library.add_to_playlist(playlist_name, track_id):
                self.library_updated.emit()
                QMessageBox.information(self, "Успішно", "Трек додано до плейлиста")

    def remove_track_from_playlist(self, track_id):
        if self.current_playlist_name:
            if self.library.remove_from_playlist(self.current_playlist_name, track_id):
                self.update_track_list(self.current_playlist_name)
                self.library_updated.emit()

    # ---------- Програвання ----------
    def play_track_by_id(self, track_id):
        track = self.library.get_track_by_id(track_id)
        if track:
            # Знаходимо індекс трека в поточному плейлисті
            for i, t in enumerate(self.current_playlist):
                if t['id'] == track_id:
                    self.current_track_index = i
                    break

            self.play_track(track)

    def play_track(self, track):
        file_url = QUrl.fromLocalFile(track['file_path'])
        self.media_player.setSource(file_url)
        self.media_player.play()

        self.current_track_info.setText(f"{track['title']} - {track['artist']}")
        self.btn_play.setIcon(QIcon('assets/pause.png'))
        self._is_playing = True

        # Оновлюємо лічильник відтворень
        self.library.increment_play_count(track['id'])
        self.library_updated.emit()

    def update_progress(self, position):
        if self.media_player.duration() > 0:
            self._progress_value = int((position / self.media_player.duration()) * 100)
            self.progress_bar.setValue(self._progress_value)

    def update_duration(self, duration):
        pass

    def media_status_changed(self, status):
        try:
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.on_next()
        except Exception:
            # на всякий випадок — старі версії можуть використовувати інші енуми
            if status == QMediaPlayer.EndOfMedia:  # запасний варіант
                self.on_next()

    def on_play_pause(self):
        state = self.media_player.playbackState()

        if state == QMediaPlayer.PlayingState:
            # Пауза
            self.media_player.pause()
            self.btn_play.setIcon(QIcon('assets/play.png'))
            self._is_playing = False

        elif state == QMediaPlayer.PausedState:
            # Продовжити програвання (не перезавантажувати)
            self.media_player.play()
            self.btn_play.setIcon(QIcon('assets/pause.png'))
            self._is_playing = True

        else:
            # Stopped / NoMedia — починаємо відтворення поточного або першого треку
            if self.current_playlist and self.current_track_index >= 0:
                self.play_track(self.current_playlist[self.current_track_index])
            elif self.current_playlist:
                # якщо індекс ще не встановлено — 0
                self.current_track_index = 0
                self.play_track(self.current_playlist[0])
            else:
                QMessageBox.information(self, "Плейлист пустий", "У вибраному плейлисті немає треків.")

    def on_prev(self):
        if self.current_playlist:
            self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
            self.play_track(self.current_playlist[self.current_track_index])

    def on_next(self):
        if self.current_playlist:
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            self.play_track(self.current_playlist[self.current_track_index])

    def on_track_double_clicked(self, item):
        track_id = item.data(Qt.UserRole)
        self.play_track_by_id(track_id)

    def _on_tick(self):
        # Для демонстрації, якщо немає реального трека
        if not self._is_playing or self.media_player.playbackState() != QMediaPlayer.PlayingState:
            return

    # ---------- Теми ----------
    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        pal = QPalette()
        if theme == "dark":
            pal.setColor(QPalette.Window, QColor(18, 18, 18))
            pal.setColor(QPalette.WindowText, QColor(230, 230, 230))
        else:
            pal.setColor(QPalette.Window, QColor(245, 245, 245))
            pal.setColor(QPalette.WindowText, QColor(30, 30, 30))
        QApplication.setPalette(pal)

    # ---------- Сторінки ----------
    def show_page(self, page: str):
        if page == "home":
            self.pages.setCurrentWidget(self.page_home)
        elif page == "library":
            self.pages.setCurrentWidget(self.page_playlist_page)
            self.page_playlist_page.refresh_playlists()
        elif page == "settings":
            self.pages.setCurrentWidget(self.page_settings)
            try:
                self.page_settings.apply_settings(self.settings)
            except Exception:
                pass

    def apply_settings(self):
        try:
            self.page_home.apply_settings(self.settings)
        except Exception:
            pass
        try:
            self.page_playlist_page.apply_settings(self.settings)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.sync()
        except Exception:
            pass
        try:
            self.page_home.cleanup()
        except Exception:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if os.path.exists("app_icon.png"):
        app.setWindowIcon(QIcon("app_icon.png"))

    # Створюємо необхідні папки
    os.makedirs('music', exist_ok=True)
    os.makedirs('covers', exist_ok=True)
    os.makedirs('assets', exist_ok=True)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())