"""Database optimization module for improving query performance."""
from typing import List
from app.core.database import Database
from app.core.logging import get_logger

logger = get_logger(__name__)

class DatabaseOptimizer:
    def __init__(self, db: Database):
        self.db = db

    def create_indexes(self) -> None:
        """Create all necessary indexes for optimal performance."""
        try:
            # Media table indexes
            self._create_index('idx_media_type', 'media', ['type'])
            self._create_index('idx_media_artist', 'media', ['artist'])
            self._create_index('idx_media_title', 'media', ['title'])
            self._create_index('idx_media_checksum', 'media', ['checksum'])

            # Playlist related indexes
            self._create_index('idx_playlist_items_playlist', 'playlist_items', ['playlist_id'])
            self._create_index('idx_playlist_items_media', 'playlist_items', ['media_id'])
            self._create_index('idx_playlist_items_position', 'playlist_items', ['order_position'])
            self._create_index('idx_playlist_state_playlist', 'playlist_state', ['playlist_id'])

            # Tag related indexes
            self._create_index('idx_media_tags_media', 'media_tags', ['media_id'])
            self._create_index('idx_media_tags_tag', 'media_tags', ['tag_id'])
            self._create_index('idx_tags_name', 'tags', ['name'])

            # Ad campaign related indexes
            self._create_index('idx_ad_campaigns_status', 'ad_campaigns', ['status'])
            self._create_index('idx_ad_campaigns_dates', 'ad_campaigns', ['start_date', 'end_date'])
            self._create_index('idx_ad_campaigns_updated', 'ad_campaigns', ['updated_at'])

            # Ad assets indexes
            self._create_index('idx_ad_assets_campaign', 'ad_assets', ['campaign_id'])
            self._create_index('idx_ad_assets_media', 'ad_assets', ['media_id'])
            self._create_index('idx_ad_assets_type', 'ad_assets', ['type'])
            self._create_index('idx_ad_assets_active', 'ad_assets', ['active'])

            # Ad schedule indexes
            self._create_index('idx_ad_schedules_campaign', 'ad_schedules', ['campaign_id'])
            self._create_index('idx_ad_schedules_playlist', 'ad_schedules', ['playlist_id'])
            self._create_index('idx_ad_schedules_priority', 'ad_schedules', ['priority'])
            self._create_index('idx_ad_schedules_time', 'ad_schedules', ['start_time', 'end_time'])

            # Ad logs indexes for analytics
            self._create_index('idx_ad_logs_campaign', 'ad_logs', ['campaign_id'])
            self._create_index('idx_ad_logs_asset', 'ad_logs', ['asset_id'])
            self._create_index('idx_ad_logs_playlist', 'ad_logs', ['playlist_id'])
            self._create_index('idx_ad_logs_timestamp', 'ad_logs', ['timestamp'])
            self._create_index('idx_ad_logs_completed', 'ad_logs', ['completed'])

            logger.info("Successfully created all database indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise

    def analyze_tables(self) -> None:
        """Run ANALYZE on all tables to update statistics."""
        try:
            self.db.execute("ANALYZE")
            logger.info("Successfully analyzed database tables")
        except Exception as e:
            logger.error(f"Error analyzing tables: {e}")
            raise

    def optimize_database(self) -> None:
        """Run VACUUM to optimize database file structure."""
        try:
            # Enable auto_vacuum for better space management
            self.db.execute("PRAGMA auto_vacuum = FULL")
            # Run VACUUM to rebuild the database file
            self.db.execute("VACUUM")
            logger.info("Successfully optimized database file structure")
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            raise

    def optimize_query_planner(self) -> None:
        """Configure SQLite query planner for optimal performance."""
        try:
            # Enable WAL mode for better concurrency
            self.db.execute("PRAGMA journal_mode = WAL")
            # Set reasonable cache size (4MB)
            self.db.execute("PRAGMA cache_size = -4000")
            # Enable memory-mapped I/O for better performance
            self.db.execute("PRAGMA mmap_size = 268435456")  # 256MB
            # Set reasonable page size
            self.db.execute("PRAGMA page_size = 4096")
            # Enable foreign key constraints
            self.db.execute("PRAGMA foreign_keys = ON")
            logger.info("Successfully configured query planner settings")
        except Exception as e:
            logger.error(f"Error configuring query planner: {e}")
            raise

    def _create_index(self, index_name: str, table: str, columns: List[str]) -> None:
        """Create an index if it doesn't exist."""
        columns_str = ', '.join(columns)
        query = f"""
        CREATE INDEX IF NOT EXISTS {index_name}
        ON {table} ({columns_str})
        """
        try:
            self.db.execute(query)
            logger.debug(f"Created index {index_name} on {table}({columns_str})")
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            raise

    def get_index_stats(self) -> list[dict]:
        """Get statistics about existing indexes."""
        query = """
        SELECT 
            m.type as object_type,
            m.name as object_name,
            m.tbl_name as table_name,
            m.sql as creation_sql
        FROM sqlite_master m
        WHERE m.type = 'index'
        ORDER BY m.tbl_name, m.name
        """
        try:
            return self.db.fetch_all(query)
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            raise

    def get_table_stats(self) -> list[dict]:
        """Get statistics about tables."""
        query = """
        SELECT 
            m.name as table_name,
            (SELECT COUNT(*) FROM sqlite_master i 
             WHERE i.type = 'index' AND i.tbl_name = m.name) as index_count,
            (SELECT COUNT(*) FROM pragma_table_info(m.name)) as column_count
        FROM sqlite_master m
        WHERE m.type = 'table'
        ORDER BY m.name
        """
        try:
            return self.db.fetch_all(query)
        except Exception as e:
            logger.error(f"Error getting table statistics: {e}")
            raise
