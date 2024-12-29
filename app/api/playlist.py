from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, current_app
import json

from ..core.config import get_settings
from ..core.logging import api_logger, log_function_call, log_error
from ..core.database import Database
from ..playlist.manager import PlaylistManager
from ..playlist.scheduler import AdScheduler

# Create Blueprint
playlist_api = Blueprint('playlist_api', __name__)

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
playlist_manager = PlaylistManager(db)
ad_scheduler = AdScheduler(db)

@playlist_api.route('/', methods=['GET'])
@log_function_call(api_logger)
def get_playlists():
    """Get list of all playlists."""
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')
        search = request.args.get('q', '')
        
        # Base query
        query = """
            SELECT 
                p.*,
                COUNT(pi.id) as track_count,
                SUM(COALESCE(m.duration, 0)) as duration,
                ps.is_repeat,
                ps.is_shuffle,
                MAX(ph.played_at) as last_played_at
            FROM playlists p
            LEFT JOIN playlist_items pi ON p.id = pi.playlist_id
            LEFT JOIN media m ON pi.media_id = m.id
            LEFT JOIN playlist_state ps ON p.id = ps.playlist_id
            LEFT JOIN playlist_history ph ON p.id = ph.playlist_id
            WHERE 1=1
        """
        params = []
        
        # Add filters
        if status:
            query += " AND p.status = ?"
            params.append(status)
        if search:
            query += " AND p.name LIKE ?"
            params.append(f"%{search}%")
            
        query += " GROUP BY p.id"
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) as sub"
        total = db.fetch_one(count_query, params)['COUNT(*)']
        
        # Add pagination
        per_page = 10
        offset = (page - 1) * per_page
        query += f" LIMIT {per_page} OFFSET {offset}"
        
        # Get paginated results
        playlists = db.fetch_all(query, params)
        
        return jsonify({
            'items': [dict(p) for p in playlists],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting playlists: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>', methods=['GET'])
@log_function_call(api_logger)
def get_playlist_details(playlist_id: int):
    """Get detailed information about a playlist."""
    try:
        # Get playlist info
        playlist = db.fetch_one(
            """
            SELECT 
                p.*,
                ps.current_position,
                ps.last_ad_position,
                ps.is_repeat,
                ps.is_shuffle
            FROM playlists p
            LEFT JOIN playlist_state ps ON p.id = ps.playlist_id
            WHERE p.id = ?
            """,
            (playlist_id,)
        )
        
        if not playlist:
            return jsonify({'error': 'Playlist not found'}), 404
        
        # Get items
        items = playlist_manager.get_playlist_items(playlist_id)
        
        # Get current item
        current_item = playlist_manager.get_current_item(playlist_id)
        
        return jsonify({
            **dict(playlist),
            'items': items,
            'current_item': current_item
        })

    except Exception as e:
        api_logger.error(f"Error getting playlist details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/', methods=['POST'])
@log_function_call(api_logger)
def create_playlist():
    """Create a new playlist."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        playlist_id = playlist_manager.create_playlist(
            name=data['name'],
            description=data.get('description')
        )
        
        if not playlist_id:
            return jsonify({'error': 'Failed to create playlist'}), 500
        
        # Add items if provided
        if 'items' in data:
            playlist_manager.add_items(playlist_id, data['items'])
        
        return jsonify({
            'id': playlist_id,
            'message': 'Playlist created successfully'
        })

    except Exception as e:
        api_logger.error(f"Error creating playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>', methods=['PUT'])
@log_function_call(api_logger)
def update_playlist(playlist_id: int):
    """Update playlist details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update basic info
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        
        if updates:
            db.update('playlists', updates, {'id': playlist_id})
        
        # Handle items if provided
        if 'items' in data:
            # Clear existing items
            db.execute(
                "DELETE FROM playlist_items WHERE playlist_id = ?",
                (playlist_id,)
            )
            # Add new items
            playlist_manager.add_items(playlist_id, data['items'])
        
        return jsonify({'message': 'Playlist updated successfully'})

    except Exception as e:
        api_logger.error(f"Error updating playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>', methods=['DELETE'])
@log_function_call(api_logger)
def delete_playlist(playlist_id: int):
    """Delete a playlist."""
    try:
        # Delete playlist items
        db.execute(
            "DELETE FROM playlist_items WHERE playlist_id = ?",
            (playlist_id,)
        )
        
        # Delete playlist state
        db.execute(
            "DELETE FROM playlist_state WHERE playlist_id = ?",
            (playlist_id,)
        )
        
        # Delete playlist
        db.delete('playlists', {'id': playlist_id})
        
        return jsonify({'message': 'Playlist deleted successfully'})

    except Exception as e:
        api_logger.error(f"Error deleting playlist: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/items', methods=['POST'])
@log_function_call(api_logger)
def add_playlist_items(playlist_id: int):
    """Add items to a playlist."""
    try:
        data = request.get_json()
        if not data or 'media_ids' not in data:
            return jsonify({'error': 'Media IDs are required'}), 400
        
        success = playlist_manager.add_items(
            playlist_id,
            data['media_ids']
        )
        
        if not success:
            return jsonify({'error': 'Failed to add items'}), 500
        
        return jsonify({'message': 'Items added successfully'})

    except Exception as e:
        api_logger.error(f"Error adding playlist items: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/items', methods=['DELETE'])
@log_function_call(api_logger)
def remove_playlist_items(playlist_id: int):
    """Remove items from a playlist."""
    try:
        data = request.get_json()
        if not data or 'media_ids' not in data:
            return jsonify({'error': 'Media IDs are required'}), 400
        
        success = playlist_manager.remove_items(
            playlist_id,
            data['media_ids']
        )
        
        if not success:
            return jsonify({'error': 'Failed to remove items'}), 500
        
        return jsonify({'message': 'Items removed successfully'})

    except Exception as e:
        api_logger.error(f"Error removing playlist items: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/next', methods=['POST'])
@log_function_call(api_logger)
def next_item(playlist_id: int):
    """Get next item in playlist, considering ad scheduling."""
    try:
        # Check if we should play an ad
        if ad_scheduler.should_play_ad(playlist_id):
            ad = ad_scheduler.get_next_ad(playlist_id)
            if ad:
                return jsonify({
                    'type': 'ad',
                    'item': ad
                })
        
        # Get next regular item
        item = playlist_manager.next_item(playlist_id)
        if not item:
            return jsonify({'error': 'No more items'}), 404
        
        return jsonify({
            'type': 'media',
            'item': item
        })

    except Exception as e:
        api_logger.error(f"Error getting next item: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/shuffle', methods=['POST'])
@log_function_call(api_logger)
def toggle_shuffle(playlist_id: int):
    """Toggle shuffle mode for a playlist."""
    try:
        success = playlist_manager.toggle_shuffle(playlist_id)
        if not success:
            return jsonify({'error': 'Failed to toggle shuffle'}), 500
        
        return jsonify({'message': 'Shuffle mode toggled'})

    except Exception as e:
        api_logger.error(f"Error toggling shuffle: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/schedule', methods=['POST'])
@log_function_call(api_logger)
def set_schedule(playlist_id: int):
    """Set a playlist's schedule."""
    try:
        data = request.get_json()
        if not data or 'type' not in data:
            return jsonify({'error': 'Schedule type is required'}), 400

        # Validate schedule data
        if data['type'] not in ['once', 'daily', 'weekly']:
            return jsonify({'error': 'Invalid schedule type'}), 400

        if data['type'] == 'once' and 'datetime' not in data:
            return jsonify({'error': 'Datetime is required for one-time schedule'}), 400

        if 'time' not in data:
            return jsonify({'error': 'Time is required'}), 400

        if data['type'] == 'weekly' and 'days' not in data:
            return jsonify({'error': 'Days are required for weekly schedule'}), 400

        success = playlist_manager.set_schedule(playlist_id, data)
        if not success:
            return jsonify({'error': 'Failed to set schedule'}), 500

        return jsonify({'message': 'Schedule set successfully'})

    except Exception as e:
        api_logger.error(f"Error setting schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/schedule', methods=['GET'])
@log_function_call(api_logger)
def get_schedule(playlist_id: int):
    """Get a playlist's schedule."""
    try:
        schedule = playlist_manager.get_schedule(playlist_id)
        if not schedule:
            return jsonify({'message': 'No schedule found'}), 404

        return jsonify(schedule)

    except Exception as e:
        api_logger.error(f"Error getting schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/repeat', methods=['POST'])
@log_function_call(api_logger)
def toggle_repeat(playlist_id: int):
    """Toggle repeat mode for a playlist."""
    try:
        success = playlist_manager.toggle_repeat(playlist_id)
        if not success:
            return jsonify({'error': 'Failed to toggle repeat'}), 500
        
        return jsonify({'message': 'Repeat mode toggled'})

    except Exception as e:
        api_logger.error(f"Error toggling repeat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@playlist_api.route('/<int:playlist_id>/move', methods=['POST'])
@log_function_call(api_logger)
def move_item(playlist_id: int):
    """Move an item to a new position in the playlist."""
    try:
        data = request.get_json()
        if not data or 'item_id' not in data or 'new_position' not in data:
            return jsonify({
                'error': 'Item ID and new position are required'
            }), 400
        
        success = playlist_manager.move_item(
            playlist_id,
            data['item_id'],
            data['new_position']
        )
        
        if not success:
            return jsonify({'error': 'Failed to move item'}), 500
        
        return jsonify({'message': 'Item moved successfully'})

    except Exception as e:
        api_logger.error(f"Error moving playlist item: {str(e)}")
        return jsonify({'error': str(e)}), 500
