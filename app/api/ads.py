from flask import Blueprint, jsonify, request
from app.core.database import get_db
import random

ads_api = Blueprint('ads_api', __name__)

def pick_weighted_ad():
    """Pick an ad based on weights."""
    db = get_db()
    ads = db.execute('SELECT * FROM ads WHERE active = 1').fetchall()
    if not ads:
        return None
    
    total_weight = sum(ad['weight'] for ad in ads)
    r = random.uniform(0, total_weight)
    current_weight = 0
    
    for ad in ads:
        current_weight += ad['weight']
        if r <= current_weight:
            media = db.execute('SELECT * FROM media WHERE id = ?', [ad['media_id']]).fetchone()
            return dict(media)
    
    return None

@ads_api.route('/ads', methods=['GET', 'POST'])
def handle_ads():
    """Get all ads or create a new ad."""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        media_id = data.get('media_id')
        weight = data.get('weight', 1)
        active = data.get('active', True)
        
        if not media_id:
            return jsonify({'error': 'Media ID is required'}), 400
            
        try:
            cursor = db.execute('''
                INSERT INTO ads (media_id, weight, active)
                VALUES (?, ?, ?)
            ''', [media_id, weight, active])
            db.commit()
            
            return jsonify({
                'id': cursor.lastrowid,
                'media_id': media_id,
                'weight': weight,
                'active': active
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET request
    ads = db.execute('''
        SELECT a.*, m.title, m.type, m.file_path
        FROM ads a
        JOIN media m ON a.media_id = m.id
    ''').fetchall()
    return jsonify([dict(row) for row in ads])

@ads_api.route('/ads/<int:ad_id>', methods=['PUT', 'DELETE'])
def handle_ad(ad_id):
    """Update or delete an ad."""
    db = get_db()
    
    if request.method == 'DELETE':
        db.execute('DELETE FROM ads WHERE id = ?', [ad_id])
        db.commit()
        return jsonify({'message': 'Ad deleted'})
    
    # PUT request
    data = request.get_json()
    weight = data.get('weight')
    active = data.get('active')
    
    if weight is None and active is None:
        return jsonify({'error': 'No update parameters provided'}), 400
    
    # Build update query dynamically based on provided fields
    update_fields = []
    params = []
    if weight is not None:
        update_fields.append('weight = ?')
        params.append(weight)
    if active is not None:
        update_fields.append('active = ?')
        params.append(active)
    
    params.append(ad_id)
    query = f"UPDATE ads SET {', '.join(update_fields)} WHERE id = ?"
    
    db.execute(query, params)
    db.commit()
    
    # Return updated ad
    ad = db.execute('''
        SELECT a.*, m.title, m.type, m.file_path
        FROM ads a
        JOIN media m ON a.media_id = m.id
        WHERE a.id = ?
    ''', [ad_id]).fetchone()
    
    if not ad:
        return jsonify({'error': 'Ad not found'}), 404
        
    return jsonify(dict(ad))

@ads_api.route('/ads/next')
def get_next_ad():
    """Get the next ad to play based on weights."""
    ad = pick_weighted_ad()
    if not ad:
        return jsonify({'error': 'No ads available'}), 404
    return jsonify(ad)
