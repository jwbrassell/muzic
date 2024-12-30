import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random

from ..core.logging import media_logger, log_function_call, log_error
from ..core.database import Database, dict_from_row
from ..core.cache import cached, invalidate_cache, cache_get, cache_set, cache_delete

class PlaylistManager:
    """Manages playlist operations and state."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger

    def _build_cache_key(self, prefix: str, **kwargs) -> str:
        """Build a cache key from prefix and parameters."""
        parts = [prefix]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")
        return ":".join(parts)

    @log_function_call(media_logger)
    @invalidate_cache('playlist:*')
    def create_playlist(self, name: str, description: str = None) -> Optional[int]:
        """Create a new playlist."""
        try:
            with self.db.transaction():
                # Create playlist
                playlist_id = self.db.insert('playlists', {
                    'name': name,
                    'description': description,
                    'status': 'active',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
                
                # Initialize playlist state
                self.db.insert('playlist_state', {
                    'playlist_id': playlist_id,
                    'current_position': 0,
                    'last_ad_position': 0,
                    'is_repeat': True,
                    'is_shuffle': False,
                    'shuffle_queue': None,
                    'last_played_at': None
                })
                
                return playlist_id

        except Exception as e:
            self.logger.error(f"Failed to create playlist: {str(e)}")
            return None

    def _validate_media_items(self, media_ids: List[int]) -> Tuple[bool, Optional[str]]:
        """Validate that all media items exist and are active."""
        try:
            # Optimized query with single IN clause
            placeholders = ','.join('?' * len(media_ids))
            items = self.db.fetch_all(
                f"""
                SELECT id, status 
                FROM media 
                WHERE id IN ({placeholders})
                """,
                tuple(media_ids)
            )
            
            found_ids = {item['id'] for item in items}
            missing_ids = set(media_ids) - found_ids
            if missing_ids:
                return False, f"Media items not found: {missing_ids}"
            
            inactive_ids = {item['id'] for item in items if item['status'] != 'active'}
            if inactive_ids:
                return False, f"Media items are inactive: {inactive_ids}"
            
            return True, None
            
        except Exception as e:
            return False, f"Error validating media items: {str(e)}"

    @log_function_call(media_logger)
    @invalidate_cache('playlist:*')
    def add_items(self, playlist_id: int, media_ids: List[int]) -> bool:
        """Add multiple items to a playlist."""
        if not media_ids:
            return True
            
        try:
            with self.db.transaction():
                # Lock playlist and verify it exists
                playlist = self.db.fetch_one(
                    "SELECT id, status FROM playlists WHERE id = ? FOR UPDATE",
                    (playlist_id,)
                )
                if not playlist:
                    raise ValueError("Playlist not found")
                if playlist['status'] not in ['active', 'scheduled']:
                    raise ValueError(f"Cannot add items to playlist in {playlist['status']} status")
                
                # Validate media items
                is_valid, error = self._validate_media_items(media_ids)
                if not is_valid:
                    raise ValueError(error)
                
                # Lock playlist state
                state = self.db.fetch_one(
                    "SELECT * FROM playlist_state WHERE playlist_id = ? FOR UPDATE",
                    (playlist_id,)
                )
                if not state:
                    raise ValueError("Playlist state not found")
                
                # Get current max position with lock
                result = self.db.fetch_one(
                    """
                    SELECT COALESCE(MAX(order_position), -1) as max_pos 
                    FROM playlist_items 
                    WHERE playlist_id = ?
                    FOR UPDATE
                    """,
                    (playlist_id,)
                )
                current_max = result['max_pos'] + 1 if result else 0
                
                # Prepare items for batch insertion
                items = [
                    (playlist_id, media_id, current_max + i)
                    for i, media_id in enumerate(media_ids)
                ]
                
                # Batch insert items
                self.db.execute_many(
                    """
                    INSERT INTO playlist_items 
                    (playlist_id, media_id, order_position) 
                    VALUES (?, ?, ?)
                    """,
                    items
                )
                
                # Update shuffle queue if enabled
                if state['is_shuffle']:
                    current_queue = json.loads(state['shuffle_queue'] or '[]')
                    new_positions = list(range(current_max, current_max + len(media_ids)))
                    if current_queue:
                        current_pos = current_queue[0]
                        random.shuffle(new_positions)
                        current_queue[1:1] = new_positions
                    else:
                        all_positions = list(range(current_max + len(media_ids)))
                        random.shuffle(all_positions)
                        current_queue = all_positions
                    
                    self.db.update(
                        'playlist_state',
                        {'shuffle_queue': json.dumps(current_queue)},
                        {'playlist_id': playlist_id}
                    )
                
                # Update playlist modified timestamp
                self.db.update(
                    'playlists',
                    {'updated_at': datetime.now().isoformat()},
                    {'id': playlist_id}
                )
                
                return True

        except Exception as e:
            self.logger.error(f"Failed to add items to playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    @cached('playlist_items', timeout=300)
    def get_playlist_items(self, playlist_id: int) -> List[Dict]:
        """Get all items in a playlist with media details."""
        try:
            # Try to get from cache first
            cache_key = f'playlist_items:{playlist_id}'
            cached_result = cache_get(cache_key)
            if cached_result:
                return cached_result
            
            # Optimized query with JOIN and additional media info
            items = self.db.fetch_all(
                """
                SELECT 
                    pi.id as item_id,
                    pi.order_position,
                    m.*,
                    GROUP_CONCAT(t.name) as tag_names
                FROM playlist_items pi 
                JOIN media m ON pi.media_id = m.id 
                LEFT JOIN media_tags mt ON m.id = mt.media_id
                LEFT JOIN tags t ON mt.tag_id = t.id
                WHERE pi.playlist_id = ? 
                GROUP BY pi.id
                ORDER BY pi.order_position
                """,
                (playlist_id,)
            )
            
            # Process items
            result = []
            for item in items:
                processed_item = dict_from_row(item)
                processed_item['tags'] = item['tag_names'].split(',') if item['tag_names'] else []
                del processed_item['tag_names']
                result.append(processed_item)
            
            # Cache the result
            cache_set(cache_key, result, timeout=300)
            
            return result

        except Exception as e:
            self.logger.error(f"Failed to get items for playlist {playlist_id}: {str(e)}")
            return []

    @log_function_call(media_logger)
    @cached('playlist_state', timeout=60)
    def get_playlist_state(self, playlist_id: int) -> Optional[Dict]:
        """Get the current state of a playlist."""
        try:
            # Try to get from cache first
            cache_key = f'playlist_state:{playlist_id}'
            cached_result = cache_get(cache_key)
            if cached_result:
                return cached_result
            
            # Get state with additional info
            state = self.db.fetch_one(
                """
                SELECT ps.*, p.name, p.status
                FROM playlist_state ps
                JOIN playlists p ON ps.playlist_id = p.id
                WHERE ps.playlist_id = ?
                """,
                (playlist_id,)
            )
            
            if state:
                result = dict_from_row(state)
                # Cache the result
                cache_set(cache_key, result, timeout=60)
                return result
            
            return None

        except Exception as e:
            self.logger.error(f"Failed to get state for playlist {playlist_id}: {str(e)}")
            return None

    @log_function_call(media_logger)
    @cached('current_item', timeout=60)
    def get_current_item(self, playlist_id: int) -> Optional[Dict]:
        """Get the current item in the playlist."""
        try:
            # Try to get from cache first
            cache_key = f'current_item:{playlist_id}'
            cached_result = cache_get(cache_key)
            if cached_result:
                return cached_result
            
            state = self.db.fetch_one(
                "SELECT * FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            if not state:
                return None
            
            if state['is_shuffle'] and state['shuffle_queue']:
                shuffle_queue = json.loads(state['shuffle_queue'])
                if shuffle_queue:
                    current_pos = shuffle_queue[0]
                else:
                    return None
            else:
                current_pos = state['current_position']
            
            # Optimized query with JOINs for tags
            item = self.db.fetch_one(
                """
                SELECT 
                    pi.id as item_id,
                    pi.order_position,
                    m.*,
                    GROUP_CONCAT(t.name) as tag_names
                FROM playlist_items pi 
                JOIN media m ON pi.media_id = m.id 
                LEFT JOIN media_tags mt ON m.id = mt.media_id
                LEFT JOIN tags t ON mt.tag_id = t.id
                WHERE pi.playlist_id = ? 
                AND pi.order_position = ?
                GROUP BY pi.id
                """,
                (playlist_id, current_pos)
            )
            
            if item:
                result = dict_from_row(item)
                result['tags'] = item['tag_names'].split(',') if item['tag_names'] else []
                del result['tag_names']
                
                # Cache the result
                cache_set(cache_key, result, timeout=60)
                return result
            
            return None

        except Exception as e:
            self.logger.error(f"Failed to get current item for playlist {playlist_id}: {str(e)}")
            return None
