from flask import render_template, redirect, url_for, request, flash, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from . import admin
from ..core.database import Database
from ..core.config import get_settings
from ..ads.campaign import CampaignManager
from ..ads.analytics import AdAnalytics

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
campaign_manager = CampaignManager(db)
ad_analytics = AdAnalytics(db)

@admin.route('/')
def index():
    """Admin dashboard."""
    return redirect(url_for('admin.dashboard'))

@admin.route('/dashboard')
def dashboard():
    """Main admin dashboard."""
    return render_template('admin/dashboard.html', now=datetime.now())

@admin.route('/media/library')
def media_library():
    """Media library management interface."""
    return render_template('admin/media/library.html')

@admin.route('/media/upload')
def media_upload():
    """Media upload interface."""
    return render_template('admin/media/upload.html')

@admin.route('/media/tags')
def media_tags():
    """Media tags management."""
    return render_template('admin/media/tags.html')

@admin.route('/playlist/list')
def playlist_list():
    """List all playlists."""
    return render_template('admin/playlist/list.html')

@admin.route('/playlist/create')
def playlist_create():
    """Create new playlist."""
    return render_template('admin/playlist/create.html')

@admin.route('/ad/assets')
def ad_assets():
    """Ad assets management."""
    return render_template('admin/ads/assets.html')

@admin.route('/ad/schedules')
def ad_schedules():
    """Ad schedules management."""
    return render_template('admin/ads/schedules.html')

@admin.route('/ad/analytics')
def ad_analytics_dashboard():
    """Ad analytics dashboard."""
    return render_template('admin/ads/analytics.html')

@admin.route('/system/status')
def system_status():
    """System status dashboard."""
    return render_template('admin/system/status.html')

@admin.route('/system/logs')
def system_logs():
    """System logs viewer."""
    return render_template('admin/system/logs.html')

@admin.route('/system/settings')
def system_settings():
    """System settings interface."""
    return render_template('admin/system/settings.html')

@admin.route('/help')
def help():
    """Help documentation."""
    return render_template('admin/help.html')

