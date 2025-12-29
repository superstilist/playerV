"""
Sticky Desktop Music Widget - Minimalistic Design
- Sticks to screen edges with smooth animations
- Beautiful minimalistic UI with 50% opacity
- Fully rounded corners and glass effect
- Constantly visible widget with edge docking
"""

import sys
import os

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from mutagen import File as MutagenFile
from mutagen.id3 import APIC
from PySide6.QtCore import Qt, QTimer, QUrl, QPoint, QPropertyAnimation, QEasingCurve, QRect, QEvent
from PySide6.QtGui import (QPixmap, QPainter, QPainterPath, QColor,
                           QBrush, QLinearGradient, QFont, QFontMetrics,
                           QPen, QPainterPath, QRegion, QGradient, QMouseEvent)
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                               QProgressBar, QHBoxLayout, QVBoxLayout, QGraphicsDropShadowEffect)

# ===================== CONSTANTS =====================
# Screen edge constants
STICKY_NONE = 0
STICKY_LEFT = 1
STICKY_RIGHT = 2
STICKY_TOP = 3
STICKY_BOTTOM = 4

# Widget dimensions
WIDGET_WIDTH = 350
WIDGET_HEIGHT = 110
WIDGET_RADIUS = 20
COVER_SIZE = 60
COVER_RADIUS = 10

# Colors (minimalistic palette)
COLOR_BG = QColor(30, 30, 35, 230)  # Dark gray with slight transparency
COLOR_PRIMARY = QColor(100, 220, 255, 200)  # Cyan blue
COLOR_SECONDARY = QColor(255, 255, 255, 180)  # White with transparency
COLOR_TERTIARY = QColor(255, 255, 255, 100)  # More transparent white
COLOR_PROGRESS_BG = QColor(255, 255, 255, 50)
COLOR_PROGRESS_FILL = QColor(100, 220, 255, 220)

# Animation constants
ANIMATION_DURATION = 300  # ms
STICKY_THRESHOLD = 30  # pixels from edge to stick


# ===================== HELPER FUNCTIONS =====================
def rounded_pixmap(src: QPixmap, size: tuple, radius: int) -> QPixmap:
    """Create a pixmap with rounded corners"""
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


