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
    QFileDialog, QMessageBox, QMenu, QInputDialog, QListWidget, QListWidgetItem,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QThread, Signal, QUrl, QRectF
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QPixmap, QPainter, QBrush, QLinearGradient, QPainterPath
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui_base.home_page import HomePage
from gui_base.playist_page import Playlist
from gui_base.settings_page import SettingsPage
from gui_base.style import StyleManager, UpperToolBar

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


class RoundedProgressBar(QProgressBar):
    """Custom QProgressBar with adjustable corner rounding via radius_factor.

    radius_factor: fraction of height used for corner radius (0.0..0.5).
                   0.5 => fully semicircular ends.
                   0.25 => milder rounding.
    """

    def __init__(self, parent=None, height: int = 14, radius_factor: float = 0.25):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 1000)
        self.setValue(0)
        self.setFixedHeight(height)

        # Colors
        self._bg_color = QColor(60, 60, 60, 200)
        self._grad_colors = [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)]

        # remember last painted value to minimize repaints
        self._last_painted_value = None
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        # rounding control: keep in [0.0, 0.5]
        try:
            rf = float(radius_factor)
        except Exception:
            rf = 0.25
        self.radius_factor = max(0.0, min(0.5, rf))

    def set_colors(self, bg_color: QColor, grad_colors: list):
        self._bg_color = bg_color
        self._grad_colors = grad_colors
        self.update()

    def set_radius_factor(self, factor: float):
        """Update radius factor at runtime (0.0..0.5)."""
        try:
            f = float(factor)
        except Exception:
            return
        self.radius_factor = max(0.0, min(0.5, f))
        self.update()

    def paintEvent(self, event):
        # Avoid full repaint if value hasn't changed and event is tiny
        current_value = self.value()
        if self._last_painted_value == current_value and (event.rect().width() == 0 or event.rect().height() == 0):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Use radius_factor to control how rounded corners are.
        radius = rect.height() * self.radius_factor

        # Draw background rounded rect
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        # Draw foreground (chunk) with gradient
        minimum = self.minimum()
        maximum = self.maximum()
        if maximum > minimum and current_value > minimum:
            ratio = (current_value - minimum) / (maximum - minimum)
            fg_width = max(1.0, rect.width() * ratio)
            fg_rect = QRectF(rect.x(), rect.y(), fg_width, rect.height())

            grad = QLinearGradient(fg_rect.topLeft(), fg_rect.topRight())
            if len(self._grad_colors) >= 3:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(0.5, self._grad_colors[1])
                grad.setColorAt(1.0, self._grad_colors[2])
            elif len(self._grad_colors) == 2:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[1])
            else:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[0])

            painter.setBrush(QBrush(grad))
            # Use same radius for foreground rounded rect to keep consistent look
            painter.drawRoundedRect(fg_rect, radius, radius)

        # subtle border for crispness
        painter.setPen(QColor(255, 255, 255, 10))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        painter.end()
        self._last_painted_value = current_value


