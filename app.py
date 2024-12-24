from flask import Flask, render_template, jsonify, request, send_file, abort, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import re
from config import Config
from mutagen import File as MutagenFile
import json
from datetime import datetime
import random

app = Flask(__name__, static_folder='static')
CORS(app)
app.config.from_object(Config)

# Ensure static files are served correctly
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

def get_db():
    """Get database connection."""
    try:
        # Create instance directory if it doesn't exist
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
        
        # Check if database exists, if not initialize it
        db_exists = os.path.exists(Config.DATABASE_PATH)
        
        print(f"Connecting to database at: {Config.DATABASE_PATH}")
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        
        # Initialize database if it doesn't exist
        if not db_exists:
            print("Database doesn't exist, initializing...")
            init_db()
            print("Database initialized successfully")
        
        # Test the connection
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Available tables:", [table[0] for table in tables])
        return db
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise

def get_playlist_state():
    """Get current playlist state from database."""
    db = get_db()
    state = db.execute('SELECT * FROM playlist_state ORDER BY id DESC LIMIT 1').fetchone()
    if state:
        return {
            'current_playlist': state['playlist_id'],
            'current_position': state['current_position'],
            'last_ad_position': state['last_ad_position'],
            'is_repeat': bool(state['is_repeat']),
            'is_shuffle': bool(state['is_shuffle']),
            'shuffle_queue': json.loads(state['shuffle_queue']) if state['shuffle_queue'] else []
        }
    return {
        'current_playlist': None,
        'current_position': 0,
        'last_ad_position': 0,
        'is_repeat': True,
        'is_shuffle': False,
        'shuffle_queue': []
    }

