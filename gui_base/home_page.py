from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QScrollArea
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QPixmap, QLinearGradient

class HomePage(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Cover art section
        self.cover_container = QWidget()
        cover_layout = QVBoxLayout(self.cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)

        self.cover_frame = QFrame()
        self.cover_frame.setMinimumSize(320, 320)
        self.cover_frame.setMaximumSize(400, 400)

        # Напівпрозорий фон
        self.cover_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
                border-radius: 20px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.cover_frame)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.cover_frame.setGraphicsEffect(shadow)

        cover_layout.addWidget(self.cover_frame)
        layout.addWidget(self.cover_container, 0, Qt.AlignCenter)

        # Track info
        track_layout = QVBoxLayout()
        track_layout.setSpacing(8)

        self.track_title = QLabel("Chill Vibes")
        self.track_title.setFont(QFont("Arial", 24, QFont.Bold))
        self.track_title.setAlignment(Qt.AlignCenter)
        self.track_title.setStyleSheet("color: white;")

        self.track_artist = QLabel("Various Artists")
        self.track_artist.setFont(QFont("Arial", 18))
        self.track_artist.setAlignment(Qt.AlignCenter)
        self.track_artist.setStyleSheet("color: #b3b3b3;")

        self.track_album = QLabel("Relaxing Tunes Vol. 1")
        self.track_album.setFont(QFont("Arial", 16))
        self.track_album.setAlignment(Qt.AlignCenter)
        self.track_album.setStyleSheet("color: #b3b3b3;")

        track_layout.addWidget(self.track_title)
        track_layout.addWidget(self.track_artist)
        track_layout.addWidget(self.track_album)
        layout.addLayout(track_layout)

        # Recommendations section
        self.add_recommendations_section(layout)
        layout.addStretch()

    def add_recommendations_section(self, layout):
        rec_title = QLabel("Recommended for You")
        rec_title.setFont(QFont("Arial", 18, QFont.Bold))
        rec_title.setStyleSheet("color: white; margin-top: 20px;")
        layout.addWidget(rec_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(700)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollBar:horizontal { background: #404040; height: 10px; border-radius: 5px; }
            QScrollBar::handle:horizontal { background: #606060; border-radius: 5px; }
            QScrollBar::handle:horizontal:hover { background: #808080; }
        """)

        container = QWidget()
        self.rec_layout = QGridLayout(container)
        self.rec_layout.setContentsMargins(5, 5, 5, 5)
        self.rec_layout.setSpacing(15)

        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        self.populate_recommendations()

    def populate_recommendations(self):
        recommendations = [
            {"title": "Discover Weekly", "color": (80, 120, 200)},
            {"title": "Release Radar", "color": (200, 80, 100)},
            {"title": "Chill Hits", "color": (80, 180, 120)},
            {"title": "Rock Classics", "color": (180, 120, 80)},
            {"title": "Mood Booster", "color": (160, 100, 200)},
            {"title": "Jazz Vibes", "color": (120, 160, 180)},
            {"title": "Electronic Dance", "color": (200, 160, 80)}
        ]

        for i, rec in enumerate(recommendations):
            card = self.create_recommendation_card(rec)
            row = i // 4
            col = i % 4
            self.rec_layout.addWidget(card, row, col)

    def create_recommendation_card(self, rec):
        card = QFrame()
        card.setFixedSize(180, 220)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);  /* напівпрозорий */
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

        icon_size = QSize(160, 160)
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size)
        icon_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, icon_size.width(), icon_size.height())
        gradient.setColorAt(0, QColor(*rec["color"]))
        gradient.setColorAt(1, QColor(rec["color"][0] // 2,
                                      rec["color"][1] // 2,
                                      rec["color"][2] // 2))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, icon_size.width(), icon_size.height(), 12, 12)

        note_color = QColor(255, 255, 255, 200)
        painter.setBrush(note_color)
        painter.drawEllipse(60, 50, 40, 40)
        painter.drawRect(75, 90, 10, 50)
        painter.drawRect(45, 35, 10, 40)
        painter.drawRect(35, 75, 30, 10)
        painter.end()

        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        name_label = QLabel(rec["title"])
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        return card

    def apply_settings(self, settings):
        try:
            self.settings = settings
            show_cover = settings.value("show_cover", True, type=bool)
            self.cover_container.setVisible(show_cover)

            theme = settings.value("theme", "dark", type=str)
            if theme == "dark":
                self.track_title.setStyleSheet("color: white;")
                self.track_artist.setStyleSheet("color: #b3b3b3;")
                self.track_album.setStyleSheet("color: #b3b3b3;")
            else:
                self.track_title.setStyleSheet("color: black;")
                self.track_artist.setStyleSheet("color: #555555;")
                self.track_album.setStyleSheet("color: #555555;")
        except Exception as e:
            print(f"Error applying settings to home page: {str(e)}")

    def cleanup(self):
        pass
