import sys
import os
import random
import math
import statistics
from collections import Counter
from io import BytesIO

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QComboBox
)
from PySide6.QtGui import QIcon, QPixmap, QPalette, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl

from mutagen.id3 import ID3, APIC
from PIL import Image


def ensure_rgb(image: Image.Image) -> Image.Image:
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def sample_pixels(image: Image.Image, max_samples=1000):
    """Повертає список RGB кортежів, вибірково зменшуючи зображення для швидкості."""
    image = ensure_rgb(image)
    w, h = image.size
    # зменшимо для ефективності
    sample_size = int(math.sqrt(max_samples))
    if sample_size < 1:
        sample_size = 1
    img_small = image.resize((min(sample_size, w), min(sample_size, h)))
    pixels = list(img_small.getdata())
    # Якщо все одно забагато — випадково підвізьмемо підмножину
    if len(pixels) > max_samples:
        pixels = random.sample(pixels, max_samples)
    return pixels


def dominant_average(image: Image.Image):
    pixels = sample_pixels(image, max_samples=2000)
    if not pixels:
        return (30, 30, 30)
    r = int(sum(p[0] for p in pixels) / len(pixels))
    g = int(sum(p[1] for p in pixels) / len(pixels))
    b = int(sum(p[2] for p in pixels) / len(pixels))
    return (r, g, b)


