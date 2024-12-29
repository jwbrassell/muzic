import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import hashlib

from ..core.config import get_settings
from ..core.logging import media_logger, log_function_call, log_error
from ..core.database import Database

class MediaStorage:
    """Handles media file storage operations."""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger
        self.base_path = get_settings().media.upload_path
        self._ensure_storage_structure()

    def _ensure_storage_structure(self) -> None:
        """Ensure required storage directories exist."""
        directories = [
            self.base_path,
            os.path.join(self.base_path, 'uploads'),
            os.path.join(self.base_path, 'processed'),
            os.path.join(self.base_path, 'archive'),
            os.path.join(self.base_path, 'temp')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @log_function_call(media_logger)
    def store_file(self, source_path: str, metadata: dict = None) -> Optional[str]:
        """Store a file in the media storage system."""
        if not os.path.exists(source_path):
            self.logger.error(f"Source file not found: {source_path}")
            return None

        try:
            # Generate storage path
            filename = self._generate_filename(source_path, metadata)
            relative_path = self._get_storage_path(filename)
            absolute_path = os.path.join(self.base_path, relative_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            
            # Copy file to storage
            shutil.copy2(source_path, absolute_path)
            
            return relative_path

        except Exception as e:
            self.logger.error(f"Failed to store file {source_path}: {str(e)}")
            return None

    def _generate_filename(self, source_path: str, metadata: dict = None) -> str:
        """Generate a unique filename for storage."""
        # Use metadata if available, otherwise use original filename
        if metadata and metadata.get('title') and metadata.get('artist'):
            base_name = f"{metadata['artist']} - {metadata['title']}"
        else:
            base_name = Path(source_path).stem
            
        # Clean filename
        base_name = "".join(c for c in base_name if c.isalnum() or c in "- _")
        base_name = base_name.strip()
        
        # Add extension
        extension = Path(source_path).suffix
        filename = f"{base_name}{extension}"
        
        # Add timestamp if file exists
        if os.path.exists(os.path.join(self.base_path, filename)):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_{timestamp}{extension}"
            
        return filename

    def _get_storage_path(self, filename: str) -> str:
        """Generate hierarchical storage path."""
        # Create year/month based directory structure
        date = datetime.now()
        return os.path.join(
            'processed',
            str(date.year),
            f"{date.month:02d}",
            filename
        )

    @log_function_call(media_logger)
    def move_to_archive(self, file_path: str) -> Optional[str]:
        """Move a file to the archive directory."""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None

            # Generate archive path
            archive_path = os.path.join(
                'archive',
                datetime.now().strftime("%Y/%m"),
                os.path.basename(file_path)
            )
            absolute_archive_path = os.path.join(self.base_path, archive_path)
            
            # Ensure archive directory exists
            os.makedirs(os.path.dirname(absolute_archive_path), exist_ok=True)
            
            # Move file to archive
            shutil.move(file_path, absolute_archive_path)
            
            return archive_path

        except Exception as e:
            self.logger.error(f"Failed to archive {file_path}: {str(e)}")
            return None

    @log_function_call(media_logger)
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            absolute_path = os.path.join(self.base_path, file_path)
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to delete {file_path}: {str(e)}")
            return False

    @log_function_call(media_logger)
    def cleanup_storage(self, days: int = 30) -> Tuple[int, List[str]]:
        """Clean up temporary and old archived files."""
        deleted_count = 0
        failed_deletes = []
        
        try:
            # Clean temp directory
            temp_dir = os.path.join(self.base_path, 'temp')
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete temp file {file}: {str(e)}")
                    failed_deletes.append(file_path)

            # Clean old archives
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            archive_dir = os.path.join(self.base_path, 'archive')
            
            for root, _, files in os.walk(archive_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getmtime(file_path) < cutoff_date:
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to delete archive file {file}: {str(e)}")
                        failed_deletes.append(file_path)

            # Remove empty directories
            for root, dirs, _ in os.walk(archive_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except Exception as e:
                        self.logger.error(f"Failed to remove empty directory {dir_path}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Storage cleanup failed: {str(e)}")

        return deleted_count, failed_deletes

    @log_function_call(media_logger)
    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        try:
            total_size = 0
            file_count = 0
            type_counts = {}
            
            for root, _, files in os.walk(self.base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # Get file size
                        size = os.path.getsize(file_path)
                        total_size += size
                        file_count += 1
                        
                        # Count file types
                        ext = os.path.splitext(file)[1].lower()
                        type_counts[ext] = type_counts.get(ext, 0) + 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")

            return {
                'total_size': total_size,
                'total_files': file_count,
                'type_distribution': type_counts,
                'available_space': shutil.disk_usage(self.base_path).free
            }

        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {str(e)}")
            return {}

    @log_function_call(media_logger)
    def verify_file_integrity(self, file_path: str) -> bool:
        """Verify file integrity using stored checksum."""
        try:
            # Get stored checksum
            media_record = self.db.fetch_one(
                "SELECT checksum FROM media WHERE file_path = ?",
                (file_path,)
            )
            
            if not media_record:
                self.logger.error(f"No database record for {file_path}")
                return False

            # Calculate current checksum
            sha256_hash = hashlib.sha256()
            with open(os.path.join(self.base_path, file_path), "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
            current_checksum = sha256_hash.hexdigest()

            return current_checksum == media_record['checksum']

        except Exception as e:
            self.logger.error(f"Failed to verify {file_path}: {str(e)}")
            return False
