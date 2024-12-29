from flask import Blueprint
import os
from datetime import datetime

# Get the absolute paths
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../static'))

admin = Blueprint('admin', __name__, 
                 url_prefix='/admin',
                 template_folder=template_dir,
                 static_folder=static_dir,
                 static_url_path='/static')

# Template filters
@admin.app_template_filter('format_date')
def format_date(value):
    """Format datetime object to string."""
    if not value:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')

@admin.app_template_filter('format_date_input')
def format_date_input(value):
    """Format datetime object for HTML date input."""
    if not value:
        return ''
    return value.strftime('%Y-%m-%d')

@admin.app_template_filter('format_duration')
def format_duration(seconds):
    """Format duration in seconds to MM:SS."""
    if not seconds:
        return '0:00'
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f'{minutes}:{remaining_seconds:02d}'

@admin.app_template_filter('format_number')
def format_number(value):
    """Format number with thousands separator."""
    if not value:
        return '0'
    return '{:,}'.format(value)

@admin.app_template_filter('status_color')
def status_color(status):
    """Get Bootstrap color class for status."""
    colors = {
        'active': 'success',
        'paused': 'warning',
        'draft': 'secondary',
        'completed': 'info',
        'error': 'danger'
    }
    return colors.get(status.lower(), 'secondary')

@admin.app_template_filter('asset_type_color')
def asset_type_color(type_):
    """Get Bootstrap color class for asset type."""
    colors = {
        'audio': 'primary',
        'video': 'info'
    }
    return colors.get(type_.lower(), 'secondary')

# Template globals
@admin.app_context_processor
def utility_processor():
    """Add utility functions to template context."""
    return {
        'now': datetime.utcnow,
        'format_schedule': format_schedule
    }

def format_schedule(schedule):
    """Format schedule for display."""
    if not schedule:
        return 'Not scheduled'
    
    if schedule.type == 'once':
        return f'Once at {format_date(schedule.datetime)}'
    
    if schedule.type == 'daily':
        slots = [f'{hour:02d}:00' for hour in schedule.slots]
        return f'Daily at {", ".join(slots)}'
    
    if schedule.type == 'weekly':
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        day_names = [days[day] for day in schedule.days]
        return f'{", ".join(day_names)} at {schedule.start_time}-{schedule.end_time}'
    
    return str(schedule)

from . import routes  # Import routes after Blueprint creation to avoid circular imports
