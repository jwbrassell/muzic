from flask import Flask, render_template, jsonify, request, send_file, abort, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import re
import hashlib
from app.core.config import get_settings
from mutagen import File as MutagenFile
import json
from datetime import datetime
import random
from app.api.media import media_api
from app.admin import admin

def calculate_file_checksum(file_path):
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_filename(filename):
    """Clean filename to remove weird characters while preserving spaces."""
    # Remove file extension
    base = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    
    # Remove leading underscores from base name
    base = base.lstrip('_')
    
    # Keep alphanumeric, spaces, and common special characters
    cleaned = re.sub(r'[^\w\-\. ]', '', base)
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip('. ')
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return (cleaned if cleaned else 'unnamed') + ext

def clean_filepath(filepath):
    """Clean filepath to ensure consistent paths for comparison."""
    # Split path into directory and filename
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    
    # Clean the filename
    clean_name = clean_filename(filename)
    
    # Join back together
    return os.path.join(directory, clean_name)

def file_exists_by_checksum(db, checksum, clean_path):
    """Check if a file with the same checksum or cleaned path exists in the database."""
    cursor = db.execute('SELECT id FROM media WHERE checksum = ? OR file_path = ?', [checksum, clean_path])
    return cursor.fetchone() is not None

app = Flask(__name__, static_folder='static')
CORS(app)
settings = get_settings()
app.config.from_mapping(
    DATABASE_PATH=settings.DATABASE_PATH,
    MEDIA_DIRS=settings.MEDIA_DIRS,
    AUDIO_EXTENSIONS=settings.AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS=settings.VIDEO_EXTENSIONS,
    HOST=settings.HOST,
    PORT=settings.PORT
)

# Register blueprints
app.register_blueprint(media_api, url_prefix='/api/v1/media')
app.register_blueprint(admin, url_prefix='/admin')

# Ensure static files are served correctly
@app.route('/static/<path:path>')
def send_static(path):
    try:
        return send_from_directory('static', path)
    except Exception as e:
        print(f"Error serving static file {path}: {str(e)}")
        abort(404)

def get_db():
    """Get database connection."""
    try:
        # Create instance directory if it doesn't exist
        os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
        
        # Check if database exists, if not initialize it
        db_exists = os.path.exists(settings.DATABASE_PATH)
        
        print(f"Connecting to database at: {settings.DATABASE_PATH}")
        db = sqlite3.connect(settings.DATABASE_PATH)
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
    
    # Add checksum column if it doesn't exist
    try:
        db.execute('ALTER TABLE media ADD COLUMN checksum TEXT')
        print("Added checksum column to media table")
    except sqlite3.OperationalError:
        print("Checksum column already exists")
    
    db.commit()

# Initialize global state from database
def init_global_state():
    global current_playlist, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue
    try:
        db = get_db()
        state = db.execute('SELECT * FROM playlist_state ORDER BY id DESC LIMIT 1').fetchone()
        if state:
            current_playlist = state['playlist_id']
            current_position = state['current_position']
            last_ad_position = state['last_ad_position']
            is_repeat = bool(state['is_repeat'])
            is_shuffle = bool(state['is_shuffle'])
            shuffle_queue = json.loads(state['shuffle_queue']) if state['shuffle_queue'] else []
            print(f"Loaded playlist state: playlist={current_playlist}, position={current_position}")
        else:
            current_playlist = None
            current_position = 0
            last_ad_position = 0
            is_repeat = True
            is_shuffle = False
            shuffle_queue = []
            print("No saved playlist state found, using defaults")
    except Exception as e:
        print(f"Error loading playlist state: {str(e)}")
        current_playlist = None
        current_position = 0
        last_ad_position = 0
        is_repeat = True
        is_shuffle = False
        shuffle_queue = []

# Initialize state when app starts
init_global_state()

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    init_db()
    print('Initialized the database.')

