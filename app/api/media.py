from typing import Dict, List, Optional
from flask import Blueprint, request, jsonify, current_app
import os
from werkzeug.utils import secure_filename

from ..core.config import get_settings
from ..core.logging import api_logger, log_function_call, log_error
from ..core.database import Database
from ..media.scanner import MediaScanner
from ..media.processor import MediaProcessor
from ..media.storage import MediaStorage

# Create Blueprint
media_api = Blueprint('media_api', __name__)

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
scanner = MediaScanner(db)
processor = MediaProcessor(db)
storage = MediaStorage(db)

@media_api.route('/library', methods=['GET'])
@log_function_call(api_logger)
def get_media_library():
    """Get list of media files with optional filtering."""
    try:
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        type_filter = request.args.get('type')
        search = request.args.get('q')
        
        # Build base query
        query = "SELECT * FROM media WHERE 1=1"
        count_query = "SELECT COUNT(*) as count FROM media WHERE 1=1"
        params = []
        
        # Add filters
        if type_filter:
            query += " AND type = ?"
            count_query += " AND type = ?"
            params.append(type_filter)
        
        if search:
            # Search in title, artist, and tags
            query += """ 
                AND (
                    title LIKE ? 
                    OR artist LIKE ? 
                    OR EXISTS (
                        SELECT 1 FROM tags t 
                        JOIN media_tags mt ON t.id = mt.tag_id 
                        WHERE mt.media_id = media.id AND t.name LIKE ?
                    )
                )
            """
            count_query += """ 
                AND (
                    title LIKE ? 
                    OR artist LIKE ? 
                    OR EXISTS (
                        SELECT 1 FROM tags t 
                        JOIN media_tags mt ON t.id = mt.tag_id 
                        WHERE mt.media_id = media.id AND t.name LIKE ?
                    )
                )
            """
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        # Get total count
        total = db.fetch_one(count_query, tuple(params))['count']
        
        # Add pagination
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        # Get media items
        items = db.fetch_all(query, tuple(params))
        
        # Get tags and additional info for each media item
        for item in items:
            # Get tags
            tags = db.fetch_all("""
                SELECT t.name 
                FROM tags t
                JOIN media_tags mt ON t.id = mt.tag_id
                WHERE mt.media_id = ?
            """, (item['id'],))
            item['tags'] = [tag['name'] for tag in tags]
            
            # Get file size and duration
            try:
                # Try to find the file in various media directories
                file_path = None
                possible_paths = [
                    os.path.join(current_app.root_path, '..', 'media', item['file_path']),
                    os.path.join(current_app.root_path, '..', 'media', 'processed', item['file_path']),
                    os.path.join(current_app.root_path, '..', 'media', 'processed', os.path.basename(item['file_path']))
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        file_path = path
                        break
                
                if file_path:
                    item['size'] = os.path.getsize(file_path)
                    item['duration'] = processor.get_duration(file_path)
                else:
                    item['size'] = 0
                    item['duration'] = 0
            except Exception as e:
                api_logger.error(f"Error getting file info: {str(e)}")
                item['size'] = 0
                item['duration'] = 0
        
        return jsonify({
            'items': [dict(item) for item in items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting media list: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/<int:media_id>', methods=['GET'])
@log_function_call(api_logger)
def get_media_details(media_id: int):
    """Get detailed information about a media file."""
    try:
        # Get basic media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        # Get tags
        tags = db.fetch_all(
            """
            SELECT t.name 
            FROM tags t
            JOIN media_tags mt ON t.id = mt.tag_id
            WHERE mt.media_id = ?
            """,
            (media_id,)
        )
        
        # Get file info
        try:
            # Try to find the file in various media directories
            file_path = None
            possible_paths = [
                os.path.join(current_app.root_path, '..', 'media', media['file_path']),
                os.path.join(current_app.root_path, '..', 'media', 'processed', media['file_path']),
                os.path.join(current_app.root_path, '..', 'media', 'processed', os.path.basename(media['file_path']))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    break
            
            if file_path:
                size = os.path.getsize(file_path)
                duration = processor.get_duration(file_path)
                properties = processor.get_audio_properties(file_path)
            else:
                size = 0
                duration = 0
                properties = None
        except Exception as e:
            api_logger.error(f"Error getting file info: {str(e)}")
            size = 0
            duration = 0
            properties = None
        
        return jsonify({
            **dict(media),
            'tags': [t['name'] for t in tags],
            'properties': properties,
            'size': size,
            'duration': duration
        })

    except Exception as e:
        api_logger.error(f"Error getting media details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/', methods=['POST'])
@log_function_call(api_logger)
def upload_media():
    """Upload media files."""
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        for file in files:
            if not file.filename:
                continue
                
            filename = secure_filename(file.filename)
            if not any(filename.endswith(ext) 
                      for ext in settings.media.allowed_extensions):
                results.append({
                    'filename': filename,
                    'error': 'Invalid file type'
                })
                continue
            
            try:
                # Save uploaded file temporarily
                temp_path = os.path.join(settings.media.upload_path, 'temp', filename)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                file.save(temp_path)
                
                # Process file
                processed_path = processor.process_upload(temp_path)
                if not processed_path:
                    results.append({
                        'filename': filename,
                        'error': 'Failed to process file'
                    })
                    continue
                
                # Extract metadata and store in database
                metadata = scanner.process_file(processed_path)
                if not metadata:
                    results.append({
                        'filename': filename,
                        'error': 'Failed to extract metadata'
                    })
                    continue
                
                # Store file
                stored_path = storage.store_file(processed_path, metadata)
                if not stored_path:
                    results.append({
                        'filename': filename,
                        'error': 'Failed to store file'
                    })
                    continue
                
                # Update metadata with stored path
                metadata['file_path'] = stored_path
                media_id = db.insert('media', metadata)
                
                # Clean up temp file
                os.remove(temp_path)
                
                results.append({
                    'filename': filename,
                    'id': media_id,
                    'message': 'File uploaded successfully',
                    **metadata
                })
                
            except Exception as e:
                results.append({
                    'filename': filename,
                    'error': str(e)
                })
        
        return jsonify(results)

    except Exception as e:
        api_logger.error(f"Error uploading media: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/<int:media_id>', methods=['PUT'])
@log_function_call(api_logger)
def update_media(media_id: int):
    """Update media metadata."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        # Try to update metadata in file, but continue even if it fails
        if 'title' in data or 'artist' in data:
            try:
                processor.update_metadata(
                    media['file_path'],
                    {
                        'title': data.get('title'),
                        'artist': data.get('artist')
                    }
                )
            except Exception as e:
                api_logger.warning(f"Failed to update file metadata: {str(e)}")
                # Continue anyway to update database
        
        # Update database
        updates = {}
        for field in ['title', 'artist']:
            if field in data:
                updates[field] = data[field]
        
        if updates:
            db.update('media', updates, {'id': media_id})
        
        # Handle tags if provided
        if 'tags' in data:
            # Remove existing tags
            db.execute(
                "DELETE FROM media_tags WHERE media_id = ?",
                (media_id,)
            )
            
            # Add new tags
            for tag_name in data['tags']:
                # Get or create tag
                tag = db.fetch_one(
                    "SELECT id FROM tags WHERE name = ?",
                    (tag_name,)
                )
                if tag:
                    tag_id = tag['id']
                else:
                    tag_id = db.insert('tags', {'name': tag_name})
                
                # Add media-tag relationship
                db.insert('media_tags', {
                    'media_id': media_id,
                    'tag_id': tag_id
                })
        
        return jsonify({'message': 'Media updated successfully'})

    except Exception as e:
        api_logger.error(f"Error updating media: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/<int:media_id>', methods=['DELETE'])
@log_function_call(api_logger)
def delete_media(media_id: int):
    """Delete a media file."""
    try:
        # Get media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            return jsonify({'error': 'Media not found'}), 404
        
        # Delete file
        success = storage.delete_file(media['file_path'])
        if not success:
            return jsonify({'error': 'Failed to delete file'}), 500
        
        # Delete from database
        db.delete('media', {'id': media_id})
        
        # Clean up tags
        db.execute(
            "DELETE FROM media_tags WHERE media_id = ?",
            (media_id,)
        )
        
        return jsonify({'message': 'Media deleted successfully'})

    except Exception as e:
        api_logger.error(f"Error deleting media: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/scan', methods=['POST'])
@log_function_call(api_logger)
def scan_media():
    """Scan media directory for new files."""
    try:
        directory = request.json.get('directory', settings.media.upload_path)
        new_files, updated_files = scanner.update_database(directory)
        deleted_files = scanner.cleanup_database()
        
        return jsonify({
            'message': 'Scan completed successfully',
            'new_files': new_files,
            'updated_files': updated_files,
            'deleted_files': deleted_files
        })

    except Exception as e:
        api_logger.error(f"Error scanning media: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/tags', methods=['GET'])
@log_function_call(api_logger)
def get_tags():
    """Get list of all tags with usage counts."""
    try:
        tags = db.fetch_all(
            """
            SELECT 
                t.name,
                COUNT(mt.media_id) as usage_count
            FROM tags t
            LEFT JOIN media_tags mt ON t.id = mt.tag_id
            GROUP BY t.id, t.name
            ORDER BY t.name
            """
        )
        return jsonify([dict(t) for t in tags])

    except Exception as e:
        api_logger.error(f"Error getting tags: {str(e)}")
        return jsonify({'error': str(e)}), 500

@media_api.route('/storage/stats', methods=['GET'])
@log_function_call(api_logger)
def get_storage_stats():
    """Get media storage statistics."""
    try:
        stats = storage.get_storage_stats()
        return jsonify(stats)

    except Exception as e:
        api_logger.error(f"Error getting storage stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