class PlaylistItem(QFrame):
    """Custom widget for displaying a playlist with collage of up to 4 track covers"""

    playlist_clicked = Signal(str, list)  # Emits playlist name and tracks when clicked

    def __init__(self, playlist_name, tracks, library):
        super().__init__()
        self.playlist_name = playlist_name
        self.tracks = tracks
        self.library = library
        self._selected = False
        self.setFixedHeight(200)  # Large playlist items
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("playlistItem")
        self.init_ui()
        self.update_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Playlist collage (2x2 grid of track covers)
        self.collage_label = QLabel()
        self.collage_label.setFixedSize(150, 150)
        self.collage_label.setAlignment(Qt.AlignCenter)
        self.collage_label.setStyleSheet("""
            QLabel {
                background-color: rgba(60, 60, 60, 0.5);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        # Create the collage
        collage_pixmap = self.create_playlist_collage()
        self.collage_label.setPixmap(collage_pixmap)

        layout.addWidget(self.collage_label, alignment=Qt.AlignCenter)

        # Playlist title and track count
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        # Playlist title
        title_label = QLabel(self.playlist_name)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ffffff;")
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label)

        # Track count
        track_count = len(self.tracks)
        count_label = QLabel(f"{track_count} track{'s' if track_count != 1 else ''}")
        count_label.setFont(QFont("Segoe UI", 9))
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet("color: #b3b3b3;")
        title_layout.addWidget(count_label)

        layout.addLayout(title_layout)

        # Connect click event
        self.mousePressEvent = self.on_click

    def create_playlist_collage(self):
        collage_size = QSize(150, 150)
        cell_size = QSize(72, 72)
        spacing = 3

        collage = QPixmap(collage_size)
        collage.fill(Qt.transparent)

        painter = QPainter(collage)
        painter.setRenderHint(QPainter.Antialiasing)

        # Build list of pixmaps or None
        track_covers = []
        for track in self.tracks[:4]:
            cover_path = track.get('cover_path')
            if cover_path and os.path.exists(cover_path):
                pixmap = QPixmap(cover_path)
                if not pixmap.isNull():
                    track_covers.append(pixmap)
                    continue
            track_covers.append(None)

        # Ensure length 4
        while len(track_covers) < 4:
            track_covers.append(None)

        positions = [
            (0, 0), (1, 0),
            (0, 1), (1, 1)
        ]

        for i, (row, col) in enumerate(positions):
            x = col * (cell_size.width() + spacing)
            y = row * (cell_size.height() + spacing)

            if track_covers[i] is not None:
                # Scale and draw with rounded clipping using QPainterPath
                scaled = track_covers[i].scaled(cell_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                # center
                draw_x = x + (cell_size.width() - scaled.width()) // 2
                draw_y = y + (cell_size.height() - scaled.height()) // 2

                path = QPainterPath()
                path.addRoundedRect(draw_x, draw_y, cell_size.width(), cell_size.height(), 8, 8)
                painter.setClipPath(path)
                painter.drawPixmap(draw_x, draw_y, scaled)
                painter.setClipping(False)
            else:
                painter.setBrush(QBrush(QColor(80, 80, 80, 180)))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, y, cell_size.width(), cell_size.height(), 8, 8)

                painter.setBrush(QBrush(QColor(200, 200, 200, 150)))
                note_size = 24
                note_x = x + (cell_size.width() - note_size) // 2
                note_y = y + (cell_size.height() - note_size) // 2
                painter.drawEllipse(note_x, note_y, note_size, note_size)

        painter.end()
        return collage

    def setSelected(self, selected):
        self._selected = selected
        self.update_style()

    def update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(29, 185, 84, 0.3);
                    border: 2px solid rgba(29, 185, 84, 0.6);
                    border-radius: 14px;
                    margin: 2px;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(29, 185, 84, 0.4);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(40, 40, 40, 0.8);
                    border-radius: 14px;
                    margin: 2px;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(60, 60, 60, 0.9);
                }
            """)

    def on_click(self, event):
        if event.button() == Qt.LeftButton:
            self.playlist_clicked.emit(self.playlist_name, self.tracks)
        super().mousePressEvent(event)


