from celery import shared_task
from celery.utils.log import get_task_logger
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from ..core.config import get_settings
from ..core.database import Database
from ..media.storage import MediaStorage

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
storage = MediaStorage(db)
logger = get_task_logger(__name__)

@shared_task(name='app.tasks.maintenance.cleanup_temp_files')
def cleanup_temp_files() -> Dict[str, int]:
    """Clean up temporary files."""
    try:
        logger.info("Starting temporary file cleanup")
        results = {
            'deleted_files': 0,
            'deleted_dirs': 0,
            'freed_space': 0
        }
        
        temp_dirs = [
            os.path.join(settings.media.upload_path, 'temp'),
            os.path.join(settings.media.upload_path, 'previews'),
            'reports/temp'
        ]
        
        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
                
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # Remove files older than 24 hours
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if (datetime.now().timestamp() - 
                            os.path.getmtime(file_path)) > (24 * 60 * 60):
                            size = os.path.getsize(file_path)
                            os.remove(file_path)
                            results['deleted_files'] += 1
                            results['freed_space'] += size
                    except OSError as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
                
                # Remove empty directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            results['deleted_dirs'] += 1
                    except OSError as e:
                        logger.error(f"Error removing directory {dir_path}: {str(e)}")
        
        logger.info(
            f"Cleanup complete: {results['deleted_files']} files, "
            f"{results['deleted_dirs']} directories, "
            f"{results['freed_space'] / (1024*1024):.2f}MB freed"
        )
        return results

    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {str(e)}")
        raise

@shared_task(name='app.tasks.maintenance.verify_file_integrity')
def verify_file_integrity() -> Dict[str, List[str]]:
    """Verify integrity of all media files."""
    try:
        logger.info("Starting file integrity verification")
        results = {
            'verified': [],
            'failed': [],
            'missing': []
        }
        
        # Get all media files
        media_files = db.fetch_all("SELECT * FROM media")
        
        for media in media_files:
            file_path = media['file_path']
            
            # Check if file exists
            if not os.path.exists(file_path):
                results['missing'].append(file_path)
                continue
            
            # Verify file integrity
            if storage.verify_file_integrity(file_path):
                results['verified'].append(file_path)
            else:
                results['failed'].append(file_path)
        
        logger.info(
            f"Verification complete: {len(results['verified'])} verified, "
            f"{len(results['failed'])} failed, {len(results['missing'])} missing"
        )
        return results

    except Exception as e:
        logger.error(f"Error verifying file integrity: {str(e)}")
        raise

from ..core.optimization import DatabaseOptimizer

@shared_task(name='app.tasks.maintenance.optimize_database')
def optimize_database() -> Dict[str, any]:
    """Optimize database performance using comprehensive optimization strategies."""
    try:
        logger.info("Starting comprehensive database optimization")
        results = {
            'before_size': 0,
            'after_size': 0,
            'indexes': {
                'created': 0,
                'stats': None
            },
            'tables': {
                'analyzed': 0,
                'stats': None
            },
            'query_planner': 'configured',
            'vacuum_performed': False
        }
        
        # Get database file size before optimization
        db_path = settings.database.path
        results['before_size'] = os.path.getsize(db_path)
        
        # Initialize optimizer
        optimizer = DatabaseOptimizer(db)
        
        # Create and update indexes
        optimizer.create_indexes()
        index_stats = optimizer.get_index_stats()
        results['indexes']['created'] = len(index_stats)
        results['indexes']['stats'] = index_stats
        
        # Analyze tables for query optimization
        optimizer.analyze_tables()
        table_stats = optimizer.get_table_stats()
        results['tables']['analyzed'] = len(table_stats)
        results['tables']['stats'] = table_stats
        
        # Configure query planner for optimal performance
        optimizer.optimize_query_planner()
        
        # Optimize database file structure
        optimizer.optimize_database()
        results['vacuum_performed'] = True
        
        # Get final database size
        results['after_size'] = os.path.getsize(db_path)
        results['size_reduction'] = results['before_size'] - results['after_size']
        
        # Log detailed results
        logger.info(
            f"Optimization complete:\n"
            f"- Size reduction: {results['size_reduction'] / (1024*1024):.2f}MB\n"
            f"- Indexes created/updated: {results['indexes']['created']}\n"
            f"- Tables analyzed: {results['tables']['analyzed']}\n"
            f"- Query planner configured: {results['query_planner']}\n"
            f"- Vacuum performed: {results['vacuum_performed']}"
        )
        return results

    except Exception as e:
        logger.error(f"Error during comprehensive database optimization: {str(e)}")
        raise

