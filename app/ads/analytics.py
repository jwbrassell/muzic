from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

from ..core.logging import ad_logger, log_function_call, log_error
from ..core.database import Database, dict_from_row

class AdAnalytics:
    """Handles ad performance analytics and reporting."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = ad_logger

    @log_function_call(ad_logger)
    def get_campaign_metrics(
        self,
        campaign_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get comprehensive metrics for a campaign."""
        try:
            # Base query for metrics
            query = """
                SELECT 
                    COUNT(*) as impressions,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completions,
                    SUM(duration) as total_duration,
                    COUNT(DISTINCT playlist_id) as reach,
                    AVG(CASE WHEN completed = 1 THEN duration ELSE NULL END) as avg_view_time
                FROM ad_logs
                WHERE campaign_id = ?
            """
            params = [campaign_id]
            
            # Add date filters if provided
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            metrics = self.db.fetch_one(query, tuple(params))
            
            return {
                'impressions': metrics['impressions'],
                'completions': metrics['completions'],
                'completion_rate': (
                    (metrics['completions'] / metrics['impressions'] * 100)
                    if metrics['impressions'] > 0 else 0
                ),
                'total_duration': metrics['total_duration'],
                'avg_view_time': metrics['avg_view_time'] or 0,
                'reach': metrics['reach']
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get metrics for campaign {campaign_id}: {str(e)}"
            )
            return {}

    @log_function_call(ad_logger)
    def get_asset_performance(
        self,
        campaign_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get performance metrics for each asset in a campaign."""
        try:
            query = """
                SELECT 
                    a.id,
                    a.type,
                    m.title,
                    COUNT(l.id) as impressions,
                    SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END) as completions,
                    AVG(CASE WHEN l.completed = 1 THEN l.duration ELSE NULL END) as avg_view_time,
                    COUNT(DISTINCT l.playlist_id) as reach
                FROM ad_assets a
                JOIN media m ON a.media_id = m.id
                LEFT JOIN ad_logs l ON a.id = l.asset_id
                WHERE a.campaign_id = ?
            """
            params = [campaign_id]
            
            if start_date:
                query += " AND l.timestamp >= ?"
                params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
            if end_date:
                query += " AND l.timestamp <= ?"
                params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += " GROUP BY a.id"
            
            assets = self.db.fetch_all(query, tuple(params))
            
            return [{
                **dict_from_row(asset),
                'completion_rate': (
                    (asset['completions'] / asset['impressions'] * 100)
                    if asset['impressions'] > 0 else 0
                )
            } for asset in assets]

        except Exception as e:
            self.logger.error(
                f"Failed to get asset performance for campaign {campaign_id}: {str(e)}"
            )
            return []

    @log_function_call(ad_logger)
    def get_time_distribution(
        self,
        campaign_id: int,
        interval: str = 'hour',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get time-based distribution of ad plays."""
        try:
            # Define time format based on interval
            if interval == 'hour':
                time_format = '%H'
                group_by = "strftime('%H', timestamp)"
            elif interval == 'day':
                time_format = '%Y-%m-%d'
                group_by = "date(timestamp)"
            elif interval == 'week':
                time_format = '%W'
                group_by = "strftime('%W', timestamp)"
            elif interval == 'month':
                time_format = '%Y-%m'
                group_by = "strftime('%Y-%m', timestamp)"
            else:
                raise ValueError(f"Invalid interval: {interval}")
            
            query = f"""
                SELECT 
                    {group_by} as period,
                    COUNT(*) as impressions,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completions,
                    COUNT(DISTINCT playlist_id) as reach
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
            
            query += f" GROUP BY {group_by} ORDER BY period"
            
            distribution = self.db.fetch_all(query, tuple(params))
            
            return [dict_from_row(period) for period in distribution]

        except Exception as e:
            self.logger.error(
                f"Failed to get time distribution for campaign {campaign_id}: {str(e)}"
            )
            return []

    @log_function_call(ad_logger)
    def get_playlist_performance(
        self,
        campaign_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get performance metrics by playlist."""
        try:
            query = """
                SELECT 
                    l.playlist_id,
                    p.name as playlist_name,
                    COUNT(*) as impressions,
                    SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END) as completions,
                    AVG(CASE WHEN l.completed = 1 THEN l.duration ELSE NULL END) as avg_view_time
                FROM ad_logs l
                JOIN playlists p ON l.playlist_id = p.id
                WHERE l.campaign_id = ?
            """
            params = [campaign_id]
            
            if start_date:
                query += " AND l.timestamp >= ?"
                params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
            if end_date:
                query += " AND l.timestamp <= ?"
                params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += " GROUP BY l.playlist_id"
            
            playlists = self.db.fetch_all(query, tuple(params))
            
            return [{
                **dict_from_row(playlist),
                'completion_rate': (
                    (playlist['completions'] / playlist['impressions'] * 100)
                    if playlist['impressions'] > 0 else 0
                )
            } for playlist in playlists]

        except Exception as e:
            self.logger.error(
                f"Failed to get playlist performance for campaign {campaign_id}: {str(e)}"
            )
            return []

    @log_function_call(ad_logger)
    def get_comparative_metrics(
        self,
        campaign_ids: List[int],
        metric: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[int, float]:
        """Compare specific metrics across multiple campaigns."""
        try:
            # Define metric calculation
            metric_calc = {
                'impressions': "COUNT(*)",
                'completions': "SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END)",
                'completion_rate': """
                    (SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*))
                """,
                'avg_duration': "AVG(duration)",
                'reach': "COUNT(DISTINCT playlist_id)"
            }.get(metric)
            
            if not metric_calc:
                raise ValueError(f"Invalid metric: {metric}")
            
            placeholders = ','.join('?' * len(campaign_ids))
            query = f"""
                SELECT 
                    campaign_id,
                    {metric_calc} as value
                FROM ad_logs
                WHERE campaign_id IN ({placeholders})
            """
            params = campaign_ids.copy()
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += " GROUP BY campaign_id"
            
            results = self.db.fetch_all(query, tuple(params))
            
            return {
                row['campaign_id']: row['value']
                for row in results
            }

        except Exception as e:
            self.logger.error(
                f"Failed to get comparative metrics: {str(e)}"
            )
            return {}

    @log_function_call(ad_logger)
    def generate_report(
        self,
        campaign_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Generate a comprehensive performance report for a campaign."""
        try:
            return {
                'overview': self.get_campaign_metrics(
                    campaign_id, start_date, end_date
                ),
                'assets': self.get_asset_performance(
                    campaign_id, start_date, end_date
                ),
                'hourly_distribution': self.get_time_distribution(
                    campaign_id, 'hour', start_date, end_date
                ),
                'daily_distribution': self.get_time_distribution(
                    campaign_id, 'day', start_date, end_date
                ),
                'playlist_performance': self.get_playlist_performance(
                    campaign_id, start_date, end_date
                )
            }

        except Exception as e:
            self.logger.error(
                f"Failed to generate report for campaign {campaign_id}: {str(e)}"
            )
            return {}
