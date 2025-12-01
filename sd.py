import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFileDialog
from PySide6.QtGui import QIcon, QPixmap, QPalette, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl
from mutagen.id3 import ID3, APIC
from PIL import Image
from io import BytesIO

class MiniPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Player")
        self.setFixedSize(340, 480)
        self.is_playing = False
        self.file_path = None


        # --- Audio player ---
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        # --- Cover ---
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(220, 220)
        self.cover_label.setAlignment(Qt.AlignCenter)

        # --- Title / Artist ---
        self.title_label = QLabel("Назва: -")
        self.artist_label = QLabel("Виконавець: -")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.artist_label.setWordWrap(True)

        # --- Buttons ---
        self.btn_play = QPushButton()
        self.btn_open = QPushButton("Відкрити файл")
        self.btn_play.setIcon(QIcon("assets/play.png"))
        self.btn_play.setFixedSize(64, 40)
        self.btn_open.setFixedHeight(36)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_open.clicked.connect(self.open_file)

        # --- Layouts ---
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.btn_play)
        h_layout.addStretch()

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(12, 12, 12, 12)
        v_layout.setSpacing(10)
        v_layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.artist_label)
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.btn_open)
        self.setLayout(v_layout)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Вибрати MP3 файл", "", "MP3 Files (*.mp3)")
        if path:
            self.file_path = os.path.abspath(path)
            self.play_current_track()

    def play_current_track(self):
        if not self.file_path:
            return
        self.player.setSource(QUrl.fromLocalFile(self.file_path))
        self.load_tags_and_theme()
        self.player.play()
        self.btn_play.setIcon(QIcon("assets/pause.png"))
        self.is_playing = True

    def toggle_play(self):
        if not self.file_path:
            return
        if self.is_playing:
            self.player.pause()
            self.btn_play.setIcon(QIcon("assets/play.png"))
        else:
            self.player.play()
            self.btn_play.setIcon(QIcon("assets/pause.png"))
        self.is_playing = not self.is_playing

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            self.btn_play.setIcon(QIcon("assets/play.png"))
            self.is_playing = False

    def load_tags_and_theme(self):
        try:
            tags = ID3(self.file_path)
            title = tags.get("TIT2")
            artist = tags.get("TPE1")
            self.title_label.setText(f"Назва: {title.text[0] if title else '-'}")
            self.artist_label.setText(f"Виконавець: {artist.text[0] if artist else '-'}")

            cover_found = False
            for tag in tags.values():
                if isinstance(tag, APIC):
                    pixmap = QPixmap()
                    pixmap.loadFromData(tag.data)
                    self.cover_label.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    cover_found = True
                    # беремо тему з середнього кольору обкладинки
                    image = Image.open(BytesIO(tag.data))
                    avg_color = image.resize((1,1)).getpixel((0,0))
                    palette = self.palette()
                    palette.setColor(QPalette.Window, QColor(*avg_color))
                    self.setPalette(palette)
                    break
            if not cover_found:
                self.cover_label.setText("Немає обкладинки")
                palette = self.palette()
                palette.setColor(QPalette.Window, QColor(30,30,30))
                self.setPalette(palette)

        except Exception:
            self.title_label.setText("Помилка при завантаженні тегів")
            self.cover_label.setText("Немає обкладинки")
            palette = self.palette()
            palette.setColor(QPalette.Window, QColor(30,30,30))
            self.setPalette(palette)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MiniPlayer()
    player.show()
    sys.exit(app.exec())
