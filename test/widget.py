"""
Desktop Music Widget (full reworked version)
- PySide6 floating widget with rounded corners and 50% opacity background
- Shows cover art from ID3, track title (auto-ellipsed), progress bar, Prev/Play/Next
- Fixed size, draggable, bottom-right placement by default
- Uses Mutagen for ID3 parsing
"""

import sys
import os
from mutagen import File as MutagenFile
from mutagen.id3 import APIC

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QProgressBar,
    QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QPixmap, QPainter, QPainterPath
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# ---------------------------- Helper: Rounded pixmap ------------------
def rounded_pixmap(src: QPixmap, size: tuple, radius: int) -> QPixmap:
    w, h = size
    if src.isNull():
        out = QPixmap(w, h)
        out.fill(Qt.transparent)
        return out
    scaled = src.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    result = QPixmap(w, h)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return result

# ---------------------------- Desktop Music Widget --------------------
class DesktopMusicWidget(QWidget):
    WIDTH = 360
    HEIGHT = 140
    WIDGET_RADIUS = 20
    COVER_RADIUS = 12

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        # 50% opacity background with rounded corners
        self.setStyleSheet(f"background-color: rgba(25,25,25,0.5); border-radius:{self.WIDGET_RADIUS}px; color:#eee;")

        # Playback
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.files = []
        self.current_index = -1

        # UI Elements
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(96, 96)
        self.cover_label.setStyleSheet(f"background: transparent; border-radius:{self.COVER_RADIUS}px;")
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setPixmap(self._placeholder_pixmap())

        self.title_label = QLabel("No track")
        self.title_label.setFixedHeight(20)
        self.title_label.setStyleSheet("color:#ddd; font-size:12px;")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        self.progress.setStyleSheet(
            "QProgressBar{border-radius:6px;background:#333;}"
            "QProgressBar::chunk{border-radius:6px;background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a6, stop:1 #2a2);}"
        )

        # Buttons
        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        for b in (self.prev_btn, self.play_btn, self.next_btn):
            b.setFixedSize(36, 36)
            b.setFlat(True)
            b.setStyleSheet("QPushButton{border:none;font-size:16px;} QPushButton:pressed{transform:translateY(1px);}")

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.title_label)
        right_layout.addWidget(self.progress)
        right_layout.addLayout(controls_layout)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8,8,8,8)
        main_layout.addWidget(self.cover_label)
        main_layout.addLayout(right_layout)

        # Connect buttons
        self.play_btn.clicked.connect(self.toggle_play)
        self.prev_btn.clicked.connect(self.prev_track)
        self.next_btn.clicked.connect(self.next_track)

        # Timer for progress update
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(250)
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.start()

        # Connect player signals
        self.player.durationChanged.connect(lambda d: self.progress.setMaximum(max(1, int(d))))
        self.player.positionChanged.connect(lambda p: self.progress.setValue(int(p)))
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        # Scan music folder
        self.scan_music_folder()

    def _placeholder_pixmap(self) -> QPixmap:
        p = QPixmap(96,96)
        p.fill(Qt.transparent)
        return rounded_pixmap(p,(96,96),self.COVER_RADIUS)

    def scan_music_folder(self):
        music_dir = os.path.join(os.path.expanduser('~'),'Music')
        found = []
        if os.path.exists(music_dir):
            for root, _, files in os.walk(music_dir):
                for f in files:
                    if f.lower().endswith(('.mp3','.wav','.ogg','.m4a')):
                        found.append(os.path.join(root,f))
        if found:
            found.sort()
            self.files = found
            self.current_index = 0
            self.play_index(self.current_index)

    def play_index(self, idx:int):
        if not (0 <= idx < len(self.files)):
            return
        self.current_index = idx
        path = self.files[idx]
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.update_cover_and_title(path)

    def update_cover_and_title(self, path:str):
        pixmap = QPixmap()
        title_text = os.path.basename(path)
        try:
            audio = MutagenFile(path)
            if audio and getattr(audio,'tags',None):
                tags = audio.tags
                title = tags.get('TIT2') if 'TIT2' in tags else None
                artist = tags.get('TPE1') if 'TPE1' in tags else None
                if title or artist:
                    title_text = f"{title or ''}{' - ' if title and artist else ''}{artist or ''}"
                for v in getattr(tags,'values',lambda:[])():
                    if isinstance(v,APIC):
                        pixmap.loadFromData(v.data)
                        break
        except Exception:
            pass
        if pixmap.isNull():
            pixmap = self._placeholder_pixmap()
        else:
            pixmap = rounded_pixmap(pixmap,(self.cover_label.width(),self.cover_label.height()),self.COVER_RADIUS)
        self.cover_label.setPixmap(pixmap)
        self.title_label.setText(title_text)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self.current_index==-1 and self.files:
                self.current_index=0
                self.play_index(self.current_index)
            else:
                self.player.play()

    def prev_track(self):
        if not self.files:
            return
        idx=self.current_index-1
        if idx<0:
            idx=len(self.files)-1
        self.play_index(idx)

    def next_track(self):
        if not self.files:
            return
        idx=(self.current_index+1)%len(self.files)
        self.play_index(idx)

    def update_progress(self):
        pass

    def _on_playback_state_changed(self,state):
        self.play_btn.setText("⏸" if state==QMediaPlayer.PlayingState else "▶")

# ---------------------------- Main ----------------------------------
def main():
    app=QApplication(sys.argv)
    w=DesktopMusicWidget()
    w.show()

    # Place bottom-right
    screen=app.primaryScreen().availableGeometry()
    w.move(screen.right()-w.width()-20, screen.bottom()-w.height()-40)

    sys.exit(app.exec())

if __name__=='__main__':
    main()