# ===================== STICKY MUSIC WIDGET =====================
class StickyMusicWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint |
                            Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)

        # Sticky edge tracking
        self.sticky_edge = STICKY_NONE
        self.dragging = False
        self.drag_position = QPoint()
        self.last_valid_pos = QPoint()
        self.hidden = False

        # Shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)

        # Playback
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        self.files = []
        self.current_index = -1

        # Setup UI
        self.setup_ui()

        # Connect signals
        self.setup_connections()

        # Initial scan
        self.scan_music_folder()

        # Position widget at startup
        QTimer.singleShot(100, self.position_at_edge)

    def setup_ui(self):
        """Setup minimalistic UI"""
        # Main container
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(15)

        # Album cover
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(COVER_SIZE, COVER_SIZE)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setPixmap(self.create_placeholder_cover())

        # Track info container
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Title label (minimalistic)
        self.title_label = QLabel("No Music")
        self.title_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.95);
            font-size: 14px;
            font-weight: 500;
            background: transparent;
        """)
        self.title_label.setFixedHeight(22)

        # Artist label
        self.artist_label = QLabel("Add music to ~/Music")
        self.artist_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 11px;
            font-weight: 400;
            background: transparent;
        """)
        self.artist_label.setFixedHeight(18)

        # Progress bar (ultra minimal)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 1.5px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: rgba({COLOR_PROGRESS_FILL.red()}, 
                                      {COLOR_PROGRESS_FILL.green()}, 
                                      {COLOR_PROGRESS_FILL.blue()}, 
                                      {COLOR_PROGRESS_FILL.alpha()});
                border-radius: 1.5px;
            }}
        """)

        # Time labels
        time_layout = QHBoxLayout()
        self.time_current = QLabel("0:00")
        self.time_total = QLabel("0:00")
        for label in [self.time_current, self.time_total]:
            label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.4);
                font-size: 9px;
                font-weight: 400;
                background: transparent;
            """)
            label.setFixedHeight(14)
        time_layout.addWidget(self.time_current)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)

        # Add to info layout
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addWidget(self.progress)
        info_layout.addLayout(time_layout)

        # Controls layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(6)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # Playback buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.prev_btn = self.create_minimal_button("◀")
        self.play_btn = self.create_minimal_button("▶")
        self.next_btn = self.create_minimal_button("▶")
        self.next_btn.setText("▶")  # Using ▶ for next (rotate in CSS if needed)

        # Simple volume slider placeholder (icon)
        self.volume_btn = self.create_minimal_button("♪")

        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.volume_btn)

        controls_layout.addLayout(button_layout)
        controls_layout.addStretch()

        # Assemble main layout
        main_layout.addWidget(self.cover_label)
        main_layout.addLayout(info_layout)
        main_layout.addLayout(controls_layout)

    def create_minimal_button(self, text):
        """Create a minimalistic button"""
        btn = QPushButton(text)
        btn.setFixedSize(28, 28)
        btn.setFlat(True)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 14px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 10px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.2);
            }}
        """)
        return btn

    def create_placeholder_cover(self):
        """Create minimal placeholder album cover"""
        pixmap = QPixmap(COVER_SIZE, COVER_SIZE)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rect background
        path = QPainterPath()
        path.addRoundedRect(0, 0, COVER_SIZE, COVER_SIZE, COVER_RADIUS, COVER_RADIUS)

        # Gradient background
        gradient = QLinearGradient(0, 0, COVER_SIZE, COVER_SIZE)
        gradient.setColorAt(0.0, QColor(50, 50, 60, 150))
        gradient.setColorAt(1.0, QColor(40, 40, 50, 150))
        painter.fillPath(path, gradient)

        # Draw music note
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1.5))
        painter.setFont(QFont("Arial", 18, QFont.Light))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "♫")

        # Subtle border
        painter.setPen(QPen(QColor(255, 255, 255, 30), 0.5))
        painter.drawPath(path)

        painter.end()
        return pixmap

    def setup_connections(self):
        """Connect signals and slots"""
        # Button connections
        self.play_btn.clicked.connect(self.toggle_play)
        self.prev_btn.clicked.connect(self.prev_track)
        self.next_btn.clicked.connect(self.next_track)
        self.volume_btn.clicked.connect(self.toggle_mute)

        # Timer for progress updates
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self.update_progress_display)
        self.update_timer.start()

        # Player connections
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)
        self.player.playbackStateChanged.connect(self.update_play_button)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

    def paintEvent(self, event):
        """Draw the widget with minimalistic design"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create rounded rect path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(),
                            WIDGET_RADIUS, WIDGET_RADIUS)

        # Solid background with slight transparency
        painter.fillPath(path, COLOR_BG)

        # Subtle border
        painter.setPen(QPen(QColor(255, 255, 255, 30), 0.5))
        painter.drawPath(path)

        # Add a thin accent line at the top
        accent_path = QPainterPath()
        accent_path.addRoundedRect(1, 1, self.width() - 2, 1, 0, 0)
        painter.setPen(QPen(COLOR_PRIMARY, 1))
        painter.drawPath(accent_path)

        painter.end()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_valid_pos = self.pos()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release and stick to nearest edge"""
        self.dragging = False
        self.setCursor(Qt.ArrowCursor)

        # Stick to nearest edge
        self.stick_to_edge()
        event.accept()

    def stick_to_edge(self):
        """Make widget stick to the nearest screen edge"""
        screen = QApplication.primaryScreen().availableGeometry()
        widget_rect = self.geometry()

        # Calculate distances to edges
        left_dist = widget_rect.left()
        right_dist = screen.right() - widget_rect.right()
        top_dist = widget_rect.top()
        bottom_dist = screen.bottom() - widget_rect.bottom()

        # Find minimum distance
        min_dist = min(left_dist, right_dist, top_dist, bottom_dist)

        # If close enough to an edge, stick to it
        if min_dist < STICKY_THRESHOLD:
            if min_dist == left_dist:
                self.animate_to_position(QPoint(0, widget_rect.y()))
                self.sticky_edge = STICKY_LEFT
            elif min_dist == right_dist:
                self.animate_to_position(QPoint(screen.right() - self.width(), widget_rect.y()))
                self.sticky_edge = STICKY_RIGHT
            elif min_dist == top_dist:
                self.animate_to_position(QPoint(widget_rect.x(), 0))
                self.sticky_edge = STICKY_TOP
            else:
                self.animate_to_position(QPoint(widget_rect.x(), screen.bottom() - self.height()))
                self.sticky_edge = STICKY_BOTTOM
        else:
            self.sticky_edge = STICKY_NONE

    def animate_to_position(self, target_pos):
        """Animate widget to target position"""
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(ANIMATION_DURATION)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(self.pos())
        anim.setEndValue(target_pos)
        anim.start()

    def position_at_edge(self):
        """Position widget at startup (right edge by default)"""
        screen = QApplication.primaryScreen().availableGeometry()

        # Default to right edge, centered vertically
        x = screen.right() - self.width()
        y = (screen.height() - self.height()) // 2

        self.move(x, y)
        self.sticky_edge = STICKY_RIGHT

        # Hide partially off-screen
        self.hide_partially()

    def hide_partially(self):
        """Hide widget partially off-screen (peek mode)"""
        if self.sticky_edge == STICKY_RIGHT:
            target_x = QApplication.primaryScreen().availableGeometry().right() - 50
            self.animate_to_position(QPoint(target_x, self.y()))
            self.hidden = True
        elif self.sticky_edge == STICKY_LEFT:
            target_x = -self.width() + 50
            self.animate_to_position(QPoint(target_x, self.y()))
            self.hidden = True

    def enterEvent(self, event):
        """Show full widget on hover"""
        if self.hidden:
            screen = QApplication.primaryScreen().availableGeometry()

            if self.sticky_edge == STICKY_RIGHT:
                target_x = screen.right() - self.width()
                self.animate_to_position(QPoint(target_x, self.y()))
            elif self.sticky_edge == STICKY_LEFT:
                self.animate_to_position(QPoint(0, self.y()))

            self.hidden = False

    def leaveEvent(self, event):
        """Hide partially when leaving (after delay)"""
        if self.sticky_edge in [STICKY_LEFT, STICKY_RIGHT]:
            QTimer.singleShot(500, self.check_hide)

    def check_hide(self):
        """Check if mouse is still over widget before hiding"""
        if not self.geometry().contains(QApplication.cursor().pos()):
            self.hide_partially()

    def scan_music_folder(self):
        """Scan music folders"""
        music_dirs = [
            os.path.join(os.path.expanduser('~'), 'Music'),
            os.path.join(os.path.expanduser('~'), 'Downloads')
        ]

        found = []
        extensions = ('.mp3', '.wav', '.ogg', '.m4a', '.flac')

        for music_dir in music_dirs:
            if os.path.exists(music_dir):
                for root, _, files in os.walk(music_dir):
                    for f in files:
                        if f.lower().endswith(extensions):
                            found.append(os.path.join(root, f))

        if found:
            found.sort()
            self.files = found
            self.current_index = 0
            self.play_index(self.current_index)

    def play_index(self, idx: int):
        """Play track at index"""
        if not (0 <= idx < len(self.files)):
            return

        self.current_index = idx
        path = self.files[idx]
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.update_metadata(path)

    def update_metadata(self, path: str):
        """Update cover art and track info"""
        pixmap = QPixmap()
        filename = os.path.basename(path)
        title = filename.rsplit('.', 1)[0]
        artist = "Unknown Artist"

        try:
            audio = MutagenFile(path)
            if audio:
                if hasattr(audio, 'tags') and audio.tags:
                    title_tag = audio.tags.get('TIT2') or audio.tags.get('title')
                    artist_tag = audio.tags.get('TPE1') or audio.tags.get('artist')

                    if title_tag:
                        title = str(title_tag)[:40]  # Limit length
                    if artist_tag:
                        artist = str(artist_tag)[:30]

                # Get cover art
                if hasattr(audio, 'tags'):
                    for tag in audio.tags.values():
                        if isinstance(tag, APIC):
                            pixmap.loadFromData(tag.data)
                            break
        except:
            pass

        # Update cover
        if pixmap.isNull():
            self.cover_label.setPixmap(self.create_placeholder_cover())
        else:
            self.cover_label.setPixmap(
                rounded_pixmap(pixmap, (COVER_SIZE, COVER_SIZE), COVER_RADIUS)
            )

        # Update labels
        self.title_label.setText(title)
        self.artist_label.setText(artist)

    def toggle_play(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia and self.files:
                self.play_index(0)
            else:
                self.player.play()

    def prev_track(self):
        """Play previous track"""
        if not self.files:
            return
        idx = self.current_index - 1
        if idx < 0:
            idx = len(self.files) - 1
        self.play_index(idx)

    def next_track(self):
        """Play next track"""
        if not self.files:
            return
        idx = (self.current_index + 1) % len(self.files)
        self.play_index(idx)

    def toggle_mute(self):
        """Toggle mute"""
        self.audio_output.setMuted(not self.audio_output.isMuted())
        color = "rgba(255, 100, 100, 0.8)" if self.audio_output.isMuted() else "rgba(255, 255, 255, 0.8)"
        self.volume_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 14px;
                color: {color};
                font-size: 10px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)

    def update_duration(self, duration):
        """Update total duration"""
        if duration > 0:
            minutes = duration // 60000
            seconds = (duration % 60000) // 1000
            self.time_total.setText(f"{minutes}:{seconds:02d}")

    def update_position(self, position):
        """Update current position"""
        if position > 0:
            minutes = position // 60000
            seconds = (position % 60000) // 1000
            self.time_current.setText(f"{minutes}:{seconds:02d}")
            if self.player.duration() > 0:
                self.progress.setValue(int((position / self.player.duration()) * 1000))

    def update_progress_display(self):
        """Update progress bar (called by timer)"""
        pass  # Handled by positionChanged signal

    def update_play_button(self, state):
        """Update play button icon"""
        self.play_btn.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def on_media_status_changed(self, status):
        """Handle end of track"""
        if status == QMediaPlayer.EndOfMedia:
            self.next_track()


# ===================== MAIN APPLICATION =====================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sticky Music Widget")
    app.setStyle("Fusion")

    # Set application-wide font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    # Create widget
    widget = StickyMusicWidget()
    widget.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()