from flask import Blueprint, jsonify, request
from app.core.database import get_db, get_playlist_state, save_playlist_state
import random

playlist_api = Blueprint('playlist_api', __name__)

# Global state variables
current_playlist = None
current_position = 0
last_ad_position = 0
is_repeat = True
is_shuffle = False
shuffle_queue = []

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

@playlist_api.route('/playlists')
def get_playlists():
    """Get all playlists."""
    db = get_db()
    playlists = db.execute('SELECT * FROM playlists').fetchall()
    return jsonify([dict(row) for row in playlists])

@playlist_api.route('/playlist/<int:playlist_id>')
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

@playlist_api.route('/now-playing')
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

@playlist_api.route('/play', methods=['POST'])
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
        save_playlist_state({
            'current_playlist': current_playlist,
            'current_position': current_position,
            'last_ad_position': last_ad_position,
            'is_repeat': is_repeat,
            'is_shuffle': is_shuffle,
            'shuffle_queue': shuffle_queue
        })
        
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

@playlist_api.route('/playlists', methods=['POST'])
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

@playlist_api.route('/playlist/<int:playlist_id>/items', methods=['POST'])
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

@playlist_api.route('/playlist/<int:playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    """Delete a playlist."""
    db = get_db()
    db.execute('DELETE FROM playlists WHERE id = ?', [playlist_id])
    db.commit()
    return jsonify({'message': 'Playlist deleted'})

@playlist_api.route('/playlist/<int:playlist_id>/items/<int:item_id>', methods=['DELETE'])
def delete_playlist_item(playlist_id, item_id):
    """Delete an item from a playlist."""
    db = get_db()
    db.execute('DELETE FROM playlist_items WHERE playlist_id = ? AND id = ?', [playlist_id, item_id])
    db.commit()
    return jsonify({'message': 'Item deleted'})

@playlist_api.route('/playlist/<int:playlist_id>/order', methods=['PUT'])
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

@playlist_api.route('/next', methods=['POST'])
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

@playlist_api.route('/save-state', methods=['POST'])
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

@playlist_api.route('/toggle-repeat', methods=['POST'])
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

@playlist_api.route('/toggle-shuffle', methods=['POST'])
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

@playlist_api.route('/next-track')
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
