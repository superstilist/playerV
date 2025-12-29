# main.py
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
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QThread, Signal, QObject, QUrl, QRectF, QPropertyAnimation, \
    QEasingCurve
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QPixmap, QPainter, QBrush, QLinearGradient, QPainterPath

# try to import vlc (python-vlc). If not available, we'll fallback to QtMultimedia QMediaPlayer.
try:
    import vlc  # type: ignore

    _HAVE_VLC = True
except Exception:
    _HAVE_VLC = False

# Import QtMultimedia for fallback
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui_base.home_page import HomePage
from gui_base.playist_page import Playlist
from gui_base.settings_page import SettingsPage

SETTINGS_ORG = "PlayerV"
SETTINGS_APP = "Player"


# -----------------------
# Audio engine wrappers
# -----------------------
class AudioEngineVLC(QObject):
    """Audio engine using python-vlc with Qt-friendly signals."""
    position_changed = Signal(int)  # ms
    duration_changed = Signal(int)  # ms
    state_changed = Signal(str)  # 'playing', 'paused', 'stopped'
    end_of_media = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self._media = None
        self._duration = 0
        self._position = 0

        # event manager
        self._em = self.player.event_manager()
        # attach events
        self._em.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
        self._em.event_attach(vlc.EventType.MediaPlayerPaused, self._on_state_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_state_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerStopped, self._on_state_changed)

    def _on_time_changed(self, event):
        # pollable - emit current time
        try:
            t = self.player.get_time()
            if t is None: t = 0
            self.position_changed.emit(max(0, int(t)))
        except Exception:
            pass

    def _on_end_reached(self, event):
        # ended
        self.end_of_media.emit()

    def _on_state_changed(self, event):
        # map to simple states
        st = self.player.get_state()
        if st == vlc.State.Playing:
            self.state_changed.emit('playing')
        elif st == vlc.State.Paused:
            self.state_changed.emit('paused')
        elif st in (vlc.State.Ended, vlc.State.Stopped):
            self.state_changed.emit('stopped')

    def set_source(self, file_path):
        try:
            media = self.instance.media_new(str(file_path))
            # parse media metadata asynchronously (may help duration)
            try:
                media.parse_with_options(vlc.MediaParseFlag.parse_local, timeout=0)
            except Exception:
                pass
            self.player.set_media(media)
            self._media = media
            # after setting media, length may appear only after play/parse
            # we'll poll duration externally from MainWindow
        except Exception as e:
            print("VLC set_source error:", e)

    def play(self):
        try:
            self.player.play()
        except Exception as e:
            print("VLC play error:", e)

    def pause(self):
        try:
            self.player.pause()
        except Exception as e:
            print("VLC pause error:", e)

    def stop(self):
        try:
            self.player.stop()
        except Exception as e:
            print("VLC stop error:", e)

    def set_position(self, ms):
        try:
            # set_time expects ms
            self.player.set_time(int(ms))
        except Exception:
            pass

    def get_position(self):
        try:
            t = self.player.get_time()
            return t if t and t != -1 else 0
        except Exception:
            return 0

    def get_duration(self):
        try:
            d = self.player.get_length()
            return d if d and d != -1 else 0
        except Exception:
            return 0


class AudioEngineQt(QObject):
    """Fallback audio engine that wraps QMediaPlayer to provide same signals."""
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(str)
    end_of_media = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.playbackStateChanged.connect(self._on_playback_state)

    def set_source(self, file_path):
        try:
            url = QUrl.fromLocalFile(file_path)
            self.player.setSource(url)
        except Exception as e:
            print("QtAudio set_source error:", e)

    def play(self):
        try:
            self.player.play()
        except Exception as e:
            print("QtAudio play error:", e)

    def pause(self):
        try:
            self.player.pause()
        except Exception as e:
            print("QtAudio pause error:", e)

    def stop(self):
        try:
            self.player.stop()
        except Exception as e:
            print("QtAudio stop error:", e)

    def set_position(self, ms):
        try:
            self.player.setPosition(int(ms))
        except Exception:
            pass

    def get_position(self):
        try:
            return int(self.player.position())
        except Exception:
            return 0

    def get_duration(self):
        try:
            return int(self.player.duration())
        except Exception:
            return 0

    def _on_position(self, pos):
        self.position_changed.emit(int(pos))

    def _on_duration(self, dur):
        self.duration_changed.emit(int(dur))

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlayingState:
            self.state_changed.emit('playing')
        elif state == QMediaPlayer.PausedState:
            self.state_changed.emit('paused')
        else:
            self.state_changed.emit('stopped')

    def _on_media_status(self, status):
        # EndOfMedia handled by playbackState/duration logic sometimes; emit end if ended
        from PySide6.QtMultimedia import QMediaPlayer as QMP
        if status == QMP.MediaStatus.EndOfMedia:
            self.end_of_media.emit()


