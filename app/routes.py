from flask import Blueprint, render_template, jsonify, request, send_file, abort, send_from_directory
import os
from app.core.database import get_db
from app.core.config import get_settings
from app.media.scanner import scan_media, process_upload

routes = Blueprint('routes', __name__)
settings = get_settings()

@routes.route('/')
def index():
    """Admin interface."""
    playlist_id = request.args.get('playlist')
    if playlist_id:
        return render_template('admin.html', playlist_id=playlist_id)
    return render_template('admin.html')

@routes.route('/library')
def media_library():
    """Media library management interface."""
    return render_template('media_library.html')

@routes.route('/display')
def display():
    """Display interface for OBS."""
    return render_template('display.html')

@routes.route('/media-display')
def media_display():
    """Media display interface that supports both audio and video playback."""
    return render_template('media_display.html')

@routes.route('/static/<path:path>')
def send_static(path):
    """Serve static files."""
    try:
        return send_from_directory('static', path)
    except Exception as e:
        print(f"Error serving static file {path}: {str(e)}")
        abort(404)

@routes.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files directly."""
    try:
        # First try to find the media in the database
        db = get_db()
        media = db.execute('SELECT * FROM media WHERE file_path LIKE ?', ['%' + filename]).fetchone()
        
        if media:
            file_path = media['file_path']
            print(f"Found file in database: {file_path}")
        else:
            # Try to find in media directories
            for media_dir in settings.MEDIA_DIRS:
                possible_path = os.path.join(media_dir, filename)
                if os.path.exists(possible_path):
                    file_path = possible_path
                    print(f"Found file in media dir: {file_path}")
                    break
            else:
                print(f"File not found: {filename}")
                abort(404)
        
        if not os.path.exists(file_path):
            print(f"File not found at path: {file_path}")
            abort(404)

        # Determine mimetype based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        mimetypes = {
            # Audio types
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac',
            # Video types
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska'
        }
        mimetype = mimetypes.get(ext, 'application/octet-stream')

        # Send entire file directly
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=None,
            conditional=False,
            etag=False
        )

    except Exception as e:
        print(f"Error serving media: {str(e)}")
        abort(404)

@routes.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    paths = request.form.getlist('paths')  # Get the relative paths
    uploaded = []
    errors = []
    db = get_db()
    
    try:
        # Start transaction
        db.execute('BEGIN')
        
        for file, path in zip(files, paths):
            if not file.filename:
                continue
            
            result = process_upload(file, path)
            if result is None:
                continue
            elif isinstance(result, dict) and 'error' in result:
                errors.append(result['error'])
            else:
                uploaded.append(result)
        
        # Commit transaction if we got here
        db.commit()
        print(f"Successfully uploaded and processed {len(uploaded)} files")
        
        return jsonify({
            'message': 'Upload complete',
            'uploaded': uploaded,
            'errors': errors
        })
        
    except Exception as e:
        if db:
            db.rollback()
        error_msg = f"Error during upload: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg,
            'uploaded': uploaded,
            'errors': errors
        }), 500

@routes.route('/api/purge-library', methods=['POST'])
def purge_library():
    """Delete all entries from the media library."""
    db = get_db()
    try:
        # Start transaction
        db.execute('BEGIN')
        
        # Delete all media entries
        db.execute('DELETE FROM media')
        
        # Commit transaction
        db.commit()
        print("Successfully purged all entries from media library")
        
        return jsonify({
            'message': 'Media library purged successfully'
        })
        
    except Exception as e:
        if db:
            db.rollback()
        error_msg = f"Error purging library: {str(e)}"
        print(error_msg)
        return jsonify({
            'error': error_msg
        }), 500

@routes.route('/api/scan-media', methods=['POST'])
def scan_media_endpoint():
    """API endpoint to trigger media scan."""
    result = scan_media()
    if 'error' in result:
        return jsonify(result), 500
    return jsonify(result)
