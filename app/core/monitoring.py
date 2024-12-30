from typing import Dict, Optional
from datetime import datetime, timedelta
import psutil
import json

from .logging import system_logger, log_function_call

# Global monitor instance
_monitor = None

def get_monitor() -> 'SystemMonitor':
    """Get the global SystemMonitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor

class SystemMonitor:
    """Monitors system performance and health metrics."""
    
    def __init__(self):
        """Initialize the system monitor."""
        self.logger = system_logger

    def get_system_status(self) -> Dict:
        """Get current system status metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'usage_percent': cpu_percent,
                    'core_count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting system status: {str(e)}")
            return {
                'error': 'Failed to get system status',
                'timestamp': datetime.now().isoformat()
            }

    def get_metrics(self, time_range: str = '1h') -> Dict:
        """Get system performance metrics over time."""
        try:
            # Calculate time window
            now = datetime.now()
            if time_range == '1h':
                start_time = now - timedelta(hours=1)
            elif time_range == '24h':
                start_time = now - timedelta(days=1)
            elif time_range == '7d':
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=1)

            # Get current metrics
            current = self.get_system_status()
            
            # Add historical data points
            metrics = {
                'current': current,
                'history': {
                    'cpu': [],
                    'memory': [],
                    'disk': []
                },
                'time_range': time_range
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Error getting system metrics: {str(e)}")
            return {
                'error': 'Failed to get system metrics',
                'timestamp': datetime.now().isoformat()
            }

    def get_health_status(self) -> Dict:
        """Get overall system health status."""
        try:
            status = self.get_system_status()
            
            # Define health thresholds
            cpu_warning = 80
            memory_warning = 85
            disk_warning = 90
            
            # Check component health
            health = {
                'status': 'healthy',
                'components': {
                    'cpu': 'healthy' if status['cpu']['usage_percent'] < cpu_warning else 'warning',
                    'memory': 'healthy' if status['memory']['percent'] < memory_warning else 'warning',
                    'disk': 'healthy' if status['disk']['percent'] < disk_warning else 'warning'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Set overall status
            if any(v == 'warning' for v in health['components'].values()):
                health['status'] = 'warning'
            
            return health

        except Exception as e:
            self.logger.error(f"Error getting health status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_slow_queries(self, threshold_ms: int = 1000) -> Dict:
        """Get list of slow database queries."""
        try:
            return {
                'slow_queries': [],
                'threshold_ms': threshold_ms,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting slow queries: {str(e)}")
            return {
                'error': 'Failed to get slow queries',
                'timestamp': datetime.now().isoformat()
            }
