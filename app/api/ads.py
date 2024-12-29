from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json

from ..core.config import get_settings
from ..core.logging import api_logger, log_function_call, log_error
from ..core.database import Database
from ..ads.campaign import CampaignManager
from ..ads.analytics import AdAnalytics

# Create Blueprint
ads_api = Blueprint('ads_api', __name__)

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
campaign_manager = CampaignManager(db)
ad_analytics = AdAnalytics(db)

@ads_api.route('/', methods=['GET'])
@log_function_call(api_logger)
def get_campaigns():
    """Get list of all campaigns with optional filtering."""
    try:
        # Parse query parameters
        status = request.args.get('status')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        # Build query
        query = "SELECT * FROM ad_campaigns WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if active_only:
            query += """
                AND status = 'active'
                AND (start_date IS NULL OR start_date <= datetime('now'))
                AND (end_date IS NULL OR end_date >= datetime('now'))
            """
        
        campaigns = db.fetch_all(query, tuple(params))
        return jsonify([dict(c) for c in campaigns])

    except Exception as e:
        api_logger.error(f"Error getting campaigns: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>', methods=['GET'])
@log_function_call(api_logger)
def get_campaign_details(campaign_id: int):
    """Get detailed information about a campaign."""
    try:
        details = campaign_manager.get_campaign_details(campaign_id)
        if not details:
            return jsonify({'error': 'Campaign not found'}), 404
        
        return jsonify(details)

    except Exception as e:
        api_logger.error(f"Error getting campaign details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/', methods=['POST'])
@log_function_call(api_logger)
def create_campaign():
    """Create a new campaign."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        # Parse dates if provided
        start_date = None
        end_date = None
        if 'start_date' in data:
            start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            end_date = datetime.fromisoformat(data['end_date'])
        
        campaign_id = campaign_manager.create_campaign(
            name=data['name'],
            start_date=start_date,
            end_date=end_date,
            target_percentage=data.get('target_percentage')
        )
        
        if not campaign_id:
            return jsonify({'error': 'Failed to create campaign'}), 500
        
        return jsonify({
            'id': campaign_id,
            'message': 'Campaign created successfully'
        })

    except Exception as e:
        api_logger.error(f"Error creating campaign: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>', methods=['PUT'])
@log_function_call(api_logger)
def update_campaign(campaign_id: int):
    """Update campaign details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Parse dates if provided
        start_date = None
        end_date = None
        if 'start_date' in data:
            start_date = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data:
            end_date = datetime.fromisoformat(data['end_date'])
        
        success = campaign_manager.update_campaign(
            campaign_id=campaign_id,
            name=data.get('name'),
            start_date=start_date,
            end_date=end_date,
            target_percentage=data.get('target_percentage'),
            status=data.get('status')
        )
        
        if not success:
            return jsonify({'error': 'Failed to update campaign'}), 500
        
        return jsonify({'message': 'Campaign updated successfully'})

    except Exception as e:
        api_logger.error(f"Error updating campaign: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/assets', methods=['POST'])
@log_function_call(api_logger)
def add_asset():
    """Add an asset to a campaign."""
    try:
        data = request.get_json()
        if not data or 'media_id' not in data or 'type' not in data:
            return jsonify({
                'error': 'Media ID and type are required'
            }), 400
        
        asset_id = campaign_manager.add_asset(
            campaign_id=data['campaign_id'],
            media_id=data['media_id'],
            asset_type=data['type'],
            duration=data.get('duration'),
            weight=data.get('weight', 1)
        )
        
        if not asset_id:
            return jsonify({'error': 'Failed to add asset'}), 500
        
        return jsonify({
            'id': asset_id,
            'message': 'Asset added successfully'
        })

    except Exception as e:
        api_logger.error(f"Error adding asset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/assets/<int:asset_id>', methods=['PUT'])
@log_function_call(api_logger)
def update_asset(campaign_id: int, asset_id: int):
    """Update asset properties."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        success = campaign_manager.update_asset(
            asset_id=asset_id,
            weight=data.get('weight'),
            active=data.get('active')
        )
        
        if not success:
            return jsonify({'error': 'Failed to update asset'}), 500
        
        return jsonify({'message': 'Asset updated successfully'})

    except Exception as e:
        api_logger.error(f"Error updating asset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/assets/<int:asset_id>', methods=['DELETE'])
@log_function_call(api_logger)
def remove_asset(campaign_id: int, asset_id: int):
    """Remove an asset from a campaign."""
    try:
        success = campaign_manager.remove_asset(asset_id)
        if not success:
            return jsonify({'error': 'Failed to remove asset'}), 500
        
        return jsonify({'message': 'Asset removed successfully'})

    except Exception as e:
        api_logger.error(f"Error removing asset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/metrics', methods=['GET'])
@log_function_call(api_logger)
def get_campaign_metrics(campaign_id: int):
    """Get campaign performance metrics."""
    try:
        # Parse date range
        start_date = None
        end_date = None
        if 'start_date' in request.args:
            start_date = datetime.fromisoformat(request.args['start_date'])
        if 'end_date' in request.args:
            end_date = datetime.fromisoformat(request.args['end_date'])
        
        metrics = ad_analytics.get_campaign_metrics(
            campaign_id,
            start_date,
            end_date
        )
        
        return jsonify(metrics)

    except Exception as e:
        api_logger.error(f"Error getting campaign metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/performance', methods=['GET'])
@log_function_call(api_logger)
def get_campaign_performance(campaign_id: int):
    """Get detailed campaign performance data."""
    try:
        # Parse date range
        start_date = None
        end_date = None
        if 'start_date' in request.args:
            start_date = datetime.fromisoformat(request.args['start_date'])
        if 'end_date' in request.args:
            end_date = datetime.fromisoformat(request.args['end_date'])
        
        performance = ad_analytics.get_campaign_performance(
            campaign_id,
            start_date,
            end_date
        )
        
        return jsonify(performance)

    except Exception as e:
        api_logger.error(f"Error getting campaign performance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/<int:campaign_id>/report', methods=['GET'])
@log_function_call(api_logger)
def generate_campaign_report(campaign_id: int):
    """Generate comprehensive campaign report."""
    try:
        # Parse date range
        start_date = None
        end_date = None
        if 'start_date' in request.args:
            start_date = datetime.fromisoformat(request.args['start_date'])
        if 'end_date' in request.args:
            end_date = datetime.fromisoformat(request.args['end_date'])
        
        report = ad_analytics.generate_report(
            campaign_id,
            start_date,
            end_date
        )
        
        return jsonify(report)

    except Exception as e:
        api_logger.error(f"Error generating campaign report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@ads_api.route('/compare', methods=['GET'])
@log_function_call(api_logger)
def compare_campaigns():
    """Compare metrics across multiple campaigns."""
    try:
        campaign_ids = request.args.getlist('campaign_ids')
        metric = request.args.get('metric', 'impressions')
        
        if not campaign_ids:
            return jsonify({'error': 'Campaign IDs are required'}), 400
        
        # Convert to integers
        campaign_ids = [int(cid) for cid in campaign_ids]
        
        # Parse date range
        start_date = None
        end_date = None
        if 'start_date' in request.args:
            start_date = datetime.fromisoformat(request.args['start_date'])
        if 'end_date' in request.args:
            end_date = datetime.fromisoformat(request.args['end_date'])
        
        comparison = ad_analytics.get_comparative_metrics(
            campaign_ids,
            metric,
            start_date,
            end_date
        )
        
        return jsonify(comparison)

    except Exception as e:
        api_logger.error(f"Error comparing campaigns: {str(e)}")
        return jsonify({'error': str(e)}), 500
