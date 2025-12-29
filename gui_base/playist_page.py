from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, QScrollArea, QPushButton, \
    QInputDialog, QMessageBox, QMenu, QSizePolicy, QFileDialog
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QLinearGradient, QAction, QPainterPath
import json
import os
import random


class Playlist(QWidget):
    playlist_clicked = Signal(str)
    track_context_requested = Signal(dict, QPoint)

    def __init__(self, settings, library, main_window):
        super().__init__()
        self.settings = settings
        self.library = library
        self.main_window = main_window
        self.playlists_file = "playlists.json"
        self.playlists = self.load_playlists()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        title = QLabel("Your Playlists")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignLeft)
        title_layout.addWidget(title)

        self.new_playlist_btn = QPushButton("+ New Playlist")
        self.new_playlist_btn.setFixedHeight(30)
        self.new_playlist_btn.clicked.connect(self.create_new_playlist)
        self.new_playlist_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
                padding: 0 15px;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)
        title_layout.addWidget(self.new_playlist_btn)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search playlists...")
        self.search_field.setMinimumHeight(30)
        self.search_field.textChanged.connect(self.filter_playlists)
        main_layout.addWidget(self.search_field)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.playlists_container = QWidget()
        self.playlists_container.setObjectName("playlists_container")
        self.playlists_container.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlists_container.customContextMenuRequested.connect(self.show_container_context_menu)

        self.playlists_layout = QVBoxLayout(self.playlists_container)
        self.playlists_layout.setContentsMargins(0, 0, 0, 0)
        self.playlists_layout.setSpacing(10)

        scroll_area.setWidget(self.playlists_container)
        main_layout.addWidget(scroll_area)

        self.populate_playlists()

    def load_playlists(self):
        """Load playlists from JSON file"""
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading playlists: {e}")
                return self.get_default_playlists()
        else:
            return self.get_default_playlists()

    def get_default_playlists(self):
        """Default playlists"""
        return [
            {"name": "Favorite Tracks", "count": 0, "color": [220, 20, 60], "tracks": []},
            {"name": "Workout Mix", "count": 0, "color": [30, 144, 255], "tracks": []},
            {"name": "Chill Vibes", "count": 0, "color": [50, 205, 50], "tracks": []},
            {"name": "Study Focus", "count": 0, "color": [138, 43, 226], "tracks": []},
            {"name": "Road Trip", "count": 0, "color": [255, 140, 0], "tracks": []},
        ]

    def save_playlists(self):
        """Save playlists to JSON file"""
        try:
            with open(self.playlists_file, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save playlists: {e}")

    def create_new_playlist(self):
        """Create new playlist"""
        name, ok = QInputDialog.getText(self, "New Playlist", "Enter playlist name:")
        if ok and name:
            if any(p['name'].lower() == name.lower() for p in self.playlists):
                QMessageBox.warning(self, "Error", "Playlist with this name already exists!")
                return

            color = [random.randint(50, 200), random.randint(50, 200), random.randint(50, 200)]

            new_playlist = {
                "name": name,
                "count": 0,
                "color": color,
                "tracks": []
            }

            self.playlists.append(new_playlist)
            self.save_playlists()
            self.populate_playlists()

            if hasattr(self.library, 'create_playlist'):
                try:
                    self.library.create_playlist(name)
                except Exception:
                    pass

            QMessageBox.information(self, "Success", f"Playlist '{name}' created!")

    def populate_playlists(self):
        """Display playlists"""
        while self.playlists_layout.count():
            child = self.playlists_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for playlist in self.playlists:
            item = self.create_playlist_item(playlist)
            self.playlists_layout.addWidget(item)
        self.playlists_layout.addStretch()

    def filter_playlists(self, text):
        """Filter playlists by text"""
        for i in range(self.playlists_layout.count()):
            item = self.playlists_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if widget:
                playlist_name = widget.property('playlist_name')
                if playlist_name:
                    widget.setVisible(text.lower() in playlist_name.lower())

    def get_first_track_cover(self, playlist_name):
        """Get cover of first track in playlist (QPixmap or None)"""
        try:
            if hasattr(self.library, 'playlists') and playlist_name in self.library.playlists:
                track_ids = self.library.playlists[playlist_name]
                if track_ids:
                    first_track_id = track_ids[0]
                    if hasattr(self.library, 'get_track_by_id'):
                        track = self.library.get_track_by_id(first_track_id)
                    else:
                        track = None
                    if track and track.get('cover_path'):
                        cover_path = track['cover_path']
                        if cover_path and os.path.exists(cover_path):
                            pix = QPixmap(cover_path)
                            if not pix.isNull():
                                return pix
        except Exception:
            pass
        return None

    def create_playlist_item(self, playlist):
        """Create widget for one playlist (now with context menu on entire element)"""
        item = QFrame()
        item.setProperty('playlist_name', playlist['name'])
        item.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 0.7);
                border-radius: 15px;
            }
            QFrame:hover {
                background-color: rgba(40, 40, 40, 0.85);
            }
        """)
        item.setMinimumHeight(70)
        item.setCursor(Qt.PointingHandCursor)

        item.setContextMenuPolicy(Qt.CustomContextMenu)
        item.customContextMenuRequested.connect(lambda pos, p=playlist, w=item: self.show_playlist_context_menu_at(w, pos, p))

        layout = QHBoxLayout(item)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        icon_size = QSize(50, 50)
        icon_label = QLabel()
        icon_label.setFixedSize(icon_size)
        icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        cover_pixmap = self.get_first_track_cover(playlist["name"])

        if cover_pixmap and not cover_pixmap.isNull():
            cover_pixmap = cover_pixmap.scaled(icon_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            w = cover_pixmap.width()
            h = cover_pixmap.height()
            side = min(w, h)
            x = (w - side) // 2
            y = (h - side) // 2
            cover_pixmap = cover_pixmap.copy(x, y, side, side)
            cover_pixmap = cover_pixmap.scaled(icon_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(cover_pixmap)
        else:
            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            gradient = QLinearGradient(0, 0, icon_size.width(), icon_size.height())
            base = playlist.get("color", [100, 100, 100])
            gradient.setColorAt(0, QColor(*base))
            gradient.setColorAt(1, QColor(max(0, base[0] // 2),
                                          max(0, base[1] // 2),
                                          max(0, base[2] // 2)))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, icon_size.width(), icon_size.height(), 10, 10)

            note_color = QColor(255, 255, 255, 200)
            painter.setBrush(QBrush(note_color))
            painter.drawEllipse(15, 15, 20, 20)
            painter.end()

            icon_label.setPixmap(pixmap)

        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        name_label = QLabel(playlist["name"])
        name_label.setFont(QFont("Arial", 12, QFont.Bold))
        name_label.setStyleSheet("color: white;")
        text_layout.addWidget(name_label)

        track_count = 0
        if hasattr(self.library, 'playlists') and playlist["name"] in self.library.playlists:
            try:
                track_count = len(self.library.playlists[playlist["name"]])
            except Exception:
                track_count = 0

        count_label = QLabel(f"{track_count} tracks")
        count_label.setFont(QFont("Arial", 10))
        count_label.setStyleSheet("color: #b3b3b3;")
        text_layout.addWidget(count_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        context_btn = QPushButton("⋮")
        context_btn.setFixedSize(30, 30)
        context_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 5px;
            }
        """)
        context_btn.clicked.connect(lambda _, p=playlist, btn=context_btn: self.show_playlist_context_menu(p, btn.mapToGlobal(QPoint(0, btn.height()))))
        layout.addWidget(context_btn)

        def mousePressEvent(event, p=playlist):
            if event.button() == Qt.LeftButton:
                self.on_playlist_clicked(p)
            else:
                event.ignore()

        item.mousePressEvent = mousePressEvent

        return item

    def on_playlist_clicked(self, playlist):
        """Handle playlist click"""
        self.playlist_clicked.emit(playlist["name"])

        if hasattr(self.main_window, 'show_page'):
            try:
                self.main_window.show_page("home")
            except Exception:
                pass

        if hasattr(self.main_window, 'page_home'):
            try:
                self.main_window.page_home.on_playlist_changed(playlist["name"])
            except Exception:
                pass

    def show_playlist_context_menu(self, playlist, pos):
        """Show context menu for playlist (position in global coordinates)"""
        menu = QMenu(self)

        play_action = QAction("Play", menu)
        rename_action = QAction("Rename", menu)
        delete_action = QAction("Delete", menu)
        export_action = QAction("Export...", menu)

        menu.addAction(play_action)
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(export_action)

        action = menu.exec_(pos)

        if action == play_action:
            self.on_playlist_clicked(playlist)
        elif action == rename_action:
            self.rename_playlist(playlist)
        elif action == delete_action:
            self.delete_playlist(playlist)
        elif action == export_action:
            self.export_playlist(playlist)

    def show_playlist_context_menu_at(self, widget, local_pos, playlist):
        """Show context menu for playlist element (local widget position)"""
        global_pos = widget.mapToGlobal(local_pos)
        self.show_playlist_context_menu(playlist, global_pos)

    def show_container_context_menu(self, local_pos):
        """Container context menu (global actions: New, Import, Export all)"""
        global_pos = self.playlists_container.mapToGlobal(local_pos)
        menu = QMenu(self)

        new_action = QAction("New Playlist", menu)
        import_action = QAction("Import Playlists...", menu)
        export_all_action = QAction("Export All Playlists...", menu)

        menu.addAction(new_action)
        menu.addSeparator()
        menu.addAction(import_action)
        menu.addAction(export_all_action)

        action = menu.exec_(global_pos)

        if action == new_action:
            self.create_new_playlist()
        elif action == import_action:
            self.import_playlists()
        elif action == export_all_action:
            self.export_all_playlists()

    def rename_playlist(self, playlist):
        """Rename playlist"""
        new_name, ok = QInputDialog.getText(self, "Rename Playlist",
                                            "Enter new name:",
                                            text=playlist["name"])
        if ok and new_name:
            old_name = playlist["name"]
            if any(p['name'].lower() == new_name.lower() and p is not playlist for p in self.playlists):
                QMessageBox.warning(self, "Error", "Another playlist with this name already exists!")
                return

            playlist["name"] = new_name

            if hasattr(self.library, 'rename_playlist'):
                try:
                    self.library.rename_playlist(old_name, new_name)
                except Exception:
                    pass

            self.save_playlists()
            self.populate_playlists()
            QMessageBox.information(self, "Success", f"Playlist renamed to '{new_name}'")

    def delete_playlist(self, playlist):
        """Delete playlist"""
        reply = QMessageBox.question(self, "Delete Playlist",
                                     f"Are you sure you want to delete '{playlist['name']}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if hasattr(self.library, 'delete_playlist'):
                try:
                    self.library.delete_playlist(playlist["name"])
                except Exception:
                    pass

            try:
                self.playlists.remove(playlist)
            except ValueError:
                pass
            self.save_playlists()
            self.populate_playlists()
            QMessageBox.information(self, "Success", f"Playlist '{playlist['name']}' deleted")

    def refresh_playlists(self):
        """Update playlist list"""
        self.playlists = self.load_playlists()
        self.populate_playlists()

    def apply_settings(self, settings):
        """Apply settings (theme etc.)"""
        self.settings = settings
        theme = settings.value("theme", "dark", type=str) if hasattr(settings, 'value') else "dark"

        for i in range(self.playlists_layout.count()):
            widget = self.playlists_layout.itemAt(i).widget()
            if widget:
                for label in widget.findChildren(QLabel):
                    if label.font().bold():
                        if theme == "dark":
                            label.setStyleSheet("color: white;")
                        else:
                            label.setStyleSheet("color: black;")
                    else:
                        if theme == "dark":
                            label.setStyleSheet("color: #b3b3b3;")
                        else:
                            label.setStyleSheet("color: #555555;")

    def export_playlist(self, playlist):
        """Export one playlist to JSON file"""
        fname, _ = QFileDialog.getSaveFileName(self, "Export Playlist", f"{playlist['name']}.json", "JSON Files (*.json)")
        if not fname:
            return
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(playlist, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export", f"Playlist exported to {fname}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export playlist: {e}")

    def export_all_playlists(self):
        """Export all playlists to file"""
        fname, _ = QFileDialog.getSaveFileName(self, "Export All Playlists", "playlists_export.json", "JSON Files (*.json)")
        if not fname:
            return
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export", f"All playlists exported to {fname}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export playlists: {e}")

    def import_playlists(self):
        """Import playlists from JSON (can import one or list)"""
        fname, _ = QFileDialog.getOpenFileName(self, "Import Playlists", "", "JSON Files (*.json)")
        if not fname:
            return
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                incoming = [data]
            elif isinstance(data, list):
                incoming = data
            else:
                QMessageBox.warning(self, "Import Error", "File format not recognized.")
                return

            added = 0
            for p in incoming:
                name = p.get('name')
                if not name:
                    continue
                if any(existing['name'].lower() == name.lower() for existing in self.playlists):
                    continue
                self.playlists.append(p)
                if hasattr(self.library, 'create_playlist'):
                    try:
                        self.library.create_playlist(name)
                    except Exception:
                        pass
                added += 1

            if added:
                self.save_playlists()
                self.populate_playlists()
                QMessageBox.information(self, "Import", f"Imported {added} playlists.")
            else:
                QMessageBox.information(self, "Import", "No new playlists were imported.")
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import playlists: {e}")
class PlaylistItem(QFrame):
    """Custom widget for displaying a playlist with collage of up to 4 track covers"""

    playlist_clicked = Signal(str, list)

    def __init__(self, playlist_name, tracks, library):
        super().__init__()
        self.playlist_name = playlist_name
        self.tracks = tracks
        self.library = library
        self._selected = False
        self.setFixedHeight(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("playlistItem")
        self._collage_pixmap = None
        self.init_ui()
        self.update_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.collage_label = QLabel()
        self.collage_label.setFixedSize(150, 150)
        self.collage_label.setAlignment(Qt.AlignCenter)
        self.collage_label.setStyleSheet("""
            QLabel {
                background-color: rgba(60, 60, 60, 0.5);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        layout.addWidget(self.collage_label, alignment=Qt.AlignCenter)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel(self.playlist_name)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ffffff;")
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label)

        track_count = len(self.tracks)
        count_label = QLabel(f"{track_count} track{'s' if track_count != 1 else ''}")
        count_label.setFont(QFont("Segoe UI", 9))
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet("color: #b3b3b3;")
        title_layout.addWidget(count_label)

        layout.addLayout(title_layout)

        self.mousePressEvent = self.on_click

    def update_collage(self):
        """Update the collage image if not cached"""
        if self._collage_pixmap is None:
            self._collage_pixmap = self.create_playlist_collage()
        self.collage_label.setPixmap(self._collage_pixmap)

    def create_playlist_collage(self):
        collage_size = QSize(150, 150)
        cell_size = QSize(72, 72)
        spacing = 3

        collage = QPixmap(collage_size)
        collage.fill(Qt.transparent)

        painter = QPainter(collage)
        painter.setRenderHint(QPainter.Antialiasing)

        positions = [(0, 0), (1, 0), (0, 1), (1, 1)]

        for i, (row, col) in enumerate(positions):
            x = col * (cell_size.width() + spacing)
            y = row * (cell_size.height() + spacing)

            # Create rounded rectangle path for this cell
            cell_path = QPainterPath()
            cell_path.addRoundedRect(x, y, cell_size.width(), cell_size.height(), 8, 8)

            painter.save()
            painter.setClipPath(cell_path)

            if i < len(self.tracks) and self.tracks[i].get('cover_path'):
                cover_path = self.tracks[i]['cover_path']
                if cover_path and os.path.exists(cover_path):
                    pixmap = QPixmap(cover_path)
                    if not pixmap.isNull():
                        # Scale to fill the cell
                        scaled = pixmap.scaled(
                            cell_size,
                            Qt.KeepAspectRatioByExpanding,
                            Qt.SmoothTransformation
                        )
                        # Center the image
                        draw_x = x + (cell_size.width() - scaled.width()) // 2
                        draw_y = y + (cell_size.height() - scaled.height()) // 2
                        painter.drawPixmap(draw_x, draw_y, scaled)
                        painter.restore()
                        continue

            # Draw placeholder
            painter.setClipping(False)  # Remove clip for placeholder
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(80, 80, 80, 180)))
            painter.drawPath(cell_path)

            # Draw note icon
            painter.setBrush(QBrush(QColor(200, 200, 200, 150)))
            note_size = 24
            note_x = x + (cell_size.width() - note_size) // 2
            note_y = y + (cell_size.height() - note_size) // 2
            painter.drawEllipse(note_x, note_y, note_size, note_size)

            painter.restore()

        painter.end()
        return collage

    def setSelected(self, selected):
        self._selected = selected
        self.update_style()

    def update_style(self):
        if self._selected:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(29, 185, 84, 0.3);
                    border: 2px solid rgba(29, 185, 84, 0.6);
                    border-radius: 14px;
                    margin: 2px;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(29, 185, 84, 0.4);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#playlistItem {
                    background-color: rgba(40, 40, 40, 0.8);
                    border-radius: 14px;
                    margin: 2px;
                }
                QFrame#playlistItem:hover {
                    background-color: rgba(60, 60, 60, 0.9);
                }
            """)

    def on_click(self, event):
        if event.button() == Qt.LeftButton:
            self.playlist_clicked.emit(self.playlist_name, self.tracks)
        super().mousePressEvent(event)