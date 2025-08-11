import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.sidebar import Sidebar, TriangleButton
from gui.recommendation import RecommendationCard


class RecommendationsPage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recommendations")
        self.setMinimumSize(1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # Главный лейаут (горизонтальный)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # Левая панель (15%)
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar, 15)  # 15% ширины

        # Треугольная кнопка
        self.triangle_button = TriangleButton()
        main_layout.addWidget(self.triangle_button, 0)  # Фиксированная ширина

        # Контентная область (85%)
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 85)  # 85% ширины

        # Заголовок (10% высоты контентной области)
        self.header = QLabel("recommend")
        self.header.setObjectName("headerLabel")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout.addWidget(self.header, 10)  # 10% высоты

        # Сетка с карточками (90% высоты контентной области)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("gridContainer")
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)  # Отступы между карточками
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.grid_container.setLayout(self.grid_layout)
        content_layout.addWidget(self.grid_container, 90)  # 90% высоты

        # Генерация данных
        self.recommendations = [
            ("Summer Vibes", "Adventure", "cover1.jpg"),
            ("Mountain Echo", "Fantasy", "cover2.jpg"),
            ("City Lights", "Sci-Fi", "cover3.jpg"),
            ("Desert Wind", "Romance", "cover4.jpg"),
            ("Night Sky", "Mystery", "cover5.jpg"),
            ("Deep Space", "Horror", "cover6.jpg"),
            ("Morning Dew", "Comedy", "cover7.jpg"),
            ("Jazz Lounge", "Drama", "cover8.jpg"),
            ("Classical Moments", "Historical", "cover9.jpg"),
            ("Rock Anthems", "Action", "cover10.jpg"),
            ("Electronic Dreams", "Thriller", "cover11.jpg"),
            ("Chillout Zone", "Documentary", "cover12.jpg")
        ]

        # Создаем карточки
        self.create_cards()

        # Применяем стили
        self.apply_styles()

    def create_cards(self):
        # Распределяем по 3 ряда и 4 колонки
        for i in range(3):  # Ряды
            for j in range(4):  # Колонки
                idx = i * 4 + j
                if idx < len(self.recommendations):
                    title, genre, cover = self.recommendations[idx]
                    card = RecommendationCard(title, genre, cover)
                    self.grid_layout.addWidget(card, i, j)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Обновляем размер шрифта заголовка
        font_size = max(16, int(self.height() * 0.04))
        font = QFont("Arial", font_size, QFont.Bold)
        self.header.setFont(font)

        # Обновляем размеры карточек для соотношения 9:16
        self.update_card_sizes()

    def update_card_sizes(self):
        # Рассчитываем ширину одной карточки
        container_width = self.grid_container.width() - self.grid_layout.spacing() * 3
        card_width = int(container_width / 4)

        # Рассчитываем высоту для соотношения 9:16
        card_height = int(card_width * 16 / 9)

        # Устанавливаем размеры карточек
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, RecommendationCard):
                widget.setFixedSize(card_width, card_height)

    def apply_styles(self):
        self.setStyleSheet("""
            #centralWidget {
                background-color: #121212;
            }

            #sidebar {
                background-color: #181818;
                border-right: 1px solid #282828;
            }

            #sidebarButton {
                background-color: #282828;
                border-radius: 30px;
                border: none;
                transition: background-color 0.3s, transform 0.3s;
            }

            #sidebarButton:hover {
                background-color: #1db954;
                transform: scale(1.05);
            }

            #triangleButton {
                background-color: transparent;
                border: none;
                transition: background-color 0.3s;
            }

            #triangleButton:hover {
                background-color: #1ed760;
            }

            #contentWidget {
                background-color: #0a0a0a;
            }

            #headerLabel {
                color: #ffffff;
                font-weight: bold;
                padding: 15px;
                border-bottom: 2px solid #1db954;
                transition: font-size 0.3s;
            }

            #gridContainer {
                background-color: transparent;
            }

            #recommendationCard {
                background-color: #181818;
                border-radius: 8px;
                border: 1px solid #282828;
                cursor: pointer;
                transition: transform 0.3s, border-color 0.3s;
            }

            #recommendationCard:hover {
                transform: translateY(-5px);
                border-color: #1db954;
            }

            #imageContainer {
                border-radius: 8px;
                background-color: #333;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecommendationsPage()
    window.show()
    sys.exit(app.exec())