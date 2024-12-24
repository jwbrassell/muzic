# System Architecture

## Overview

TapForNerd Radio follows a client-server architecture with a Flask backend and JavaScript frontend. The system is designed to handle music streaming, real-time audio visualization, and dynamic display updates.

## Components

### Backend (Python/Flask)

```
app.py
├── Database Management
│   ├── SQLite database (music.db)
│   └── Schema management (schema.sql)
├── Media Management
│   ├── File scanning
│   ├── Metadata extraction
│   └── File serving
├── Playlist Management
│   ├── CRUD operations
│   └── Playback state
└── Configuration (config.py)
```

#### Key Components:
- **Database Layer**: SQLite database storing media metadata, playlists, and subscriber information
- **Media Scanner**: Processes audio files and extracts metadata using mutagen
- **API Layer**: RESTful endpoints for frontend communication
- **Configuration**: Centralized configuration management

### Frontend (JavaScript)

```
static/js/
├── admin.js
│   ├── Media Library Management
│   ├── Playlist Management
│   └── Display Control
├── visualizer.js
│   ├── Audio Context Management
│   ├── Frequency Analysis
│   └── Canvas Rendering
└── templates/
    ├── admin.html
    └── display.html
```

#### Key Components:
- **Admin Interface**: Manages media library and playlists
- **Display Interface**: Handles visualization and dynamic text
- **Audio Visualizer**: Real-time audio analysis and visualization
- **Window Communication**: Cross-window messaging for control

## Data Flow

1. **Media Upload/Scan**
```
User → Admin Interface → Backend → File System
                     ↳ Database (metadata)
```

2. **Playlist Management**
```
User → Admin Interface → Backend → Database
```

3. **Playback**
```
User → Admin Interface → Display Window
    → Backend (track info) → Audio File → Web Audio API
                         → Visualizer
```

4. **Display Updates**
```
User → Admin Interface → Display Window
    → Marquee/Footer Updates
```

## Technologies Used

### Backend
- **Flask**: Web framework
- **SQLite**: Database
- **Mutagen**: Audio metadata extraction
- **Flask-CORS**: Cross-origin resource sharing

### Frontend
- **Web Audio API**: Audio processing and analysis
- **Canvas API**: Visualization rendering
- **Bootstrap**: UI framework
- **SortableJS**: Drag-and-drop functionality

## Communication

### API Communication
- RESTful endpoints for data operations
- JSON for data exchange
- File streaming for media content

### Cross-Window Communication
- PostMessage API for admin-display communication
- Event-based messaging system
- Structured message format for different operations

## Security Considerations

1. **File Access**
   - Restricted media directory access
   - File type validation
   - Secure file paths

2. **API Security**
   - Input validation
   - Error handling
   - Safe file operations

## Future Considerations

1. **Scalability**
   - Media file storage optimization
   - Caching layer
   - Background task processing

2. **Features**
   - User authentication
   - Remote control capabilities
   - Advanced visualization options
   - Previous track functionality
   - Celery integration for async tasks

3. **Performance**
   - Media streaming optimization
   - Visualization performance improvements
   - Database query optimization