def dominant_center(image: Image.Image):
    image = ensure_rgb(image)
    w, h = image.size
    center = image.getpixel((w // 2, h // 2))
    return center


def dominant_histogram(image: Image.Image):
    image = ensure_rgb(image)
    # getcolors може повертати None якщо надто багато кольорів; тоді зменшимо
    colors = image.getcolors(maxcolors=1000000)
    if not colors:
        small = image.resize((100, 100))
        colors = small.getcolors(maxcolors=1000000)
        if not colors:
            return dominant_average(image)
    # colors: [(count, (r,g,b)), ...]
    most = max(colors, key=lambda c: c[0])[1]
    return most


def dominant_median(image: Image.Image):
    pixels = sample_pixels(image, max_samples=3000)
    if not pixels:
        return (30, 30, 30)
    r = int(statistics.median([p[0] for p in pixels]))
    g = int(statistics.median([p[1] for p in pixels]))
    b = int(statistics.median([p[2] for p in pixels]))
    return (r, g, b)


def dominant_mode(image: Image.Image):
    image = ensure_rgb(image)
    pixels = sample_pixels(image, max_samples=3000)
    if not pixels:
        return (30, 30, 30)
    cnt = Counter(pixels)
    most_common = cnt.most_common(1)
    if most_common:
        return most_common[0][0]
    return dominant_average(image)


def euclidean(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def dominant_kmeans(image: Image.Image, k=3, max_iter=10, sample_limit=1000):
    """
    Простий реалізацій K-Means без залежностей. Повертає центр найбільшого кластера.
    """
    pixels = sample_pixels(image, max_samples=sample_limit)
    if not pixels:
        return (30, 30, 30)

    # Ініціалізація центрів випадково
    centers = random.sample(pixels, min(k, len(pixels)))

    for _ in range(max_iter):
        clusters = {i: [] for i in range(len(centers))}
        # Прив'язуємо пікселі до найближчого центру
        for p in pixels:
            distances = [euclidean(p, c) for c in centers]
            idx = distances.index(min(distances))
            clusters[idx].append(p)
        new_centers = []
        changed = False
        for i in range(len(centers)):
            if clusters[i]:
                r = int(sum(px[0] for px in clusters[i]) / len(clusters[i]))
                g = int(sum(px[1] for px in clusters[i]) / len(clusters[i]))
                b = int(sum(px[2] for px in clusters[i]) / len(clusters[i]))
                new_centers.append((r, g, b))
            else:
                # якщо кластер порожній — вибираємо випадковий піксель
                new_centers.append(random.choice(pixels))
        for a, b in zip(centers, new_centers):
            if a != b:
                changed = True
                break
        centers = new_centers
        if not changed:
            break

    # вибираємо найбільший кластер (за кількістю пікселів) та повертаємо його центр
    largest_idx = max(clusters.keys(), key=lambda i: len(clusters[i]) if clusters[i] else 0)
    if clusters[largest_idx]:
        # повертаємо середній колір великого кластера
        r = int(sum(px[0] for px in clusters[largest_idx]) / len(clusters[largest_idx]))
        g = int(sum(px[1] for px in clusters[largest_idx]) / len(clusters[largest_idx]))
        b = int(sum(px[2] for px in clusters[largest_idx]) / len(clusters[largest_idx]))
        return (r, g, b)

    # fallback
    return dominant_average(image)


def compute_all_methods(image: Image.Image):
    """Повертає словник усіх методів (ключ — назва методу, значення — (r,g,b))."""
    # гарантуємо RGB
    image = ensure_rgb(image)
    return {
        "K-Means": dominant_kmeans(image),
        "Середнє": dominant_average(image),
        "Центр": dominant_center(image),
        "Гістограма": dominant_histogram(image),
        "Медіана": dominant_median(image),
        "Режим": dominant_mode(image),
    }


def contrast_color(rgb):
    """Повертає (r,g,b) чорного або білого для контрастності тексту."""
    r, g, b = rgb
    # обчислимо відносну яскравість (luminance)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (0, 0, 0) if luminance > 0.5 else (255, 255, 255)


class MiniPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Player")
        self.setFixedSize(340, 520)
        self.is_playing = False
        self.file_path = None
        self.playlist = []
        self.current_index = -1

        # --- Audio player ---
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        # --- Cover ---
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(220, 220)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid rgba(255,255,255,0.08);")

        # --- Title / Artist ---
        self.title_label = QLabel("Назва: -")
        self.artist_label = QLabel("Виконавець: -")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.artist_label.setWordWrap(True)

        # --- Playlist view ---
        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(80)
        self.list_widget.itemDoubleClicked.connect(self.play_selected_item)

        # --- Method selector ---
        self.method_combo = QComboBox()
        # порядок методів у комбо та мови — українською
        self.methods_order = ["K-Means", "Середнє", "Центр", "Гістограма", "Медіана", "Режим"]
        self.method_combo.addItems(self.methods_order)
        self.method_combo.setToolTip("Оберіть метод визначення теми за обкладинкою")
        self.method_combo.currentIndexChanged.connect(self.apply_current_theme_choice)

        # --- Buttons ---
        self.btn_prev = QPushButton()
        self.btn_play = QPushButton()
        self.btn_next = QPushButton()
        self.btn_open = QPushButton("Відкрити файл")
        self.btn_prev.setIcon(QIcon("assets/back.png"))
        self.btn_play.setIcon(QIcon("assets/play.png"))
        self.btn_next.setIcon(QIcon("assets/next.png"))
        self.btn_prev.setFixedSize(64, 40)
        self.btn_play.setFixedSize(64, 40)
        self.btn_next.setFixedSize(64, 40)
        self.btn_open.setFixedHeight(36)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_prev.clicked.connect(self.prev_track)
        self.btn_next.clicked.connect(self.next_track)

        # --- Layouts ---
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.btn_prev)
        h_layout.addWidget(self.btn_play)
        h_layout.addWidget(self.btn_next)
        h_layout.addStretch()

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(12, 12, 12, 12)
        v_layout.setSpacing(8)
        v_layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)
        v_layout.addWidget(self.title_label)
        v_layout.addWidget(self.artist_label)
        v_layout.addLayout(h_layout)

        # метод вибору + кнопка відкриття
        method_row = QHBoxLayout()
        method_row.addWidget(self.method_combo)
        method_row.addWidget(self.btn_open)
        v_layout.addLayout(method_row)

        self.setLayout(v_layout)

        # встановимо початкову тему
        self.apply_theme((30, 30, 30))

    def load_playlist(self):
        if not self.file_path:
            return
        folder = os.path.dirname(self.file_path)
        files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith('.mp3')]
        self.playlist = [os.path.join(folder, f) for f in files]
        self.list_widget.clear()
        for f in files:
            self.list_widget.addItem(f)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Вибрати MP3 файл", "", "MP3 Files (*.mp3)")
        if path:
            self.file_path = os.path.abspath(path)
            folder = os.path.dirname(self.file_path)
            self.playlist = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith('.mp3')]
            try:
                self.current_index = self.playlist.index(self.file_path)
            except ValueError:
                self.current_index = 0
            self.load_playlist()
            # встановимо виділення в списку
            if 0 <= self.current_index < self.list_widget.count():
                self.list_widget.setCurrentRow(self.current_index)
            self.play_current_track()

    def play_selected_item(self, item):
        row = self.list_widget.row(item)
        if 0 <= row < len(self.playlist):
            self.current_index = row
            self.file_path = self.playlist[self.current_index]
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

    def prev_track(self):
        if not self.playlist:
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.file_path = self.playlist[self.current_index]
        self.list_widget.setCurrentRow(self.current_index)
        self.play_current_track()

    def next_track(self):
        if not self.playlist:
            return
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.file_path = self.playlist[self.current_index]
        self.list_widget.setCurrentRow(self.current_index)
        self.play_current_track()

    def on_media_status_changed(self, status):
        # Якщо трек закінчився — зупинити й змінити іконку
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.stop()
            self.btn_play.setIcon(QIcon("assets/play.png"))
            self.is_playing = False

    def load_tags_and_theme(self):
        """Завантажує теги mp3, обкладинку, обчислює палітру та застосовує тему."""
        try:
            tags = ID3(self.file_path)
            title = tags.get("TIT2")
            artist = tags.get("TPE1")
            self.title_label.setText(f"Назва: {title.text[0] if title else '-'}")
            self.artist_label.setText(f"Виконавець: {artist.text[0] if artist else '-'}")

            cover_found = False
            for tag in tags.values():
                if isinstance(tag, APIC):
                    # Зображення у tag.data
                    img = Image.open(BytesIO(tag.data)).convert("RGB")
                    pixmap = QPixmap()
                    pixmap.loadFromData(tag.data)
                    self.cover_label.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    cover_found = True

                    # обчислюємо всі методи
                    methods = compute_all_methods(img)
                    # застосовуємо вибраний метод
                    self.apply_theme_from_methods(methods)
                    break
            if not cover_found:
                self.cover_label.setText("Немає обкладинки")
                self.apply_theme((30, 30, 30))

        except Exception as e:
            # у випадку помилки — показуємо повідомлення та базову тему
            self.title_label.setText("Помилка при завантаженні тегів")
            self.cover_label.setText("Немає обкладинки")
            self.apply_theme((30, 30, 30))
            print("Error loading tags:", e)

    def apply_theme_from_methods(self, methods_dict):
        """
        Очікує словник методів -> (r,g,b), застосовує колір за вибраним методом.
        Також оновлює підказку combobox-а з реальними кольорами (для зручності).
        """
        # оновимо combo підказки (не змінюючи поточний вибір)
        current = self.method_combo.currentText()
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        for k in self.methods_order:
            color = methods_dict.get(k, (30, 30, 30))
            r, g, b = color
            # представимо в тексті для зручності
            self.method_combo.addItem(f"{k}  ({r},{g},{b})", userData=color)
        # Відновимо індекс на відповідний без user-visible змін
        idx = 0
        try:
            idx = self.methods_order.index(current)
        except ValueError:
            idx = 0
        # якщо попередній вибір існував — вибираємо його, інакше 0
        self.method_combo.setCurrentIndex(idx if idx < self.method_combo.count() else 0)
        self.method_combo.blockSignals(False)

        # застосуємо колір для поточного індексу
        self.apply_current_theme_choice()

    def apply_current_theme_choice(self):
        """Беремо колір з userData поточного елементу combo і застосовуємо тему."""
        idx = self.method_combo.currentIndex()
        if idx < 0:
            return
        data = self.method_combo.itemData(idx)
        if isinstance(data, tuple) and len(data) == 3:
            self.apply_theme(data)
        else:
            # якщо userData не встановлений (наприклад немає обкладинки) — fallback
            text = self.method_combo.currentText()
            # спробуємо витягти rgb з тексту "(r,g,b)"
            import re
            m = re.search(r"\((\d+),\s*(\d+),\s*(\d+)\)", text)
            if m:
                r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                self.apply_theme((r, g, b))
            else:
                self.apply_theme((30, 30, 30))

    def apply_theme(self, rgb):
        """Застосовує тему по rgb: фон вікна, кольори текстів і кнопок."""
        r, g, b = rgb
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(r, g, b))
        # збережемо фон
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        # контрастний текст
        tr, tg, tb = contrast_color((r, g, b))
        text_color = f"color: rgb({tr}, {tg}, {tb});"

        # стилі для кнопок (фон трохи темніший/світліший)
        def adjust(c, factor):
            return max(0, min(255, int(c * factor)))

        btn_r = adjust(r, 0.9)
        btn_g = adjust(g, 0.9)
        btn_b = adjust(b, 0.9)
        btn_style = f"background-color: rgb({btn_r},{btn_g},{btn_b}); {text_color} border-radius: 8px;"

        # застосуємо стилі
        self.title_label.setStyleSheet(f"{text_color} font-weight: 600;")
        self.artist_label.setStyleSheet(text_color)
        self.btn_open.setStyleSheet(btn_style)
        self.btn_play.setStyleSheet(btn_style)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_next.setStyleSheet(btn_style)
        self.list_widget.setStyleSheet(f"background-color: rgba(255,255,255,0.05); {text_color}")

        # рамка обкладинки та текст в ній
        self.cover_label.setStyleSheet(f"border: 1px solid rgba(255,255,255,0.12); {text_color}")

        # також оновимо іконки якщо потрібно (необов'язково)
        # --- кінець apply_theme ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MiniPlayer()
    player.show()
    sys.exit(app.exec())
