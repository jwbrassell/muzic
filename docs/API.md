# API Documentation

## Overview

The TapForNerd Radio API is a RESTful API that provides endpoints for managing media, playlists, and playback control. All responses are in JSON format.

## Base URL

```
http://localhost:5000/api
```

## Endpoints

### Media Management

#### Scan Media Files

```http
POST /scan-media
```

Scans configured media directories for new audio files.

**Response**
```json
{
    "message": "Media scan completed",
    "files_found": 3,
    "files": [
        {
            "path": "/path/to/file.mp3",
            "type": "audio",
            "title": "Song Title",
            "artist": "Artist Name"
        }
    ]
}
```

#### Get All Media

```http
GET /media
```

Returns a list of all media files in the library.

**Response**
```json
[
    {
        "id": 1,
        "file_path": "/path/to/file.mp3",
        "type": "audio",
        "title": "Song Title",
        "artist": "Artist Name"
    }
]
```

#### Upload Files

```http
POST /upload
```

Upload new media files.

**Request**
- Content-Type: multipart/form-data
- Body: files[] (multiple file upload supported)

**Response**
```json
{
    "message": "Upload complete",
    "uploaded": ["file1.mp3", "file2.mp3"],
    "errors": []
}
```

### Playlist Management

#### Get All Playlists

```http
GET /playlists
```

Returns a list of all playlists.

**Response**
```json
[
    {
        "id": 1,
        "name": "My Playlist",
        "description": "Description"
    }
]
```

#### Create Playlist

```http
POST /playlists
```

Create a new playlist.

**Request**
```json
{
    "name": "New Playlist",
    "description": "Optional description"
}
```

**Response**
```json
{
    "id": 2,
    "name": "New Playlist",
    "description": "Optional description"
}
```

#### Get Playlist Details

```http
GET /playlist/{playlist_id}
```

Get details of a specific playlist including its items.

**Response**
```json
{
    "playlist": {
        "id": 1,
        "name": "My Playlist",
        "description": "Description"
    },
    "items": [
        {
            "id": 1,
            "media_id": 1,
            "title": "Song Title",
            "artist": "Artist Name",
            "order_position": 0
        }
    ]
}
```

#### Add Item to Playlist

```http
POST /playlist/{playlist_id}/items
```

Add a media item to a playlist.

**Request**
```json
{
    "media_id": 1
}
```

**Response**
```json
{
    "id": 1,
    "playlist_id": 1,
    "media_id": 1,
    "order_position": 0
}
```

#### Update Playlist Order

```http
PUT /playlist/{playlist_id}/order
```

Update the order of items in a playlist.

**Request**
```json
{
    "items": [
        {
            "id": 1,
            "order_position": 0
        },
        {
            "id": 2,
            "order_position": 1
        }
    ]
}
```

**Response**
```json
{
    "message": "Playlist order updated"
}
```

#### Delete Playlist

```http
DELETE /playlist/{playlist_id}
```

Delete a playlist.

**Response**
```json
{
    "message": "Playlist deleted"
}
```

### Playback Control

#### Start Playback

```http
POST /play
```

Start playing a playlist.

**Request**
```json
{
    "playlist_id": 1
}
```

**Response**
```json
{
    "message": "Playlist started"
}
```

#### Next Track

```http
POST /next
```

Skip to the next track.

**Response**
```json
{
    "message": "Moved to next track"
}
```

#### Get Now Playing

```http
GET /now-playing
```

Get information about the currently playing track.

**Response**
```json
{
    "id": 1,
    "title": "Song Title",
    "artist": "Artist Name",
    "file_path": "/path/to/file.mp3",
    "type": "audio"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a message:

```json
{
    "error": "Error message here"
}
```

## Rate Limiting

Currently, there are no rate limits implemented.

## Authentication

Currently, there is no authentication required for API endpoints.

## Future API Enhancements

1. Authentication and authorization
2. Rate limiting
3. Pagination for large datasets
4. WebSocket endpoints for real-time updates
5. Enhanced error responses
6. API versioning
7. Additional endpoints for:
   - Previous track control
   - Volume control
   - Visualization settings
   - User management
   - Analytics
