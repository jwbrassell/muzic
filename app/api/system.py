from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import json

from ..core.config import get_settings
from ..core.logging import api_logger, log_function_call
from ..core.database import get_db
from ..core.monitoring import SystemMonitor

# Create Blueprint
system_api = Blueprint('system_api', __name__)

# Initialize components
settings = get_settings()
monitor = SystemMonitor()

@system_api.route('/logs', methods=['GET'])
@log_function_call(api_logger)
def get_logs():
    """Get system logs with filtering and pagination."""
    try:
        db = get_db()
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        level = request.args.get('level')
        component = request.args.get('component')
        search = request.args.get('search')
        time_range = request.args.get('time_range', '24h')

        # Calculate time filter
        now = datetime.utcnow()
        if time_range == '1h':
            start_time = now - timedelta(hours=1)
        elif time_range == '24h':
            start_time = now - timedelta(days=1)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)  # Default to 24h

        # Build query
        query = """
            SELECT * FROM logs 
            WHERE timestamp >= ?
        """
        params = [start_time.isoformat()]

        if level:
            query += " AND level = ?"
            params.append(level)

        if component:
            query += " AND component = ?"
            params.append(component)

        if search:
            query += " AND (message LIKE ? OR details LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        # Add pagination
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])

        # Get logs
        logs = db.execute(query, params).fetchall()

        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as count FROM logs 
            WHERE timestamp >= ?
        """
        count_params = [start_time.isoformat()]

        if level:
            count_query += " AND level = ?"
            count_params.append(level)

        if component:
            count_query += " AND component = ?"
            count_params.append(component)

        if search:
            count_query += " AND (message LIKE ? OR details LIKE ?)"
            count_params.extend([search_param, search_param])

        total = db.execute(count_query, count_params).fetchone()[0]

        return jsonify({
            'logs': [dict(log) for log in logs],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@system_api.route('/logs/components', methods=['GET'])
@log_function_call(api_logger)
def get_log_components():
    """Get list of all log components."""
    try:
        db = get_db()
        components = db.execute(
            """
            SELECT DISTINCT component 
            FROM logs 
            WHERE component IS NOT NULL
            ORDER BY component
            """
        ).fetchall()
        return jsonify([c['component'] for c in components])

    except Exception as e:
        api_logger.error(f"Error getting log components: {str(e)}")
        return jsonify({'error': str(e)}), 500

@system_api.route('/settings', methods=['GET'])
@log_function_call(api_logger)
def get_system_settings():
    """Get system settings."""
    try:
        db = get_db()
        # Get all settings
        settings = db.execute("SELECT * FROM settings ORDER BY category, name").fetchall()
        
        # Group by category
        categorized = {}
        for setting in settings:
            category = setting['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append({
                'name': setting['name'],
                'value': setting['value'],
                'type': setting['type'],
                'description': setting['description']
            })
        
        return jsonify(categorized)

    except Exception as e:
        api_logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@system_api.route('/settings/<category>/<name>', methods=['PUT'])
@log_function_call(api_logger)
def update_setting(category: str, name: str):
    """Update a system setting."""
    try:
        db = get_db()
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({'error': 'Value is required'}), 400

        # Verify setting exists
        setting = db.execute(
            """
            SELECT * FROM settings 
            WHERE category = ? AND name = ?
            """,
            [category, name]
        ).fetchone()
        
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404

        # Update setting
        cursor = db.execute(
            """
            UPDATE settings 
            SET value = ?
            WHERE category = ? AND name = ?
            """,
            [data['value'], category, name]
        )
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Failed to update setting'}), 500

        return jsonify({'message': 'Setting updated successfully'})

    except Exception as e:
        api_logger.error(f"Error updating setting: {str(e)}")
        return jsonify({'error': str(e)}), 500

@system_api.route('/status', methods=['GET'])
@log_function_call(api_logger)
def get_system_status():
    """Get current system status and metrics."""
    try:
        status = monitor.get_system_status()
        return jsonify(status)

    except Exception as e:
        api_logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@system_api.route('/metrics', methods=['GET'])
@log_function_call(api_logger)
def get_system_metrics():
    """Get system performance metrics."""
    try:
        # Parse time range
        time_range = request.args.get('range', '1h')
        metrics = monitor.get_metrics(time_range)
        return jsonify(metrics)

    except Exception as e:
        api_logger.error(f"Error getting metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500