def save_playlist_state(state):
    """Save current playlist state to database."""
    db = get_db()
    db.execute('''
        INSERT INTO playlist_state 
        (playlist_id, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [
        state['current_playlist'],
        state['current_position'],
        state['last_ad_position'],
        state['is_repeat'],
        state['is_shuffle'],
        json.dumps(state['shuffle_queue'])
    ])
    db.commit()

def init_db():
    """Initialize the database with required tables."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

# Initialize global state
current_playlist = None
current_position = 0
last_ad_position = 0
is_repeat = True
is_shuffle = False
shuffle_queue = []

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    init_db()
    print('Initialized the database.')

@app.cli.command('scan-media')
def scan_media_command():
    """Scan configured directories for media files."""
    print("Starting media scan...")
    db = get_db()
    total_files = 0
    
    for media_dir in Config.MEDIA_DIRS:
        abs_media_dir = os.path.abspath(media_dir)
        print(f"\nScanning directory: {abs_media_dir}")
        print(f"Directory exists: {os.path.exists(abs_media_dir)}")
        
        if not os.path.exists(abs_media_dir):
            os.makedirs(abs_media_dir)
            print(f"Created media directory: {abs_media_dir}")
            continue
        
        try:
            # List all files in the directory
            files = os.listdir(abs_media_dir)
            print(f"Found {len(files)} files in directory:")
            for f in files:
                print(f"  - {f}")
            
            # Process each file
            for file in files:
                print(f"\nProcessing file: {file}")
                ext = file.split('.')[-1].lower() if '.' in file else ''
                print(f"File extension: {ext}")
                
                if ext in Config.AUDIO_EXTENSIONS:
                    media_type = 'audio'
                    print("File type: audio")
                elif ext in Config.VIDEO_EXTENSIONS:
                    media_type = 'video'
                    print("File type: video")
                else:
                    print(f"Skipping unsupported file type: {ext}")
                    continue
                
                full_path = os.path.abspath(os.path.join(abs_media_dir, file))
                print(f"Full path: {full_path}")
                print(f"File exists: {os.path.exists(full_path)}")
                print(f"File is readable: {os.access(full_path, os.R_OK)}")
                
                try:
                    media_file = MutagenFile(full_path)
                    if media_file and hasattr(media_file, 'tags') and media_file.tags:
                        title = str(media_file.tags.get('title', [file])[0])
                        artist = str(media_file.tags.get('artist', ['Unknown Artist'])[0])
                        print(f"Found metadata - Title: {title}, Artist: {artist}")
                    else:
                        title = os.path.splitext(file)[0]
                        artist = 'TapForNerd'
                        print("No metadata found, using filename as title")
                except Exception as e:
                    print(f"Error reading metadata: {str(e)}")
                    title = os.path.splitext(file)[0]
                    artist = 'TapForNerd'
                
                print(f"Adding to database: {title} by {artist}")
                db.execute('''
                    INSERT OR REPLACE INTO media (file_path, type, title, artist)
                    VALUES (?, ?, ?, ?)
                ''', (full_path, media_type, title, artist))
                total_files += 1
                
        except Exception as e:
            print(f"Error scanning directory {abs_media_dir}: {str(e)}")
            continue
    
    db.commit()
    print(f"\nMedia scan complete. Added {total_files} files to database.")

def pick_weighted_ad():
    """Pick an ad based on weights."""
    db = get_db()
    ads = db.execute('SELECT * FROM ads WHERE active = 1').fetchall()
    if not ads:
        return None
    
    total_weight = sum(ad['weight'] for ad in ads)
    r = random.uniform(0, total_weight)
    current_weight = 0
    
    for ad in ads:
        current_weight += ad['weight']
        if r <= current_weight:
            media = db.execute('SELECT * FROM media WHERE id = ?', [ad['media_id']]).fetchone()
            return dict(media)
    
    return None

@app.route('/')
def index():
    """Admin interface."""
    return render_template('admin.html')

@app.route('/display')
def display():
    """Display interface for OBS."""
    return render_template('display.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    uploaded = []
    errors = []

    for file in files:
        if file.filename:
            ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if ext not in Config.AUDIO_EXTENSIONS and ext not in Config.VIDEO_EXTENSIONS:
                errors.append(f'Unsupported file type: {file.filename}')
                continue

            try:
                # Save file
                filename = os.path.basename(file.filename)
                save_path = os.path.join(Config.MEDIA_DIRS[0], filename)
                file.save(save_path)
                uploaded.append(filename)
            except Exception as e:
                errors.append(f'Error saving {file.filename}: {str(e)}')

    return jsonify({
        'message': 'Upload complete',
        'uploaded': uploaded,
        'errors': errors
    })

@app.route('/api/scan-media', methods=['POST'])
def scan_media():
    """API endpoint to trigger media scan."""
    found_files = []
    errors = []
    try:
        print("Starting media scan...")
        db = get_db()
        
        # First, verify the media directories exist
        for media_dir in Config.MEDIA_DIRS:
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
                print(f"Created media directory: {media_dir}")
                continue
            
            # Get list of files
            files = os.listdir(media_dir)
            print(f"Found {len(files)} files in {media_dir}")
            
            for file in files:
                try:
                    print(f"Processing file: {file}")
                    # Check file extension
                    ext = file.split('.')[-1].lower() if '.' in file else ''
                    print(f"File extension: {ext}")
                    
                    if ext not in Config.AUDIO_EXTENSIONS and ext not in Config.VIDEO_EXTENSIONS:
                        print(f"Skipping file with unsupported extension: {ext}")
                        continue
                    
                    media_type = 'audio' if ext in Config.AUDIO_EXTENSIONS else 'video'
                    full_path = os.path.abspath(os.path.join(media_dir, file))
                    
                    if not os.path.isfile(full_path):
                        print(f"Not a file: {full_path}")
                        continue
                    
                    print(f"Processing media file: {full_path}")
                    try:
                        media_file = MutagenFile(full_path)
                        if media_file and hasattr(media_file, 'tags') and media_file.tags:
                            title = str(media_file.tags.get('title', [file])[0])
                            artist = str(media_file.tags.get('artist', ['Unknown Artist'])[0])
                        else:
                            title = os.path.splitext(file)[0]
                            artist = 'TapForNerd'
                    except Exception as e:
                        print(f"Error reading metadata for {file}: {str(e)}")
                        title = os.path.splitext(file)[0]
                        artist = 'TapForNerd'
                    
                    print(f"Adding to database: {title} by {artist}")
                        
                    # Add to database
                    db.execute('''
                        INSERT OR REPLACE INTO media (file_path, type, title, artist)
                        VALUES (?, ?, ?, ?)
                    ''', (full_path, media_type, title, artist))
                    
                    found_files.append({
                        'path': full_path,
                        'type': media_type,
                        'title': title,
                        'artist': artist
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing {file}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
        
        db.commit()
        response = {
            'message': 'Media scan completed',
            'files_found': len(found_files),
            'files': found_files
        }
        if errors:
            response['errors'] = errors
        return jsonify(response)
        
    except Exception as e:
        error_msg = f"Error during media scan: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg,
            'files_found': len(found_files),
            'files': found_files,
            'errors': errors
        }), 500

@app.route('/api/media')
def get_media():
    """Get all media files."""
    db = get_db()
    media = db.execute('SELECT * FROM media').fetchall()
    result = [dict(row) for row in media]
    print(f"Found {len(result)} media files in database")
    for item in result:
        print(f"Media item: {item['title']} ({item['type']}) - {item['file_path']}")
    return jsonify(result)

@app.route('/api/playlists')
def get_playlists():
    """Get all playlists."""
    db = get_db()
    playlists = db.execute('SELECT * FROM playlists').fetchall()
    return jsonify([dict(row) for row in playlists])

@app.route('/api/playlist/<int:playlist_id>')
def get_playlist(playlist_id):
    """Get a specific playlist with its items."""
    db = get_db()
    playlist = db.execute('SELECT * FROM playlists WHERE id = ?', [playlist_id]).fetchone()
    if not playlist:
        return jsonify({'error': 'Playlist not found'}), 404
    
    items = db.execute('''
        SELECT pi.*, m.* 
        FROM playlist_items pi 
        JOIN media m ON pi.media_id = m.id 
        WHERE pi.playlist_id = ? 
        ORDER BY pi.order_position
    ''', [playlist_id]).fetchall()
    
    return jsonify({
        'playlist': dict(playlist),
        'items': [dict(item) for item in items]
    })

@app.route('/api/now-playing')
def now_playing():
    """Get currently playing media info."""
    global current_playlist, current_position
    
    print(f"Current playlist: {current_playlist}, position: {current_position}")
    
    if not current_playlist:
        return jsonify({'error': 'No playlist active'}), 404
    
    db = get_db()
    try:
        playlist_items = db.execute('''
            SELECT m.* 
            FROM playlist_items pi 
            JOIN media m ON pi.media_id = m.id 
            WHERE pi.playlist_id = ? 
            ORDER BY pi.order_position
        ''', [current_playlist]).fetchall()
        
        print(f"Found {len(playlist_items) if playlist_items else 0} items in playlist")
        
        if not playlist_items or current_position >= len(playlist_items):
            return jsonify({'error': 'No media playing'}), 404
        
        current_media = dict(playlist_items[current_position])
        print(f"Current media: {current_media}")
        return jsonify(current_media)
    except Exception as e:
        print(f"Error in now_playing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscribers', methods=['GET', 'POST'])
def subscribers():
    """Handle subscriber operations."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        display_text = data.get('display_text')
        
        if not username:
            return jsonify({'error': 'Username is required'}), 400
            
        cursor = db.execute(
            'INSERT INTO subscribers (username, display_text) VALUES (?, ?)',
            [username, display_text]
        )
        db.commit()
        
        return jsonify({
            'id': cursor.lastrowid,
            'username': username,
            'display_text': display_text
        })
    
    # GET request
    subscribers = db.execute('SELECT * FROM subscribers WHERE active = 1').fetchall()
    return jsonify([dict(row) for row in subscribers])

@app.route('/api/play', methods=['POST'])
def play_playlist():
    """Start playing a playlist."""
    global current_playlist, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue
    
    data = request.get_json()
    playlist_id = data.get('playlist_id')
    
    print(f"Received request to play playlist {playlist_id}")
    
    if not playlist_id:
        return jsonify({'error': 'Playlist ID required'}), 400
    
    db = get_db()
    playlist = db.execute('SELECT * FROM playlists WHERE id = ?', [playlist_id]).fetchone()
    if not playlist:
        return jsonify({'error': 'Playlist not found'}), 404
    
    # Always start fresh when playing a playlist
    current_playlist = int(playlist_id)
    current_position = 0
    last_ad_position = 0
    is_repeat = True  # Always enable repeat by default
    is_shuffle = False  # Start with shuffle off
    shuffle_queue = []
    
    save_playlist_state({
        'current_playlist': current_playlist,
        'current_position': current_position,
        'last_ad_position': last_ad_position,
        'is_repeat': is_repeat,
        'is_shuffle': is_shuffle,
        'shuffle_queue': shuffle_queue
    })
    
    print(f"Started playlist {current_playlist} at position {current_position}")
    
    # Get the first track info to return
    playlist_items = db.execute('''
        SELECT m.* 
        FROM playlist_items pi 
        JOIN media m ON pi.media_id = m.id 
        WHERE pi.playlist_id = ? 
        ORDER BY pi.order_position
    ''', [current_playlist]).fetchall()
    
    if not playlist_items:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    current_track = dict(playlist_items[current_position])
    return jsonify(current_track)

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    """Create a new playlist."""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    
    if not name:
        return jsonify({'error': 'Playlist name is required'}), 400
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO playlists (name, description) VALUES (?, ?)',
        [name, description]
    )
    playlist_id = cursor.lastrowid
    db.commit()
    
    return jsonify({
        'id': playlist_id,
        'name': name,
        'description': description
    })

@app.route('/api/playlist/<int:playlist_id>/items', methods=['POST'])
def add_playlist_item(playlist_id):
    """Add an item to a playlist."""
    data = request.get_json()
    media_id = data.get('media_id')
    
    if not media_id:
        return jsonify({'error': 'Media ID is required'}), 400
    
    db = get_db()
    # Get the highest order position
    max_order = db.execute(
        'SELECT MAX(order_position) as max_order FROM playlist_items WHERE playlist_id = ?',
        [playlist_id]
    ).fetchone()
    next_order = (max_order['max_order'] or -1) + 1
    
    cursor = db.execute(
        'INSERT INTO playlist_items (playlist_id, media_id, order_position) VALUES (?, ?, ?)',
        [playlist_id, media_id, next_order]
    )
    db.commit()
    
    return jsonify({
        'id': cursor.lastrowid,
        'playlist_id': playlist_id,
        'media_id': media_id,
        'order_position': next_order
    })

@app.route('/api/playlist/<int:playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    """Delete a playlist."""
    db = get_db()
    db.execute('DELETE FROM playlists WHERE id = ?', [playlist_id])
    db.commit()
    return jsonify({'message': 'Playlist deleted'})

@app.route('/api/playlist/<int:playlist_id>/items/<int:item_id>', methods=['DELETE'])
def delete_playlist_item(playlist_id, item_id):
    """Delete an item from a playlist."""
    db = get_db()
    db.execute('DELETE FROM playlist_items WHERE playlist_id = ? AND id = ?', [playlist_id, item_id])
    db.commit()
    return jsonify({'message': 'Item deleted'})

@app.route('/api/playlist/<int:playlist_id>/order', methods=['PUT'])
def update_playlist_order(playlist_id):
    """Update the order of items in a playlist."""
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': 'Items array is required'}), 400
    
    db = get_db()
    for item in items:
        db.execute(
            'UPDATE playlist_items SET order_position = ? WHERE id = ? AND playlist_id = ?',
            [item['order_position'], item['id'], playlist_id]
        )
    db.commit()
    
    return jsonify({'message': 'Playlist order updated'})

@app.route('/api/next', methods=['POST'])
def next_track():
    """Move to next track in playlist."""
    global current_position, last_ad_position, shuffle_queue
    
    if not current_playlist:
        return jsonify({'error': 'No playlist active'}), 404
    
    db = get_db()
    playlist_items = db.execute('''
        SELECT m.* 
        FROM playlist_items pi 
        JOIN media m ON pi.media_id = m.id 
        WHERE pi.playlist_id = ? 
        ORDER BY pi.order_position
    ''', [current_playlist]).fetchall()
    
    if not playlist_items:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    # Check if we should play an ad
    if current_position - last_ad_position >= 3:  # Play ad every 3 tracks
        ad = pick_weighted_ad()
        if ad:
            last_ad_position = current_position
            return jsonify({'type': 'ad', **ad})
    
    total_tracks = len(playlist_items)
    
    if is_shuffle:
        if not shuffle_queue:
            # Generate new shuffle queue when empty
            shuffle_queue = list(range(total_tracks))
            random.shuffle(shuffle_queue)
            current_position = shuffle_queue.pop(0)
        else:
            if shuffle_queue:
                current_position = shuffle_queue.pop(0)
            elif is_repeat:
                # Regenerate shuffle queue if repeat is on
                shuffle_queue = list(range(total_tracks))
                random.shuffle(shuffle_queue)
                current_position = shuffle_queue.pop(0)
            else:
                # If not repeating and no more tracks, return error
                return jsonify({'error': 'End of playlist'}), 404
    else:
        # Save current position before incrementing
        current_position = (current_position + 1) % total_tracks if is_repeat else current_position + 1
        if current_position >= total_tracks:
            return jsonify({'error': 'End of playlist'}), 404
    
    # Return the current track information
    if 0 <= current_position < len(playlist_items):
        current_track = dict(playlist_items[current_position])
        # Save state after track change
        save_playlist_state({
            'current_playlist': current_playlist,
            'current_position': current_position,
            'last_ad_position': last_ad_position,
            'is_repeat': is_repeat,
            'is_shuffle': is_shuffle,
            'shuffle_queue': shuffle_queue
        })
        return jsonify(current_track)
    return jsonify({'error': 'No media playing'}), 404

@app.route('/api/save-state', methods=['POST'])
def save_state():
    """Save current playlist state."""
    global current_playlist, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue
    save_playlist_state({
        'current_playlist': current_playlist,
        'current_position': current_position,
        'last_ad_position': last_ad_position,
        'is_repeat': is_repeat,
        'is_shuffle': is_shuffle,
        'shuffle_queue': shuffle_queue
    })
    return jsonify({'message': 'Playlist state saved'})

@app.route('/api/toggle-repeat', methods=['POST'])
def toggle_repeat():
    """Toggle repeat mode."""
    global is_repeat, current_playlist, current_position, last_ad_position, is_shuffle, shuffle_queue
    is_repeat = not is_repeat
    # Save state after toggling repeat
    save_playlist_state({
        'current_playlist': current_playlist,
        'current_position': current_position,
        'last_ad_position': last_ad_position,
        'is_repeat': is_repeat,
        'is_shuffle': is_shuffle,
        'shuffle_queue': shuffle_queue
    })
    return jsonify({'repeat': is_repeat})

@app.route('/api/toggle-shuffle', methods=['POST'])
def toggle_shuffle():
    """Toggle shuffle mode."""
    global is_shuffle, shuffle_queue, current_playlist, current_position, last_ad_position, is_repeat
    is_shuffle = not is_shuffle
    shuffle_queue = []  # Reset shuffle queue when toggling
    # Save state after toggling shuffle
    save_playlist_state({
        'current_playlist': current_playlist,
        'current_position': current_position,
        'last_ad_position': last_ad_position,
        'is_repeat': is_repeat,
        'is_shuffle': is_shuffle,
        'shuffle_queue': shuffle_queue
    })
    return jsonify({'shuffle': is_shuffle})

@app.route('/api/next-track')
def get_next_track():
    """Get information about the next track in the playlist."""
    if not current_playlist:
        return jsonify({'error': 'No playlist active'}), 404
    
    db = get_db()
    playlist_items = db.execute('''
        SELECT m.* 
        FROM playlist_items pi 
        JOIN media m ON pi.media_id = m.id 
        WHERE pi.playlist_id = ? 
        ORDER BY pi.order_position
    ''', [current_playlist]).fetchall()
    
    if not playlist_items:
        return jsonify({'error': 'Playlist is empty'}), 404
    
    total_tracks = len(playlist_items)
    next_position = 0
    
    if is_shuffle:
        if shuffle_queue:
            next_position = shuffle_queue[0]
        elif is_repeat:
            # If shuffle queue is empty but repeat is on, next would be first track of new shuffle
            next_position = 0
        else:
            return jsonify({'error': 'End of playlist'}), 404
    else:
        next_position = (current_position + 1) % total_tracks if is_repeat else current_position + 1
        if next_position >= total_tracks:
            return jsonify({'error': 'End of playlist'}), 404
    
    if 0 <= next_position < len(playlist_items):
        next_track = dict(playlist_items[next_position])
        return jsonify(next_track)
    
    return jsonify({'error': 'No next track available'}), 404

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files directly."""
    try:
        # First try to find the media in the database
        db = get_db()
        media = db.execute('SELECT * FROM media WHERE file_path LIKE ?', ['%' + filename]).fetchone()
        
        if media:
            file_path = media['file_path']
            print(f"Found file in database: {file_path}")
        else:
            # Try to find in media directories
            for media_dir in Config.MEDIA_DIRS:
                possible_path = os.path.join(media_dir, filename)
                if os.path.exists(possible_path):
                    file_path = possible_path
                    print(f"Found file in media dir: {file_path}")
                    break
            else:
                print(f"File not found: {filename}")
                abort(404)
        
        if not os.path.exists(file_path):
            print(f"File not found at path: {file_path}")
            abort(404)

        # Determine mimetype based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        mimetypes = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac'
        }
        mimetype = mimetypes.get(ext, 'audio/mpeg')

        # Send entire file directly
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=None,
            conditional=False,
            etag=False
        )

    except Exception as e:
        print(f"Error serving media: {str(e)}")
        abort(404)

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT)
