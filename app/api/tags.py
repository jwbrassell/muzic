from flask import Blueprint, jsonify, request
from app.core.database import get_db

tags_api = Blueprint('tags_api', __name__)

@tags_api.route('/tags', methods=['GET', 'POST'])
def handle_tags():
    """Get all tags or create a new tag."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Tag name is required'}), 400
            
        try:
            cursor = db.execute('INSERT INTO tags (name) VALUES (?)', [name])
            db.commit()
            return jsonify({
                'id': cursor.lastrowid,
                'name': name
            })
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Tag already exists'}), 409
    
    # GET request
    tags = db.execute('SELECT * FROM tags').fetchall()
    return jsonify([dict(row) for row in tags])

@tags_api.route('/media/<int:media_id>/tags', methods=['GET', 'POST'])
def handle_media_tags(media_id):
    """Get or add tags for a media item."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        tag_names = data.get('tags', [])
        
        if not tag_names:
            return jsonify({'error': 'Tags are required'}), 400
            
        added_tags = []
        for tag_name in tag_names:
            # First try to get existing tag
            tag = db.execute('SELECT * FROM tags WHERE name = ?', [tag_name]).fetchone()
            
            # Create tag if it doesn't exist
            if not tag:
                cursor = db.execute('INSERT INTO tags (name) VALUES (?)', [tag_name])
                tag_id = cursor.lastrowid
            else:
                tag_id = tag['id']
                
            # Add tag to media if not already added
            try:
                db.execute('INSERT INTO media_tags (media_id, tag_id) VALUES (?, ?)',
                          [media_id, tag_id])
                added_tags.append({'id': tag_id, 'name': tag_name})
            except sqlite3.IntegrityError:
                # Tag already exists for this media, skip it
                continue
                
        db.commit()
        return jsonify(added_tags)
    
    # GET request
    tags = db.execute('''
        SELECT t.* FROM tags t
        JOIN media_tags mt ON t.id = mt.tag_id
        WHERE mt.media_id = ?
    ''', [media_id]).fetchall()
    return jsonify([dict(row) for row in tags])

@tags_api.route('/media/<int:media_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_media_tag(media_id, tag_id):
    """Remove a tag from a media item."""
    db = get_db()
    db.execute('DELETE FROM media_tags WHERE media_id = ? AND tag_id = ?',
               [media_id, tag_id])
    db.commit()
    return jsonify({'message': 'Tag removed'})

@tags_api.route('/media/by-tag/<int:tag_id>')
def get_media_by_tag(tag_id):
    """Get all media items with a specific tag."""
    db = get_db()
    media = db.execute('''
        SELECT m.* FROM media m
        JOIN media_tags mt ON m.id = mt.media_id
        WHERE mt.tag_id = ?
    ''', [tag_id]).fetchall()
    return jsonify([dict(row) for row in media])
