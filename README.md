# PlayerV
![License](https://img.shields.io/badge/license-MIT-blue.svg)

![Stars](https://img.shields.io/github/stars/superstilist/playerV)


![PlayerV Logo](app_ico.png)

PlayerV is a modern, feature-rich music player application with a clean and intuitive user interface. Built with PySide6 (Qt for Python), it offers a seamless music listening experience with support for various audio formats, playlist management, and customizable themes.

## Features

### Core Functionality
- **Audio Playback**: Play, pause, next, and previous track controls
- **Audio Engine Support**: VLC and Qt-based audio engines for compatibility with various audio formats
- **Music Library**: Automatic scanning and metadata extraction from your music collection
- **Album Art**: Display and extraction of embedded album artwork

### Playlist Management
- **Create Playlists**: Create custom playlists with an easy-to-use interface
- **Manage Playlists**: Rename, delete, and organize your playlists
- **Import/Export**: Backup and share your playlists in JSON format
- **Playlist Collage**: Visual representation of playlists with album art collages

### User Interface
- **Modern Design**: Clean and intuitive interface with rounded corners and gradients
- **Theme Support**: Dark and light themes for comfortable viewing in any environment
- **Album Art Display**: Large album art view with rounded corners and shadow effects
- **Visual Feedback**: Animated play/pause buttons for better user experience

### Additional Features
- **Search**: Search for playlists and tracks
- **Metadata Editing**: View and edit track information
- **Settings**: Customize the application to your preferences

## Performance

- **Memory Usage**: Approximately 60 MB RAM
- **CPU Usage**: 0.2-1% on an Intel i5-12400F

## Screenshots

| Home Page | Playlist |
|-----------|----------|
| ![Home Page](example/home.png) | ![Playlist Page](example/playlist.png) |

| Bar | All |
|-----|-----|
| ![Settings Page](example/bar.png) | ![all](example/all.png) |

## Color Scheme

The application uses a modern and vibrant color scheme:

- **Primary Color**: `#1DB954` (Green)
- **Secondary Color**: `#121212` (Dark Background)
- **Accent Color**: `#FFC107` (Amber)
- **Text Color**: `#FFFFFF` (White) for dark theme, `#333333` (Dark) for light theme

### Color Palette

<div style="display: flex; gap: 10px;">
  <div style="width: 50px; height: 50px; background-color: #1DB954;"></div>
  <div style="width: 50px; height: 50px; background-color: #121212;"></div>
  <div style="width: 50px; height: 50px; background-color: #FFC107;"></div>
  <div style="width: 50px; height: 50px; background-color: #FFFFFF;"></div>
  <div style="width: 50px; height: 50px; background-color: #333333;"></div>
</div>

## Project Structure

- `main.py`: Entry point of the application
- `gui_base/`: Contains GUI-related files
  - `bar/`: Progress bar component
     - `RoundedProgressBar.py`: Custom rounded progress bar component

  - `home_page.py`: Main home page with album art and track listing
  - `playist_page.py`: Playlist management page
  - `settings_page.py`: Settings page for customization
  - `style.py`: Centralized style management for themes
- `engine_sound/`: Audio engine implementations
  - `AudioEngineQt.py`: Qt-based audio engine
  - `AudioEngineVLC.py`: VLC-based audio engine
- `assets/`: UI assets like buttons and icons
- `music/`: Music library directory
- `covers/`: Album covers directory
- `bar/`: Progress bar component
  - `RoundedProgressBar.py`: Custom rounded progress bar component


## Getting Started

1. **Clone the repository**
2. ```bash
   git clone https://github.com/superstilist/playerV.git
   cd playerV
   ```
2. **Install the required dependencies:**
   ```bash
   pip install PySide6 python-vlc mutagen
   ```
3. **Run the application:**
   ```bash
   python main.py
   ```

## Dependencies

- **Python 3.x**
- PySide6 (Qt for Python)
- VLC (for VLC audio engine)
- Mutagen (for audio metadata extraction)

## License

This project is licensed under the MIT License.
