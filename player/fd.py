import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QSlider, QFileDialog,
                               QLabel, QFrame, QMenu, QSizePolicy, QGraphicsOpacityEffect)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, QTimer, QPoint, QEvent, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QColor, QPalette, QPainter, QPainterPath, QBrush, QPen, QFont


class GlassFrame(QFrame):
    def __init__(self, parent=None, radius=15):
        super().__init__(parent)
        self.radius = radius
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(self.rect(), self.radius, self.radius)

        # Apply glass effect
        painter.setClipPath(path)
        painter.fillPath(path, QColor(30, 30, 46, 220))

        # Draw border
        pen = QPen(QColor(108, 112, 134, 180), 2)
        painter.setPen(pen)
        painter.drawPath(path)


class GlassMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QMenu {
                background-color: transparent;
                padding: 10px;
            }
            QMenu::item {
                background-color: rgba(49, 50, 68, 0.8);
                color: #cdd6f4;
                border: 1px solid rgba(108, 112, 134, 0.4);
                border-radius: 8px;
                padding: 8px 16px;
                margin: 4px 0;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: rgba(69, 71, 90, 0.9);
                border: 1px solid rgba(180, 190, 254, 0.6);
            }
            QMenu::item:pressed {
                background-color: rgba(180, 190, 254, 0.4);
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 15, 15)

        # Apply glass effect
        painter.setClipPath(path)
        painter.fillPath(path, QColor(30, 30, 46, 220))

        # Draw border
        pen = QPen(QColor(108, 112, 134, 180), 2)
        painter.setPen(pen)
        painter.drawPath(path)

        super().paintEvent(event)


class MediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Glass Media Player")
        self.setGeometry(100, 100, 800, 500)
        self.setMinimumSize(400, 300)

        # Create central widget with glass effect
        self.central_widget = GlassFrame()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Video display
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("""
            background-color: black; 
            border-radius: 15px;
        """)
        main_layout.addWidget(self.video_widget, 1)

        # Create overlay frame for controls
        self.overlay_frame = GlassFrame(radius=12)
        self.overlay_frame.setObjectName("OverlayFrame")
        self.overlay_frame.setFixedHeight(120)

        # Add opacity effect for fade animation
        self.overlay_opacity = QGraphicsOpacityEffect(self.overlay_frame)
        self.overlay_frame.setGraphicsEffect(self.overlay_opacity)
        self.overlay_opacity.setOpacity(1.0)

        overlay_layout = QVBoxLayout(self.overlay_frame)
        overlay_layout.setContentsMargins(20, 15, 20, 15)

        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(108, 112, 134, 0.3);
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #cba6f7;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(203, 166, 247, 0.6);
                border-radius: 4px;
            }
        """)
        overlay_layout.addWidget(self.progress_slider)

        # Control buttons
        control_layout = QHBoxLayout()

        self.open_button = self.create_glass_button("Open", "folder_open")
        self.play_button = self.create_glass_button("Play", "play_arrow")
        self.pause_button = self.create_glass_button("Pause", "pause")
        self.stop_button = self.create_glass_button("Stop", "stop")
        self.transparency_button = self.create_glass_button("Transparency", "opacity")
        self.overlay_button = self.create_glass_button("Menu", "menu")

        control_layout.addWidget(self.open_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch(1)
        control_layout.addWidget(self.transparency_button)
        control_layout.addWidget(self.overlay_button)

        overlay_layout.addLayout(control_layout)

        # Add overlay to main layout
        main_layout.addWidget(self.overlay_frame)

        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Settings
        self.is_transparent = False
        self.controls_visible = True

        # Inactivity timer for auto-hiding controls
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setInterval(3000)  # 3 seconds
        self.inactivity_timer.timeout.connect(self.hide_controls)
        self.inactivity_timer.start()

        # Connect signals
        self.connect_signals()

        # Apply stylesheet
        self.apply_styles()

        # Create context menu
        self.create_context_menu()

        # Create animations
        self.fade_in_animation = QPropertyAnimation(self.overlay_opacity, b"opacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_out_animation = QPropertyAnimation(self.overlay_opacity, b"opacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_out_animation.finished.connect(self.overlay_frame.hide)

    def create_glass_button(self, text, icon_name):
        button = QPushButton(text)
        button.setObjectName(icon_name)
        button.setMinimumHeight(40)
        button.setMinimumWidth(80)
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(49, 50, 68, 0.8);
                color: #cdd6f4;
                border: 1px solid rgba(108, 112, 134, 0.4);
                border-radius: 10px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(69, 71, 90, 0.9);
                border: 1px solid rgba(180, 190, 254, 0.6);
            }
            QPushButton:pressed {
                background-color: rgba(180, 190, 254, 0.4);
            }
        """)
        return button

    def connect_signals(self):
        self.open_button.clicked.connect(self.open_file)
        self.play_button.clicked.connect(self.media_player.play)
        self.pause_button.clicked.connect(self.media_player.pause)
        self.stop_button.clicked.connect(self.media_player.stop)
        self.transparency_button.clicked.connect(self.toggle_transparency)
        self.overlay_button.clicked.connect(self.show_context_menu)

        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.update_buttons)
        self.media_player.errorOccurred.connect(self.handle_error)
        self.progress_slider.sliderMoved.connect(self.set_position)

        # Install event filter for mouse tracking
        self.central_widget.installEventFilter(self)

    def create_context_menu(self):
        self.context_menu = GlassMenu(self)
        self.context_menu.setFont(QFont("Arial", 11))

        transparency_action = QAction("Toggle Transparency", self)
        transparency_action.triggered.connect(self.toggle_transparency)

        always_on_top = QAction("Always on Top", self, checkable=True)
        always_on_top.triggered.connect(self.toggle_always_on_top)

        video_info = QAction("Video Information", self)
        video_info.triggered.connect(self.show_video_info)

        playback_speed = QAction("Playback Speed", self)
        playback_speed.triggered.connect(self.adjust_playback_speed)

        audio_settings = QAction("Audio Settings", self)
        audio_settings.triggered.connect(self.adjust_audio_settings)

        exit_action = QAction("Exit Player", self)
        exit_action.triggered.connect(self.close)

        self.context_menu.addAction(transparency_action)
        self.context_menu.addAction(always_on_top)
        self.context_menu.addSeparator()
        self.context_menu.addAction(video_info)
        self.context_menu.addAction(playback_speed)
        self.context_menu.addAction(audio_settings)
        self.context_menu.addSeparator()
        self.context_menu.addAction(exit_action)

    def show_context_menu(self):
        # Position menu above the button
        pos = self.overlay_button.mapToGlobal(QPoint(0, 0))
        pos.setY(pos.y() - self.context_menu.sizeHint().height())
        self.context_menu.exec(pos)

    def contextMenuEvent(self, event):
        # Show menu at mouse position
        self.context_menu.exec(event.globalPos())

    def eventFilter(self, source, event):
        # Reset inactivity timer on mouse movement
        if event.type() == QEvent.Type.MouseMove:
            self.show_controls()
            self.inactivity_timer.start()
        return super().eventFilter(source, event)

    def show_controls(self):
        if not self.controls_visible:
            self.overlay_frame.show()
            if self.fade_out_animation.state() == QPropertyAnimation.Running:
                self.fade_out_animation.stop()
            self.fade_in_animation.start()
            self.controls_visible = True

    def hide_controls(self):
        if self.controls_visible:
            if self.fade_in_animation.state() == QPropertyAnimation.Running:
                self.fade_in_animation.stop()
            self.fade_out_animation.start()
            self.controls_visible = False

    def toggle_transparency(self):
        self.is_transparent = not self.is_transparent
        if self.is_transparent:
            self.setWindowOpacity(0.85)
            self.transparency_button.setStyleSheet("background-color: rgba(100, 149, 237, 0.7);")
        else:
            self.setWindowOpacity(1.0)
            self.transparency_button.setStyleSheet("")

    def toggle_always_on_top(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def open_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Media Files (*.mp3 *.mp4 *.wav *.avi *.mkv *.mov)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()

    def set_position(self, position):
        self.media_player.setPosition(position)

    def update_position(self, position):
        self.progress_slider.setValue(position)

    def update_duration(self, duration):
        self.progress_slider.setRange(0, duration)

    def update_buttons(self, state):
        self.play_button.setEnabled(state != QMediaPlayer.PlayingState)
        self.pause_button.setEnabled(state == QMediaPlayer.PlayingState)
        self.stop_button.setEnabled(state != QMediaPlayer.StoppedState)

    def handle_error(self):
        error = self.media_player.errorString()
        if error:
            print(f"Player error: {error}")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: rgba(25, 23, 36, 0.95);
                border-radius: 16px;
            }
            #CentralWidget {
                background-color: rgba(30, 30, 46, 0.85);
                border-radius: 14px;
            }
            #OverlayFrame {
                background-color: rgba(30, 30, 46, 0.7);
                border: 2px solid rgba(108, 112, 134, 0.5);
                border-radius: 12px;
            }
        """)

        # Apply blur effect for acrylic/glass effect
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.setPalette(palette)

        # Enable window transparency
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def show_video_info(self):
        source = self.media_player.source().fileName()
        duration = self.media_player.duration() // 1000
        minutes, seconds = divmod(duration, 60)

        info = f"File: {source.split('/')[-1]}\nDuration: {minutes}:{seconds:02d}"
        self.show_overlay_message(info)

    def adjust_playback_speed(self):
        self.show_overlay_message("Playback Speed Adjustment")

    def adjust_audio_settings(self):
        self.show_overlay_message("Audio Settings Panel")

    def show_overlay_message(self, text):
        # Create overlay message
        self.msg_label = QLabel(text, self.video_widget)
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 46, 0.85);
                color: #cdd6f4;
                border: 2px solid rgba(203, 166, 247, 0.7);
                border-radius: 15px;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.msg_label.setGeometry(
            self.video_widget.width() // 4,
            self.video_widget.height() // 3,
            self.video_widget.width() // 2,
            100
        )
        self.msg_label.show()

        # Create animation for fade out
        self.msg_opacity = QGraphicsOpacityEffect(self.msg_label)
        self.msg_label.setGraphicsEffect(self.msg_opacity)
        self.msg_opacity.setOpacity(1.0)

        fade_animation = QPropertyAnimation(self.msg_opacity, b"opacity")
        fade_animation.setDuration(2000)
        fade_animation.setStartValue(1.0)
        fade_animation.setEndValue(0.0)
        fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        fade_animation.finished.connect(self.msg_label.deleteLater)
        fade_animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    player = MediaPlayer()
    player.show()
    sys.exit(app.exec())