import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random

from ..core.logging import media_logger, log_function_call, log_error
from ..core.database import Database, dict_from_row

class PlaylistManager:
    """Manages playlist operations and state."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger

    @log_function_call(media_logger)
    def create_playlist(self, name: str, description: str = None) -> Optional[int]:
        """Create a new playlist."""
        try:
            playlist_id = self.db.insert('playlists', {
                'name': name,
                'description': description
            })
            
            # Initialize playlist state
            self.db.insert('playlist_state', {
                'playlist_id': playlist_id,
                'current_position': 0,
                'last_ad_position': 0,
                'is_repeat': True,
                'is_shuffle': False
            })
            
            return playlist_id

        except Exception as e:
            self.logger.error(f"Failed to create playlist: {str(e)}")
            return None

    @log_function_call(media_logger)
    def add_items(self, playlist_id: int, media_ids: List[int]) -> bool:
        """Add multiple items to a playlist."""
        try:
            # Get current max position
            result = self.db.fetch_one(
                """
                SELECT COALESCE(MAX(order_position), -1) as max_pos 
                FROM playlist_items 
                WHERE playlist_id = ?
                """,
                (playlist_id,)
            )
            current_max = result['max_pos'] + 1 if result else 0
            
            # Prepare items for insertion
            items = [
                (playlist_id, media_id, current_max + i)
                for i, media_id in enumerate(media_ids)
            ]
            
            # Insert items
            self.db.execute_many(
                """
                INSERT INTO playlist_items 
                (playlist_id, media_id, order_position) 
                VALUES (?, ?, ?)
                """,
                items
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to add items to playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def remove_items(self, playlist_id: int, media_ids: List[int]) -> bool:
        """Remove items from a playlist."""
        try:
            placeholders = ','.join('?' * len(media_ids))
            self.db.execute(
                f"""
                DELETE FROM playlist_items 
                WHERE playlist_id = ? 
                AND media_id IN ({placeholders})
                """,
                (playlist_id, *media_ids)
            )
            
            # Reorder remaining items
            self._reorder_items(playlist_id)
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove items from playlist {playlist_id}: {str(e)}")
            return False

    def _reorder_items(self, playlist_id: int) -> None:
        """Reorder items to ensure sequential positions."""
        items = self.db.fetch_all(
            """
            SELECT id, order_position 
            FROM playlist_items 
            WHERE playlist_id = ? 
            ORDER BY order_position
            """,
            (playlist_id,)
        )
        
        for i, item in enumerate(items):
            if item['order_position'] != i:
                self.db.update(
                    'playlist_items',
                    {'order_position': i},
                    {'id': item['id']}
                )

    @log_function_call(media_logger)
    def move_item(self, playlist_id: int, item_id: int, new_position: int) -> bool:
        """Move an item to a new position in the playlist."""
        try:
            # Get current position
            item = self.db.fetch_one(
                """
                SELECT order_position 
                FROM playlist_items 
                WHERE id = ? AND playlist_id = ?
                """,
                (item_id, playlist_id)
            )
            
            if not item:
                return False
                
            current_pos = item['order_position']
            
            # Update positions
            if new_position > current_pos:
                self.db.execute(
                    """
                    UPDATE playlist_items 
                    SET order_position = order_position - 1 
                    WHERE playlist_id = ? 
                    AND order_position > ? 
                    AND order_position <= ?
                    """,
                    (playlist_id, current_pos, new_position)
                )
            else:
                self.db.execute(
                    """
                    UPDATE playlist_items 
                    SET order_position = order_position + 1 
                    WHERE playlist_id = ? 
                    AND order_position >= ? 
                    AND order_position < ?
                    """,
                    (playlist_id, new_position, current_pos)
                )
            
            # Update item position
            self.db.update(
                'playlist_items',
                {'order_position': new_position},
                {'id': item_id}
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to move item {item_id} in playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def get_playlist_items(self, playlist_id: int) -> List[Dict]:
        """Get all items in a playlist with media details."""
        try:
            items = self.db.fetch_all(
                """
                SELECT 
                    pi.id as item_id,
                    pi.order_position,
                    m.* 
                FROM playlist_items pi 
                JOIN media m ON pi.media_id = m.id 
                WHERE pi.playlist_id = ? 
                ORDER BY pi.order_position
                """,
                (playlist_id,)
            )
            return [dict_from_row(item) for item in items]

        except Exception as e:
            self.logger.error(f"Failed to get items for playlist {playlist_id}: {str(e)}")
            return []

    @log_function_call(media_logger)
    def get_current_item(self, playlist_id: int) -> Optional[Dict]:
        """Get the current item in the playlist."""
        try:
            state = self.db.fetch_one(
                "SELECT * FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            if not state:
                return None
            
            if state['is_shuffle'] and state['shuffle_queue']:
                # Get current item from shuffle queue
                shuffle_queue = json.loads(state['shuffle_queue'])
                if shuffle_queue:
                    current_pos = shuffle_queue[0]
                else:
                    return None
            else:
                current_pos = state['current_position']
            
            item = self.db.fetch_one(
                """
                SELECT 
                    pi.id as item_id,
                    pi.order_position,
                    m.* 
                FROM playlist_items pi 
                JOIN media m ON pi.media_id = m.id 
                WHERE pi.playlist_id = ? 
                AND pi.order_position = ?
                """,
                (playlist_id, current_pos)
            )
            
            return dict_from_row(item) if item else None

        except Exception as e:
            self.logger.error(f"Failed to get current item for playlist {playlist_id}: {str(e)}")
            return None

    @log_function_call(media_logger)
    def next_item(self, playlist_id: int) -> Optional[Dict]:
        """Move to and return the next item in the playlist."""
        try:
            state = self.db.fetch_one(
                "SELECT * FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            if not state:
                return None
            
            if state['is_shuffle']:
                next_item = self._next_shuffle_item(playlist_id, state)
            else:
                next_item = self._next_sequential_item(playlist_id, state)
            
            if next_item:
                self._update_position(playlist_id, next_item['order_position'])
            
            return next_item

        except Exception as e:
            self.logger.error(f"Failed to get next item for playlist {playlist_id}: {str(e)}")
            return None

    def _next_sequential_item(self, playlist_id: int, state: Dict) -> Optional[Dict]:
        """Get next item in sequential mode."""
        next_pos = state['current_position'] + 1
        
        # Get total items
        count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM playlist_items WHERE playlist_id = ?",
            (playlist_id,)
        )['count']
        
        if next_pos >= count:
            if not state['is_repeat']:
                return None
            next_pos = 0
        
        item = self.db.fetch_one(
            """
            SELECT 
                pi.id as item_id,
                pi.order_position,
                m.* 
            FROM playlist_items pi 
            JOIN media m ON pi.media_id = m.id 
            WHERE pi.playlist_id = ? 
            AND pi.order_position = ?
            """,
            (playlist_id, next_pos)
        )
        
        return dict_from_row(item) if item else None

    def _next_shuffle_item(self, playlist_id: int, state: Dict) -> Optional[Dict]:
        """Get next item in shuffle mode."""
        shuffle_queue = json.loads(state['shuffle_queue'] or '[]')
        
        # If queue is empty or None, generate new queue
        if not shuffle_queue:
            items = self.db.fetch_all(
                """
                SELECT order_position 
                FROM playlist_items 
                WHERE playlist_id = ? 
                ORDER BY order_position
                """,
                (playlist_id,)
            )
            positions = [item['order_position'] for item in items]
            random.shuffle(positions)
            shuffle_queue = positions
        
        # Remove current position from queue
        if shuffle_queue:
            shuffle_queue.pop(0)
        
        # Update shuffle queue
        self.db.update(
            'playlist_state',
            {'shuffle_queue': json.dumps(shuffle_queue)},
            {'playlist_id': playlist_id}
        )
        
        if not shuffle_queue:
            if not state['is_repeat']:
                return None
            # Generate new queue if repeat is enabled
            return self._next_shuffle_item(playlist_id, state)
        
        next_pos = shuffle_queue[0]
        item = self.db.fetch_one(
            """
            SELECT 
                pi.id as item_id,
                pi.order_position,
                m.* 
            FROM playlist_items pi 
            JOIN media m ON pi.media_id = m.id 
            WHERE pi.playlist_id = ? 
            AND pi.order_position = ?
            """,
            (playlist_id, next_pos)
        )
        
        return dict_from_row(item) if item else None

    def _update_position(self, playlist_id: int, position: int) -> None:
        """Update the current position in playlist state."""
        self.db.update(
            'playlist_state',
            {'current_position': position},
            {'playlist_id': playlist_id}
        )

    @log_function_call(media_logger)
    def toggle_shuffle(self, playlist_id: int) -> bool:
        """Toggle shuffle mode for a playlist."""
        try:
            state = self.db.fetch_one(
                "SELECT is_shuffle FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            if not state:
                return False
            
            new_shuffle = not state['is_shuffle']
            shuffle_queue = None
            
            if new_shuffle:
                # Generate initial shuffle queue
                items = self.db.fetch_all(
                    """
                    SELECT order_position 
                    FROM playlist_items 
                    WHERE playlist_id = ? 
                    ORDER BY order_position
                    """,
                    (playlist_id,)
                )
                positions = [item['order_position'] for item in items]
                random.shuffle(positions)
                shuffle_queue = json.dumps(positions)
            
            self.db.update(
                'playlist_state',
                {
                    'is_shuffle': new_shuffle,
                    'shuffle_queue': shuffle_queue
                },
                {'playlist_id': playlist_id}
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to toggle shuffle for playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def toggle_repeat(self, playlist_id: int) -> bool:
        """Toggle repeat mode for a playlist."""
        try:
            state = self.db.fetch_one(
                "SELECT is_repeat FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            if not state:
                return False
            
            self.db.update(
                'playlist_state',
                {'is_repeat': not state['is_repeat']},
                {'playlist_id': playlist_id}
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to toggle repeat for playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def get_playlist_state(self, playlist_id: int) -> Optional[Dict]:
        """Get the current state of a playlist."""
        try:
            state = self.db.fetch_one(
                "SELECT * FROM playlist_state WHERE playlist_id = ?",
                (playlist_id,)
            )
            return dict_from_row(state) if state else None

        except Exception as e:
            self.logger.error(f"Failed to get state for playlist {playlist_id}: {str(e)}")
            return None

    @log_function_call(media_logger)
    def set_schedule(self, playlist_id: int, schedule: Dict) -> bool:
        """Set or update a playlist's schedule."""
        try:
            # Delete existing schedule
            self.db.execute(
                "DELETE FROM playlist_schedules WHERE playlist_id = ?",
                (playlist_id,)
            )
            
            # Insert new schedule
            self.db.insert('playlist_schedules', {
                'playlist_id': playlist_id,
                'type': schedule['type'],
                'datetime': schedule.get('datetime'),
                'time': schedule.get('time'),
                'days': schedule.get('days')
            })
            
            # Update playlist status
            self.db.update(
                'playlists',
                {'status': 'scheduled'},
                {'id': playlist_id}
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Failed to set schedule for playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def get_schedule(self, playlist_id: int) -> Optional[Dict]:
        """Get a playlist's schedule."""
        try:
            schedule = self.db.fetch_one(
                "SELECT * FROM playlist_schedules WHERE playlist_id = ?",
                (playlist_id,)
            )
            return dict_from_row(schedule) if schedule else None

        except Exception as e:
            self.logger.error(f"Failed to get schedule for playlist {playlist_id}: {str(e)}")
            return None

    @log_function_call(media_logger)
    def log_play(self, playlist_id: int) -> bool:
        """Log that a playlist was played."""
        try:
            self.db.insert('playlist_history', {
                'playlist_id': playlist_id
            })
            return True

        except Exception as e:
            self.logger.error(f"Failed to log play for playlist {playlist_id}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def update_status(self, playlist_id: int, status: str) -> bool:
        """Update a playlist's status."""
        try:
            self.db.update(
                'playlists',
                {
                    'status': status,
                    'updated_at': datetime.now().isoformat()
                },
                {'id': playlist_id}
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update status for playlist {playlist_id}: {str(e)}")
            return False