@admin.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files."""
    media_base = os.path.join(current_app.root_path, '..', 'media')
    
    # Try to find the file in various media directories
    possible_paths = [
        os.path.join(media_base, filename),
        os.path.join(media_base, 'processed', filename),
        os.path.join(media_base, 'processed', os.path.basename(filename))
    ]
    
    # Handle year/month directory structure
    if not any(os.path.isfile(path) for path in possible_paths):
        # Try to find in year/month structure
        try:
            # Extract year and month from path if present
            parts = filename.split('/')
            if len(parts) >= 4 and parts[0] == 'processed':
                year = parts[1]
                month = parts[2]
                file_name = parts[3]
                year_month_path = os.path.join(media_base, 'processed', year, month, file_name)
                if os.path.isfile(year_month_path):
                    possible_paths.append(year_month_path)
        except Exception as e:
            current_app.logger.error(f"Error parsing year/month path: {str(e)}")
    
    for path in possible_paths:
        if os.path.isfile(path):
            directory = os.path.dirname(path)
            basename = os.path.basename(path)
            
            # Get file extension
            ext = os.path.splitext(path)[1].lower()
            
            # Set content type based on file extension
            content_type = None
            if ext in {'.mp3', '.m4a'}:
                content_type = 'audio/mpeg'
            elif ext == '.wav':
                content_type = 'audio/wav'
            elif ext == '.ogg':
                content_type = 'audio/ogg'
            elif ext == '.mp4':
                content_type = 'video/mp4'
            elif ext == '.webm':
                content_type = 'video/webm'
            elif ext == '.mkv':
                content_type = 'video/x-matroska'
            
            # Get file size for range requests
            file_size = os.path.getsize(path)
            
            # Handle range requests for media streaming
            range_header = request.headers.get('Range')
            if range_header:
                try:
                    # Parse range header
                    byte1, byte2 = range_header.replace('bytes=', '').split('-')
                    byte1 = int(byte1)
                    byte2 = min(int(byte2) if byte2 else file_size - 1, file_size - 1)
                    
                    # Calculate content length
                    content_length = byte2 - byte1 + 1
                    
                    # Send partial content
                    response = send_from_directory(
                        directory, 
                        basename,
                        mimetype=content_type,
                        conditional=True
                    )
                    response.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
                    response.headers.add('Accept-Ranges', 'bytes')
                    response.headers.add('Content-Length', content_length)
                    response.status_code = 206
                    return response
                    
                except (ValueError, TypeError):
                    # If range header is invalid, serve full file
                    pass
            
            # Serve full file
            response = send_from_directory(
                directory, 
                basename,
                mimetype=content_type,
                conditional=True
            )
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Length', file_size)
            return response
    
    return jsonify({'error': 'File not found'}), 404

@admin.route('/logout')
def logout():
    """Logout user."""
    # Add logout logic here
    return redirect(url_for('admin.index'))

@admin.route('/campaigns')
def campaign_list():
    """List all campaigns."""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    search = request.args.get('q')
    
    # Build query
    query = "SELECT * FROM ad_campaigns WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    
    # Get total count
    count_query = query.replace("*", "COUNT(*) as count")
    total = db.fetch_one(count_query, tuple(params))['count']
    
    # Add pagination
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    # Get campaigns
    campaigns = db.fetch_all(query, tuple(params))
    
    # Enhance campaign data
    for campaign in campaigns:
        # Get asset count
        assets = db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM ad_assets 
            WHERE campaign_id = ?
            """,
            (campaign['id'],)
        )
        campaign['asset_count'] = assets['count']
        
        # Get metrics
        metrics = ad_analytics.get_campaign_metrics(campaign['id'])
        campaign.update({
            'impressions': metrics.get('impressions', 0),
            'completion_rate': metrics.get('completion_rate', 0),
            'progress': min(
                round(metrics.get('impressions', 0) / campaign['target_percentage'], 2) * 100 
                if campaign['target_percentage'] else 100,
                100
            )
        })
    
    # Create pagination object
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'iter_pages': lambda: range(1, ((total + per_page - 1) // per_page) + 1)
    }
    
    return render_template(
        'admin/campaigns/list.html',
        campaigns=campaigns,
        pagination=pagination
    )

@admin.route('/campaigns/create', methods=['GET'])
def campaign_create():
    """Show campaign creation form."""
    return render_template('admin/campaigns/create.html')

@admin.route('/campaigns/<int:campaign_id>')
def campaign_details(campaign_id):
    """Show campaign details."""
    details = campaign_manager.get_campaign_details(campaign_id)
    if not details:
        flash('Campaign not found', 'error')
        return redirect(url_for('admin.campaign_list'))
    
    # Get performance metrics
    metrics = ad_analytics.get_campaign_metrics(campaign_id)
    
    # Get hourly distribution
    distribution = ad_analytics.get_time_distribution(
        campaign_id,
        interval='hour'
    )
    
    # Get asset performance
    asset_performance = ad_analytics.get_asset_performance(campaign_id)
    
    return render_template(
        'admin/campaigns/details.html',
        campaign=details['campaign'],
        assets=details['assets'],
        schedules=details['schedules'],
        metrics=metrics,
        distribution=distribution,
        asset_performance=asset_performance
    )

@admin.route('/campaigns/<int:campaign_id>/edit', methods=['GET'])
def campaign_edit(campaign_id):
    """Show campaign edit form."""
    details = campaign_manager.get_campaign_details(campaign_id)
    if not details:
        flash('Campaign not found', 'error')
        return redirect(url_for('admin.campaign_list'))
    
    return render_template(
        'admin/campaigns/edit.html',
        campaign=details['campaign'],
        assets=details['assets'],
        schedules=details['schedules']
    )

@admin.route('/campaigns/<int:campaign_id>/assets')
def campaign_assets(campaign_id):
    """Show campaign assets management."""
    details = campaign_manager.get_campaign_details(campaign_id)
    if not details:
        flash('Campaign not found', 'error')
        return redirect(url_for('admin.campaign_list'))
    
    # Get asset performance
    performance = ad_analytics.get_asset_performance(campaign_id)
    
    return render_template(
        'admin/campaigns/assets.html',
        campaign=details['campaign'],
        assets=details['assets'],
        performance=performance
    )

@admin.route('/campaigns/<int:campaign_id>/schedule')
def campaign_schedule(campaign_id):
    """Show campaign schedule management."""
    details = campaign_manager.get_campaign_details(campaign_id)
    if not details:
        flash('Campaign not found', 'error')
        return redirect(url_for('admin.campaign_list'))
    
    return render_template(
        'admin/campaigns/schedule.html',
        campaign=details['campaign'],
        schedules=details['schedules']
    )

@admin.route('/campaigns/<int:campaign_id>/analytics')
def campaign_analytics(campaign_id):
    """Show campaign analytics."""
    details = campaign_manager.get_campaign_details(campaign_id)
    if not details:
        flash('Campaign not found', 'error')
        return redirect(url_for('admin.campaign_list'))
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Generate report
    report = ad_analytics.generate_report(
        campaign_id,
        start_date,
        end_date
    )
    
    return render_template(
        'admin/campaigns/analytics.html',
        campaign=details['campaign'],
        report=report,
        start_date=start_date,
        end_date=end_date
    )

@admin.route('/quick-stats')
def quick_stats():
    """Get quick statistics for the admin dashboard."""
    try:
        # Get active campaigns count
        active_campaigns = db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM ad_campaigns 
            WHERE status = 'active'
            """
        )['count']
        
        # Get total impressions today
        today_impressions = db.fetch_one(
            """
            SELECT COUNT(*) as count 
            FROM ad_logs 
            WHERE DATE(timestamp) = DATE(CURRENT_TIMESTAMP)
            """
        )['count']
        
        # Get average completion rate
        completion_rate = db.fetch_one(
            """
            SELECT AVG(CASE WHEN completed = 1 THEN 1 ELSE 0 END) * 100 as rate
            FROM ad_logs
            WHERE DATE(timestamp) = DATE(CURRENT_TIMESTAMP)
            """
        )['rate'] or 0
        
        # Get asset count
        asset_count = db.fetch_one(
            "SELECT COUNT(*) as count FROM ad_assets"
        )['count']
        
        return jsonify({
            'active_campaigns': active_campaigns,
            'today_impressions': today_impressions,
            'completion_rate': round(completion_rate, 1),
            'total_assets': asset_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting quick stats: {str(e)}")
        return jsonify({
            'error': 'Failed to get statistics'
        }), 500

@admin.route('/recent-activity')
def recent_activity():
    """Get recent activity for the admin dashboard."""
    try:
        # Get recent ad plays
        logs = db.fetch_all(
            """
            SELECT 
                l.*,
                c.name as campaign_name,
                a.type as asset_type,
                m.title as asset_title
            FROM ad_logs l
            JOIN ad_campaigns c ON l.campaign_id = c.id
            JOIN ad_assets a ON l.asset_id = a.id
            JOIN media m ON a.media_id = m.id
            ORDER BY l.timestamp DESC
            LIMIT 10
            """
        )
        
        return jsonify([dict(log) for log in logs])
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent activity: {str(e)}")
        return jsonify({
            'error': 'Failed to get recent activity'
        }), 500

# Helper functions
def format_number(value):
    """Format number for display (e.g., 1000 -> 1K)."""
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value/1_000:.1f}K"
    return str(value)

# Register template filters
admin.add_app_template_filter(format_number)
