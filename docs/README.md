# TapForNerd Radio

A web-based music streaming application with real-time audio visualization and dynamic display features.

## Overview

TapForNerd Radio is a Flask-based music streaming application that provides:
- Music library management
- Playlist creation and management
- Real-time audio visualization
- Dynamic display text for streaming overlays
- Admin interface for content management

## Getting Started

### Prerequisites

- Python 3.x
- Flask
- SQLite3
- Modern web browser with Web Audio API support

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install flask flask-cors mutagen
```

3. Initialize the database:
```bash
flask init-db
```

4. Start the server:
```bash
python app.py
```

5. Access the application:
- Admin interface: http://localhost:5000/
- Display window: http://localhost:5000/display

## Quick Start Guide

1. **Upload Music**
   - Drag and drop audio files into the Media Library section
   - Click "Scan Media" to detect new files

2. **Create Playlists**
   - Click "New Playlist" to create a playlist
   - Drag songs from the Media Library to your playlist
   - Reorder songs by dragging within the playlist

3. **Start Playback**
   - Click "Play" on any playlist to begin playback
   - The display window will open automatically
   - Use playback controls to manage playback

4. **Customize Display**
   - Update marquee text to show custom messages
   - Modify footer text
   - Toggle fullscreen for optimal viewing

## Documentation

- [Architecture](ARCHITECTURE.md) - System design and components
- [Features](FEATURES.md) - Detailed feature documentation
- [API](API.md) - API endpoints documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.