@app.cli.command('scan-media')
def scan_media_command():
    """Scan configured directories for media files."""
    print("Starting media scan...")
    db = get_db()
    total_files = 0
    
    try:
        # Start transaction
        db.execute('BEGIN')
        
        for media_dir in settings.MEDIA_DIRS:
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
                    
                    # Skip macOS metadata files
                    if file.startswith('._'):
                        print(f"Skipping macOS metadata file: {file}")
                        continue
                    
                    ext = file.split('.')[-1].lower() if '.' in file else ''
                    print(f"File extension: {ext}")
                    
                    if ext not in settings.AUDIO_EXTENSIONS and ext not in settings.VIDEO_EXTENSIONS:
                        print(f"Skipping unsupported file type: {ext}")
                        continue
                    
                    media_type = 'audio' if ext in settings.AUDIO_EXTENSIONS else 'video'
                    full_path = os.path.abspath(os.path.join(abs_media_dir, file))
                    
                    if not os.path.isfile(full_path):
                        print(f"Not a file: {full_path}")
                        continue
                    
                    # Clean the filepath and get clean filename
                    clean_path = clean_filepath(full_path)
                    clean_name = clean_filename(file)
                    
                    # Calculate checksum
                    checksum = calculate_file_checksum(full_path)
                    
                    # Check if file already exists by checksum or cleaned path
                    if file_exists_by_checksum(db, checksum, clean_path):
                        print(f"Skipping duplicate file: {file}")
                        continue
                    
                    # Use clean filename as title
                    title = os.path.splitext(clean_name)[0]
                    artist = 'TapForNerd'  # Always set artist as TapForNerd
                    
                    print(f"Adding to database: {title} by {artist}")
                    
                    # Add to database with checksum and clean path
                    cursor = db.execute('''
                        INSERT OR REPLACE INTO media (file_path, type, title, artist, checksum)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (clean_path, media_type, title, artist, checksum))
                    
                    if cursor.rowcount > 0:
                        total_files += 1
                    else:
                        print(f"Failed to insert {file} into database")
                    
            except Exception as e:
                print(f"Error scanning directory {abs_media_dir}: {str(e)}")
                continue
        
        # Commit transaction if we got here
        db.commit()
        print(f"\nMedia scan complete. Added {total_files} files to database.")
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error during scan: {str(e)}")

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
    playlist_id = request.args.get('playlist')
    if playlist_id:
        return render_template('admin.html', playlist_id=playlist_id)
    return render_template('admin.html')

@app.route('/library')
def media_library():
    """Media library management interface."""
    return render_template('media_library.html')

@app.route('/display')
def display():
    """Display interface for OBS."""
    return render_template('display.html')

@app.route('/media-display')
def media_display():
    """Media display interface that supports both audio and video playback."""
    return render_template('media_display.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    paths = request.form.getlist('paths')  # Get the relative paths
    uploaded = []
    errors = []
    db = get_db()
    
    try:
        # Start transaction
        db.execute('BEGIN')
        
        for file, path in zip(files, paths):
            if not file.filename:
                continue
                
            # Skip macOS metadata files
            if os.path.basename(path).startswith('._'):
                print(f"Skipping macOS metadata file: {path}")
                continue
                
            ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            if ext not in settings.AUDIO_EXTENSIONS and ext not in settings.VIDEO_EXTENSIONS:
                errors.append(f'Unsupported file type: {file.filename}')
                continue

            try:
                # Determine media type
                media_type = 'audio' if ext in settings.AUDIO_EXTENSIONS else 'video'
                
                # Create directory structure matching the source
                dir_path = os.path.dirname(path)
                if dir_path:
                    save_dir = os.path.join(settings.MEDIA_DIRS[0], dir_path)
                else:
                    save_dir = os.path.join(settings.MEDIA_DIRS[0], media_type)
                os.makedirs(save_dir, exist_ok=True)
                
                # Clean and use original filename
                filename = clean_filename(os.path.basename(path))
                save_path = os.path.join(save_dir, filename)
                
                # Save the file
                file.save(save_path)
                
                # Clean the filepath and get clean filename
                clean_path = clean_filepath(save_path)
                
                # Calculate checksum
                checksum = calculate_file_checksum(save_path)
                
                # Check if file already exists by checksum or cleaned path
                if file_exists_by_checksum(db, checksum, clean_path):
                    os.remove(save_path)  # Remove the duplicate file
                    print(f"Skipping duplicate file: {filename}")
                    continue
                
                # Use clean filename as title, TapForNerd as artist
                title = os.path.splitext(filename)[0]
                artist = 'TapForNerd'
                
                # Add to database with checksum and clean path
                cursor = db.execute('''
                    INSERT OR REPLACE INTO media (file_path, type, title, artist, checksum)
                    VALUES (?, ?, ?, ?, ?)
                ''', (clean_path, media_type, title, artist, checksum))
                
                if cursor.rowcount > 0:
                    uploaded.append(filename)
                else:
                    errors.append(f'Failed to insert {filename} into database')
                    
            except Exception as e:
                errors.append(f'Error processing {file.filename}: {str(e)}')
                continue
        
        # Commit transaction if we got here
        db.commit()
        print(f"Successfully uploaded and processed {len(uploaded)} files")
        
        return jsonify({
            'message': 'Upload complete',
            'uploaded': uploaded,
            'errors': errors
        })
        
    except Exception as e:
        if db:
            db.rollback()
        error_msg = f"Error during upload: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg,
            'uploaded': uploaded,
            'errors': errors
        }), 500

def scan_directory(media_dir, db, found_files, errors):
    """Recursively scan a directory for media files."""
    try:
        # Walk through directory recursively
        for root, dirs, files in os.walk(media_dir):
            print(f"Scanning directory: {root}")
            print(f"Found {len(files)} files")
            
            for file in files:
                try:
                    print(f"Processing file: {file}")
                    # Skip macOS metadata files
                    if file.startswith('._'):
                        print(f"Skipping macOS metadata file: {file}")
                        continue
                        
                    # Check file extension
                    ext = file.split('.')[-1].lower() if '.' in file else ''
                    print(f"File extension: {ext}")
                    
                    if ext not in settings.AUDIO_EXTENSIONS and ext not in settings.VIDEO_EXTENSIONS:
                        print(f"Skipping file with unsupported extension: {ext}")
                        continue
                    
                    media_type = 'audio' if ext in settings.AUDIO_EXTENSIONS else 'video'
                    full_path = os.path.abspath(os.path.join(root, file))
                    
                    if not os.path.isfile(full_path):
                        print(f"Not a file: {full_path}")
                        continue
                    
                    # Clean the filepath and get clean filename
                    clean_path = clean_filepath(full_path)
                    clean_name = clean_filename(file)
                    
                    # Calculate checksum
                    checksum = calculate_file_checksum(full_path)
                    
                    # Check if file already exists by checksum or cleaned path
                    if file_exists_by_checksum(db, checksum, clean_path):
                        print(f"Skipping duplicate file: {file}")
                        continue
                    
                    print(f"Processing media file: {full_path}")
                    
                    # Use clean filename as title
                    title = os.path.splitext(clean_name)[0]
                    artist = 'TapForNerd'  # Always set artist as TapForNerd
                    
                    print(f"Adding to database: {title} by {artist}")
                        
                    # Add to database with checksum and clean path
                    cursor = db.execute('''
                        INSERT OR REPLACE INTO media (file_path, type, title, artist, checksum)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (clean_path, media_type, title, artist, checksum))
                    
                    # Verify the insert was successful
                    if cursor.rowcount > 0:
                        found_files.append({
                            'path': full_path,
                            'type': media_type,
                            'title': title,
                            'artist': artist
                        })
                    else:
                        error_msg = f"Failed to insert {file} into database"
                        print(error_msg)
                        errors.append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error processing {file}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
                    
    except Exception as e:
        error_msg = f"Error scanning directory {media_dir}: {str(e)}"
        print(error_msg)
        errors.append(error_msg)

