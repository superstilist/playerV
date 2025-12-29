import sys
import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QProgressBar, QPushButton, QLabel, QFrame,
    QFileDialog, QMessageBox, QMenu, QInputDialog,
    QScrollArea
)
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QPixmap

from engine_sound.AudioEngineQt import AudioEngineQt
from engine_sound.AudioEngineVLC import AudioEngineVLC
from gui_base.bar.RoundedProgressBar import RoundedProgressBar

try:
    import vlc

    _HAVE_VLC = True
except Exception:
    _HAVE_VLC = False


from gui_base.home_page import HomePage
from gui_base.playist_page import Playlist, PlaylistItem
from gui_base.settings_page import SettingsPage

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"





class MusicScanner(QThread):
    scan_progress = Signal(int, int)
    scan_complete = Signal(list)

    def __init__(self, music_dir):
        super().__init__()
        self.music_dir = music_dir

    def run(self):
        extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        all_files = []
        root = Path(self.music_dir)
        if not root.exists():
            self.scan_complete.emit([])
            return

        total = 0
        for p in root.rglob('*'):
            if p.is_file() and p.suffix.lower() in extensions:
                total += 1

        self.scan_progress.emit(0, total)

        music_data = []
        processed = 0
        for p in root.rglob('*'):
            if p.is_file() and p.suffix.lower() in extensions:
                try:
                    music_data.append(self.extract_track_info(p))
                except Exception as e:
                    print(f"Error reading {p}: {e}")
                processed += 1
                if processed % 10 == 0:
                    self.scan_progress.emit(processed, total)

        self.scan_complete.emit(music_data)

    def extract_track_info(self, file_path):
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
                tags = getattr(audio, 'tags', None)
                if tags:
                    try:
                        if 'TIT2' in tags: track['title'] = str(tags['TIT2'][0])
                        if 'TPE1' in tags: track['artist'] = str(tags['TPE1'][0])
                        if 'TALB' in tags: track['album'] = str(tags['TALB'][0])
                        if 'TCON' in tags: track['genre'] = str(tags['TCON'][0])
                        if 'TRCK' in tags: track['track_number'] = str(tags['TRCK'][0])
                        if 'TDRC' in tags: track['year'] = str(tags['TDRC'][0])
                    except Exception:
                        pass

                    try:
                        for key in tags.keys():
                            if key.startswith('APIC') or key.lower().startswith('apic'):
                                apic = tags[key]
                                cover_data = getattr(apic, 'data', None)
                                mime = getattr(apic, 'mime', None)
                                if cover_data:
                                    cover_ext = '.jpg' if mime and 'jpeg' in mime.lower() else '.png'
                                    cover_filename = f"{track['id']}{cover_ext}"
                                    cover_path = Path('covers') / cover_filename
                                    cover_path.parent.mkdir(exist_ok=True)
                                    with open(cover_path, 'wb') as f:
                                        f.write(cover_data)
                                    track['cover_path'] = str(cover_path)
                                    break
                    except Exception:
                        pass

                info = getattr(audio, 'info', None)
                if info and hasattr(info, 'length'):
                    try:
                        track['duration'] = int(info.length * 1000)
                    except Exception:
                        pass

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
        existing_ids = [t['id'] for t in self.tracks]
        if track_info['id'] not in existing_ids:
            self.tracks.append(track_info)
            if 'Recently Added' in self.playlists:
                self.playlists['Recently Added'].insert(0, track_info['id'])
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

                if 'Most Played' in self.playlists:
                    if track_id not in self.playlists['Most Played']:
                        self.playlists['Most Played'].append(track_id)
                    most_played_tracks = []
                    for t in self.tracks:
                        if t['id'] in self.playlists['Most Played']:
                            most_played_tracks.append((t['id'], t.get('play_count', 0)))
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

    def get_albums(self):
        albums = {}
        for track in self.tracks:
            album_name = track.get('album', 'Unknown Album')
            if album_name not in albums:
                albums[album_name] = {
                    'name': album_name,
                    'artist': track.get('artist', 'Unknown Artist'),
                    'tracks': [],
                    'cover_path': track.get('cover_path')
                }
            albums[album_name]['tracks'].append(track)
        sorted_albums = sorted(albums.values(), key=lambda x: x['name'].lower())
        return sorted_albums

    def get_album_by_name(self, album_name):
        albums = self.get_albums()
        for album in albums:
            if album['name'] == album_name:
                return album
        return None


