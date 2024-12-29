import random
from typing import Optional, Dict, List, Tuple
from datetime import datetime, time
import json

from ..core.logging import media_logger, log_function_call, log_error
from ..core.database import Database, dict_from_row

class AdScheduler:
    """Manages ad scheduling and insertion into playlists."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger

    @log_function_call(media_logger)
    def should_play_ad(self, playlist_id: int) -> bool:
        """Determine if an ad should be played based on scheduling rules."""
        try:
            # Get playlist state
            state = self.db.fetch_one(
                """
                SELECT current_position, last_ad_position 
                FROM playlist_state 
                WHERE playlist_id = ?
                """,
                (playlist_id,)
            )
            
            if not state:
                return False
            
            # Get active ad schedules for this playlist
            schedules = self.db.fetch_all(
                """
                SELECT s.*, c.target_percentage
                FROM ad_schedules s
                JOIN ad_campaigns c ON s.campaign_id = c.id
                WHERE s.playlist_id = ?
                AND c.status = 'active'
                AND (c.start_date IS NULL OR c.start_date <= datetime('now'))
                AND (c.end_date IS NULL OR c.end_date >= datetime('now'))
                ORDER BY s.priority DESC
                """,
                (playlist_id,)
            )
            
            if not schedules:
                return False
            
            current_time = datetime.now().time()
            current_day = datetime.now().weekday() + 1  # 1-7 for Monday-Sunday
            
            for schedule in schedules:
                # Check frequency
                positions_since_last = (
                    state['current_position'] - state['last_ad_position']
                )
                if positions_since_last < schedule['frequency']:
                    continue
                
                # Check time restrictions
                if schedule['start_time'] and schedule['end_time']:
                    start = datetime.strptime(
                        schedule['start_time'], '%H:%M:%S'
                    ).time()
                    end = datetime.strptime(
                        schedule['end_time'], '%H:%M:%S'
                    ).time()
                    if not self._is_time_in_range(current_time, start, end):
                        continue
                
                # Check day restrictions
                if schedule['days_of_week']:
                    allowed_days = [
                        int(d) for d in schedule['days_of_week'].split(',')
                    ]
                    if current_day not in allowed_days:
                        continue
                
                # Check if campaign has met its target percentage
                if schedule['target_percentage']:
                    actual_percentage = self._get_campaign_percentage(
                        schedule['campaign_id'],
                        playlist_id
                    )
                    if actual_percentage >= schedule['target_percentage']:
                        continue
                
                return True
            
            return False

        except Exception as e:
            self.logger.error(f"Error checking ad schedule: {str(e)}")
            return False

    def _is_time_in_range(
        self,
        current: time,
        start: time,
        end: time
    ) -> bool:
        """Check if current time is within range."""
        if start <= end:
            return start <= current <= end
        else:  # Handle overnight ranges
            return current >= start or current <= end

    def _get_campaign_percentage(
        self,
        campaign_id: int,
        playlist_id: int
    ) -> float:
        """Calculate actual percentage of ads played for a campaign."""
        try:
            # Get total ads played in playlist
            total = self.db.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM ad_logs 
                WHERE playlist_id = ?
                """,
                (playlist_id,)
            )['count']
            
            if not total:
                return 0.0
            
            # Get campaign ads played
            campaign = self.db.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM ad_logs 
                WHERE campaign_id = ? AND playlist_id = ?
                """,
                (campaign_id, playlist_id)
            )['count']
            
            return (campaign / total) * 100 if total > 0 else 0.0

        except Exception as e:
            self.logger.error(
                f"Error calculating campaign percentage: {str(e)}"
            )
            return 0.0

    @log_function_call(media_logger)
    def get_next_ad(self, playlist_id: int) -> Optional[Dict]:
        """Get the next ad to play based on scheduling rules."""
        try:
            # Get eligible campaigns
            campaigns = self.db.fetch_all(
                """
                SELECT DISTINCT c.id, c.target_percentage, s.priority
                FROM ad_campaigns c
                JOIN ad_schedules s ON s.campaign_id = c.id
                WHERE s.playlist_id = ?
                AND c.status = 'active'
                AND (c.start_date IS NULL OR c.start_date <= datetime('now'))
                AND (c.end_date IS NULL OR c.end_date >= datetime('now'))
                ORDER BY s.priority DESC
                """,
                (playlist_id,)
            )
            
            if not campaigns:
                return None
            
            # Select campaign based on priority and target percentage
            selected_campaign = None
            for campaign in campaigns:
                actual_percentage = self._get_campaign_percentage(
                    campaign['id'],
                    playlist_id
                )
                if (not campaign['target_percentage'] or 
                    actual_percentage < campaign['target_percentage']):
                    selected_campaign = campaign
                    break
            
            if not selected_campaign:
                return None
            
            # Get random ad from selected campaign
            ad = self.db.fetch_one(
                """
                SELECT 
                    a.id as asset_id,
                    a.type,
                    a.duration,
                    a.weight,
                    m.*
                FROM ad_assets a
                JOIN media m ON a.media_id = m.id
                WHERE a.campaign_id = ?
                AND a.active = 1
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (selected_campaign['id'],)
            )
            
            if not ad:
                return None
            
            return dict_from_row(ad)

        except Exception as e:
            self.logger.error(f"Error getting next ad: {str(e)}")
            return None

    @log_function_call(media_logger)
    def log_ad_play(
        self,
        playlist_id: int,
        campaign_id: int,
        asset_id: int,
        duration: int,
        completed: bool = True
    ) -> bool:
        """Log an ad play event."""
        try:
            self.db.insert('ad_logs', {
                'campaign_id': campaign_id,
                'asset_id': asset_id,
                'playlist_id': playlist_id,
                'duration': duration,
                'completed': completed
            })
            
            # Update last ad position
            state = self.db.fetch_one(
                """
                SELECT current_position 
                FROM playlist_state 
                WHERE playlist_id = ?
                """,
                (playlist_id,)
            )
            
            if state:
                self.db.update(
                    'playlist_state',
                    {'last_ad_position': state['current_position']},
                    {'playlist_id': playlist_id}
                )
            
            return True

        except Exception as e:
            self.logger.error(f"Error logging ad play: {str(e)}")
            return False

    @log_function_call(media_logger)
    def get_campaign_stats(self, campaign_id: int) -> Dict:
        """Get statistics for a campaign."""
        try:
            # Get total plays
            total_plays = self.db.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM ad_logs 
                WHERE campaign_id = ?
                """,
                (campaign_id,)
            )['count']
            
            # Get completed plays
            completed_plays = self.db.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM ad_logs 
                WHERE campaign_id = ? AND completed = 1
                """,
                (campaign_id,)
            )['count']
            
            # Get total duration
            total_duration = self.db.fetch_one(
                """
                SELECT SUM(duration) as total 
                FROM ad_logs 
                WHERE campaign_id = ?
                """,
                (campaign_id,)
            )['total'] or 0
            
            # Get playlist distribution
            playlist_stats = self.db.fetch_all(
                """
                SELECT 
                    playlist_id,
                    COUNT(*) as plays,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
                FROM ad_logs
                WHERE campaign_id = ?
                GROUP BY playlist_id
                """,
                (campaign_id,)
            )
            
            return {
                'total_plays': total_plays,
                'completed_plays': completed_plays,
                'completion_rate': (
                    (completed_plays / total_plays * 100)
                    if total_plays > 0 else 0
                ),
                'total_duration': total_duration,
                'average_duration': (
                    total_duration / total_plays if total_plays > 0 else 0
                ),
                'playlist_distribution': [
                    dict_from_row(stat) for stat in playlist_stats
                ]
            }

        except Exception as e:
            self.logger.error(f"Error getting campaign stats: {str(e)}")
            return {}

    @log_function_call(media_logger)
    def update_schedule(
        self,
        schedule_id: int,
        frequency: Optional[int] = None,
        priority: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days_of_week: Optional[str] = None
    ) -> bool:
        """Update an ad schedule."""
        try:
            updates = {}
            if frequency is not None:
                updates['frequency'] = frequency
            if priority is not None:
                updates['priority'] = priority
            if start_time is not None:
                updates['start_time'] = start_time
            if end_time is not None:
                updates['end_time'] = end_time
            if days_of_week is not None:
                updates['days_of_week'] = days_of_week
            
            if updates:
                self.db.update(
                    'ad_schedules',
                    updates,
                    {'id': schedule_id}
                )
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error updating schedule: {str(e)}")
            return False
