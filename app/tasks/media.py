from celery import shared_task
from celery.utils.log import get_task_logger
import os
import shutil
from typing import Optional, List
from datetime import datetime

from ..core.config import get_settings
from ..core.database import Database
from ..media.scanner import MediaScanner
from ..media.processor import MediaProcessor
from ..media.storage import MediaStorage

# Initialize components
settings = get_settings()
db = Database(settings.database.path)
scanner = MediaScanner(db)
processor = MediaProcessor(db)
storage = MediaStorage(db)
logger = get_task_logger(__name__)

@shared_task(bind=True, name='app.tasks.media.process_upload')
def process_upload(self, file_path: str, target_format: Optional[str] = None) -> Optional[str]:
    """Process an uploaded media file."""
    try:
        logger.info(f"Processing upload: {file_path}")
        
        # Process file
        processed_path = processor.process_upload(file_path, target_format)
        if not processed_path:
            raise Exception("Failed to process file")
        
        # Extract metadata
        metadata = scanner.process_file(processed_path)
        if not metadata:
            raise Exception("Failed to extract metadata")
        
        # Store file
        stored_path = storage.store_file(processed_path, metadata)
        if not stored_path:
            raise Exception("Failed to store file")
        
        # Update metadata with stored path
        metadata['file_path'] = stored_path
        db.insert('media', metadata)
        
        # Clean up temporary files
        if os.path.exists(file_path):
            os.remove(file_path)
        if processed_path != stored_path and os.path.exists(processed_path):
            os.remove(processed_path)
        
        logger.info(f"Successfully processed upload: {stored_path}")
        return stored_path

    except Exception as e:
        logger.error(f"Error processing upload {file_path}: {str(e)}")
        self.retry(exc=e, countdown=60)  # Retry after 1 minute

@shared_task(name='app.tasks.media.scan_media_directory')
def scan_media_directory() -> tuple[int, int, int]:
    """Scan media directory for new files."""
    try:
        logger.info("Starting media directory scan")
        
        # Update database with new files
        new_files, updated_files = scanner.update_database()
        
        # Clean up database entries for missing files
        deleted_files = scanner.cleanup_database()
        
        logger.info(
            f"Scan complete: {new_files} new, "
            f"{updated_files} updated, {deleted_files} deleted"
        )
        return new_files, updated_files, deleted_files

    except Exception as e:
        logger.error(f"Error scanning media directory: {str(e)}")
        raise

@shared_task(bind=True, name='app.tasks.media.process_bulk_upload')
def process_bulk_upload(self, file_paths: List[str], target_format: Optional[str] = None) -> dict:
    """Process multiple uploaded files."""
    results = {
        'successful': [],
        'failed': []
    }
    
    for file_path in file_paths:
        try:
            stored_path = process_upload.delay(file_path, target_format).get()
            if stored_path:
                results['successful'].append({
                    'original': file_path,
                    'stored': stored_path
                })
            else:
                results['failed'].append({
                    'path': file_path,
                    'error': 'Processing failed'
                })
        except Exception as e:
            results['failed'].append({
                'path': file_path,
                'error': str(e)
            })
    
    return results

@shared_task(name='app.tasks.media.generate_previews')
def generate_previews(media_id: int) -> bool:
    """Generate preview versions of media files."""
    try:
        # Get media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            raise Exception(f"Media {media_id} not found")
        
        # Generate preview
        preview_path = processor.create_preview(
            media['file_path'],
            duration=30  # 30-second preview
        )
        
        if not preview_path:
            raise Exception("Failed to generate preview")
        
        # Store preview path in database
        db.update(
            'media',
            {'preview_path': preview_path},
            {'id': media_id}
        )
        
        return True

    except Exception as e:
        logger.error(f"Error generating preview for media {media_id}: {str(e)}")
        raise

@shared_task(name='app.tasks.media.cleanup_previews')
def cleanup_previews() -> int:
    """Clean up old preview files."""
    try:
        preview_dir = os.path.join(settings.media.upload_path, 'previews')
        deleted = 0
        
        # Get all preview files
        for root, _, files in os.walk(preview_dir):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file is older than 7 days
                if (datetime.now().timestamp() - 
                    os.path.getmtime(file_path)) > (7 * 24 * 60 * 60):
                    try:
                        os.remove(file_path)
                        deleted += 1
                    except OSError as e:
                        logger.error(f"Error deleting preview {file_path}: {str(e)}")
        
        return deleted

    except Exception as e:
        logger.error(f"Error cleaning up previews: {str(e)}")
        raise

@shared_task(name='app.tasks.media.optimize_storage')
def optimize_storage() -> dict:
    """Optimize media storage."""
    try:
        stats = storage.get_storage_stats()
        results = {
            'before': stats,
            'optimized': 0,
            'space_saved': 0
        }
        
        # Get all media files
        media_files = db.fetch_all(
            """
            SELECT * FROM media 
            WHERE type IN ('mp3', 'wav', 'ogg', 'flac')
            """
        )
        
        for media in media_files:
            try:
                # Get current file size
                original_size = os.path.getsize(media['file_path'])
                
                # Process file with optimization
                optimized_path = processor.process_upload(
                    media['file_path'],
                    target_format='mp3'  # Convert to MP3 for optimization
                )
                
                if optimized_path:
                    new_size = os.path.getsize(optimized_path)
                    
                    # If new file is smaller, replace old file
                    if new_size < original_size:
                        shutil.move(optimized_path, media['file_path'])
                        results['optimized'] += 1
                        results['space_saved'] += (original_size - new_size)
                    else:
                        os.remove(optimized_path)
                
            except Exception as e:
                logger.error(f"Error optimizing {media['file_path']}: {str(e)}")
        
        # Get final stats
        results['after'] = storage.get_storage_stats()
        return results

    except Exception as e:
        logger.error(f"Error optimizing storage: {str(e)}")
        raise

@shared_task(bind=True, name='app.tasks.media.verify_media')
def verify_media(self, media_id: int) -> bool:
    """Verify media file integrity."""
    try:
        # Get media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            raise Exception(f"Media {media_id} not found")
        
        # Verify file integrity
        if not storage.verify_file_integrity(media['file_path']):
            # Log error and trigger repair
            logger.error(f"File integrity check failed for {media['file_path']}")
            repair_media.delay(media_id)
            return False
        
        return True

    except Exception as e:
        logger.error(f"Error verifying media {media_id}: {str(e)}")
        self.retry(exc=e, countdown=300)  # Retry after 5 minutes

@shared_task(name='app.tasks.media.repair_media')
def repair_media(media_id: int) -> bool:
    """Attempt to repair corrupted media file."""
    try:
        # Get media info
        media = db.fetch_one(
            "SELECT * FROM media WHERE id = ?",
            (media_id,)
        )
        if not media:
            raise Exception(f"Media {media_id} not found")
        
        # Process file to attempt repair
        repaired_path = processor.process_upload(
            media['file_path'],
            target_format=media['type']
        )
        
        if not repaired_path:
            raise Exception("Failed to repair file")
        
        # Verify repaired file
        metadata = scanner.process_file(repaired_path)
        if not metadata:
            raise Exception("Failed to verify repaired file")
        
        # Replace corrupted file
        shutil.move(repaired_path, media['file_path'])
        
        # Update metadata
        db.update('media', metadata, {'id': media_id})
        
        logger.info(f"Successfully repaired media {media_id}")
        return True

    except Exception as e:
        logger.error(f"Error repairing media {media_id}: {str(e)}")
        raise