@app.route('/api/purge-library', methods=['POST'])
def purge_library():
    """Delete all entries from the media library."""
    db = get_db()
    try:
        # Start transaction
        db.execute('BEGIN')
        
        # Delete all media entries
        db.execute('DELETE FROM media')
        
        # Commit transaction
        db.commit()
        print("Successfully purged all entries from media library")
        
        return jsonify({
            'message': 'Media library purged successfully'
        })
        
    except Exception as e:
        if db:
            db.rollback()
        error_msg = f"Error purging library: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg
        }), 500

@app.route('/api/scan-media', methods=['POST'])
def scan_media():
    """API endpoint to trigger media scan."""
    found_files = []
    errors = []
    db = None
    try:
        print("Starting media scan...")
        db = get_db()
        
        # Start transaction
        db.execute('BEGIN')
        
        # First, verify the media directories exist
            for media_dir in settings.MEDIA_DIRS:
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
                print(f"Created media directory: {media_dir}")
                continue
            
            # Recursively scan the directory
            scan_directory(media_dir, db, found_files, errors)
        
        # If we got here without errors, commit the transaction
        db.commit()
        print("Successfully committed all changes to database")
        
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
        if db:
            db.rollback()
            print("Rolled back database changes due to error")
        return jsonify({
            'error': error_msg,
            'files_found': len(found_files),
            'files': found_files,
            'errors': errors
        }), 500

