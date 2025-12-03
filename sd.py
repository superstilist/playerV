import sys
import os
import random
from io import BytesIO

# --- PySide6 Imports ---
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QSlider, QLabel,
                               QFileDialog, QListWidget, QStyle, QFrame,
                               QGraphicsDropShadowEffect, QListWidgetItem,
                               QSizePolicy, QScrollArea)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import (Qt, QUrl, QSize, QThread, Signal, Slot, QObject,
                            QPoint, QRect, Property, QParallelAnimationGroup, QPropertyAnimation)
from PySide6.QtGui import (QIcon, QPixmap, QImage, QColor, QPainter, QBrush,
                           QPen, QLinearGradient, QFontDatabase, QFont, QPainterPath)

# --- Data & Image Processing ---
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, APIC
    from mutagen.flac import FLAC

    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    import cv2
    import numpy as np
    from sklearn.cluster import KMeans
    from collections import Counter

    HAS_CV = True
except ImportError:
    HAS_CV = False


# ============================================================================
#  WORKER: EXTRACT 6-COLOR PALETTE (Executed in a separate thread)
# ============================================================================

class PaletteWorker(QObject):
    finished = Signal(list)  # Returns list of 6 RGB colors

    def __init__(self, qimage):
        super().__init__()
        self.qimage = qimage

    @Slot()
    def process(self):
        if not HAS_CV or self.qimage is None:
            # Default dark colors if dependencies or image is missing
            self.finished.emit([[30, 30, 46]] * 6)
            return

        try:
            # 1. Convert QImage to Numpy
            ptr = self.qimage.bits()
            # Ensure format is correct for OpenCV
            if self.qimage.format() != QImage.Format_RGB888:
                self.qimage = self.qimage.convertToFormat(QImage.Format_RGB888)
                ptr = self.qimage.bits()

            arr = np.array(ptr).reshape(self.qimage.height(), self.qimage.width(), 3)
            img = cv2.resize(arr, (100, 100))  # Resize for speed
            pixels = img.reshape(-1, 3)

            # 2. K-Means with k=6 (Get 6 colors)
            # n_init=3 is used for speed and consistency
            kmeans = KMeans(n_clusters=6, n_init=3, random_state=42)
            labels = kmeans.fit_predict(pixels)
            centers = kmeans.cluster_centers_.astype(int)

            # Sort by frequency (most dominant first)
            counts = Counter(labels)
            sorted_centers = [centers[i] for i, _ in counts.most_common(6)]

            # Ensure we have exactly 6
            while len(sorted_centers) < 6:
                sorted_centers.append(sorted_centers[0])

            self.finished.emit(sorted_centers)

        except Exception as e:
            print(f"Palette Error: {e}")
            self.finished.emit([[30, 30, 46]] * 6)


# ============================================================================
#  CUSTOM WIDGETS
# ============================================================================

class ModernSlider(QSlider):
    """
    A custom slider that draws its own track and handle, and can be accented
    with a specific color.
    """

    def __init__(self, orientation=Qt.Horizontal):
        super().__init__(orientation)
        self.setFixedHeight(20)
        self.accent_color = QColor(255, 255, 255)

    def set_accent(self, c):
        self.accent_color = c
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        y = rect.height() // 2

        # Background Track (light gray/transparent)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 50))
        painter.drawRoundedRect(0, y - 3, rect.width(), 6, 3, 3)

        # Active Track (accent color)
        if self.maximum() > 0:
            pos = (self.value() / self.maximum()) * rect.width()
            painter.setBrush(self.accent_color)
            painter.drawRoundedRect(0, y - 3, int(pos), 6, 3, 3)

            # Handle (white circle)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(QPoint(int(pos), y), 8, 8)


class ColorPaletteBar(QWidget):
    """Displays the 6 extracted colors as a sleek horizontal bar."""

    def __init__(self):
        super().__init__()
        self.colors = []
        self.setFixedHeight(12)
        self.setFixedWidth(200)

    def set_colors(self, colors):
        self.colors = colors
        self.update()

    def paintEvent(self, event):
        if not self.colors: return
        p = QPainter(self)
        p.setPen(Qt.NoPen)

        w = self.width() / len(self.colors)
        for i, rgb in enumerate(self.colors):
            c = QColor(rgb[0], rgb[1], rgb[2])
            p.setBrush(c)
            # Draw each color segment
            rect = QRect(int(i * w), 0, int(w) + 1, self.height())
            p.drawRect(rect)


