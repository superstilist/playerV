import os
import hashlib
from pathlib import Path
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QScrollArea, \
    QPushButton, QHBoxLayout, QMenu, QMessageBox, QInputDialog
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QFont, QPixmap, QLinearGradient, QIcon, QPainterPath

try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


class HomePage(QWidget):
    track_selected = Signal(dict)
    playlist_selected = Signal(str)

    def __init__(self, settings, library, main_window):
        super().__init__()
        self.settings = settings
        self.library = library
        self.main_window = main_window
        self.current_playlist = "Recently Added"
        self.context_menu_track = None

        # Simplified layout - only scroll area
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Only keep the music library scroll area
        self.add_music_library_section(layout)

        self.refresh_library()

    def add_music_library_section(self, layout):
        rec_title = QLabel("Your Music Library")
        rec_title.setFont(QFont("Arial", 18, QFont.Bold))
        rec_title.setStyleSheet("color: inherit; margin-top: 20px;")
        layout.addWidget(rec_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(800)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #121212;
                border: none;
            }
        """)

        self.songs_container = QWidget()
        self.songs_layout = QGridLayout(self.songs_container)
        self.songs_layout.setContentsMargins(15, 25, 25, 15)
        self.songs_layout.setSpacing(35)

        scroll_area.setWidget(self.songs_container)
        layout.addWidget(scroll_area)

    def refresh_library(self):
        """Update the song list from the current playlist"""
        for i in reversed(range(self.songs_layout.count())):
            widget = self.songs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if self.current_playlist in self.library.playlists:
            tracks = self.library.get_playlist_tracks(self.current_playlist)
        else:
            tracks = self.library.get_all_tracks()

        for i, song in enumerate(tracks):
            card = self.create_song_card(song)
            row = i // 3
            col = i % 3
            self.songs_layout.addWidget(card, row, col)

    def update_playlist_cover(self):
        """Update playlist cover based on first track"""
        if self.current_playlist in self.library.playlists:
            tracks = self.library.get_playlist_tracks(self.current_playlist)
            if tracks:
                first_track = tracks[0]
                cover_pixmap = self.get_cover_pixmap_for_song(first_track, QSize(300, 300))
                self.update_cover(cover_pixmap)

    def create_song_card(self, song):
        card = QFrame()
        card.setFixedSize(220, 270)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
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

        def rounded_pixmap(pixmap, radius):
            size = pixmap.size()
            rounded = QPixmap(size)
            rounded.fill(Qt.transparent)

            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            path = QPainterPath()
            path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)

            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            return rounded

        icon_size = QSize(200, 200)
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size)
        icon_label.setAlignment(Qt.AlignCenter)

        pixmap = self.get_cover_pixmap_for_song(song, icon_size)
        pixmap = rounded_pixmap(pixmap, radius=20)

        icon_label.setPixmap(pixmap)

        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        title = song.get('title', 'Unknown') or 'Unknown'
        display_title = title[:20] + ('...' if len(title) > 20 else '')
        name_label = QLabel(display_title)
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        artist = song.get('artist', 'Unknown') or 'Unknown'
        display_artist = artist[:20] + ('...' if len(artist) > 20 else '')
        artist_label = QLabel(display_artist)
        artist_label.setFont(QFont("Arial", 12))
        artist_label.setStyleSheet("color: #b3b3b3;")
        artist_label.setWordWrap(True)
        artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(artist_label)

        card.mousePressEvent = lambda event, s=song, p=pixmap: self.on_song_clicked(event, s, p)

        return card

    def get_cover_pixmap_for_song(self, song, icon_size):
        """Return QPixmap cover for song.
        Sequence of attempts:
         1) If song['cover_path'] exists on disk — load it.
         2) Try to extract embedded artwork from audio file (via mutagen).
         3) Generate default cover.
        """
        if 'cover_path' in song and song['cover_path'] and os.path.exists(song['cover_path']):
            pixmap = QPixmap(song['cover_path'])
            if not pixmap.isNull():
                return pixmap.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        audio_path = song.get('file_path') or song.get('path') or song.get('filepath')
        if audio_path and os.path.exists(audio_path) and MutagenFile is not None:
            try:
                af = MutagenFile(audio_path)
                if af is not None:
                    pic_data = None
                    if hasattr(af, 'tags') and af.tags is not None:
                        tags = af.tags
                        # APIC (ID3) style
                        for key in getattr(tags, 'keys', lambda: [])():
                            try:
                                if str(key).upper().startswith('APIC'):
                                    pic = tags.get(key)
                                    if pic and hasattr(pic, 'data'):
                                        pic_data = pic.data
                                        break
                            except Exception:
                                continue
                        # MP4 covr
                        if pic_data is None:
                            try:
                                if 'covr' in tags:
                                    covr = tags.get('covr')
                                    if covr:
                                        pic_data = covr[0]
                            except Exception:
                                pass
                        # pictures (mutagen FLAC)
                        if pic_data is None and hasattr(af, 'pictures') and af.pictures:
                            try:
                                pic_data = af.pictures[0].data
                            except Exception:
                                pass

                    if pic_data:
                        qpix = QPixmap()
                        if qpix.loadFromData(pic_data):
                            return qpix.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            except Exception:
                pass

        return self.create_default_cover(song.get('title', 'Unknown'), icon_size)

    def create_default_cover(self, title, size):
        """Create default cover"""
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Use hash of title to produce consistent color
        hash_obj = hashlib.md5((title or "Unknown").encode('utf-8'))
        hash_num = int(hash_obj.hexdigest()[:6], 16)
        r = (hash_num & 0xFF0000) >> 16
        g = (hash_num & 0x00FF00) >> 8
        b = (hash_num & 0x0000FF)

        gradient = QLinearGradient(0, 0, size.width(), size.height())
        gradient.setColorAt(0, QColor(r, g, b))
        gradient.setColorAt(1, QColor(max(0, r // 2), max(0, g // 2), max(0, b // 2)))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, size.width(), size.height(), 12, 12)

        # Simple music-note-ish glyph
        note_color = QColor(255, 255, 255, 200)
        painter.setBrush(QBrush(note_color))

        center_x, center_y = size.width() // 2, size.height() // 2
        painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)
        painter.drawRect(center_x - 5, center_y + 20, 10, 40)
        painter.drawEllipse(center_x - 30, center_y - 30, 20, 20)
        painter.drawRect(center_x - 35, center_y - 10, 25, 10)

        painter.end()
        return pixmap

    def on_cover_double_clicked(self, event):
        """Double-click on cover toggles play/pause (if main_window has handler)."""
        if event.button() == Qt.LeftButton:
            if hasattr(self.main_window, 'on_play_pause'):
                try:
                    self.main_window.on_play_pause()
                except Exception:
                    pass
        # call base implementation to keep event propagation
        super().mouseDoubleClickEvent(event)


    def add_to_favorites(self, track):
        """Add track to favorites playlist"""
        if hasattr(self.library, 'add_to_playlist'):
            if self.library.add_to_playlist('Favorites', track['id']):
                QMessageBox.information(self, "Success", f"'{track['title']}' added to Favorites")
            else:
                QMessageBox.warning(self, "Error", "Track already in Favorites")

    def on_song_clicked(self, event, song, cover_pixmap):
        """Handle song click"""
        if event.button() == Qt.LeftButton:
            self.play_song(song, cover_pixmap)
        elif event.button() == Qt.RightButton:
            self.show_track_context_menu(song, event.globalPos())

    def play_song(self, song, cover_pixmap):
        """Play song"""
        self.track_selected.emit(song)

        if hasattr(self.main_window, 'play_track_by_id'):
            try:
                self.main_window.play_track_by_id(song['id'])
            except Exception:
                pass

    def show_track_context_menu(self, song, global_pos):
        """Show context menu for track"""
        self.context_menu_track = song
        menu = QMenu(self)

        play_action = menu.addAction("▶ Play")
        menu.addSeparator()

        add_to_playlist_action = menu.addAction("➕ Add to playlist...")
        remove_from_playlist_action = menu.addAction("➖ Remove from playlist")

        menu.addSeparator()
        show_info_action = menu.addAction("ℹ Track info")
        delete_action = menu.addAction("🗑 Delete track from library")

        system_playlists = ['Favorites', 'Recently Added', 'Most Played']
        is_system_playlist = self.current_playlist in system_playlists
        remove_from_playlist_action.setEnabled(not is_system_playlist)

        action = menu.exec_(global_pos)

        if action == play_action:
            self.play_song(song, None)
        elif action == add_to_playlist_action:
            self.add_track_to_playlist(song)
        elif action == remove_from_playlist_action:
            self.remove_track_from_playlist(song)
        elif action == show_info_action:
            self.show_track_info(song)
        elif action == delete_action:
            self.delete_track_from_library(song)

    def add_track_to_playlist(self, track):
        """Add track to playlist"""
        playlists = list(self.library.playlists.keys())
        if self.current_playlist in playlists:
            playlists.remove(self.current_playlist)

        if not playlists:
            QMessageBox.information(self, "No playlists", "Create a new playlist first!")
            return

        playlist_name, ok = QInputDialog.getItem(
            self, "Add to playlist",
            "Select playlist:", playlists, 0, False
        )

        if ok and playlist_name:
            if self.library.add_to_playlist(playlist_name, track['id']):
                QMessageBox.information(self, "Success", f"Track added to '{playlist_name}'")
            else:
                QMessageBox.warning(self, "Error", "Track already in this playlist!")

    def remove_track_from_playlist(self, track):
        """Remove track from current playlist"""
        reply = QMessageBox.question(
            self, "Remove from playlist",
            f"Remove '{track['title']}' from '{self.current_playlist}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.library.remove_from_playlist(self.current_playlist, track['id']):
                self.refresh_library()
                QMessageBox.information(self, "Success", "Track removed from playlist")
            else:
                QMessageBox.warning(self, "Error", "Failed to remove track")

    def show_track_info(self, track):
        """Show track info"""
        info_text = f"""
        <b>Title:</b> {track.get('title', 'Unknown')}<br>
        <b>Artist:</b> {track.get('artist', 'Unknown')}<br>
        <b>Album:</b> {track.get('album', 'Unknown')}<br>
        <b>Duration:</b> {self.format_duration(track.get('duration', 0))}<br>
        <b>Genre:</b> {track.get('genre', 'Unknown')}<br>
        <b>Year:</b> {track.get('year', 'Unknown')}<br>
        <b>Play count:</b> {track.get('play_count', 0)}<br>
        <b>File path:</b><br>{track.get('file_path', 'Unknown')}
        """

        QMessageBox.information(self, "Track info", info_text)

    def delete_track_from_library(self, track):
        """Delete track from library"""
        reply = QMessageBox.question(
            self, "Delete track",
            f"Are you sure you want to delete '{track['title']}' from library?<br><br>"
            f"<i>This will also remove the track from all playlists!</i>",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for playlist_name in list(self.library.playlists.keys()):
                self.library.remove_from_playlist(playlist_name, track['id'])

            self.library.tracks = [t for t in self.library.tracks if t['id'] != track['id']]
            self.library.save_library()

            self.refresh_library()
            QMessageBox.information(self, "Success", "Track deleted from library")

    def format_duration(self, seconds):
        """Format duration in seconds to readable format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def update_cover(self, pixmap):
        """Update cover on top panel"""
        if pixmap:
            # compute target size safely
            frame_w = max(1, self.cover_frame.width() - 20)
            frame_h = max(1, self.cover_frame.height() - 20)
            target_size = QSize(frame_w, frame_h)

            scaled_pixmap = pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            def rounded_pixmap(pixmap, radius):
                size = pixmap.size()
                rounded = QPixmap(size)
                rounded.fill(Qt.transparent)

                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)

                path = QPainterPath()
                path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)

                painter.setClipPath(path)
                painter.drawPixmap(0, 0, pixmap)
                painter.end()

                return rounded

            rounded_pixmap_result = rounded_pixmap(scaled_pixmap, radius=20)
            self.cover_label.setPixmap(rounded_pixmap_result)
        else:
            self.cover_label.clear()

    def on_playlist_changed(self, playlist_name):
        """Handle playlist change"""
        self.current_playlist = playlist_name
        self.refresh_library()

    def apply_settings(self, settings):
        try:
            self.settings = settings
            show_cover = settings.value("show_cover", True, type=bool)
            self.cover_container.setVisible(show_cover)

            theme = settings.value("theme", "dark", type=str)
            if theme == "dark":
                for i in range(self.songs_layout.count()):
                    widget = self.songs_layout.itemAt(i).widget()
                    if widget:
                        for label in widget.findChildren(QLabel):
                            if label.font().bold():
                                label.setStyleSheet("color: white;")
                            else:
                                label.setStyleSheet("color: #b3b3b3;")
            else:
                for i in range(self.songs_layout.count()):
                    widget = self.songs_layout.itemAt(i).widget()
                    if widget:
                        for label in widget.findChildren(QLabel):
                            if label.font().bold():
                                label.setStyleSheet("color: black;")
                            else:
                                label.setStyleSheet("color: #555555;")
        except Exception as e:
            print(f"Error applying settings to home page: {str(e)}")

    def cleanup(self):
        """Clean temporary files created when extracting covers"""
        for p in self._temp_cover_files:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self._temp_cover_files.clear()
