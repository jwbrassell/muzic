from celery import Celery
from ..core.config import get_settings

# Get settings
settings = get_settings()

# Initialize Celery
celery = Celery(
    'tapfornerd',
    broker=settings.app.celery_broker_url,
    backend=settings.app.celery_result_backend,
    include=[
        'app.tasks.media',
        'app.tasks.analytics',
        'app.tasks.maintenance'
    ]
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    
    # Task routing
    task_routes={
        'app.tasks.media.*': {'queue': 'media'},
        'app.tasks.analytics.*': {'queue': 'analytics'},
        'app.tasks.maintenance.*': {'queue': 'maintenance'}
    },
    
    # Task scheduling
    beat_schedule={
        'cleanup-temp-files': {
            'task': 'app.tasks.maintenance.cleanup_temp_files',
            'schedule': 3600.0,  # every hour
        },
        'update-analytics': {
            'task': 'app.tasks.analytics.update_campaign_stats',
            'schedule': 300.0,  # every 5 minutes
        },
        'scan-media-directory': {
            'task': 'app.tasks.media.scan_media_directory',
            'schedule': 1800.0,  # every 30 minutes
        },
        'verify-file-integrity': {
            'task': 'app.tasks.maintenance.verify_file_integrity',
            'schedule': 86400.0,  # daily
        },
        'generate-daily-reports': {
            'task': 'app.tasks.analytics.generate_daily_reports',
            'schedule': 86400.0,  # daily
            'args': (),
            'kwargs': {'send_email': True},
            'options': {'queue': 'analytics'}
        }
    },
    
    # Result backend settings
    result_expires=86400,  # results expire in 1 day
    
    # Worker settings
    worker_prefetch_multiplier=1,  # disable prefetching
    worker_max_tasks_per_child=1000,  # restart worker after 1000 tasks
    
    # Error handling
    task_annotations={
        '*': {
            'rate_limit': '10/s',
            'max_retries': 3,
            'default_retry_delay': 180  # 3 minutes
        }
    }
)

# Optional configuration to be read from environment variables
celery.conf.update(
    broker_url=settings.app.celery_broker_url,
    result_backend=settings.app.celery_result_backend,
    imports=('app.tasks.media', 'app.tasks.analytics', 'app.tasks.maintenance'),
)

if __name__ == '__main__':
    celery.start()