@shared_task(name='app.tasks.maintenance.cleanup_old_reports')
def cleanup_old_reports() -> Tuple[int, int]:
    """Clean up old report files."""
    try:
        logger.info("Starting report cleanup")
        deleted_files = 0
        freed_space = 0
        
        reports_dir = Path('reports')
        if not reports_dir.exists():
            return deleted_files, freed_space
        
        # Keep reports for last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for report_dir in reports_dir.iterdir():
            if not report_dir.is_dir():
                continue
            
            try:
                # Parse directory name as date
                dir_date = datetime.strptime(report_dir.name, '%Y-%m-%d')
                
                # Remove old directories
                if dir_date < cutoff_date:
                    for file in report_dir.glob('*'):
                        if file.is_file():
                            freed_space += file.stat().st_size
                            file.unlink()
                            deleted_files += 1
                    report_dir.rmdir()
            except ValueError:
                # Skip directories that don't match date format
                continue
        
        logger.info(
            f"Report cleanup complete: {deleted_files} files deleted, "
            f"{freed_space / (1024*1024):.2f}MB freed"
        )
        return deleted_files, freed_space

    except Exception as e:
        logger.error(f"Error cleaning up old reports: {str(e)}")
        raise

@shared_task(name='app.tasks.maintenance.cleanup_logs')
def cleanup_logs() -> Dict[str, int]:
    """Clean up old log entries."""
    try:
        logger.info("Starting log cleanup")
        results = {
            'ad_logs': 0,
            'system_logs': 0
        }
        
        # Clean up ad logs older than 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        deleted = db.execute(
            """
            DELETE FROM ad_logs 
            WHERE timestamp < datetime(?)
            """,
            (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),)
        ).rowcount
        results['ad_logs'] = deleted
        
        # Clean up system logs
        log_dir = Path('logs')
        if log_dir.exists():
            for log_file in log_dir.glob('*.log.*'):
                try:
                    # Parse timestamp from log filename
                    timestamp_str = log_file.suffix[1:]  # Remove leading dot
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d')
                    
                    if timestamp < cutoff_date:
                        log_file.unlink()
                        results['system_logs'] += 1
                except (ValueError, OSError) as e:
                    logger.error(f"Error processing log file {log_file}: {str(e)}")
        
        logger.info(
            f"Log cleanup complete: {results['ad_logs']} ad logs, "
            f"{results['system_logs']} system logs"
        )
        return results

    except Exception as e:
        logger.error(f"Error cleaning up logs: {str(e)}")
        raise

from ..core.optimization import DatabaseOptimizer
from ..core.cache import health_check as cache_health_check

@shared_task(name='app.tasks.maintenance.system_health_check')
def system_health_check() -> Dict[str, any]:
    """Perform comprehensive system health check including performance metrics."""
    try:
        logger.info("Starting comprehensive system health check")
        results = {
            'database': {
                'status': 'ok',
                'message': None,
                'performance': {},
                'stats': {}
            },
            'cache': {
                'status': 'ok',
                'message': None,
                'connected': False
            },
            'storage': {
                'status': 'ok',
                'message': None,
                'stats': {}
            },
            'memory': {
                'status': 'ok',
                'message': None,
                'usage': {}
            }
        }
        
        # Check database and get performance metrics
        try:
            db.execute("SELECT 1")
            optimizer = DatabaseOptimizer(db)
            
            # Get database statistics
            results['database']['stats'] = {
                'tables': optimizer.get_table_stats(),
                'indexes': optimizer.get_index_stats()
            }
            
            # Check query performance
            start_time = datetime.now()
            db.execute("PRAGMA integrity_check")
            end_time = datetime.now()
            results['database']['performance']['integrity_check_ms'] = (end_time - start_time).total_seconds() * 1000
            
        except Exception as e:
            results['database'] = {
                'status': 'error',
                'message': str(e),
                'performance': {},
                'stats': {}
            }
            
        # Check Redis cache
        try:
            results['cache']['connected'] = cache_health_check()
            if not results['cache']['connected']:
                results['cache']['status'] = 'warning'
                results['cache']['message'] = 'Redis cache is not connected'
        except Exception as e:
            results['cache'] = {
                'status': 'error',
                'message': str(e),
                'connected': False
            }
        
        # Enhanced storage check with detailed stats
        try:
            stats = storage.get_storage_stats()
            results['storage']['stats'] = stats
            available_gb = stats['available_space'] / (1024**3)
            
            # Set warning thresholds
            if available_gb < 1:
                results['storage']['status'] = 'warning'
                results['storage']['message'] = f'Low storage space: {available_gb:.2f}GB available'
            elif available_gb < 5:
                results['storage']['status'] = 'notice'
                results['storage']['message'] = f'Storage space below 5GB: {available_gb:.2f}GB available'
                
        except Exception as e:
            results['storage'] = {
                'status': 'error',
                'message': str(e),
                'stats': {}
            }
        
        # Enhanced memory check with detailed metrics
        try:
            import psutil
            memory = psutil.virtual_memory()
            results['memory']['usage'] = {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent,
                'swap_used': psutil.swap_memory().used
            }
            
            # Set warning thresholds
            if memory.percent > 90:
                results['memory']['status'] = 'warning'
                results['memory']['message'] = f'Critical memory usage: {memory.percent}%'
            elif memory.percent > 80:
                results['memory']['status'] = 'notice'
                results['memory']['message'] = f'High memory usage: {memory.percent}%'
                
        except Exception as e:
            results['memory'] = {
                'status': 'error',
                'message': str(e),
                'usage': {}
            }
        
        logger.info(f"Health check complete: {results}")
        return results

    except Exception as e:
        logger.error(f"Error performing health check: {str(e)}")
        raise
