from flask import Blueprint, jsonify, request, send_file
from app.core.database import get_db
from app.media.scanner import scan_media
from app.core.files import move_media_file
import os

media_api = Blueprint('media_api', __name__)

def get_pagination_params():
    """Extract pagination parameters from request."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    offset = (page - 1) * per_page
    return page, per_page, offset

@media_api.route('/library')
def get_media_library():
    """Get media library with pagination and filtering."""
    db = get_db()
    page, per_page, offset = get_pagination_params()
    
    # Get filter parameters
    search_query = request.args.get('q', '')
    media_type = request.args.get('type', '')
    
    # Build query
    query = 'SELECT * FROM media WHERE 1=1'
    params = []
    
    if search_query:
        query += ' AND (title LIKE ? OR artist LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if media_type:
        query += ' AND type = ?'
        params.append(media_type)
    
    # Get total count
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total = db.execute(count_query, params).fetchone()[0]
    
    # Add pagination
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    # Execute query
    media = db.execute(query, params).fetchall()
    result = [dict(row) for row in media]
    
    return jsonify({
        'items': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@media_api.route('/tags')
def get_media_tags():
    """Get media tags with pagination."""
    db = get_db()
    page, per_page, offset = get_pagination_params()
    
    # Get total count
    total = db.execute('SELECT COUNT(*) FROM tags').fetchone()[0]
    
    # Get paginated tags with usage count
    tags = db.execute(
        '''
        SELECT t.id, t.name, COUNT(mt.media_id) as count 
        FROM tags t
        LEFT JOIN media_tags mt ON t.id = mt.tag_id
        GROUP BY t.id, t.name
        ORDER BY count DESC, t.name
        LIMIT ? OFFSET ?
        ''',
        [per_page, offset]
    ).fetchall()
    
    result = [dict(row) for row in tags]
    
    return jsonify({
        'items': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@media_api.route('/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def media_operations(id):
    """Handle operations on individual media items."""
    db = get_db()
    
    if request.method == 'GET':
        # Get media details including tags
        media = db.execute('''
            SELECT m.*, GROUP_CONCAT(t.name) as tags
            FROM media m
            LEFT JOIN media_tags mt ON m.id = mt.media_id
            LEFT JOIN tags t ON mt.tag_id = t.id
            WHERE m.id = ?
            GROUP BY m.id
        ''', [id]).fetchone()
        
        if not media:
            return jsonify({'error': 'Media not found'}), 404
            
        result = dict(media)
        result['tags'] = result['tags'].split(',') if result['tags'] else []
        return jsonify(result)
        
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update basic media info
        db.execute('''
            UPDATE media 
            SET title = ?, artist = ?
            WHERE id = ?
        ''', [data.get('title'), data.get('artist'), id])
        
        # Update tags if provided
        if 'tags' in data:
            # First delete existing tags
            db.execute('DELETE FROM media_tags WHERE media_id = ?', [id])
            
            # Then add new tags
            for tag_name in data['tags']:
                # Insert or get tag
                db.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', [tag_name])
                tag = db.execute('SELECT id FROM tags WHERE name = ?', [tag_name]).fetchone()
                
                # Link tag to media
                if tag:
                    db.execute('''
                        INSERT OR IGNORE INTO media_tags (media_id, tag_id) 
                        VALUES (?, ?)
                    ''', [id, tag['id']])
        
        db.commit()
        return jsonify({'success': True})
        
    elif request.method == 'DELETE':
        # Get media file path before deletion
        media = db.execute('SELECT file_path FROM media WHERE id = ?', [id]).fetchone()
        if not media:
            return jsonify({'error': 'Media not found'}), 404
            
        # Delete from database
        db.execute('DELETE FROM media_tags WHERE media_id = ?', [id])
        db.execute('DELETE FROM media WHERE id = ?', [id])
        db.commit()
        
        # Delete file if it exists
        try:
            if os.path.exists(media['file_path']):
                os.remove(media['file_path'])
        except Exception as e:
            return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500
            
        return jsonify({'success': True})

@media_api.route('/<int:id>/download')
def download_media(id):
    """Download media file."""
    db = get_db()
    media = db.execute('SELECT file_path, title FROM media WHERE id = ?', [id]).fetchone()
    
    if not media:
        return jsonify({'error': 'Media not found'}), 404
        
    if not os.path.exists(media['file_path']):
        return jsonify({'error': 'Media file not found'}), 404
        
    return send_file(
        media['file_path'],
        as_attachment=True,
        download_name=os.path.basename(media['file_path'])
    )

@media_api.route('/<int:id>/move', methods=['POST'])
def move_media(id):
    """Move media file to a different folder."""
    data = request.get_json()
    if not data or 'folder' not in data:
        return jsonify({'error': 'Destination folder is required'}), 400
        
    db = get_db()
    media = db.execute('SELECT file_path FROM media WHERE id = ?', [id]).fetchone()
    
    if not media:
        return jsonify({'error': 'Media not found'}), 404
        
    try:
        new_path = move_media_file(media['file_path'], data['folder'])
        db.execute('UPDATE media SET file_path = ? WHERE id = ?', [new_path, id])
        db.commit()
        return jsonify({'success': True, 'new_path': new_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@media_api.route('/scan', methods=['POST'])
def scan_media_endpoint():
    """Scan media directory for new files."""
    try:
        result = scan_media()
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        return jsonify({
            'success': True,
            'new_files': result['files_found'],
            'files': result['files'],
            'errors': result['errors']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
