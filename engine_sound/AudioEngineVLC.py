from PySide6.QtCore import QObject, Signal
try:
    import vlc

    _HAVE_VLC = True
except Exception:
    _HAVE_VLC = False

class AudioEngineVLC(QObject):
    """Audio engine_sound using python-vlc with Qt-friendly signals."""
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(str)
    end_of_media = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vlc_args = ["--no-video", "--quiet", "--no-stats", "--no-osd"]
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()
        self._media = None
        self._duration = 0
        self._position = 0

        self._em = self.player.event_manager()
        self._em.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
        self._em.event_attach(vlc.EventType.MediaPlayerPaused, self._on_state_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_state_changed)
        self._em.event_attach(vlc.EventType.MediaPlayerStopped, self._on_state_changed)

    def _on_time_changed(self, event):
        try:
            t = self.player.get_time()
            if t is None: t = 0
            self.position_changed.emit(max(0, int(t)))
        except Exception:
            pass

    def _on_end_reached(self, event):
        self.end_of_media.emit()

    def _on_state_changed(self, event):
        st = self.player.get_state()
        if st == vlc.State.Playing:
            self.state_changed.emit('playing')
        elif st == vlc.State.Paused:
            self.state_changed.emit('paused')
        elif st in (vlc.State.Ended, vlc.State.Stopped):
            self.state_changed.emit('stopped')

    def set_source(self, file_path):
        try:
            media = self.instance.media_new(str(file_path))
            try:
                media.parse_with_options(vlc.MediaParseFlag.parse_local, timeout=0)
            except Exception:
                pass
            self.player.set_media(media)
            self._media = media
        except Exception as e:
            print("VLC set_source error:", e)

    def play(self):
        try:
            self.player.play()
        except Exception as e:
            print("VLC play error:", e)

    def pause(self):
        try:
            self.player.pause()
        except Exception as e:
            print("VLC pause error:", e)

    def stop(self):
        try:
            self.player.stop()
        except Exception as e:
            print("VLC stop error:", e)

    def set_position(self, ms):
        try:
            self.player.set_time(int(ms))
        except Exception:
            pass

    def get_position(self):
        try:
            t = self.player.get_time()
            return t if t and t != -1 else 0
        except Exception:
            return 0

    def get_duration(self):
        try:
            d = self.player.get_length()
            return d if d and d != -1 else 0
        except Exception:
            return 0