class MusicScanner(QThread):
    scan_progress = Signal(int, int)
    scan_complete = Signal(list)

    def __init__(self, music_dir):
        super().__init__()
        self.music_dir = music_dir

    def run(self):
        extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
        all_files = []
        for ext in extensions:
            all_files.extend(list(Path(self.music_dir).rglob(f'*{ext}')))

        self.scan_progress.emit(0, len(all_files))

        music_data = []
        for i, file_path in enumerate(all_files):
            try:
                music_data.append(self.extract_track_info(file_path))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            self.scan_progress.emit(i + 1, len(all_files))

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
                # Generic tag handling
                tags = getattr(audio, 'tags', None)
                if tags:
                    # ID3 style
                    try:
                        if 'TIT2' in tags: track['title'] = str(tags['TIT2'][0])
                        if 'TPE1' in tags: track['artist'] = str(tags['TPE1'][0])
                        if 'TALB' in tags: track['album'] = str(tags['TALB'][0])
                        if 'TCON' in tags: track['genre'] = str(tags['TCON'][0])
                        if 'TRCK' in tags: track['track_number'] = str(tags['TRCK'][0])
                        if 'TDRC' in tags: track['year'] = str(tags['TDRC'][0])
                    except Exception:
                        pass

                    # Extract attached pictures (APIC)
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

                # Fallbacks for other tag formats
                info = getattr(audio, 'info', None)
                if info and hasattr(info, 'length'):
                    try:
                        track['duration'] = int(info.length * 1000)  # keep milliseconds
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
        self.setMinimumSize(QSize(1200, 800))

        geom = self.settings.value("window_geometry", None)
        if geom:
            try:
                self.restoreGeometry(geom)
            except Exception:
                pass

        self.music_dir = '../../PycharmProjects/playerV/music'
        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir)

        self.library = MusicLibrary()
        self.current_playlist = []
        self.current_track_index = -1
        self.current_playlist_name = "Recently Added"

        self._is_playing = False
        self._current_duration = 0

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)

        self._progress_style_updated = False

        # Animation attributes
        self.frames_pause_to_play = []
        self.frames_play_to_pause = []
        self._animating = False
        self._anim_timer = None
        self._anim_index = 0
        self._anim_interval_ms = 40
        self._queued_state = None
        self._processing_click = False

        self.init_ui()
        self.apply_theme()
        self.apply_settings()

        # Load animations AFTER ui is created (needs btn_play)
        self.load_play_pause_animations()

        self.scan_music_library()

        self.show_page("home")

    def load_play_pause_animations(self):
        """Завантажує кадри з папок assets/pause-to-play і assets/play-to-pause."""

        def load_dir_frames(folder):
            frames = []
            if not os.path.isdir(folder):
                return frames
            files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            for fn in files:
                full = os.path.join(folder, fn)
                try:
                    pix = QPixmap(full)
                    if not pix.isNull():
                        frames.append(pix)
                except Exception:
                    pass
            return frames

        self.frames_pause_to_play = load_dir_frames(os.path.join('assets', 'pause-to-play'))
        self.frames_play_to_pause = load_dir_frames(os.path.join('assets', 'play-to-pause'))

        # Ensure a reasonable icon size on the button
        self.btn_play.setIconSize(QSize(28, 28))

        # Set initial static icon depending on current playback state
        state = self.media_player.playbackState()
        if state == QMediaPlayer.PlayingState:
            self._set_pause_icon_static()
        else:
            self._set_play_icon_static()

    def _set_play_icon_static(self):
        # prefer final frame from pause_to_play if available
        if self.frames_pause_to_play:
            pix = self.frames_pause_to_play[-1].scaled(self.btn_play.iconSize(), Qt.KeepAspectRatio,
                                                       Qt.SmoothTransformation)
            self.btn_play.setIcon(QIcon(pix))
        else:
            if os.path.exists('assets/play.png'):
                self.btn_play.setIcon(QIcon('assets/play.png'))
            else:
                self.btn_play.setIcon(QIcon())

    def _set_pause_icon_static(self):
        if self.frames_play_to_pause:
            pix = self.frames_play_to_pause[-1].scaled(self.btn_play.iconSize(), Qt.KeepAspectRatio,
                                                       Qt.SmoothTransformation)
            self.btn_play.setIcon(QIcon(pix))
        else:
            if os.path.exists('assets/pause.png'):
                self.btn_play.setIcon(QIcon('assets/pause.png'))
            else:
                self.btn_play.setIcon(QIcon())

    def _animate_frames(self, frames, on_finished_static, direction='forward'):
        """Play a list of QPixmap frames on the play button at fixed interval."""
        if not frames:
            on_finished_static()
            return

        # If already animating — queue desired final state and return
        if self._animating:
            # Determine desired state
            desired_state = 'pause' if on_finished_static == self._set_pause_icon_static else 'play'
            self._queued_state = desired_state
            return

        self._animating = True
        self._anim_index = 0

        # Prepare frame list according to direction
        frame_list = frames if direction == 'forward' else list(reversed(frames))

        # Show first frame immediately for instant feedback
        try:
            if frame_list:
                pix = frame_list[0].scaled(self.btn_play.iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.btn_play.setIcon(QIcon(pix))
        except Exception:
            pass

        def on_frame():
            if self._anim_index >= len(frame_list):
                # stop and finalize
                if self._anim_timer:
                    try:
                        self._anim_timer.stop()
                    except Exception:
                        pass
                    self._anim_timer = None

                self._animating = False

                # Apply final static icon
                try:
                    on_finished_static()
                except Exception:
                    pass

                # Check for queued state
                if self._queued_state:
                    queued = self._queued_state
                    self._queued_state = None
                    QTimer.singleShot(50, lambda: self._process_queued_state(queued))
                return

            try:
                if self._anim_index < len(frame_list):
                    pix = frame_list[self._anim_index].scaled(
                        self.btn_play.iconSize(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.btn_play.setIcon(QIcon(pix))
            except Exception:
                pass

            self._anim_index += 1

        # Timer for frames
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(on_frame)
        self._anim_timer.start(self._anim_interval_ms)

    def _process_queued_state(self, state):
        """Process queued state after current animation finishes."""
        if state == 'play':
            # Тільки якщо дійсно потрібно змінити на play
            if self.media_player.playbackState() == QMediaPlayer.PlayingState:
                # Вже граємо, нічого не робимо
                return
            self.animate_to_play()
        elif state == 'pause':
            # Тільки якщо дійсно потрібно змінити на pause
            if self.media_player.playbackState() == QMediaPlayer.PausedState:
                # Вже на паузі, нічого не робимо
                return
            self.animate_to_pause()

    def animate_to_play(self):
        # play animation from pause -> play
        if self._animating:
            # queue final desired state
            self._queued_state = 'play'
            return

        # If there are no animation frames, just set static icon
        if not self.frames_pause_to_play and not self.frames_play_to_pause:
            self._set_play_icon_static()
            return

        if self.frames_pause_to_play:
            self._animate_frames(self.frames_pause_to_play, self._set_play_icon_static, direction='forward')
        elif self.frames_play_to_pause:
            # reverse play->pause to get pause->play visual
            self._animate_frames(self.frames_play_to_pause, self._set_play_icon_static, direction='reverse')
        else:
            self._set_play_icon_static()

    def animate_to_pause(self):
        # play animation from play -> pause
        if self._animating:
            self._queued_state = 'pause'
            return

        # If there are no animation frames, just set static icon
        if not self.frames_play_to_pause and not self.frames_pause_to_play:
            self._set_pause_icon_static()
            return

        if self.frames_play_to_pause:
            self._animate_frames(self.frames_play_to_pause, self._set_pause_icon_static, direction='forward')
        elif self.frames_pause_to_play:
            # reverse pause->play to get play->pause visual
            self._animate_frames(self.frames_pause_to_play, self._set_pause_icon_static, direction='reverse')
        else:
            self._set_pause_icon_static()

    def init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add Upper Toolbar
        self.upper_toolbar = UpperToolBar(self)
        main_layout.addWidget(self.upper_toolbar)

        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(12)

        # Left panel (playlists)
        self.left_container = QFrame()
        self.left_container.setObjectName("leftPanel")
        self.left_container.setFixedWidth(320)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title_layout = QHBoxLayout()
        left_title = QLabel("Playlists")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_title_layout.addWidget(left_title)
        left_title_layout.addStretch()

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

        # Pages container
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

        content_layout.addLayout(row)

        # Bottom player controls
        self.bottom_container = QFrame()
        self.bottom_container.setObjectName("bottomPanel")
        bottom_layout = QHBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(15)

        # Cover art widget (less rounded corners now)
        self.bottom_cover_label = QLabel()
        self.bottom_cover_label.setFixedSize(60, 60)
        self.bottom_cover_label.setStyleSheet("""
            QLabel {
                background-color: rgba(60, 60, 60, 0.8);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        self.bottom_cover_label.setAlignment(Qt.AlignCenter)
        self.bottom_cover_label.setText("🎵")
        self.bottom_cover_label.setFont(QFont("Segoe UI", 20))
        bottom_layout.addWidget(self.bottom_cover_label)

        # Track info
        track_info_layout = QVBoxLayout()
        track_info_layout.setSpacing(2)

        self.current_track_info = QLabel("Select a track")
        self.current_track_info.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            padding: 0px;
        """)
        track_info_layout.addWidget(self.current_track_info)

        self.current_artist_info = QLabel("")
        self.current_artist_info.setStyleSheet("""
            color: #b3b3b3;
            font-size: 12px;
            padding: 0px;
        """)
        track_info_layout.addWidget(self.current_artist_info)

        bottom_layout.addLayout(track_info_layout, 1)

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

        # Here you can change radius_factor if you want less/more rounded corners
        self.progress_bar = RoundedProgressBar(height=14, radius_factor=0.25)
        self.progress_bar.set_colors(QColor(60, 60, 60, 200),
                                     [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)])

        def _mouse_press(event):
            if event.button() == Qt.LeftButton and self._current_duration > 0:
                x = event.position().x()
                w = self.progress_bar.width()
                pct = min(1.0, max(0.0, x / w)) if w > 0 else 0.0
                seek_pos = int(pct * self._current_duration)
                try:
                    self.media_player.setPosition(seek_pos)
                except Exception:
                    pass
                self.progress_bar.setValue(int(pct * (self.progress_bar.maximum() - self.progress_bar.minimum())))
            QProgressBar.mousePressEvent(self.progress_bar, event)

        def _mouse_move(event):
            if event.buttons() & Qt.LeftButton:
                _mouse_press(event)
            QProgressBar.mouseMoveEvent(self.progress_bar, event)

        self.progress_bar.mousePressEvent = _mouse_press
        self.progress_bar.mouseMoveEvent = _mouse_move
        self.progress_bar.setCursor(Qt.PointingHandCursor)
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

        # Player controls
        controls = QHBoxLayout()
        controls.setSpacing(12)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(QIcon('assets/back.png'))
        self.btn_prev.setToolTip("Previous track")

        self.btn_play = QPushButton()
        self.btn_play.setIcon(QIcon('assets/play.png'))
        self.btn_play.setToolTip("Play/Pause")

        self.btn_next = QPushButton()
        self.btn_next.setIcon(QIcon('assets/next.png'))
        self.btn_next.setToolTip("Next track")

        self.btn_loop = QPushButton()
        self.btn_loop.setIcon(QIcon('assets/loop.png'))
        self.btn_loop.setToolTip("Toggle loop")
        self.btn_loop.setCheckable(True)
        self._loop_enabled = False

        for btn in (self.btn_prev, self.btn_play, self.btn_next, self.btn_loop):
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setObjectName("playerButton")

        self.btn_prev.clicked.connect(self.on_prev)
        self.btn_play.clicked.connect(self.on_play_pause)
        self.btn_next.clicked.connect(self.on_next)
        self.btn_loop.clicked.connect(self.toggle_loop)

        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)
        controls.addWidget(self.btn_loop)

        bottom_layout.addLayout(controls)

        content_layout.addWidget(self.bottom_container)
        main_layout.addWidget(content_widget, 1)

        self.setCentralWidget(central)

        # Apply unified stylesheet
        self.apply_stylesheet()

        self.update_playlist_panel()

        self.playlist_changed.connect(self.page_home.on_playlist_changed)
        self.library_updated.connect(self.page_home.refresh_library)
        self.library_updated.connect(self.update_playlist_panel)
        self.progress_updated.connect(self._on_progress_updated)

    def apply_stylesheet(self):
        """Apply unified stylesheet from StyleManager"""
        theme = self.settings.value("theme", "dark", type=str)
        stylesheet = StyleManager.get_theme_stylesheet(theme)
        self.setStyleSheet(stylesheet)

        # Update upper toolbar theme
        if hasattr(self, 'upper_toolbar'):
            self.upper_toolbar.apply_theme()

    def _create_rounded_pixmap(self, source_pixmap, target_size, radius=None):
        """Return a new QPixmap sized to target_size with rounded corners (filled from source_pixmap).

        - center-crop semantics so image fills the rounded area without distortion.
        - If radius is None, use a small rounded radius proportional to size (0.15 * min(w,h)).
        """
        if source_pixmap is None or source_pixmap.isNull():
            return QPixmap()

        w = int(target_size.width())
        h = int(target_size.height())
        if w <= 0 or h <= 0:
            return QPixmap()

        out = QPixmap(w, h)
        out.fill(Qt.transparent)

        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing)

        if radius is None:
            r = min(w, h) * 0.15  # small, pleasant rounding (≈9px for 60x60)
        else:
            r = float(radius)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.0, 0.0, float(w), float(h)), r, r)

        painter.setClipPath(path)

        # Scale source to cover the target (center-crop)
        scaled = source_pixmap.scaled(QSize(w, h), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        sx = (scaled.width() - w) // 2
        sy = (scaled.height() - h) // 2
        painter.drawPixmap(-sx, -sy, scaled)

        painter.end()
        return out

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
            "Select music files",
            "",
            "Music files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac)"
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
                        print(f"Added: {track_info['title']}")

                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to add file: {e}")

            self.update_playlist_panel()
            self.library_updated.emit()
            QMessageBox.information(self, "Files added",
                                    f"Added {len(files)} files to library")

    def update_playlist_panel(self):
        while self.playlist_layout.count():
            child = self.playlist_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        playlists = self.library.playlists
        for playlist_name, track_ids in playlists.items():
            tracks = self.library.get_playlist_tracks(playlist_name)
            playlist_item = PlaylistItem(playlist_name, tracks, self.library)
            playlist_item.playlist_clicked.connect(self.on_playlist_clicked)
            self.playlist_layout.addWidget(playlist_item)
        self.playlist_layout.addStretch()

    def on_playlist_clicked(self, playlist_name, tracks):
        self.current_playlist_name = playlist_name
        self.current_playlist = tracks
        self.current_track_index = -1
        self.update_playlist_selection()
        self.playlist_changed.emit(playlist_name)

        # Determine if player is currently playing
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState

        if self.current_playlist:
            # If player is already playing, don't animate
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
        add_music_action = menu.addAction("Add music")
        menu.addSeparator()
        create_playlist_action = menu.addAction("Create new playlist")
        if self.current_playlist_name:
            menu.addSeparator()
            rename_action = menu.addAction(f"Rename '{self.current_playlist_name}'")
            delete_action = menu.addAction(f"Delete '{self.current_playlist_name}'")
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
        name, ok = QInputDialog.getText(self, "New playlist", "Enter playlist name:")
        if ok and name:
            if self.library.create_playlist(name):
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Success", f"Playlist '{name}' created")
            else:
                QMessageBox.warning(self, "Error", f"Playlist '{name}' already exists")

    def rename_current_playlist(self):
        if not self.current_playlist_name:
            return
        if self.current_playlist_name in ['Favorites', 'Recently Added', 'Most Played']:
            QMessageBox.warning(self, "Error", "System playlists cannot be renamed")
            return
        new_name, ok = QInputDialog.getText(self, "Rename playlist", "New name:",
                                            text=self.current_playlist_name)
        if ok and new_name and new_name != self.current_playlist_name:
            if self.library.rename_playlist(self.current_playlist_name, new_name):
                self.current_playlist_name = new_name
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Success", f"Playlist renamed to '{new_name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to rename playlist")

    def delete_current_playlist(self):
        if not self.current_playlist_name:
            return
        if self.current_playlist_name in ['Favorites', 'Recently Added', 'Most Played']:
            QMessageBox.warning(self, "Error", "System playlists cannot be deleted")
            return
        reply = QMessageBox.question(self, "Confirmation",
                                     f"Are you sure you want to delete playlist '{self.current_playlist_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.library.delete_playlist(self.current_playlist_name):
                self.current_playlist_name = ""
                self.current_playlist = []
                self.update_playlist_panel()
                self.library_updated.emit()
                QMessageBox.information(self, "Success", "Playlist deleted")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete playlist")

    def _progress_bar_clicked(self, event):
        if event.button() == Qt.LeftButton and self._current_duration > 0:
            click_x = event.position().x()
            progress_width = self.progress_bar.width()
            percentage = min(1.0, max(0.0, click_x / progress_width)) if progress_width > 0 else 0.0
            seek_position = int(percentage * self._current_duration)
            self.media_player.setPosition(seek_position)
            target_value = int(percentage * 1000)
            self.progress_bar.setValue(target_value)
            self.update_progress(seek_position)

    def _progress_bar_mouse_move(self, event):
        if event.buttons() & Qt.LeftButton:
            self._progress_bar_clicked(event)

    def on_playback_state_changed(self, state):
        # Don't interrupt animation if it's in progress
        if self._animating:
            return

        if state == QMediaPlayer.PlayingState:
            self._is_playing = True
            # Only set static icon if not animating
            if not self._animating:
                self._set_pause_icon_static()
            if self.current_playlist and self.current_track_index >= 0:
                track = self.current_playlist[self.current_track_index]
                self.current_track_info.setText(track.get('title', 'Unknown'))
                self.current_artist_info.setText(track.get('artist', 'Unknown Artist'))
                self.update_bottom_cover_art(track)
        elif state == QMediaPlayer.PausedState:
            self._is_playing = False
            if not self._animating:
                self._set_play_icon_static()
        elif state == QMediaPlayer.StoppedState:
            self._is_playing = False
            if not self._animating:
                self._set_play_icon_static()
            self.progress_bar.setValue(0)

    def update_progress(self, position):
        if self._current_duration > 0:
            # position may be milliseconds
            percentage = (position / self._current_duration) * 1000 if self._current_duration > 0 else 0
            self.progress_bar.setValue(int(percentage))
            elapsed_seconds = int(position // 1000)
            remaining_seconds = int((self._current_duration - position) // 1000) if self._current_duration > 0 else 0
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
            self.progress_bar.setValue(0)
            self.time_elapsed_label.setText("0:00")
            self.time_remaining_label.setText("0:00")

    def update_duration(self, duration):
        # duration may be milliseconds
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

    def update_bottom_cover_art(self, track):
        """Update cover art in bottom control panel with small corner rounding (not full circle)."""
        cover_path = track.get('cover_path') if track else None
        if cover_path and os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            if not pixmap.isNull():
                target_size = self.bottom_cover_label.size()
                # small rounded corners: 15% of min dimension
                radius = min(target_size.width(), target_size.height()) * 0.15
                rounded = self._create_rounded_pixmap(pixmap, target_size, radius=radius)
                self.bottom_cover_label.setPixmap(rounded)
                self.bottom_cover_label.setText("")
                self.bottom_cover_label.setAlignment(Qt.AlignCenter)
                return

        # If no cover art, clear pixmap and show default music note
        self.bottom_cover_label.setPixmap(QPixmap())
        self.bottom_cover_label.setText("🎵")
        self.bottom_cover_label.setFont(QFont("Segoe UI", 20))
        self.bottom_cover_label.setAlignment(Qt.AlignCenter)

    def play_track_by_id(self, track_id, should_animate=None):
        """Play track by ID with optional animation control"""
        track = self.library.get_track_by_id(track_id)
        if track:
            # Find track in current playlist
            for i, t in enumerate(self.current_playlist):
                if t['id'] == track_id:
                    self.current_track_index = i
                    break
            else:
                # If track not found in current playlist, add it
                self.current_track_index = len(self.current_playlist)
                self.current_playlist.append(track)

            # If should_animate not specified, determine automatically
            if should_animate is None:
                # Animate only if player is not playing
                should_animate = not (self.media_player.playbackState() == QMediaPlayer.PlayingState)

            self.play_track(track, should_animate)

    def play_track(self, track, should_animate=None):
        """Play a track with optional animation."""
        self._progress_style_updated = False
        file_url = QUrl.fromLocalFile(track['file_path'])
        self.media_player.setSource(file_url)
        self.progress_bar.setValue(0)

        # Get current state before playing
        current_state = self.media_player.playbackState()
        self.media_player.play()

        self.current_track_info.setText(track.get('title', 'Unknown'))
        self.current_artist_info.setText(track.get('artist', 'Unknown Artist'))
        self.update_bottom_cover_art(track)

        # If should_animate not specified, determine automatically
        if should_animate is None:
            # Animate only if player is not playing
            should_animate = not (current_state == QMediaPlayer.PlayingState)

        # Key logic: if track is already playing - don't change icon
        # If track is not playing - animate only if should_animate == True
        if current_state == QMediaPlayer.PlayingState:
            # If already playing, DON'T change icon at all
            pass  # Do nothing, icon stays as pause
        else:
            # If not playing, animate or set static icon
            if should_animate:
                self.animate_to_pause()
            else:
                self._set_pause_icon_static()

        self._is_playing = True
        self.library.increment_play_count(track['id'])
        self.library_updated.emit()

    def media_status_changed(self, status):
        try:
            # Use MediaStatus enum consistently
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                if self._loop_enabled and self.current_playlist and self.current_track_index >= 0:
                    # Small delay before replaying
                    was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState
                    QTimer.singleShot(100, lambda: self.play_track(
                        self.current_playlist[self.current_track_index],
                        should_animate=not was_playing
                    ))
                elif not self._loop_enabled:
                    was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState
                    QTimer.singleShot(100, lambda: self.on_next_auto(was_playing))
        except Exception as e:
            print(f"Error in media_status_changed: {e}")

    def on_next_auto(self, was_playing):
        """Automatic transition to next track (called after track ends)"""
        if self._animating:
            return

        if self.current_playlist:
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            # If track is already playing, don't animate icon change
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def toggle_loop(self, checked):
        self._loop_enabled = checked

    def on_play_pause(self):
        if self._animating:
            # Determine desired state based on current playback state
            state = self.media_player.playbackState()
            desired_state = 'pause' if state == QMediaPlayer.PlayingState else 'play'
            self._queued_state = desired_state
            return

        state = self.media_player.playbackState()
        if state == QMediaPlayer.PlayingState:
            self.media_player.pause()
            # animate pause -> play
            self.animate_to_play()
            self._is_playing = False
        elif state == QMediaPlayer.PausedState:
            self.media_player.play()
            # animate play -> pause
            self.animate_to_pause()
            self._is_playing = True
        else:
            if self.current_playlist and self.current_track_index >= 0:
                self.play_track(self.current_playlist[self.current_track_index])
            elif self.current_playlist:
                self.current_track_index = 0
                self.play_track(self.current_playlist[0])
            else:
                QMessageBox.information(self, "Empty playlist", "Selected playlist has no tracks.")

    def on_prev(self):
        if self._animating:
            return

        if self.current_playlist:
            # Determine if player is currently playing
            was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState
            self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
            # If track is already playing, don't animate icon change
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def on_next(self):
        if self._animating:
            return

        if self.current_playlist:
            # Determine if player is currently playing
            was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            # If track is already playing, don't animate icon change
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def on_track_double_clicked(self, track_id):
        """Called when double-clicking a track in the list"""
        # Determine if player is currently playing
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlayingState
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
        """Apply theme to the application"""
        theme = self.settings.value("theme", "dark", type=str)

        # Apply palette and stylesheet
        StyleManager.apply_application_theme(QApplication.instance(), theme)
        self.apply_stylesheet()

        # Update progress bar theme
        if theme == "dark":
            self.update_progress_bar_theme("dark")
        else:
            self.update_progress_bar_theme("light")

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
        """Apply settings to all pages"""
        try:
            self.page_home.apply_settings(self.settings)
        except Exception:
            pass
        try:
            self.page_playlist_page.apply_settings(self.settings)
        except Exception:
            pass
        try:
            self.page_settings.apply_settings(self.settings)
        except Exception:
            pass

        # Re-apply theme
        self.apply_theme()

    def closeEvent(self, event):
        # Stop all animations
        if self._anim_timer:
            self._anim_timer.stop()
            self._anim_timer = None

        try:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.sync()
        except Exception:
            pass

        try:
            self.page_home.cleanup()
        except Exception:
            pass

        # Stop media player
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.stop()

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
