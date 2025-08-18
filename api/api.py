import sys, requests, webbrowser
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtGui import QPixmap, QCursor, QBitmap, QPainter
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY  # твій ключ

class VideoCard(QFrame):
    def __init__(self, title, thumbnail_url, video_url):
        super().__init__()
        self.video_url = video_url
        self.setCursor(QCursor(Qt.PointingHandCursor))

        # Градієнтний фон картки
        self.setStyleSheet("""
            QFrame {
                border-radius: 25px;
                border: 2px solid #3a3a3a;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ff7e5f, stop:0.5 #feb47b, stop:1 #ff7e5f
                );
            }
        """)
        self.setFixedSize(240, 300)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10,10,10,10)
        main_layout.setAlignment(Qt.AlignCenter)

        # Контейнер для прев’ю і назви
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                border-radius: 20px;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2
                );
            }
        """)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(15,15,15,15)
        content_layout.setAlignment(Qt.AlignCenter)

        # Прев’ю
        self.label_thumb = QLabel()
        self.label_thumb.setFixedSize(180,180)
        self.label_thumb.setAlignment(Qt.AlignCenter)
        try:
            resp = requests.get(thumbnail_url)
            pixmap = QPixmap()
            pixmap.loadFromData(resp.content)
            pixmap = pixmap.scaled(180,180, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

            # Маска для кола
            mask = QBitmap(pixmap.size())
            mask.fill(Qt.color0)
            painter = QPainter(mask)
            painter.setBrush(Qt.color1)
            painter.drawEllipse(0,0,pixmap.width(),pixmap.height())
            painter.end()
            pixmap.setMask(mask)

            self.label_thumb.setPixmap(pixmap)
        except:
            self.label_thumb.setText("No preview")
        content_layout.addWidget(self.label_thumb, alignment=Qt.AlignCenter)

        # Назва відео з градієнтним текстом
        self.label_title = QLabel(title)
        self.label_title.setWordWrap(True)
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setStyleSheet("""
            QLabel {
                color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f7971e, stop:1 #ffd200
                );
                font-weight: bold;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        content_layout.addWidget(self.label_title)

        content_frame.setLayout(content_layout)
        main_layout.addWidget(content_frame)
        self.setLayout(main_layout)

        # Анімація при наведенні
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

        self.enterEvent = self.on_hover_enter
        self.leaveEvent = self.on_hover_leave
        self.mousePressEvent = self.open_video

    def on_hover_enter(self, event):
        rect = self.geometry()
        self.anim.stop()
        self.anim.setStartValue(rect)
        self.anim.setEndValue(rect.adjusted(-5,-5,5,5))
        self.anim.start()

    def on_hover_leave(self, event):
        rect = self.geometry()
        self.anim.stop()
        self.anim.setStartValue(rect)
        self.anim.setEndValue(rect.adjusted(5,5,-5,-5))
        self.anim.start()

    def open_video(self, event):
        webbrowser.open(self.video_url)


class YouTubeGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Preview Grid")
        self.showMaximized()

        main_layout = QVBoxLayout()

        # Пошук
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введіть пошуковий запит")
        self.search_btn = QPushButton("Пошук")
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.search_input)
        hlayout.addWidget(self.search_btn)
        main_layout.addLayout(hlayout)

        # Область для карток
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(25)
        self.container.setLayout(self.grid_layout)
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        self.setLayout(main_layout)
        self.search_btn.clicked.connect(self.search_videos)

    def search_videos(self):
        query = self.search_input.text().strip()
        if not query:
            return

        # Очистити старі результати
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=query,
            part="snippet",
            maxResults=20,
            type="video"
        )
        response = request.execute()

        row, col = 0, 0
        max_col = 5
        for item in response["items"]:
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            thumb_url = item["snippet"]["thumbnails"]["high"]["url"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            card = VideoCard(title, thumb_url, video_url)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_col:
                col = 0
                row += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeGrid()
    window.show()
    sys.exit(app.exec())
