from flask import Blueprint
from flask_sock import Sock
import json
from typing import Dict, Set
import threading
from datetime import datetime

ws_api = Blueprint('ws_api', __name__)
sock = Sock()

# Store active WebSocket connections
active_connections: Dict[str, Set] = {
    'media': set(),
    'playlist': set(),
    'monitoring': set()
}
connection_lock = threading.Lock()

def broadcast_event(channel: str, event_type: str, data: dict):
    """Broadcast event to all connected media clients."""
    message = json.dumps({
        'type': event_type,
        **data
    })
    with connection_lock:
        dead_connections = set()
        for ws in active_connections[channel]:
            try:
                ws.send(message)
            except Exception:
                dead_connections.add(ws)
        
        # Clean up dead connections
        for ws in dead_connections:
            active_connections[channel].remove(ws)

def broadcast_media_event(event_type: str, data: dict):
    """Broadcast event to all connected media clients."""
    broadcast_event('media', event_type, data)

def broadcast_monitoring_event(event_type: str, data: dict):
    """Broadcast event to all connected monitoring clients."""
    broadcast_event('monitoring', event_type, data)

@sock.route('/ws/media')
def media_socket(ws):
    """Handle media WebSocket connections."""
    try:
        with connection_lock:
            active_connections['media'].add(ws)
        
        while True:
            message = ws.receive()
            if message is None:
                break
            
            try:
                data = json.loads(message)
                pass
            except json.JSONDecodeError:
                continue
    
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    
    finally:
        with connection_lock:
            active_connections['media'].discard(ws)

@sock.route('/ws/monitoring')
def monitoring_socket(ws):
    """Handle monitoring WebSocket connections."""
    try:
        with connection_lock:
            active_connections['monitoring'].add(ws)
        
        while True:
            message = ws.receive()
            if message is None:
                break
            
            try:
                data = json.loads(message)
                pass
            except json.JSONDecodeError:
                continue
    
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    
    finally:
        with connection_lock:
            active_connections['monitoring'].discard(ws)

def notify_upload_progress(upload_id: str, progress: int):
    """Notify clients about upload progress."""
    broadcast_media_event('upload_progress', {
        'upload_id': upload_id,
        'progress': progress
    })

def notify_processing_status(media_id: int, status: str):
    """Notify clients about media processing status."""
    broadcast_media_event('processing_status', {
        'media_id': media_id,
        'status': status
    })

def notify_media_added(media: dict):
    """Notify clients about new media added."""
    broadcast_media_event('media_added', {
        'media': media
    })

def notify_media_updated(media: dict):
    """Notify clients about media updates."""
    broadcast_media_event('media_updated', {
        'media': media
    })

def notify_media_deleted(media_id: int):
    """Notify clients about media deletion."""
    broadcast_media_event('media_deleted', {
        'media_id': media_id
    })

def notify_system_metrics(metrics: dict):
    """Notify monitoring clients about system metrics."""
    broadcast_monitoring_event('system_metrics', {
        'metrics': metrics
    })

def notify_health_status(status: dict):
    """Notify monitoring clients about health status changes."""
    broadcast_monitoring_event('health_status', {
        'status': status
    })

def notify_error_event(error_type: str, details: str):
    """Notify monitoring clients about system errors."""
    broadcast_monitoring_event('error', {
        'type': error_type,
        'details': details,
        'timestamp': datetime.now().isoformat()
    })

def notify_cache_stats(hit_rate: float, error_count: int):
    """Notify monitoring clients about cache statistics."""
    broadcast_monitoring_event('cache_stats', {
        'hit_rate': hit_rate,
        'error_count': error_count
    })
