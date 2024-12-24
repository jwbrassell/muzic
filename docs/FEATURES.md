# Features Documentation

## Media Management

### Media Library
- **File Upload**
  - Drag and drop interface for audio files
  - Supported formats: MP3, WAV, OGG, M4A
  - Automatic metadata extraction
  - File validation and error handling

- **Media Scanning**
  - Automatic directory scanning
  - Metadata extraction from audio files
  - Database synchronization
  - Support for bulk file processing

### Playlist Management
- **Playlist Creation**
  - Create named playlists
  - Add/remove tracks
  - Drag and drop track ordering
  - Real-time updates

- **Playback Control**
  - Play/pause functionality
  - Next track navigation
  - Automatic track progression
  - Playlist looping

## Audio Visualization

### Real-time Visualization
- **Audio Analysis**
  - Web Audio API integration
  - Frequency data analysis
  - Real-time data processing
  - Smooth animation rendering

- **Visual Effects**
  - Frequency bar visualization
  - Color gradient effects
  - Responsive canvas sizing
  - Performance optimized rendering

### Display Window

- **Layout**
  ```
  +------------------------+
  |     Now Playing        |
  +------------------------+
  |                        |
  |     Visualization      |
  |                        |
  +------------------------+
  |     Marquee Text       |
  +------------------------+
  |     Footer Text        |
  +------------------------+
  ```

- **Components**
  - Now playing information
  - Full-screen visualization
  - Scrolling marquee text
  - Static footer text
  - Playback controls

- **Controls**
  - Fullscreen toggle
  - Play/Pause
  - Next Track
  - Volume control (through system)

## Admin Interface

### Media Controls
- **Library Management**
  - View all media files
  - Scan for new media
  - Upload new files
  - View file metadata

- **Playlist Controls**
  - Create new playlists
  - Delete playlists
  - Add/remove tracks
  - Reorder tracks
  - Start playback

### Display Controls
- **Text Management**
  - Update marquee text
  - Update footer text
  - Real-time text updates
  - Text persistence

- **Window Management**
  - Open display window
  - Control playback
  - Manage visualization

## Cross-Window Communication

### Message Types
- **Playback Control**
  ```javascript
  // Play command
  window.postMessage('play', '*');
  
  // Pause command
  window.postMessage('pause', '*');
  
  // Toggle play/pause
  window.postMessage('togglePlay', '*');
  ```

- **Text Updates**
  ```javascript
  // Update marquee
  window.postMessage({
    type: 'updateText',
    target: 'marquee',
    text: 'New marquee text'
  }, '*');
  
  // Update footer
  window.postMessage({
    type: 'updateText',
    target: 'footer',
    text: 'New footer text'
  }, '*');
  ```

## Database Structure

### Tables
- **media**
  - ID
  - File path
  - Title
  - Artist
  - Type

- **playlists**
  - ID
  - Name
  - Description

- **playlist_items**
  - ID
  - Playlist ID
  - Media ID
  - Order position

- **subscribers**
  - ID
  - Username
  - Display text
  - Active status

## API Endpoints

### Media Management
- `POST /api/scan-media` - Scan for new media files
- `GET /api/media` - Get all media files
- `POST /api/upload` - Upload new files

### Playlist Management
- `GET /api/playlists` - Get all playlists
- `POST /api/playlists` - Create new playlist
- `DELETE /api/playlist/<id>` - Delete playlist
- `GET /api/playlist/<id>` - Get playlist details
- `POST /api/playlist/<id>/items` - Add item to playlist
- `PUT /api/playlist/<id>/order` - Update playlist order

### Playback Control
- `POST /api/play` - Start playlist playback
- `POST /api/next` - Skip to next track
- `GET /api/now-playing` - Get current track info

## Future Enhancements

### Planned Features
1. Previous track functionality
2. Volume control in display window
3. Visualization style options
4. User authentication
5. Remote control capabilities
6. Celery integration for async tasks
7. Advanced playlist features
   - Shuffle mode
   - Repeat modes
   - Smart playlists
8. Enhanced metadata support
   - Album art
   - Extended track information
   - Custom tags
