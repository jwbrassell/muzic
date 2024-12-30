import os
from app.core.database import get_db, file_exists_by_checksum
from app.core.files import clean_filename, clean_filepath, calculate_file_checksum
from app.core.config import get_settings

def scan_directory(media_dir, db, found_files, errors):
    """Recursively scan a directory for media files."""
    settings = get_settings()
    try:
        # Walk through directory recursively
        for root, dirs, files in os.walk(media_dir):
            print(f"Scanning directory: {root}")
            print(f"Found {len(files)} files")
            
            for file in files:
                try:
                    print(f"Processing file: {file}")
                    # Skip macOS metadata files
                    if file.startswith('._'):
                        print(f"Skipping macOS metadata file: {file}")
                        continue
                        
                    # Check file extension
                    ext = file.split('.')[-1].lower() if '.' in file else ''
                    print(f"File extension: {ext}")
                    
                    if ext not in settings.AUDIO_EXTENSIONS and ext not in settings.VIDEO_EXTENSIONS:
                        print(f"Skipping file with unsupported extension: {ext}")
                        continue
                    
                    media_type = 'audio' if ext in settings.AUDIO_EXTENSIONS else 'video'
                    full_path = os.path.abspath(os.path.join(root, file))
                    
                    if not os.path.isfile(full_path):
                        print(f"Not a file: {full_path}")
                        continue
                    
                    # Clean the filepath and get clean filename
                    clean_path = clean_filepath(full_path)
                    clean_name = clean_filename(file)
                    
                    # Calculate checksum
                    checksum = calculate_file_checksum(full_path)
                    
                    # Check if file already exists by checksum or cleaned path
                    if file_exists_by_checksum(checksum, clean_path):
                        print(f"Skipping duplicate file: {file}")
                        continue
                    
                    print(f"Processing media file: {full_path}")
                    
                    # Use clean filename as title
                    title = os.path.splitext(clean_name)[0]
                    artist = 'TapForNerd'  # Always set artist as TapForNerd
                    
                    print(f"Adding to database: {title} by {artist}")
                        
                    # Add to database with checksum and clean path
                    cursor = db.execute('''
                        INSERT OR REPLACE INTO media (file_path, type, title, artist, checksum)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (clean_path, media_type, title, artist, checksum))
                    
                    # Verify the insert was successful
                    if cursor.rowcount > 0:
                        found_files.append({
                            'path': full_path,
                            'type': media_type,
                            'title': title,
                            'artist': artist
                        })
                    else:
                        error_msg = f"Failed to insert {file} into database"
                        print(error_msg)
                        errors.append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error processing {file}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
                    
    except Exception as e:
        error_msg = f"Error scanning directory {media_dir}: {str(e)}"
        print(error_msg)
        errors.append(error_msg)

def scan_media():
    """Scan all configured media directories."""
    settings = get_settings()
    found_files = []
    errors = []
    db = get_db()
    
    try:
        # Start transaction
        db.execute('BEGIN')
        
        # First, verify the media directories exist
        for media_dir in settings.MEDIA_DIRS:
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
                print(f"Created media directory: {media_dir}")
                continue
            
            # Recursively scan the directory
            scan_directory(media_dir, db, found_files, errors)
        
        # If we got here without errors, commit the transaction
        db.commit()
        print("Successfully committed all changes to database")
        
        return {
            'message': 'Media scan completed',
            'files_found': len(found_files),
            'files': found_files,
            'errors': errors if errors else None
        }
        
    except Exception as e:
        if db:
            db.rollback()
            print("Rolled back database changes due to error")
        error_msg = f"Error during media scan: {str(e)}"
        print(error_msg)
        return {
            'error': error_msg,
            'files_found': len(found_files),
            'files': found_files,
            'errors': errors
        }

def process_upload(file, path):
    """Process an uploaded file."""
    settings = get_settings()
    db = get_db()
    
    try:
        # Skip macOS metadata files
        if os.path.basename(path).startswith('._'):
            print(f"Skipping macOS metadata file: {path}")
            return None
            
        ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if ext not in settings.AUDIO_EXTENSIONS and ext not in settings.VIDEO_EXTENSIONS:
            return {'error': f'Unsupported file type: {file.filename}'}

        # Determine media type
        media_type = 'audio' if ext in settings.AUDIO_EXTENSIONS else 'video'
        
        # Create directory structure matching the source
        dir_path = os.path.dirname(path)
        if dir_path:
            save_dir = os.path.join(settings.MEDIA_DIRS[0], dir_path)
        else:
            save_dir = os.path.join(settings.MEDIA_DIRS[0], media_type)
        os.makedirs(save_dir, exist_ok=True)
        
        # Clean and use original filename
        filename = clean_filename(os.path.basename(path))
        save_path = os.path.join(save_dir, filename)
        
        # Save the file
        file.save(save_path)
        
        # Clean the filepath and get clean filename
        clean_path = clean_filepath(save_path)
        
        # Calculate checksum
        checksum = calculate_file_checksum(save_path)
        
        # Check if file already exists by checksum or cleaned path
        if file_exists_by_checksum(checksum, clean_path):
            os.remove(save_path)  # Remove the duplicate file
            print(f"Skipping duplicate file: {filename}")
            return None
        
        # Use clean filename as title, TapForNerd as artist
        title = os.path.splitext(filename)[0]
        artist = 'TapForNerd'
        
        # Add to database with checksum and clean path
        cursor = db.execute('''
            INSERT OR REPLACE INTO media (file_path, type, title, artist, checksum)
            VALUES (?, ?, ?, ?, ?)
        ''', (clean_path, media_type, title, artist, checksum))
        
        if cursor.rowcount > 0:
            return filename
        else:
            return {'error': f'Failed to insert {filename} into database'}
            
    except Exception as e:
        return {'error': f'Error processing {file.filename}: {str(e)}'}