# ============================================================================
#  MAIN WINDOW
# ============================================================================

class BeautifulPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flux Music Player")
        self.resize(800, 600)

        # Setup Backend
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.7)
        self.playlist = []
        self.current_idx = -1
        self.thread = None  # For palette worker

        # UI Setup
        self.init_ui()
        self.setup_connections()
        self.apply_styles() # Styles apply the new rounding

        # Default State
        self.update_background(None)

    def init_ui(self):
        # 1. Background Container (Holds the blurred image)
        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        self.bg_label.setGeometry(0, 0, 1000, 650)

        # 2. Main Overlay
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- LEFT SIDEBAR (Playlist) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)

        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 30, 20, 20)

        lbl_list = QLabel("PLAYLIST")
        lbl_list.setStyleSheet("color: rgba(255,255,255,0.6); font-weight: bold; letter-spacing: 2px;")

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Scrollbar hidden for sleekness

        btn_add = QPushButton(" + Add Music")
        btn_add.setObjectName("BtnAdd")
        btn_add.setCursor(Qt.PointingHandCursor)

        side_layout.addWidget(lbl_list)
        side_layout.addWidget(self.list_widget)
        side_layout.addWidget(btn_add)

        # --- RIGHT CONTENT (Player) ---
        self.content = QFrame()
        self.content.setObjectName("ContentArea")
        self.content.setStyleSheet("color: transparent;")

        content_layout = QVBoxLayout(self.content)

        content_layout.setContentsMargins(40, 40, 40, 40)


        # Album Art
        self.art_frame = QFrame()
        self.art_frame.setFixedSize(320, 320)
        self.lbl_art = QLabel(self.art_frame)
        self.lbl_art.setFixedSize(300, 300)
        self.lbl_art.move(10, 10)  # Offset for frame
        self.lbl_art.setScaledContents(True)

        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        self.lbl_art.setGraphicsEffect(shadow)

        # Metadata Labels
        self.lbl_title = QLabel("Ready to Play")
        self.lbl_title.setObjectName("BigTitle")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_artist = QLabel("Add audio files to start")
        self.lbl_artist.setObjectName("Artist")
        self.lbl_artist.setAlignment(Qt.AlignCenter)

        # Palette Bar
        self.palette_bar = ColorPaletteBar()

        # Controls Buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)

        # Use 45px for skip and 60px for play
        self.btn_prev = self.create_circle_btn("", 45)
        self.btn_play = self.create_circle_btn("", 60)
        self.btn_next = self.create_circle_btn("", 45)

        # Note: 'assets/play.png', etc., need to be in the execution directory
        self.btn_play.setIcon(QIcon('assets/play.png'))
        self.btn_next.setIcon(QIcon('assets/next.png'))
        self.btn_prev.setIcon(QIcon('assets/back.png'))

        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addStretch()

        # Sliders & Time Label
        self.slider_pos = ModernSlider()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: rgba(255,255,255,0.7);")

        # Assemble content layout
        content_layout.addStretch()
        content_layout.addWidget(self.art_frame, 0, Qt.AlignCenter)
        content_layout.addSpacing(20)
        content_layout.addWidget(self.lbl_title)
        content_layout.addWidget(self.lbl_artist)
        content_layout.addWidget(self.palette_bar, 0, Qt.AlignCenter)
        content_layout.addSpacing(30)
        content_layout.addWidget(self.slider_pos)
        content_layout.addWidget(self.lbl_time, 0, Qt.AlignCenter)
        content_layout.addSpacing(10)
        content_layout.addLayout(controls_layout)
        content_layout.addStretch()

        # Assemble main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content)

        self.btn_add_files = btn_add

    def create_circle_btn(self, text, size):
        """Helper to create a standard styled circular button."""
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setObjectName("CircleBtn")
        btn.setCursor(Qt.PointingHandCursor)
        # Set icon size relative to button size
        btn.setIconSize(QSize(size * 0.4, size * 0.4))
        return btn

    def setup_connections(self):
        """Connect all signals to slots."""
        self.btn_add_files.clicked.connect(self.add_files)
        self.list_widget.itemDoubleClicked.connect(self.play_item)

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(self.next_song)
        self.btn_prev.clicked.connect(self.prev_song)

        self.player.positionChanged.connect(self.update_slider)
        self.player.durationChanged.connect(self.update_duration)
        self.player.mediaStatusChanged.connect(self.media_status)

        self.slider_pos.sliderMoved.connect(self.player.setPosition)
        # Pause playback when slider is manually dragged
        self.slider_pos.sliderPressed.connect(self.player.pause)
        self.slider_pos.sliderReleased.connect(self.player.play)

    def set_rounded_pixmap(self, label, pixmap, radius=30):
        """
        Applies rounded corners to a QPixmap and sets it on a QLabel.
        """
        if pixmap is None:
            return

        size = label.size()
        # Scale pixmap to fill the label size, cropping if necessary
        pixmap = pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # Create a blank pixmap with transparency
        rounded = QPixmap(size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)

        # Define the rounded rectangle path
        # Note: The radius can be adjusted here if you want different rounding on the album art
        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)

        # Clip painting to the rounded path
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        label.setPixmap(rounded)

    def apply_styles(self):
        """Apply CSS-like styles to the widgets."""
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }

            #Sidebar { 
                /* Apply rounding to the top-right and bottom-right corners */
                background-color: rgba(20, 20, 30, 0.85); 
                border-right: 1px solid rgba(255,255,255,0.1); 
                border-top-right-radius: 20px;
                border-bottom-right-radius: 20px;
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }
            QListWidget { background: transparent; color: white; border: none; font-size: 14px; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QListWidget::item:selected { background-color: rgba(255,255,255,0.1); color: #fff; border-radius: 5px; }

            #BtnAdd {
                background-color: rgba(255,255,255,0.1); color: white; 
                border-radius: 8px; padding: 10px; font-weight: bold;
            }
            #BtnAdd:hover { background-color: rgba(255,255,255,0.2); }

            #ContentArea { 
                /* Semi-transparent dark overlay for contrast against blurred BG */
                background-color: rgba(0,0,0,0.6); 
            } 

            #BigTitle { font-size: 26px; font-weight: bold; color: white; margin-top: 10px; }
            #Artist { font-size: 16px; color: rgba(255,255,255,0.7); }

            #CircleBtn {
                background-color: rgba(255,255,255,0.15);
                color: white; border-radius: 50%; /* Makes button a true circle */
                font-size: 20px; border: 1px solid rgba(255,255,255,0.1);
            }
            #CircleBtn:hover { background-color: white; color: black; }
        """)

    def resizeEvent(self, event):
        """Ensure the background image always covers the entire window."""
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    # --- Player Logic ---

    def add_files(self):
        """Opens a file dialog and adds selected audio files to the playlist."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Music", "", "Audio (*.mp3 *.flac *.wav)")
        for f in files:
            self.playlist.append(f)
            self.list_widget.addItem(os.path.basename(f))
        if self.current_idx == -1 and self.playlist:
            self.current_idx = 0
            self.load_song(0)

    @Slot(QListWidgetItem)
    def play_item(self, item):
        """Starts playback when a playlist item is double-clicked."""
        row = self.list_widget.row(item)
        self.current_idx = row
        self.load_song(row)

    def load_song(self, idx):
        """Loads and starts playing the song at the given index."""
        path = self.playlist[idx]
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.btn_play.setIcon(QIcon('assets/pause.png'))
        self.list_widget.setCurrentRow(idx)
        self.process_metadata(path)

    def toggle_play(self):
        """Toggles between play and pause."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setIcon(QIcon('assets/play.png'))
        elif self.playlist:
            self.player.play()
            self.btn_play.setIcon(QIcon('assets/pause.png'))

    def next_song(self):
        """Skips to the next song."""
        if self.current_idx < len(self.playlist) - 1:
            self.current_idx += 1
            self.load_song(self.current_idx)

    def prev_song(self):
        """Skips to the previous song."""
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_song(self.current_idx)

    def media_status(self, status):
        """Automatically advance to the next song when current song ends."""
        if status == QMediaPlayer.EndOfMedia:
            self.next_song()

    def update_slider(self, pos):
        """Updates the position slider and time label."""
        if not self.slider_pos.isSliderDown():
            self.slider_pos.setValue(pos)
        cur = self.format_ms(pos)
        tot = self.format_ms(self.player.duration())
        self.lbl_time.setText(f"{cur} / {tot}")

    def update_duration(self, dur):
        """Updates the maximum value of the position slider."""
        self.slider_pos.setRange(0, dur)

    def format_ms(self, ms):
        """Converts milliseconds to MM:SS format."""
        s = (ms // 1000) % 60
        m = (ms // 60000)
        return f"{m:02}:{s:02}"

    # --- Visual Logic ---

    def update_background(self, pixmap):
        """Creates a highly blurred version of the album art for the background."""
        if pixmap:
            # Create blurred version
            img = pixmap.toImage()
            if HAS_CV:
                # Convert QImage to format suitable for OpenCV
                if img.format() != QImage.Format_RGB888 and img.format() != QImage.Format_RGBA8888:
                    img = img.convertToFormat(QImage.Format_RGB888)

                ptr = img.bits()
                h, w = img.height(), img.width()

                # Use np.array to get the image data
                # Determine channels based on format
                channels = 4 if img.format() == QImage.Format_RGBA8888 else 3
                arr = np.array(ptr).reshape(h, w, channels)

                # Blur with a large radius (30)
                blurred = cv2.GaussianBlur(arr, (0, 0), 30)

                # Convert back to QImage
                fmt = QImage.Format_RGBA8888 if channels == 4 else QImage.Format_RGB888
                # Note: QImage takes ownership of the data buffer in this constructor
                qimg_blur = QImage(blurred.data, w, h, fmt)
                self.bg_label.setPixmap(QPixmap.fromImage(qimg_blur))
            else:
                # Fallback if OpenCV is missing
                self.bg_label.setPixmap(pixmap)
        else:
            # Clear background and set solid dark color
            self.bg_label.clear()
            self.bg_label.setStyleSheet("background-color: #1e1e2e;")

    def process_metadata(self, path):
        """Extracts title, artist, and album art using mutagen."""
        title = os.path.basename(path)
        artist = "Unknown Artist"
        pixmap = None

        if HAS_MUTAGEN:
            try:
                f = mutagen.File(path)
                if isinstance(f, MP3):
                    tags = ID3(path)
                    title = str(tags.get("TIT2", title))
                    artist = str(tags.get("TPE1", artist))
                    # Check for APIC (Album Art) tag
                    if tags.getall("APIC"):
                        data = tags.getall("APIC")[0].data
                        pixmap = QPixmap()
                        pixmap.loadFromData(data)
                elif isinstance(f, FLAC):
                    # Check for FLAC pictures
                    if f.pictures:
                        pixmap = QPixmap()
                        pixmap.loadFromData(f.pictures[0].data)
            except:
                # Silent failure on metadata read error
                pass

        self.lbl_title.setText(str(title))
        self.lbl_artist.setText(str(artist))

        if pixmap:
            # Set the rounded album art (radius=30)
            self.set_rounded_pixmap(self.lbl_art, pixmap, radius=30)
            self.update_background(pixmap)

            # --- Start Palette Extraction in a new thread ---
            if self.thread and self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()

            self.worker = PaletteWorker(pixmap.toImage())
            self.worker.finished.connect(self.apply_palette)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.process)
            self.thread.start()

        else:
            # Default state if no album art
            self.lbl_art.setText("🎵")
            self.lbl_art.setStyleSheet(
                "background-color: #333; color: #555; font-size: 80px; qproperty-alignment: AlignCenter; border-radius: 30px;") # Added fallback border-radius
            self.palette_bar.set_colors([])
            self.update_background(None)

    @Slot(list)
    def apply_palette(self, colors):
        """Receives the dominant colors and applies them to the UI."""
        self.palette_bar.set_colors(colors)

        # Use the most dominant color as the accent
        dom_rgb = colors[0]
        accent = QColor(dom_rgb[0], dom_rgb[1], dom_rgb[2])

        # Ensure the accent color is visible against the dark background
        if accent.lightness() < 100:
            accent = accent.lighter(150)

        self.slider_pos.set_accent(accent)

        # Clean up the worker thread
        if self.thread:
            self.thread.quit()

    def closeEvent(self, event):
        """Cleanup thread on close to avoid errors."""
        if hasattr(self, 'thread') and self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set a standard font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    win = BeautifulPlayer()
    win.show()
    sys.exit(app.exec())