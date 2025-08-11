from PySide6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QBrush, QColor, QPen


class TriangleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 60)
        self.setObjectName("triangleButton")
        self.setCursor(Qt.PointingHandCursor)

        # Обработка событий
        self.clicked.connect(self.on_click)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Рисуем треугольник
        color = QColor("#1db954")
        if self.underMouse():
            color = color.lighter(120)  # Светлее при наведении

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)

        # Рисуем треугольник
        points = [
            self.rect().topLeft(),
            self.rect().bottomLeft(),
            self.rect().rightCenter()
        ]
        painter.drawPolygon(points)

        painter.end()

    def on_click(self):
        """Обработчик клика по треугольной кнопке"""
        print("Треугольная кнопка нажата")

        # Анимация нажатия
        self.animate_button()

    def animate_button(self):
        """Анимация кнопки при нажатии"""
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(150)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        start_rect = self.geometry()
        end_rect = start_rect.adjusted(0, -3, 0, 3)

        animation.setKeyValueAt(0, start_rect)
        animation.setKeyValueAt(0.5, end_rect)
        animation.setKeyValueAt(1, start_rect)

        animation.start()


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setSpacing(40)
        self.setLayout(layout)

        # Создаем 4 круглые кнопки
        self.buttons = []
        for i in range(4):
            button = QPushButton()
            button.setObjectName("sidebarButton")
            button.setFixedSize(60, 60)
            layout.addWidget(button, alignment=Qt.AlignHCenter)
            self.buttons.append(button)

        # Добавляем растягивающий элемент для выравнивания
        layout.addStretch(1)

        # Подключаем обработчики событий
        for button in self.buttons:
            button.clicked.connect(self.on_button_clicked)

    def on_button_clicked(self):
        """Обработчик клика по кнопкам сайдбара"""
        # Анимация нажатия
        sender = self.sender()
        self.animate_button(sender)

        # Здесь можно добавить логику для каждой кнопки
        print(f"Кнопка {self.buttons.index(sender)} нажата")

    def animate_button(self, button):
        """Анимация кнопки при нажатии"""
        animation = QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.OutQuad)

        start_rect = button.geometry()
        end_rect = start_rect.adjusted(-5, -5, 5, 5)

        animation.setKeyValueAt(0, start_rect)
        animation.setKeyValueAt(0.5, end_rect)
        animation.setKeyValueAt(1, start_rect)

        animation.start()