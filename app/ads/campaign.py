from typing import Optional, Dict, List
from datetime import datetime
import json

from ..core.logging import ad_logger, log_function_call, log_error
from ..core.database import Database, dict_from_row
from ..media.processor import MediaProcessor

class CampaignManager:
    """Manages ad campaigns and their assets."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = ad_logger
        self.media_processor = MediaProcessor(db)

    @log_function_call(ad_logger)
    def create_campaign(
        self,
        name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_percentage: Optional[float] = None
    ) -> Optional[int]:
        """Create a new ad campaign."""
        try:
            campaign_data = {
                'name': name,
                'status': 'active',
                'target_percentage': target_percentage
            }
            
            if start_date:
                campaign_data['start_date'] = start_date.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
            if end_date:
                campaign_data['end_date'] = end_date.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
            
            return self.db.insert('ad_campaigns', campaign_data)

        except Exception as e:
            self.logger.error(f"Failed to create campaign: {str(e)}")
            return None

    @log_function_call(ad_logger)
    def update_campaign(
        self,
        campaign_id: int,
        name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_percentage: Optional[float] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update campaign details."""
        try:
            updates = {}
            if name is not None:
                updates['name'] = name
            if start_date is not None:
                updates['start_date'] = start_date.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
            if end_date is not None:
                updates['end_date'] = end_date.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
            if target_percentage is not None:
                updates['target_percentage'] = target_percentage
            if status is not None:
                updates['status'] = status
            
            if updates:
                updates['updated_at'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
                self.db.update(
                    'ad_campaigns',
                    updates,
                    {'id': campaign_id}
                )
                return True
            return False

        except Exception as e:
            self.logger.error(
                f"Failed to update campaign {campaign_id}: {str(e)}"
            )
            return False

    @log_function_call(ad_logger)
    def add_asset(
        self,
        campaign_id: int,
        media_id: int,
        asset_type: str,
        duration: Optional[int] = None,
        weight: int = 1
    ) -> Optional[int]:
        """Add an asset to a campaign."""
        try:
            # Verify media exists
            media = self.db.fetch_one(
                "SELECT * FROM media WHERE id = ?",
                (media_id,)
            )
            if not media:
                self.logger.error(f"Media {media_id} not found")
                return None
            
            # Get duration if not provided
            if duration is None and asset_type in ['audio', 'video']:
                duration = self.media_processor.get_duration(
                    media['file_path']
                )
            
            asset_data = {
                'campaign_id': campaign_id,
                'media_id': media_id,
                'type': asset_type,
                'duration': duration,
                'weight': weight,
                'active': True
            }
            
            return self.db.insert('ad_assets', asset_data)

        except Exception as e:
            self.logger.error(
                f"Failed to add asset to campaign {campaign_id}: {str(e)}"
            )
            return None

    @log_function_call(ad_logger)
    def update_asset(
        self,
        asset_id: int,
        weight: Optional[int] = None,
        active: Optional[bool] = None
    ) -> bool:
        """Update asset properties."""
        try:
            updates = {}
            if weight is not None:
                updates['weight'] = weight
            if active is not None:
                updates['active'] = active
            
            if updates:
                self.db.update(
                    'ad_assets',
                    updates,
                    {'id': asset_id}
                )
                return True
            return False

        except Exception as e:
            self.logger.error(
                f"Failed to update asset {asset_id}: {str(e)}"
            )
            return False

    @log_function_call(ad_logger)
    def remove_asset(self, asset_id: int) -> bool:
        """Remove an asset from a campaign."""
        try:
            # Check if asset exists
            asset = self.db.fetch_one(
                "SELECT * FROM ad_assets WHERE id = ?",
                (asset_id,)
            )
            if not asset:
                return False
            
            # Delete asset
            self.db.delete('ad_assets', {'id': asset_id})
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to remove asset {asset_id}: {str(e)}"
            )
            return False

    @log_function_call(ad_logger)
    def get_campaign_details(self, campaign_id: int) -> Optional[Dict]:
        """Get detailed information about a campaign."""
        try:
            # Get campaign info
            campaign = self.db.fetch_one(
                "SELECT * FROM ad_campaigns WHERE id = ?",
                (campaign_id,)
            )
            if not campaign:
                return None
            
            # Get assets
            assets = self.db.fetch_all(
                """
                SELECT a.*, m.title, m.artist, m.file_path
                FROM ad_assets a
                JOIN media m ON a.media_id = m.id
                WHERE a.campaign_id = ?
                """,
                (campaign_id,)
            )
            
            # Get schedules
            schedules = self.db.fetch_all(
                "SELECT * FROM ad_schedules WHERE campaign_id = ?",
                (campaign_id,)
            )
            
            # Get play statistics
            stats = self.db.fetch_one(
                """
                SELECT 
                    COUNT(*) as total_plays,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_plays,
                    SUM(duration) as total_duration
                FROM ad_logs
                WHERE campaign_id = ?
                """,
                (campaign_id,)
            )
            
            return {
                'campaign': dict_from_row(campaign),
                'assets': [dict_from_row(asset) for asset in assets],
                'schedules': [dict_from_row(schedule) for schedule in schedules],
                'statistics': dict_from_row(stats)
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get campaign details for {campaign_id}: {str(e)}"
            )
            return None

    @log_function_call(ad_logger)
    def get_active_campaigns(self) -> List[Dict]:
        """Get all active campaigns."""
        try:
            campaigns = self.db.fetch_all(
                """
                SELECT * FROM ad_campaigns
                WHERE status = 'active'
                AND (start_date IS NULL OR start_date <= datetime('now'))
                AND (end_date IS NULL OR end_date >= datetime('now'))
                """
            )
            return [dict_from_row(campaign) for campaign in campaigns]

        except Exception as e:
            self.logger.error(f"Failed to get active campaigns: {str(e)}")
            return []

    @log_function_call(ad_logger)
    def get_campaign_performance(
        self,
        campaign_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get detailed performance metrics for a campaign."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_plays,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_plays,
                    SUM(duration) as total_duration,
                    COUNT(DISTINCT playlist_id) as unique_playlists,
                    AVG(CASE WHEN completed = 1 THEN duration ELSE NULL END) as avg_completion_time
                FROM ad_logs
                WHERE campaign_id = ?
            """
            params = [campaign_id]
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            stats = self.db.fetch_one(query, tuple(params))
            
            # Get hourly distribution
            hourly = self.db.fetch_all(
                """
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as plays
                FROM ad_logs
                WHERE campaign_id = ?
                GROUP BY hour
                ORDER BY hour
                """,
                (campaign_id,)
            )
            
            # Get asset performance
            assets = self.db.fetch_all(
                """
                SELECT 
                    a.id,
                    a.type,
                    COUNT(l.id) as plays,
                    SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END) as completions
                FROM ad_assets a
                LEFT JOIN ad_logs l ON a.id = l.asset_id
                WHERE a.campaign_id = ?
                GROUP BY a.id
                """,
                (campaign_id,)
            )
            
            return {
                'overview': dict_from_row(stats),
                'hourly_distribution': [
                    dict_from_row(hour) for hour in hourly
                ],
                'asset_performance': [
                    dict_from_row(asset) for asset in assets
                ]
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get performance for campaign {campaign_id}: {str(e)}"
            )
            return {}
