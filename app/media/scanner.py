import os
import hashlib
from typing import Generator, Optional
import mimetypes
from pathlib import Path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC

from ..core.config import get_settings
from ..core.logging import media_logger, log_function_call, log_error
from ..core.database import Database

class MediaScanner:
    """Scanner for media files with metadata extraction."""
    
    CHUNK_SIZE = 8192  # For file reading
    SUPPORTED_FORMATS = {
        '.mp3': MP3,
        '.wav': WAVE,
        '.ogg': OggVorbis,
        '.flac': FLAC
    }

    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger

    @log_function_call(media_logger)
    def scan_directory(self, directory: str) -> Generator[dict, None, None]:
        """Scan directory for media files and yield their metadata."""
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if self._is_supported_format(file_path):
                        metadata = self._extract_metadata(file_path)
                        if metadata:
                            yield metadata
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")

    @log_error(media_logger)
    def process_file(self, file_path: str) -> Optional[dict]:
        """Process a single media file and return its metadata."""
        if not self._is_supported_format(file_path):
            return None
        return self._extract_metadata(file_path)

    def _is_supported_format(self, file_path: str) -> bool:
        """Check if the file format is supported."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    @log_error(media_logger)
    def _extract_metadata(self, file_path: str) -> Optional[dict]:
        """Extract metadata from a media file."""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            media_class = self.SUPPORTED_FORMATS[ext]
            media_file = media_class(file_path)
            
            # Get duration using processor
            from .processor import MediaProcessor
            processor = MediaProcessor(self.db)
            duration = processor.get_duration(file_path)
            
            metadata = {
                'file_path': file_path,
                'type': ext[1:],  # Remove leading dot
                'title': self._get_title(media_file, file_path),
                'artist': self._get_artist(media_file),
                'duration': duration,  # Add duration to metadata
                'checksum': self._calculate_checksum(file_path)
            }
            
            return metadata
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {file_path}: {str(e)}")
            return None

    def _get_title(self, media_file: mutagen.FileType, file_path: str) -> str:
        """Extract title from media file, fallback to filename."""
        try:
            if isinstance(media_file, MP3) and media_file.tags:
                return media_file.tags.get('TIT2', [Path(file_path).stem])[0]
            elif hasattr(media_file, 'tags') and media_file.tags:
                return media_file.tags.get('TITLE', [Path(file_path).stem])[0]
        except Exception:
            pass
        return Path(file_path).stem

    def _get_artist(self, media_file: mutagen.FileType) -> str:
        """Extract artist from media file, fallback to 'Unknown'."""
        try:
            if isinstance(media_file, MP3) and media_file.tags:
                return media_file.tags.get('TPE1', ['Unknown'])[0]
            elif hasattr(media_file, 'tags') and media_file.tags:
                return media_file.tags.get('ARTIST', ['Unknown'])[0]
        except Exception:
            pass
        return 'Unknown'

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(self.CHUNK_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @log_function_call(media_logger)
    def update_database(self, directory: str = None) -> tuple[int, int]:
        """Update database with media files from directory."""
        directory = directory or get_settings().media.upload_path
        new_files = 0
        updated_files = 0

        for metadata in self.scan_directory(directory):
            # Check if file exists in database
            existing = self.db.fetch_one(
                "SELECT id, checksum FROM media WHERE file_path = ?",
                (metadata['file_path'],)
            )

            if not existing:
                self.db.insert('media', metadata)
                new_files += 1
            elif existing['checksum'] != metadata['checksum']:
                self.db.update(
                    'media',
                    metadata,
                    {'id': existing['id']}
                )
                updated_files += 1

        self.logger.info(
            f"Database update complete: {new_files} new files, "
            f"{updated_files} updated files"
        )
        return new_files, updated_files

    @log_function_call(media_logger)
    def cleanup_database(self) -> int:
        """Remove database entries for files that no longer exist."""
        deleted = 0
        media_files = self.db.fetch_all("SELECT id, file_path FROM media")
        
        for media in media_files:
            if not os.path.exists(media['file_path']):
                self.db.delete('media', {'id': media['id']})
                deleted += 1

        self.logger.info(f"Database cleanup complete: {deleted} entries removed")
        return deleted
