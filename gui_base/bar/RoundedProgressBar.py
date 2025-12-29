from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QBrush, QLinearGradient
from PySide6.QtWidgets import QProgressBar


class RoundedProgressBar(QProgressBar):
    """Custom QProgressBar with adjustable corner rounding via radius_factor.

    radius_factor: fraction of height used for corner radius (0.0..0.5).
                   0.5 => fully semicircular ends.
                   0.25 => milder rounding.
    """

    def __init__(self, parent=None, height: int = 14, radius_factor: float = 0.25):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setRange(0, 1000)
        self.setValue(0)
        self.setFixedHeight(height)

        self._bg_color = QColor(60, 60, 60, 200)
        self._grad_colors = [QColor(29, 185, 84), QColor(35, 200, 95), QColor(29, 185, 84)]

        self._last_painted_value = None
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        try:
            rf = float(radius_factor)
        except Exception:
            rf = 0.25
        self.radius_factor = max(0.0, min(0.5, rf))

    def set_colors(self, bg_color: QColor, grad_colors: list):
        self._bg_color = bg_color
        self._grad_colors = grad_colors
        self.update()

    def set_radius_factor(self, factor: float):
        """Update radius factor at runtime (0.0..0.5)."""
        try:
            f = float(factor)
        except Exception:
            return
        self.radius_factor = max(0.0, min(0.5, f))
        self.update()

    def paintEvent(self, event):
        current_value = self.value()
        if self._last_painted_value == current_value and (event.rect().width() == 0 or event.rect().height() == 0):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        radius = rect.height() * self.radius_factor

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        minimum = self.minimum()
        maximum = self.maximum()
        if maximum > minimum and current_value > minimum:
            ratio = (current_value - minimum) / (maximum - minimum)
            fg_width = max(1.0, rect.width() * ratio)
            fg_rect = QRectF(rect.x(), rect.y(), fg_width, rect.height())

            grad = QLinearGradient(fg_rect.topLeft(), fg_rect.topRight())
            if len(self._grad_colors) >= 3:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(0.5, self._grad_colors[1])
                grad.setColorAt(1.0, self._grad_colors[2])
            elif len(self._grad_colors) == 2:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[1])
            else:
                grad.setColorAt(0.0, self._grad_colors[0])
                grad.setColorAt(1.0, self._grad_colors[0])

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fg_rect, radius, radius)

        painter.setPen(QColor(255, 255, 255, 10))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        painter.end()
        self._last_painted_value = current_value