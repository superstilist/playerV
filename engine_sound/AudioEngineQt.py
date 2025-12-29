from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioEngineQt(QObject):
    """Fallback audio engine_sound that wraps QMediaPlayer to provide same signals."""
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(str)
    end_of_media = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.playbackStateChanged.connect(self._on_playback_state)

    def set_source(self, file_path):
        try:
            url = QUrl.fromLocalFile(file_path)
            self.player.setSource(url)
        except Exception as e:
            print("QtAudio set_source error:", e)

    def play(self):
        try:
            self.player.play()
        except Exception as e:
            print("QtAudio play error:", e)

    def pause(self):
        try:
            self.player.pause()
        except Exception as e:
            print("QtAudio pause error:", e)

    def stop(self):
        try:
            self.player.stop()
        except Exception as e:
            print("QtAudio stop error:", e)

    def set_position(self, ms):
        try:
            self.player.setPosition(int(ms))
        except Exception:
            pass

    def get_position(self):
        try:
            return int(self.player.position())
        except Exception:
            return 0

    def get_duration(self):
        try:
            return int(self.player.duration())
        except Exception:
            return 0

    def _on_position(self, pos):
        self.position_changed.emit(int(pos))

    def _on_duration(self, dur):
        self.duration_changed.emit(int(dur))

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlayingState:
            self.state_changed.emit('playing')
        elif state == QMediaPlayer.PausedState:
            self.state_changed.emit('paused')
        else:
            self.state_changed.emit('stopped')

    def _on_media_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer as QMP
        if status == QMP.MediaStatus.EndOfMedia:
            self.end_of_media.emit()