class MainWindow(QMainWindow):
    playlist_changed = Signal(str)
    library_updated = Signal()
    progress_updated = Signal(int)

    def __init__(self):
        super().__init__()

        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.setWindowTitle("PlayerV")
        self.setMinimumSize(QSize(1100, 700))

        geom = self.settings.value("window_geometry", None)
        if geom:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

        self.music_dir = 'music'
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)

        self.library = MusicLibrary()
        self.current_playlist = []
        self.current_track_index = -1
        self.current_playlist_name = "Recently Added"

        self._is_playing = False
        self._current_duration = 0

        self._progress_dragging = False
        self._progress_last_update = 0

        if _HAVE_VLC:
            self.audio = AudioEngineVLC(self)
            self._using_vlc = True
        else:
            self.audio = AudioEngineQt(self)
            self._using_vlc = False

        self.audio.position_changed.connect(self.update_progress)
        try:
            self.audio.duration_changed.connect(self.update_duration)
        except Exception:
            pass
        self.audio.state_changed.connect(self.on_playback_state_changed_wrapper)
        self.audio.end_of_media.connect(self._on_end_of_media)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(700)
        self._poll_timer.timeout.connect(self._poll_audio_status)
        self._poll_active = False

        self._progress_style_updated = False

        self.frames_pause_to_play = []
        self.frames_play_to_pause = []
        self._animating = False
        self._anim_timer = None
        self._anim_index = 0
        self._anim_interval_ms = 40
        self._queued_state = None
        self._processing_click = False

        self._cover_cache = OrderedDict()
        self._MAX_COVERS = 50

        self._playlist_widgets = {}

        self.init_ui()
        self.apply_theme()
        self.apply_settings()

        self.load_play_pause_animations()

        self.scan_music_library()

        self.show_page("home")

    def _poll_audio_status(self):
        try:
            pos = self.audio.get_position()
            dur = self.audio.get_duration()
            self.update_progress(pos)
            if dur and dur != self._current_duration:
                self.update_duration(dur)
        except Exception:
            pass

    def _start_polling(self):
        if not self._poll_active:
            self._poll_active = True
            self._poll_timer.start()

    def _stop_polling(self):
        if self._poll_active:
            self._poll_active = False
            self._poll_timer.stop()

    def on_playback_state_changed_wrapper(self, state_str):
        if state_str == 'playing':
            self._is_playing = True
            self._start_polling()
            if not self._animating:
                self._set_pause_icon_static()
        elif state_str == 'paused':
            self._is_playing = False
            self._stop_polling()
            if not self._animating:
                self._set_play_icon_static()
        elif state_str == 'stopped':
            self._is_playing = False
            self._stop_polling()
            if not self._animating:
                self._set_play_icon_static()
            self.progress_bar.setValue(0)

    def load_play_pause_animations(self):

        icon_size = QSize(32, 32)

        def load_dir_frames(folder, target_size):
            frames = []
            if not os.path.isdir(folder):
                return frames
            files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            for fn in files:
                full = os.path.join(folder, fn)
                try:
                    pix = QPixmap(full)
                    if not pix.isNull():
                        scaled_pix = pix.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        frames.append(scaled_pix)
                except Exception:
                    pass
            return frames

        self.frames_pause_to_play = load_dir_frames(os.path.join('assets', 'pause-to-play'), icon_size)
        self.frames_play_to_pause = load_dir_frames(os.path.join('assets', 'play-to-pause'), icon_size)


        self.btn_play.setIconSize(icon_size)


        if self._is_playing:
            self._set_pause_icon_static()
        else:
            self._set_play_icon_static()

    def _set_play_icon_static(self):

        if self.frames_pause_to_play:
            self.btn_play.setIcon(QIcon(self.frames_pause_to_play[-1]))
        else:
            if os.path.exists('assets/play.png'):
                self.btn_play.setIcon(QIcon('assets/play.png'))
            else:
                self.btn_play.setIcon(QIcon())

    def _set_pause_icon_static(self):
        if self.frames_play_to_pause:
            self.btn_play.setIcon(QIcon(self.frames_play_to_pause[-1]))
        else:
            if os.path.exists('assets/pause.png'):
                self.btn_play.setIcon(QIcon('assets/pause.png'))
            else:
                self.btn_play.setIcon(QIcon())

    def _animate_frames(self, frames, on_finished_static, direction='forward'):
        if not frames:
            on_finished_static()
            return

        if self._animating:
            desired_state = 'pause' if on_finished_static == self._set_pause_icon_static else 'play'
            self._queued_state = desired_state
            return

        self._animating = True
        self._anim_index = 0

        frame_list = frames if direction == 'forward' else list(reversed(frames))

        try:
            if frame_list:
                self.btn_play.setIcon(QIcon(frame_list[0]))
        except Exception:
            pass

        def on_frame():
            if self._anim_index >= len(frame_list):
                if self._anim_timer:
                    try:
                        self._anim_timer.stop()
                    except Exception:
                        pass
                    self._anim_timer = None

                self._animating = False

                try:
                    on_finished_static()
                except Exception:
                    pass

                if self._queued_state:
                    queued = self._queued_state
                    self._queued_state = None
                    QTimer.singleShot(50, lambda: self._process_queued_state(queued))
                return

            try:
                if self._anim_index < len(frame_list):
                    self.btn_play.setIcon(QIcon(frame_list[self._anim_index]))
            except Exception:
                pass

            self._anim_index += 1

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(on_frame)
        self._anim_timer.start(self._anim_interval_ms)

    def _process_queued_state(self, state):

        if state == 'play':
            if self._is_playing:
                return
            self.animate_to_play()
        elif state == 'pause':
            if not self._is_playing:
                return
            self.animate_to_pause()

    def animate_to_play(self):
        if self._animating:
            self._queued_state = 'play'
            return

        if not self.frames_pause_to_play and not self.frames_play_to_pause:
            self._set_play_icon_static()
            return

        if self.frames_pause_to_play:
            self._animate_frames(self.frames_pause_to_play, self._set_play_icon_static, direction='forward')
        elif self.frames_play_to_pause:
            self._animate_frames(self.frames_play_to_pause, self._set_play_icon_static, direction='reverse')
        else:
            self._set_play_icon_static()

    def animate_to_pause(self):
        if self._animating:
            self._queued_state = 'pause'
            return

        if not self.frames_play_to_pause and not self.frames_pause_to_play:
            self._set_pause_icon_static()
            return

        if self.frames_play_to_pause:
            self._animate_frames(self.frames_play_to_pause, self._set_pause_icon_static, direction='forward')
        elif self.frames_pause_to_play:
            self._animate_frames(self.frames_pause_to_play, self._set_pause_icon_static, direction='reverse')
        else:
            self._set_pause_icon_static()

    def _progress_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._progress_dragging = True
            self.progress_bar.set_dragging(True)
            self._handle_seek_event(event)
            event.accept()
        else:
            QProgressBar.mousePressEvent(self.progress_bar, event)

    def _progress_bar_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self._progress_dragging = False
            self.progress_bar.set_dragging(False)
            self._handle_seek_event(event)
            event.accept()
        else:
            QProgressBar.mouseReleaseEvent(self.progress_bar, event)

    def _progress_bar_mouse_move(self, event):
        if self._progress_dragging and (event.buttons() & Qt.LeftButton):
            self._handle_seek_event(event)
            event.accept()
        else:
            QProgressBar.mouseMoveEvent(self.progress_bar, event)

    def _handle_seek_event(self, event):
        if self._current_duration <= 0:
            return

        current_time = datetime.now().timestamp() * 1000

        if current_time - self._progress_last_update < 33:
            return

        self._progress_last_update = current_time

        x = event.position().x()
        w = self.progress_bar.width()

        if w <= 0:
            return

        pct = min(1.0, max(0.0, x / w))
        seek_pos = int(pct * self._current_duration)

        target_value = int(pct * (self.progress_bar.maximum() - self.progress_bar.minimum()))

        if abs(self.progress_bar.value() - target_value) > 1:
            self.progress_bar.setValue(target_value)
            elapsed_seconds = int(seek_pos // 1000)
            remaining_seconds = int((self._current_duration - seek_pos) // 1000) if self._current_duration > 0 else 0
            self.time_elapsed_label.setText(self._format_time(elapsed_seconds))
            self.time_remaining_label.setText(f"-{self._format_time(remaining_seconds)}")

        try:
            self.audio.set_position(seek_pos)
        except Exception as e:
            print(f"Error seeking: {e}")

    def init_ui(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(14, 14, 14, 14)
        central_layout.setSpacing(12)

        self.upper_bar = QFrame()
        self.upper_bar.setObjectName("upperBar")
        self.upper_bar.setFixedHeight(50)
        upper_layout = QHBoxLayout(self.upper_bar)
        upper_layout.setContentsMargins(16, 0, 16, 0)
        upper_layout.setSpacing(0)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)

        app_icon_label = QLabel()
        if os.path.exists("app_icon.png"):
            icon_pixmap = QPixmap("app_icon.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            app_icon_label.setPixmap(icon_pixmap)
        else:
            app_icon_label.setText("♫")
            app_icon_label.setFont(QFont("Segoe UI", 20))
        app_icon_label.setFixedSize(32, 32)
        title_layout.addWidget(app_icon_label)

        app_title = QLabel("PlayerV")
        app_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        app_title.setStyleSheet("color: #1DB954;")
        title_layout.addWidget(app_title)

        upper_layout.addLayout(title_layout)

        upper_layout.addStretch()

        self.btn_settings_top = QPushButton()
        self.btn_settings_top.setIcon(QIcon('assets/settings.png' if os.path.exists('assets/settings.png') else ''))
        self.btn_settings_top.setToolTip("Налаштування")
        self.btn_settings_top.setFixedSize(40, 40)
        self.btn_settings_top.setCursor(Qt.PointingHandCursor)
        self.btn_settings_top.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,10);
                border: 1px solid rgba(255,255,255,15);
                border-radius: 20px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,20);
                border-color: rgba(255,255,255,25);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,5);
            }
        """)
        self.btn_settings_top.clicked.connect(lambda: self.show_page("settings"))
        upper_layout.addWidget(self.btn_settings_top)

        central_layout.addWidget(self.upper_bar)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.left_container = QFrame()
        self.left_container.setObjectName("leftPanel")
        self.left_container.setFixedWidth(320)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title_layout = QHBoxLayout()
        left_title = QLabel("playlist")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_title_layout.addWidget(left_title)

        self.btn_add_music = QPushButton("add music")
        self.btn_add_music.setFixedHeight(30)
        self.btn_add_music.clicked.connect(self.add_music_files)
        left_title_layout.addWidget(self.btn_add_music)



        left_layout.addLayout(left_title_layout)

        self.playlist_scroll_area = QScrollArea()
        self.playlist_scroll_area.setWidgetResizable(True)
        self.playlist_scroll_area.setFrameShape(QFrame.NoFrame)
        self.playlist_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.playlist_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.playlist_container = QWidget()
        self.playlist_container.setObjectName("playlistContainer")
        self.playlist_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlist_container.customContextMenuRequested.connect(self.show_playlist_context_menu)

        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(5, 5, 5, 5)
        self.playlist_layout.setSpacing(10)

        self.playlist_scroll_area.setWidget(self.playlist_container)

        left_layout.addWidget(self.playlist_scroll_area)

        row.addWidget(self.left_container)

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

        self.bottom_container = QFrame()
        self.bottom_container.setObjectName("bottomPanel")
        bottom_layout = QHBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(10)

        self.current_track_info = QLabel("choice track")
        self.current_track_info.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
        """)
        bottom_layout.addWidget(self.current_track_info, 1)

        progress_container = QWidget()
        progress_container.setFixedHeight(50)
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(12)

        self.time_elapsed_label = QLabel("0:00")
        self.time_elapsed_label.setFixedWidth(50)
        self.time_elapsed_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_elapsed_label.setStyleSheet("""
            color: #ffffff;
            font-size: 12px;
            font-weight: bold;
            padding: 5px;
        """)
        progress_layout.addWidget(self.time_elapsed_label)

        self.progress_bar = RoundedProgressBar(height=14)
        self.progress_bar.set_colors(QColor(60, 60, 60, 200),
                                     [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)])

        self.progress_bar.mousePressEvent = self._progress_bar_mouse_press
        self.progress_bar.mouseReleaseEvent = self._progress_bar_mouse_release
        self.progress_bar.mouseMoveEvent = self._progress_bar_mouse_move
        self.progress_bar.setCursor(Qt.PointingHandCursor)

        self.progress_bar.setMouseTracking(False)

        progress_layout.addWidget(self.progress_bar, 1)

        self.time_remaining_label = QLabel("0:00")
        self.time_remaining_label.setFixedWidth(50)
        self.time_remaining_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.time_remaining_label.setStyleSheet("""
            color: #ffffff;
            font-size: 12px;
            font-weight: bold;
            padding: 5px;
        """)
        progress_layout.addWidget(self.time_remaining_label)

        bottom_layout.addWidget(progress_container, 3)

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

        self.btn_loop = QPushButton()
        self.btn_loop.setIcon(QIcon('assets/loop.png'))
        self.btn_loop.setToolTip("Увімкнути/вимкнути цикл")
        self.btn_loop.setCheckable(True)
        self._loop_enabled = False

        for btn in (self.btn_prev, self.btn_play, self.btn_next, self.btn_loop):
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
                    border-color: rgba(255,255,255,25);
                }
                QPushButton:pressed {
                    background: rgba(255,255,255,5);
                }
                QPushButton:checked {
                    background: rgba(29, 185, 84, 0.6);
                    border-color: rgba(29, 185, 84, 0.8);
                }
            """)

        self.btn_prev.clicked.connect(self.on_prev)
        self.btn_play.clicked.connect(self.on_play_pause)
        self.btn_next.clicked.connect(self.on_next)
        self.btn_loop.clicked.connect(self.toggle_loop)

        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)
        controls.addWidget(self.btn_loop)

        bottom_layout.addLayout(controls)

        central_layout.addWidget(self.bottom_container)
        self.setCentralWidget(central)

        self.setStyleSheet(self.build_stylesheet())
        self.update_playlist_panel()

        self.playlist_changed.connect(self.page_home.on_playlist_changed)
        self.library_updated.connect(self.page_home.refresh_library)
        self.library_updated.connect(self.update_playlist_panel)

        self.progress_updated.connect(self._on_progress_updated)

    def build_stylesheet(self) -> str:
        return """
        QWidget {
            background: transparent;
            color: #e8e8e8;
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 12px;
        }

        QFrame#upperBar {
            background: rgba(24,24,26,220);
            border-radius: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
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
        QWidget#playlistContainer {
            background: transparent;
        }

        QProgressBar {
            background: rgba(60, 60, 60, 200);
            border-radius: 7px;
            border: none;
            margin: 0px;
            padding: 0px;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(29, 185, 84, 1), 
                stop:0.5 rgba(35, 200, 95, 1),
                stop:1 rgba(29, 185, 84, 1));
            border-radius: 7px;
            border: none;
            margin: 0px;
        }

        QScrollArea {
            background: transparent;
            border: none;
            outline: none;
        }

        QScrollBar:vertical {
            background: rgba(255,255,255,10);
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,30);
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(255,255,255,50);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
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

    def scan_music_library(self):
        self.scanner = MusicScanner(self.music_dir)
        self.scanner.scan_complete.connect(self.on_scan_complete)
        self.scanner.start()

    def on_scan_complete(self, music_data):
        for track in music_data:
            self.library.add_track(track)
        self.update_playlist_panel()
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
                    if os.path.exists(dest_path):
                        name, ext = os.path.splitext(os.path.basename(file_path))
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(self.music_dir, f"{name}_{counter}{ext}")
                            counter += 1

                    shutil.copy2(file_path, dest_path)

                    scanner = MusicScanner(self.music_dir)
                    track_info = scanner.extract_track_info(dest_path)
                    if self.library.add_track(track_info):
                        print(f"Додано: {track_info['title']}")

                except Exception as e:
                    QMessageBox.warning(self, "Помилка", f"Не вдалося додати файл: {e}")

            self.update_playlist_panel()
            self.library_updated.emit()
            QMessageBox.information(self, "Файли додано",
                                    f"Додано {len(files)} файлів у бібліотеку")

    def update_playlist_panel(self):
        playlists = self.library.playlists

        existing_widgets = {}
        for i in range(self.playlist_layout.count()):
            item = self.playlist_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), PlaylistItem):
                widget = item.widget()
                existing_widgets[widget.playlist_name] = widget

        for playlist_name in list(existing_widgets.keys()):
            if playlist_name not in playlists:
                widget = existing_widgets.pop(playlist_name)
                widget.deleteLater()

        for playlist_name, track_ids in playlists.items():
            tracks = self.library.get_playlist_tracks(playlist_name)

            if playlist_name in existing_widgets:
                widget = existing_widgets[playlist_name]
                widget.tracks = tracks
                widget.update_collage()
                for i in range(widget.layout().count()):
                    item = widget.layout().itemAt(i)
                    if isinstance(item, QVBoxLayout):
                        for j in range(item.count()):
                            child = item.itemAt(j)
                            if child and child.widget() and isinstance(child.widget(), QLabel):
                                label = child.widget()
                                if "track" in label.text().lower():
                                    track_count = len(tracks)
                                    label.setText(f"{track_count} track{'s' if track_count != 1 else ''}")
                                    break
            else:
                playlist_item = PlaylistItem(playlist_name, tracks, self.library)
                playlist_item.playlist_clicked.connect(self.on_playlist_clicked)
                self.playlist_layout.addWidget(playlist_item)
                playlist_item.update_collage()

        for i, (playlist_name, _) in enumerate(playlists.items()):
            for j in range(self.playlist_layout.count()):
                item = self.playlist_layout.itemAt(j)
                if item and item.widget() and isinstance(item.widget(), PlaylistItem):
                    if item.widget().playlist_name == playlist_name and i != j:
                        widget = item.widget()
                        self.playlist_layout.removeWidget(widget)
                        self.playlist_layout.insertWidget(i, widget)
                        break

        self.playlist_layout.addStretch()

    def on_playlist_clicked(self, playlist_name, tracks):
        self.current_playlist_name = playlist_name
        self.current_playlist = tracks
        self.current_track_index = -1
        self.update_playlist_selection()
        self.playlist_changed.emit(playlist_name)

        was_playing = self._is_playing

        if self.current_playlist:
            self.play_track(self.current_playlist[0], should_animate=not was_playing)

    def update_playlist_selection(self):
        for i in range(self.playlist_layout.count()):
            item = self.playlist_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, PlaylistItem):
                    widget.setSelected(widget.playlist_name == self.current_playlist_name)

    def get_track_by_id(self, track_id):
        return self.library.get_track_by_id(track_id)

    def show_playlist_context_menu(self, position):
        menu = QMenu()
        add_music_action = menu.addAction("Додати музику")
        menu.addSeparator()
        create_playlist_action = menu.addAction("Створити новий плейлист")
        if self.current_playlist_name:
            menu.addSeparator()
            rename_action = menu.addAction(f"Перейменувати '{self.current_playlist_name}'")
            delete_action = menu.addAction(f"Видалити '{self.current_playlist_name}'")
        action = menu.exec_(self.playlist_scroll_area.mapToGlobal(position))
        if action == add_music_action:
            self.add_music_files()
        elif action == create_playlist_action:
            self.create_new_playlist()
        elif self.current_playlist_name:
            if action == rename_action:
                self.rename_current_playlist()
            elif action == delete_action:
                self.delete_current_playlist()

    def create_new_playlist(self):
        name, ok = QInputDialog.getText(self, "Новий плейлист", "Введіть назву плейлиста:")
        if ok and name:
            if self.library.create_playlist(name):
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Успішно", f"Плейлист '{name}' створено")
            else:
                QMessageBox.warning(self, "Помилка", f"Плейлист '{name}' вже існує")

    def rename_current_playlist(self):
        if not self.current_playlist_name:
            return
        if self.current_playlist_name in ['Favorites', 'Recently Added', 'Most Played']:
            QMessageBox.warning(self, "Помилка", "Системні плейлисти не можна перейменовувати")
            return
        new_name, ok = QInputDialog.getText(self, "Перейменувати плейлист", "Нова назва:",
                                            text=self.current_playlist_name)
        if ok and new_name and new_name != self.current_playlist_name:
            if self.library.rename_playlist(self.current_playlist_name, new_name):
                self.current_playlist_name = new_name
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Успішно", f"Плейлист перейменовано на '{new_name}'")
            else:
                QMessageBox.warning(self, "Помилка", "Не вдалося перейменувати плейлист")

    def delete_current_playlist(self):
        if not self.current_playlist_name:
            return
        if self.current_playlist_name in ['Favorites', 'Recently Added', 'Most Played']:
            QMessageBox.warning(self, "Помилка", "Системні плейлисти не можна видаляти")
            return
        reply = QMessageBox.question(self, "Підтвердження",
                                     f"Ви впевнені, що хочете видалити плейлист '{self.current_playlist_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.library.delete_playlist(self.current_playlist_name):
                self.current_playlist_name = ""
                self.current_playlist = []
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Успішно", "Плейлист видалено")
            else:
                QMessageBox.warning(self, "Помилка", "Не вдалося видалити плейлист")

    def on_playback_state_changed(self, state):
        pass

    def update_progress(self, position):
        if self._progress_dragging:
            return

        if self._current_duration > 0:
            percentage = (position / self._current_duration) * 1000 if self._current_duration > 0 else 0
            current_value = self.progress_bar.value()
            if abs(current_value - percentage) > 1:
                self.progress_bar.setValue(int(percentage))
                elapsed_seconds = int(position // 1000)
                remaining_seconds = int(
                    (self._current_duration - position) // 1000) if self._current_duration > 0 else 0
                self.time_elapsed_label.setText(self._format_time(elapsed_seconds))
                self.time_remaining_label.setText(f"-{self._format_time(remaining_seconds)}")
                self.progress_updated.emit(
                    int((position / self._current_duration) * 100) if self._current_duration > 0 else 0)
                if position > 0 and not self._progress_style_updated:
                    self._progress_style_updated = True
                    try:
                        self.progress_bar.update()
                    except Exception:
                        pass
        else:
            if self.progress_bar.value() != 0:
                self.progress_bar.setValue(0)
                self.time_elapsed_label.setText("0:00")
                self.time_remaining_label.setText("0:00")

    def update_duration(self, duration):
        if duration != self._current_duration:
            self._current_duration = duration
            if duration > 0:
                self.progress_bar.setValue(0)
                self._progress_style_updated = False
            else:
                self.progress_bar.setValue(0)

    def _format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def _on_progress_updated(self, percentage):
        pass

    def play_track_by_id(self, track_id, should_animate=None):
        """Відтворює трек за ID з можливістю контролю анімації"""
        track = self.library.get_track_by_id(track_id)
        if track:
            for i, t in enumerate(self.current_playlist):
                if t['id'] == track_id:
                    self.current_track_index = i
                    break
            else:
                self.current_track_index = len(self.current_playlist)
                self.current_playlist.append(track)

            if should_animate is None:
                should_animate = not self._is_playing

            self.play_track(track, should_animate)

    def play_track(self, track, should_animate=None):
        """Play a track with optional animation."""
        self._progress_style_updated = False
        file_path = track['file_path']
        try:
            self.audio.set_source(file_path)
        except Exception as e:
            print("Error setting source:", e)

        self.progress_bar.setValue(0)

        current_state_was_playing = self._is_playing

        try:
            self.audio.play()
        except Exception as e:
            print("Error audio.play():", e)

        self.current_track_info.setText(f"{track['title']} - {track['artist']}")

        if should_animate is None:
            should_animate = not current_state_was_playing

        if current_state_was_playing:
            pass
        else:
            if should_animate:
                self.animate_to_pause()
            else:
                self._set_pause_icon_static()

        self._is_playing = True
        self._start_polling()
        self.library.increment_play_count(track['id'])
        self.library_updated.emit()

    def media_status_changed(self, status):
        pass

    def _on_end_of_media(self):
        try:
            if self._loop_enabled and self.current_playlist and self.current_track_index >= 0:
                was_playing = self._is_playing
                QTimer.singleShot(100, lambda: self.play_track(
                    self.current_playlist[self.current_track_index],
                    should_animate=not was_playing
                ))
            elif not self._loop_enabled:
                was_playing = self._is_playing
                QTimer.singleShot(100, lambda: self.on_next_auto(was_playing))
        except Exception as e:
            print("Error in _on_end_of_media:", e)

    def on_next_auto(self, was_playing):
        """Автоматичний перехід на наступний трек (викликається після закінчення треку)"""
        if self._animating:
            return

        if self.current_playlist:
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def toggle_loop(self, checked):
        self._loop_enabled = checked



    def _on_refresh_complete(self, music_data):
        self.library.tracks.clear()
        for track in music_data:
            self.library.add_track(track)
        self.update_playlist_panel()
        self.library_updated.emit()
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("🔄 Оновити")
        QMessageBox.information(self, "Оновлено", "Музичну бібліотеку та плейлисти оновлено!")

    def on_play_pause(self):
        if self._animating:
            desired_state = 'pause' if self._is_playing else 'play'
            self._queued_state = desired_state
            return

        if self._is_playing:
            try:
                self.audio.pause()
            except Exception:
                pass
            self.animate_to_play()
            self._is_playing = False
            self._stop_polling()
        else:
            if self.current_playlist and self.current_track_index >= 0:
                self.play_track(self.current_playlist[self.current_track_index])
            elif self.current_playlist:
                self.current_track_index = 0
                self.play_track(self.current_playlist[0])
            else:
                QMessageBox.information(self, "Плейлист пустий", "У вибраному плейлисті немає треків.")

    def on_prev(self):
        if self._animating:
            return

        if self.current_playlist:
            was_playing = self._is_playing
            self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def on_next(self):
        if self._animating:
            return

        if self.current_playlist:
            was_playing = self._is_playing
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def on_track_double_clicked(self, track_id):
        """Викликається при подвійному кліку на трек у списку"""
        was_playing = self._is_playing
        self.play_track_by_id(track_id, should_animate=not was_playing)

    def update_progress_bar_theme(self, theme="default"):
        if isinstance(self.progress_bar, RoundedProgressBar):
            if theme == "dark":
                self.progress_bar.set_colors(QColor(60, 60, 60, 200),
                                             [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)])
            elif theme == "light":
                self.progress_bar.set_colors(QColor(200, 200, 200, 200),
                                             [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)])
            else:
                self.progress_bar.set_colors(QColor(60, 60, 60, 200),
                                             [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)])
        else:
            if theme == "dark":
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        background: rgba(50, 50, 50, 200);
                        border-radius: 7px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(29, 185, 84, 1), 
                            stop:0.5 rgba(35, 200, 95, 1),
                            stop:1 rgba(29, 185, 84, 1));
                        border-radius: 7px;
                    }
                """)
            elif theme == "light":
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        background: rgba(200, 200, 200, 200);
                        border-radius: 7px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(29, 185, 84, 1), 
                            stop:0.5 rgba(35, 200, 95, 1),
                            stop:1 rgba(29, 185, 84, 1));
                        border-radius: 7px;
                    }
                """)
            else:
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        background: rgba(60, 60, 60, 200);
                        border-radius: 7px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(29, 185, 84, 1), 
                            stop:0.5 rgba(35, 200, 95, 1),
                            stop:1 rgba(29, 185, 84, 1));
                        border-radius: 7px;
                    }
                """)

    def apply_theme(self):
        theme = self.settings.value("theme", "dark", type=str)
        pal = QPalette()
        if theme == "dark":
            pal.setColor(QPalette.Window, QColor(18, 18, 18))
            pal.setColor(QPalette.WindowText, QColor(230, 230, 230))
            self.update_progress_bar_theme("dark")
        else:
            pal.setColor(QPalette.Window, QColor(245, 245, 245))
            pal.setColor(QPalette.WindowText, QColor(30, 30, 30))
            self.update_progress_bar_theme("light")
        QApplication.setPalette(pal)

    def show_page(self, page: str):
        if page == "home":
            self.pages.setCurrentWidget(self.page_home)
        elif page == "library":
            self.pages.setCurrentWidget(self.page_playlist_page)
            try:
                self.page_playlist_page.refresh_playlists()
            except Exception:
                pass
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
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None

        self._cover_cache.clear()
        self._playlist_widgets.clear()

        try:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.sync()
        except Exception:
            pass

        try:
            self.page_home.cleanup()
        except Exception:
            pass

        try:
            self.audio.stop()
        except Exception:
            pass

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if os.path.exists("app_icon.png"):
        app.setWindowIcon(QIcon("app_icon.png"))

    os.makedirs('music', exist_ok=True)
    os.makedirs('covers', exist_ok=True)
    os.makedirs('assets', exist_ok=True)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())