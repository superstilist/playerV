from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QBrush, QLinearGradient


class RecommendationCard(QFrame):
    def __init__(self, title, genre, cover_path, parent=None):
        super().__init__(parent)
        self.setObjectName("recommendationCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.title = title
        self.genre = genre
        self.cover_path = cover_path
        self.setCursor(Qt.PointingHandCursor)

        # Основной лейаут
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Контейнер для изображения
        self.image_container = QLabel()
        self.image_container.setObjectName("imageContainer")
        self.image_container.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(self.image_container)

        # Обновляем обложку
        self.update_cover(cover_path)

    def update_cover(self, cover_path):
        self.cover_pixmap = QPixmap(cover_path)
        if not self.cover_pixmap.isNull():
            self.original_pixmap = self.cover_pixmap
            self.image_container.setPixmap(self.cover_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            # Масштабируем с сохранением пропорций 9:16
            scaled_pixmap = self.original_pixmap.scaled(
                self.width(),
                int(self.width() * 16 / 9),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            self.image_container.setPixmap(scaled_pixmap)
            self.image_container.setFixedHeight(int(self.width() * 16 / 9))

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Рассчитываем область для градиента (нижние 30% карточки)
        gradient_height = self.height() * 0.3
        gradient_rect = self.rect()
        gradient_rect.setTop(self.height() - gradient_height)

        # Создаем градиент
        gradient = QLinearGradient(0, self.height() - gradient_height, 0, self.height())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 200))
        painter.fillRect(gradient_rect, QBrush(gradient))

        # Настраиваем шрифты
        title_font = QFont("Arial", 12, QFont.Bold)
        genre_font = QFont("Arial", 10)

        # Рассчитываем позиции текста
        padding = 10
        title_y = self.height() - gradient_height + padding
        genre_y = self.height() - padding - genre_font.pointSize()

        # Рисуем название
        painter.setFont(title_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(padding, title_y, self.width() - 2 * padding, 30,
                         Qt.AlignLeft | Qt.AlignTop, self.title)

        # Рисуем жанр
        painter.setFont(genre_font)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(padding, genre_y, self.width() - 2 * padding, 30,
                         Qt.AlignLeft | Qt.AlignBottom, self.genre)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.animate_click()
            self.open_detail()

    def enterEvent(self, event):
        self.animate_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animate_hover(False)
        super().leaveEvent(event)

    def animate_hover(self, hover_in):
        """Анимация при наведении/уходе курсора"""
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(300)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        start_rect = self.geometry()
        end_rect = start_rect.adjusted(
            -5 if hover_in else 5,
            -5 if hover_in else 5,
            5 if hover_in else -5,
            5 if hover_in else -5
        )

        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.start()

    def animate_click(self):
        """Анимация при клике"""
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(150)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        start_rect = self.geometry()
        end_rect = start_rect.adjusted(-3, -3, 3, 3)

        animation.setKeyValueAt(0, start_rect)
        animation.setKeyValueAt(0.5, end_rect)
        animation.setKeyValueAt(1, start_rect)

        animation.start()

    def open_detail(self):
        """Открытие детального просмотра"""
        print(f"Открыта карточка: {self.title} - {self.genre}")
        # Здесь можно добавить открытие диалогового окна