@app.route('/api/tags', methods=['GET', 'POST'])
def handle_tags():
    """Get all tags or create a new tag."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Tag name is required'}), 400
            
        try:
            cursor = db.execute('INSERT INTO tags (name) VALUES (?)', [name])
            db.commit()
            return jsonify({
                'id': cursor.lastrowid,
                'name': name
            })
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Tag already exists'}), 409
    
    # GET request
    tags = db.execute('SELECT * FROM tags').fetchall()
    return jsonify([dict(row) for row in tags])

@app.route('/api/media/<int:media_id>/tags', methods=['GET', 'POST'])
def handle_media_tags(media_id):
    """Get or add tags for a media item."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        tag_names = data.get('tags', [])
        
        if not tag_names:
            return jsonify({'error': 'Tags are required'}), 400
            
        added_tags = []
        for tag_name in tag_names:
            # First try to get existing tag
            tag = db.execute('SELECT * FROM tags WHERE name = ?', [tag_name]).fetchone()
            
            # Create tag if it doesn't exist
            if not tag:
                cursor = db.execute('INSERT INTO tags (name) VALUES (?)', [tag_name])
                tag_id = cursor.lastrowid
            else:
                tag_id = tag['id']
                
            # Add tag to media if not already added
            try:
                db.execute('INSERT INTO media_tags (media_id, tag_id) VALUES (?, ?)',
                          [media_id, tag_id])
                added_tags.append({'id': tag_id, 'name': tag_name})
            except sqlite3.IntegrityError:
                # Tag already exists for this media, skip it
                continue
                
        db.commit()
        return jsonify(added_tags)
    
    # GET request
    tags = db.execute('''
        SELECT t.* FROM tags t
        JOIN media_tags mt ON t.id = mt.tag_id
        WHERE mt.media_id = ?
    ''', [media_id]).fetchall()
    return jsonify([dict(row) for row in tags])

@app.route('/api/media/<int:media_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_media_tag(media_id, tag_id):
    """Remove a tag from a media item."""
    db = get_db()
    db.execute('DELETE FROM media_tags WHERE media_id = ? AND tag_id = ?',
               [media_id, tag_id])
    db.commit()
    return jsonify({'message': 'Tag removed'})

@app.route('/api/media/by-tag/<int:tag_id>')
def get_media_by_tag(tag_id):
    """Get all media items with a specific tag."""
    db = get_db()
    media = db.execute('''
        SELECT m.* FROM media m
        JOIN media_tags mt ON m.id = mt.media_id
        WHERE mt.tag_id = ?
    ''', [tag_id]).fetchall()
    return jsonify([dict(row) for row in media])

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
    try:
        # Start transaction
        db.execute('BEGIN')
        
        playlist = db.execute('SELECT * FROM playlists WHERE id = ?', [playlist_id]).fetchone()
        if not playlist:
            return jsonify({'error': 'Playlist not found'}), 404
            
        # Get playlist items to verify it's not empty
        items = db.execute('''
            SELECT m.* 
            FROM playlist_items pi 
            JOIN media m ON pi.media_id = m.id 
            WHERE pi.playlist_id = ? 
            ORDER BY pi.order_position
        ''', [playlist_id]).fetchall()
        
        if not items:
            return jsonify({'error': 'Playlist is empty'}), 404
        
        # Start fresh when playing a playlist
        current_playlist = int(playlist_id)
        current_position = 0
        last_ad_position = 0
        is_repeat = True  # Always enable repeat by default
        is_shuffle = False  # Start with shuffle off
        shuffle_queue = []
        
        # Save state to database
        db.execute('DELETE FROM playlist_state')  # Clear old state
        db.execute('''
            INSERT INTO playlist_state 
            (playlist_id, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [current_playlist, current_position, last_ad_position, is_repeat, is_shuffle, json.dumps(shuffle_queue)])
        
        # Commit transaction
        db.commit()
        
        print(f"Started playlist {current_playlist} at position {current_position}")
        
        # Return the first track
        current_track = dict(items[0])
        return jsonify(current_track)
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"Error starting playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
            for media_dir in settings.MEDIA_DIRS:
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
            # Audio types
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac',
            # Video types
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska'
        }
        mimetype = mimetypes.get(ext, 'application/octet-stream')

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
    app.run(host=settings.HOST, port=settings.PORT)