# -----------------------------------------
# Повний main.py (оновлено)
# -----------------------------------------

class RoundedProgressBar(QProgressBar):
    """Custom QProgressBar that always paints fully rounded ends and minimizes repaints."""

    def __init__(self, parent=None, height: int = 14):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 1000)
        self.setValue(0)
        self.setFixedHeight(height)

        # Colors - smoother gradient
        self._bg_color = QColor(70, 70, 70, 180)
        self._grad_colors = [
            QColor(29, 185, 84),  # Bright green
            QColor(45, 210, 110),  # Lighter green
            QColor(29, 185, 84)  # Back to bright green
        ]

        # Add glow effect colors for active state
        self._glow_color = QColor(29, 185, 84, 80)
        self._is_active = False

        # Small optimization: remember last painted value
        self._last_painted_value = None
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def set_colors(self, bg_color: QColor, grad_colors: list):
        self._bg_color = bg_color
        self._grad_colors = grad_colors
        self.update()

    def set_active(self, active: bool):
        self._is_active = active
        self.update()

    def paintEvent(self, event):
        # Avoid full repaint if value hasn't changed and event is not a resize
        current_value = self.value()
        if self._last_painted_value == current_value and (event.rect().width() == 0 or event.rect().height() == 0):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2.0

        # Draw subtle glow when active
        if self._is_active:
            glow_rect = rect.adjusted(-1, -1, 1, 1)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._glow_color))
            painter.drawRoundedRect(glow_rect, radius + 1, radius + 1)

        # Draw background rounded rect with subtle gradient
        painter.setPen(Qt.NoPen)
        bg_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        bg_grad.setColorAt(0, QColor(60, 60, 60, 220))
        bg_grad.setColorAt(1, QColor(80, 80, 80, 220))
        painter.setBrush(QBrush(bg_grad))
        painter.drawRoundedRect(rect, radius, radius)

        # Draw foreground (chunk) with smooth gradient
        minimum = self.minimum()
        maximum = self.maximum()
        if maximum > minimum and current_value > minimum:
            ratio = (current_value - minimum) / (maximum - minimum)
            fg_width = max(2.0, rect.width() * ratio)
            fg_rect = QRectF(rect.x(), rect.y(), fg_width, rect.height())

            grad = QLinearGradient(fg_rect.topLeft(), fg_rect.topRight())
            if len(self._grad_colors) >= 3:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(0.3, self._grad_colors[1])
                grad.setColorAt(0.7, self._grad_colors[1])
                grad.setColorAt(1.0, self._grad_colors[2])
            elif len(self._grad_colors) == 2:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[1])
            else:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[0])

            painter.setBrush(QBrush(grad))
            # Rounded rect ensures circular ends even for fg_width < height
            painter.drawRoundedRect(fg_rect, radius, radius)

            # Add subtle highlight on top
            highlight_rect = fg_rect.adjusted(0, 0, 0, -fg_rect.height() * 0.7)
            highlight_grad = QLinearGradient(highlight_rect.topLeft(), highlight_rect.bottomLeft())
            highlight_grad.setColorAt(0, QColor(255, 255, 255, 40))
            highlight_grad.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(highlight_grad))
            painter.drawRoundedRect(fg_rect, radius, radius)

        # subtle border for crispness
        painter.setPen(QColor(255, 255, 255, 15))
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

        # Animation for hover effect
        self._hover_animation = QPropertyAnimation(self, b"geometry")
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

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
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

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

                # Add subtle overlay for better text visibility
                painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, y, cell_size.width(), cell_size.height(), 8, 8)
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
        if self._selected != selected:
            self._selected = selected
            self.update_style()

            # Add subtle animation for selection
            if selected:
                self.animate_selection()

    def animate_selection(self):
        """Animate the selection with a subtle pulse effect"""
        current_geom = self.geometry()
        self._hover_animation.stop()
        self._hover_animation.setStartValue(current_geom)
        self._hover_animation.setEndValue(current_geom.adjusted(-1, -1, 1, 1))
        self._hover_animation.start()

    def update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(29, 185, 84, 0.25);
                    border: 2px solid rgba(29, 185, 84, 0.5);
                    border-radius: 14px;
                    margin: 2px;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(29, 185, 84, 0.35);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(40, 40, 40, 0.8);
                    border-radius: 14px;
                    margin: 2px;
                    border: 2px solid transparent;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(60, 60, 60, 0.9);
                    border: 2px solid rgba(255, 255, 255, 0.1);
                }
            """)

    def on_click(self, event):
        if event.button() == Qt.LeftButton:
            # Add click feedback animation
            self.animate_click()
            self.playlist_clicked.emit(self.playlist_name, self.tracks)
        super().mousePressEvent(event)

    def animate_click(self):
        """Subtle click animation"""
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(100)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        current = self.geometry()
        anim.setStartValue(current)
        anim.setEndValue(current.adjusted(0, 1, 0, 1))
        anim.start()


class MusicScanner(QThread):
    scan_progress = Signal(int, int)
    scan_complete = Signal(list)

    def __init__(self, music_dir):
        super().__init__()
        self.music_dir = music_dir

    def run(self):
        # Optimize scanning: do single traversal and filter extensions
        extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}
        all_files = []
        root = Path(self.music_dir)
        if not root.exists():
            self.scan_complete.emit([])
            return

        for p in root.rglob('*'):
            if p.is_file() and p.suffix.lower() in extensions:
                all_files.append(p)

        total = len(all_files)
        self.scan_progress.emit(0, total)

        music_data = []
        for i, file_path in enumerate(all_files):
            try:
                music_data.append(self.extract_track_info(file_path))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
            self.scan_progress.emit(i + 1, total)

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

        # playback state boolean - unified regardless of engine
        self._is_playing = False
        self._current_duration = 0

        # choose audio engine (VLC preferred)
        if _HAVE_VLC:
            self.audio = AudioEngineVLC(self)
            self._using_vlc = True
        else:
            self.audio = AudioEngineQt(self)
            self._using_vlc = False

        # connect audio signals
        self.audio.position_changed.connect(self.update_progress)
        # duration may be provided by engine; we'll poll occasionally too
        try:
            self.audio.duration_changed.connect(self.update_duration)
        except Exception:
            pass
        self.audio.state_changed.connect(self.on_playback_state_changed_wrapper)
        self.audio.end_of_media.connect(self._on_end_of_media)

        # poll timer to keep position/duration accurate for engines like vlc
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)  # Increased frequency for smoother updates
        self._poll_timer.timeout.connect(self._poll_audio_status)
        self._poll_active = False

        self._progress_style_updated = False

        # Animation attributes
        self.frames_pause_to_play = []
        self.frames_play_to_pause = []
        self._animating = False
        self._anim_timer = None
        self._anim_index = 0
        self._anim_interval_ms = 30  # Increased to ~33 FPS for smoother animation
        self._queued_state = None  # 'play' or 'pause' if a click happened during animation
        self._processing_click = False  # Prevent rapid repeated clicks

        # cover pixmap cache (simple)
        self._cover_cache = {}

        self.init_ui()
        self.apply_theme()
        self.apply_settings()

        # load animations AFTER ui is created (needs btn_play)
        self.load_play_pause_animations()

        self.scan_music_library()

        self.show_page("home")

    # -------------------
    # Audio polling & signals
    # -------------------
    def _poll_audio_status(self):
        # Poll position and duration only when needed
        try:
            pos = self.audio.get_position()
            dur = self.audio.get_duration()
            # emit position
            self.update_progress(pos)
            # if duration available and changed, update
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
        # state_str: 'playing', 'paused', 'stopped'
        if state_str == 'playing':
            self._is_playing = True
            self._start_polling()
            # Activate progress bar
            if isinstance(self.progress_bar, RoundedProgressBar):
                self.progress_bar.set_active(True)
            if not self._animating:
                self._set_pause_icon_static()
        elif state_str == 'paused':
            self._is_playing = False
            # keep polling a bit; but you can stop to save CPU
            self._stop_polling()
            # Deactivate progress bar
            if isinstance(self.progress_bar, RoundedProgressBar):
                self.progress_bar.set_active(False)
            if not self._animating:
                self._set_play_icon_static()
        elif state_str == 'stopped':
            self._is_playing = False
            self._stop_polling()
            # Deactivate progress bar
            if isinstance(self.progress_bar, RoundedProgressBar):
                self.progress_bar.set_active(False)
            if not self._animating:
                self._set_play_icon_static()
            self.progress_bar.setValue(0)

    # -------------------
    # play/pause animation helpers (unchanged logic; uses self._is_playing)
    # -------------------
    def load_play_pause_animations(self):
        """Завантажує кадри з папок assets/pause-to-play і assets/play-to-pause.
        Якщо кадри відсутні — використовує статичні іконки.
        """

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
        self.btn_play.setIconSize(QSize(32, 32))  # Slightly larger for better visibility

        # Set initial static icon depending on current playback state
        if self._is_playing:
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
        """Play a list of QPixmap frames on the play button at fixed interval.
        direction: 'forward' or 'reverse' to allow reversing a sequence when needed.
        on_finished_static: callable to apply final static icon.
        """
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
                    QTimer.singleShot(30, lambda: self._process_queued_state(queued))
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
            if self._is_playing:
                # Вже граємо, нічого не робимо
                return
            self.animate_to_play()
        elif state == 'pause':
            # Тільки якщо дійсно потрібно змінити на pause
            if not self._is_playing:
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

    # -------------------
    # UI init (mostly unchanged)
    # -------------------
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

        left_title_layout = QHBoxLayout()
        left_title = QLabel("Плейлисти")
        left_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        left_title_layout.addWidget(left_title)

        self.btn_add_music = QPushButton("+ Додати музику")
        self.btn_add_music.setFixedHeight(30)
        self.btn_add_music.clicked.connect(self.add_music_files)
        left_title_layout.addWidget(self.btn_add_music)

        self.btn_refresh = QPushButton("🔄 Оновити")
        self.btn_refresh.setFixedHeight(30)
        self.btn_refresh.clicked.connect(self.refresh_library_and_playlists)
        left_title_layout.addWidget(self.btn_refresh)

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

        self.current_track_info = QLabel("Виберіть трек")
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
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        progress_layout.addWidget(self.time_elapsed_label)

        # Use custom painted progress bar
        self.progress_bar = RoundedProgressBar(height=14)
        self.progress_bar.set_colors(QColor(70, 70, 70, 180),
                                     [QColor(29, 185, 84), QColor(45, 210, 110), QColor(29, 185, 84)])

        # Override mouse events to seek audio directly
        def _mouse_press(event):
            if event.button() == Qt.LeftButton and self._current_duration > 0:
                x = event.position().x()
                w = self.progress_bar.width()
                pct = min(1.0, max(0.0, x / w)) if w > 0 else 0.0
                seek_pos = int(pct * self._current_duration)
                try:
                    self.audio.set_position(seek_pos)
                except Exception:
                    pass
                # Set internal progress for instant visual feedback
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
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
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
                    background: rgba(255,255,255,15);
                    border: 1px solid rgba(255,255,255,20);
                    border-radius: 22px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,25);
                    border-color: rgba(255,255,255,30);
                    transform: scale(1.05);
                }
                QPushButton:pressed {
                    background: rgba(255,255,255,10);
                }
                QPushButton:checked {
                    background: rgba(29, 185, 84, 0.7);
                    border-color: rgba(29, 185, 84, 0.9);
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

        QFrame#leftPanel {
            background: rgba(30,30,32,200);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        QFrame#pagesPanel {
            background: rgba(24,24,26,200);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        QFrame#bottomPanel {
            background: rgba(24,24,26,250);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        QWidget#playlistContainer {
            background: transparent;
        }

        QProgressBar {
            background: rgba(70, 70, 70, 180);
            border-radius: 7px;
            border: none;
            margin: 0px;
            padding: 0px;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(29, 185, 84, 1), 
                stop:0.3 rgba(45, 210, 110, 1),
                stop:0.7 rgba(45, 210, 110, 1),
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
            transition: all 0.2s ease;
        }

        QPushButton:hover {
            background: rgba(60, 60, 60, 0.9);
            border-color: rgba(255, 255, 255, 0.2);
        }
        """

    # -------------------
    # Library scanning & UI update
    # -------------------
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

        # Визначаємо, чи грає плеєр зараз
        was_playing = self._is_playing

        if self.current_playlist:
            # Якщо плеєр вже грає, не анімуємо
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

    def _progress_bar_clicked(self, event):
        if event.button() == Qt.LeftButton and self._current_duration > 0:
            click_x = event.position().x()
            progress_width = self.progress_bar.width()
            percentage = min(1.0, max(0.0, click_x / progress_width)) if progress_width > 0 else 0.0
            seek_position = int(percentage * self._current_duration)
            self.audio.set_position(seek_position)
            target_value = int(percentage * 1000)
            self.progress_bar.setValue(target_value)
            self.update_progress(seek_position)

    def _progress_bar_mouse_move(self, event):
        if event.buttons() & Qt.LeftButton:
            self._progress_bar_clicked(event)

    def on_playback_state_changed(self, state):
        # Unused: replaced by wrapper on_playback_state_changed_wrapper
        pass

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

    def play_track_by_id(self, track_id, should_animate=None):
        """Відтворює трек за ID з можливістю контролю анімації"""
        track = self.library.get_track_by_id(track_id)
        if track:
            # Шукаємо трек в поточному плейлисті
            for i, t in enumerate(self.current_playlist):
                if t['id'] == track_id:
                    self.current_track_index = i
                    break
            else:
                # Якщо трек не знайдено в поточному плейлисті, додаємо його
                self.current_track_index = len(self.current_playlist)
                self.current_playlist.append(track)

            # Якщо should_animate не вказано, визначаємо автоматично
            if should_animate is None:
                # Анімуємо тільки якщо плеєр не грає
                should_animate = not self._is_playing

            self.play_track(track, should_animate)

    def play_track(self, track, should_animate=None):
        """Play a track with optional animation."""
        self._progress_style_updated = False
        file_path = track['file_path']
        # set source for engine
        try:
            self.audio.set_source(file_path)
        except Exception as e:
            print("Error setting source:", e)

        # Reset progress immediately
        self.progress_bar.setValue(0)

        current_state_was_playing = self._is_playing

        # start playback
        try:
            self.audio.play()
        except Exception as e:
            print("Error audio.play():", e)

        self.current_track_info.setText(f"{track['title']} - {track['artist']}")

        # If should_animate not provided, decide: animate only if not already playing
        if should_animate is None:
            should_animate = not current_state_was_playing

        # Key logic: if already playing, don't change icon; else animate or set static
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
        # kept for compatibility if needed
        pass

    def _on_end_of_media(self):
        # forwarded to unified handler
        self._on_end_of_media()

    def on_next_auto(self, was_playing):
        """Автоматичний перехід на наступний трек (викликається після закінчення треку)"""
        if self._animating:
            return

        if self.current_playlist:
            self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
            # Якщо трек вже грає, не анімуємо зміну іконки
            self.play_track(self.current_playlist[self.current_track_index], should_animate=not was_playing)

    def toggle_loop(self, checked):
        self._loop_enabled = checked

    def refresh_library_and_playlists(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Оновлення...")
        scanner = MusicScanner(self.music_dir)
        scanner.scan_complete.connect(self._on_refresh_complete)
        scanner.start()

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
            # Determine desired state based on current playback state
            desired_state = 'pause' if self._is_playing else 'play'
            self._queued_state = desired_state
            return

        if self._is_playing:
            # pause
            try:
                self.audio.pause()
            except Exception:
                pass
            self.animate_to_play()
            self._is_playing = False
            self._stop_polling()
        else:
            # if we have a current track selected
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
                self.progress_bar.set_colors(QColor(70, 70, 70, 180),
                                             [QColor(29, 185, 84), QColor(45, 210, 110), QColor(29, 185, 84)])
            elif theme == "light":
                self.progress_bar.set_colors(QColor(200, 200, 200, 200),
                                             [QColor(29, 185, 84), QColor(45, 210, 110), QColor(29, 185, 84)])
            else:
                self.progress_bar.set_colors(QColor(70, 70, 70, 180),
                                             [QColor(29, 185, 84), QColor(45, 210, 110), QColor(29, 185, 84)])
        else:
            if theme == "dark":
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        background: rgba(70, 70, 70, 180);
                        border-radius: 7px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(29, 185, 84, 1), 
                            stop:0.3 rgba(45, 210, 110, 1),
                            stop:0.7 rgba(45, 210, 110, 1),
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
                            stop:0.3 rgba(45, 210, 110, 1),
                            stop:0.7 rgba(45, 210, 110, 1),
                            stop:1 rgba(29, 185, 84, 1));
                        border-radius: 7px;
                    }
                """)
            else:
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        background: rgba(70, 70, 70, 180);
                        border-radius: 7px;
                        border: none;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(29, 185, 84, 1), 
                            stop:0.3 rgba(45, 210, 110, 1),
                            stop:0.7 rgba(45, 210, 110, 1),
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

        # Stop media player / audio engine
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