"""Database optimization and performance management."""
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import QueuePool
from app.core.config import get_settings
from app.core.monitoring import get_monitor

logger = logging.getLogger(__name__)
monitor = get_monitor()

class DatabaseOptimizer:
    """Handles database optimization and performance monitoring."""

    def __init__(self):
        """Initialize the optimizer with database connection."""
        settings = get_settings()
        self.engine = create_engine(
            settings.get_database_url(),
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800
        )

    def analyze_table_statistics(self) -> Dict[str, Any]:
        """Analyze table statistics."""
        try:
            stats = {}
            inspector = inspect(self.engine)
            
            for table_name in inspector.get_table_names():
                with self.engine.connect() as conn:
                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.scalar()
                    
                    # Get table size
                    result = conn.execute(text(f"SELECT page_count * page_size as size FROM pragma_page_count('{table_name}'), pragma_page_size()"))
                    size = result.scalar()
                    
                    # Get index information
                    indexes = inspector.get_indexes(table_name)
                    
                    stats[table_name] = {
                        'row_count': row_count,
                        'size_bytes': size,
                        'indexes': len(indexes),
                        'index_details': indexes
                    }
            
            return stats
        except Exception as e:
            logger.error(f"Error analyzing table statistics: {e}")
            monitor.record_error('database_optimization', f"Statistics analysis failed: {e}")
            return {}

    def optimize_indexes(self) -> List[str]:
        """Create and optimize indexes based on usage patterns."""
        try:
            operations = []
            inspector = inspect(self.engine)
            
            # Common patterns for index creation
            index_patterns = {
                'id': True,  # Always index IDs
                'created_at': True,  # Timestamp columns
                'updated_at': True,
                'status': True,  # Status columns
                'type': True,
                'user_id': True,  # Foreign key columns
                'campaign_id': True,
                'playlist_id': True
            }
            
            with self.engine.connect() as conn:
                for table_name in inspector.get_table_names():
                    existing_indexes = {idx['name']: idx for idx in inspector.get_indexes(table_name)}
                    columns = inspector.get_columns(table_name)
                    
                    for column in columns:
                        col_name = column['name'].lower()
                        
                        # Check if column matches any index pattern
                        should_index = any(
                            pattern in col_name 
                            for pattern in index_patterns 
                            if index_patterns[pattern]
                        )
                        
                        if should_index:
                            index_name = f"idx_{table_name}_{col_name}"
                            
                            # Create index if it doesn't exist
                            if index_name not in existing_indexes:
                                try:
                                    conn.execute(text(
                                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({col_name})"
                                    ))
                                    operations.append(f"Created index {index_name}")
                                except Exception as e:
                                    logger.error(f"Error creating index {index_name}: {e}")
                                    monitor.record_error('database_optimization', f"Index creation failed: {e}")
            
            return operations
        except Exception as e:
            logger.error(f"Error optimizing indexes: {e}")
            monitor.record_error('database_optimization', f"Index optimization failed: {e}")
            return []

    def analyze_query_performance(self) -> List[Dict[str, Any]]:
        """Analyze and log slow queries."""
        try:
            with self.engine.connect() as conn:
                # Enable query timing
                conn.execute(text("PRAGMA query_only = ON"))
                
                # Get slow queries from SQLite statistics
                result = conn.execute(text("""
                    SELECT 
                        sql,
                        avg_us / 1000000.0 as avg_seconds,
                        count
                    FROM sqlite_stat4
                    WHERE avg_us > 100000  -- Queries taking more than 100ms
                    ORDER BY avg_us DESC
                    LIMIT 10
                """))
                
                slow_queries = []
                for row in result:
                    slow_queries.append({
                        'query': row[0],
                        'avg_duration': row[1],
                        'execution_count': row[2]
                    })
                
                return slow_queries
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            monitor.record_error('database_optimization', f"Query analysis failed: {e}")
            return []

    def optimize_database(self) -> Dict[str, Any]:
        """Run full database optimization."""
        try:
            with self.engine.connect() as conn:
                # Vacuum the database
                conn.execute(text("VACUUM"))
                
                # Analyze tables
                conn.execute(text("ANALYZE"))
                
                # Optimize indexes
                index_operations = self.optimize_indexes()
                
                # Get statistics
                stats = self.analyze_table_statistics()
                
                # Get slow queries
                slow_queries = self.analyze_query_performance()
                
                return {
                    'status': 'success',
                    'operations': {
                        'vacuum': True,
                        'analyze': True,
                        'index_operations': index_operations
                    },
                    'statistics': stats,
                    'slow_queries': slow_queries
                }
        except Exception as e:
            logger.error(f"Error during database optimization: {e}")
            monitor.record_error('database_optimization', f"Full optimization failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_connection_pool_status(self) -> Dict[str, Any]:
        """Get status of the connection pool."""
        try:
            return {
                'pool_size': self.engine.pool.size(),
                'checkedin': self.engine.pool.checkedin(),
                'checkedout': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'timeout': self.engine.pool.timeout,
                'recycle': self.engine.pool.recycle
            }
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            monitor.record_error('database_optimization', f"Pool status check failed: {e}")
            return {}

# Global optimizer instance
_optimizer_instance = None

def get_optimizer() -> DatabaseOptimizer:
    """Get the global database optimizer instance."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = DatabaseOptimizer()
    return _optimizer_instance
