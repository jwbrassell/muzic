import os
import shutil
import tempfile
from typing import Optional, Tuple
import subprocess
import json
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

class MediaProcessor:
    """Processor for media file operations and transformations."""
    
    FFMPEG_FORMATS = {
        'mp3': ['-codec:a', 'libmp3lame', '-q:a', '2'],
        'ogg': ['-codec:a', 'libvorbis', '-q:a', '4'],
        'wav': ['-codec:a', 'pcm_s16le'],
        'flac': ['-codec:a', 'flac']
    }

    def __init__(self, db: Database):
        self.db = db
        self.logger = media_logger
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            self.logger.error("ffmpeg not found. Media processing will be limited.")
            raise RuntimeError("ffmpeg is required for media processing")

    @log_function_call(media_logger)
    def process_upload(self, file_path: str, target_format: str = None) -> Optional[str]:
        """Process an uploaded file, converting if necessary."""
        actual_path = self._find_media_file(file_path)
        if not actual_path:
            self.logger.error(f"File not found: {file_path}")
            return None

        try:
            # Get current format
            current_format = Path(actual_path).suffix[1:].lower()
            
            # If no target format specified, use current format
            target_format = target_format or current_format
            
            if target_format not in self.FFMPEG_FORMATS:
                self.logger.error(f"Unsupported format: {target_format}")
                return None
            
            # Generate processed path
            processed_dir = os.path.join(os.path.dirname(os.path.dirname(actual_path)), 'processed')
            os.makedirs(processed_dir, exist_ok=True)
            processed_path = os.path.join(processed_dir, os.path.basename(actual_path))
            
            # If formats match, just copy the file
            if current_format == target_format:
                shutil.copy2(actual_path, processed_path)
                self._normalize_audio(processed_path)
                return processed_path
            
            # Otherwise convert the file
            processed_path = self._convert_format(actual_path, target_format)
            if processed_path:
                self._normalize_audio(processed_path)
                return processed_path
            return None

        except Exception as e:
            self.logger.error(f"Error processing upload {file_path}: {str(e)}")
            return None

    @log_error(media_logger)
    def _convert_format(self, file_path: str, target_format: str) -> Optional[str]:
        """Convert file to target format using ffmpeg."""
        actual_path = self._find_media_file(file_path)
        if not actual_path:
            self.logger.error(f"File not found: {file_path}")
            return None

        # Generate output path in processed directory
        processed_dir = os.path.join(os.path.dirname(os.path.dirname(actual_path)), 'processed')
        os.makedirs(processed_dir, exist_ok=True)
        output_path = os.path.join(processed_dir, f"{Path(actual_path).stem}.{target_format}")
        
        try:
            cmd = [
                'ffmpeg', '-i', actual_path, 
                *self.FFMPEG_FORMATS[target_format],
                '-y',  # Overwrite output file if exists
                output_path
            ]
            
            subprocess.run(cmd, 
                         capture_output=True, 
                         check=True)
            
            return output_path

        except subprocess.SubprocessError as e:
            self.logger.error(f"Conversion failed: {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return None

    @log_error(media_logger)
    def _normalize_audio(self, file_path: str) -> bool:
        """Normalize audio levels using ffmpeg-normalize."""
        actual_path = self._find_media_file(file_path)
        if not actual_path:
            self.logger.error(f"File not found: {file_path}")
            return False

        # Skip normalization for WAV files
        if actual_path.lower().endswith('.wav'):
            return True
            
        try:
            with tempfile.NamedTemporaryFile(suffix=Path(actual_path).suffix) as temp:
                cmd = [
                    'ffmpeg-normalize',
                    actual_path,
                    '-o', temp.name,
                    '-f'  # Force overwrite
                ]
                
                subprocess.run(cmd, 
                             capture_output=True, 
                             check=True)
                
                shutil.move(temp.name, file_path)
                return True

        except subprocess.SubprocessError as e:
            self.logger.error(f"Normalization failed: {str(e)}")
            return False

    def _get_output_path(self, input_path: str, target_format: str) -> str:
        """Generate output path for converted file."""
        directory = os.path.dirname(input_path)
        filename = Path(input_path).stem
        return os.path.join(directory, f"{filename}.{target_format}")

    @log_function_call(media_logger)
    def update_metadata(self, file_path: str, metadata: dict) -> bool:
        """Update media file metadata."""
        try:
            actual_path = self._find_media_file(file_path)
            if not actual_path:
                self.logger.error(f"File not found: {file_path}")
                return False

            # For WAV files, we'll skip metadata update since WAV doesn't support ID3 tags
            if actual_path.lower().endswith('.wav'):
                return True
                
            audio = None
            try:
                if actual_path.endswith('.mp3'):
                    audio = MP3(actual_path)
                    if not audio.tags:
                        audio.tags = EasyID3()
                elif actual_path.endswith('.ogg'):
                    audio = OggVorbis(actual_path)
                elif actual_path.endswith('.flac'):
                    audio = FLAC(actual_path)
                
                if audio and audio.tags:
                    if 'title' in metadata:
                        audio.tags['title'] = metadata['title']
                    if 'artist' in metadata:
                        audio.tags['artist'] = metadata['artist']
                    audio.save()
                    return True
            except Exception as e:
                self.logger.warning(f"Could not update file metadata: {str(e)}")
                # Return True anyway since we'll update the database
                return True
                
            return True

        except Exception as e:
            self.logger.error(f"Failed to update metadata: {str(e)}")
            return False

    def _find_media_file(self, file_path: str) -> Optional[str]:
        """Find media file in possible locations."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        media_dir = os.path.join(base_dir, 'media')
        
        possible_paths = [
            # Original paths
            os.path.join(media_dir, file_path),
            os.path.join(media_dir, 'processed', file_path),
            os.path.join(media_dir, 'processed', os.path.basename(file_path)),
            
            # Try absolute path
            file_path
        ]
        
        # Check if path contains year/month structure
        parts = file_path.split('/')
        if len(parts) >= 4 and parts[0] == 'processed':
            year = parts[1]
            month = parts[2]
            filename = parts[3]
            possible_paths.append(
                os.path.join(media_dir, 'processed', year, month, filename)
            )
        
        for path in possible_paths:
            if os.path.isfile(path):
                return path
                
        self.logger.error(f"Could not find file. Tried paths: {possible_paths}")
        return None

    @log_function_call(media_logger)
    def get_duration(self, file_path: str) -> Optional[float]:
        """Get media file duration in seconds."""
        try:
            actual_path = self._find_media_file(file_path)
            if not actual_path:
                self.logger.error(f"File not found: {file_path}")
                return None

            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                actual_path
            ]
            
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True, 
                                 check=True)
            
            return float(result.stdout.strip())

        except (subprocess.SubprocessError, ValueError) as e:
            self.logger.error(f"Failed to get duration: {str(e)}")
            return None

    @log_function_call(media_logger)
    def get_audio_properties(self, file_path: str) -> Optional[dict]:
        """Get audio properties like bitrate, sample rate, etc."""
        try:
            actual_path = self._find_media_file(file_path)
            if not actual_path:
                self.logger.error(f"File not found: {file_path}")
                return None

            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=bit_rate,sample_rate,channels',
                '-of', 'json',
                actual_path
            ]
            
            result = subprocess.run(cmd, 
                                 capture_output=True, 
                                 text=True, 
                                 check=True)
            
            data = json.loads(result.stdout)
            stream = data.get('streams', [{}])[0]
            
            return {
                'bitrate': int(stream.get('bit_rate', 0)),
                'sample_rate': int(stream.get('sample_rate', 0)),
                'channels': int(stream.get('channels', 0))
            }

        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to get audio properties: {str(e)}")
            return None

    @log_function_call(media_logger)
    def create_preview(self, file_path: str, duration: int = 30) -> Optional[str]:
        """Create a preview clip of specified duration."""
        try:
            actual_path = self._find_media_file(file_path)
            if not actual_path:
                self.logger.error(f"File not found: {file_path}")
                return None

            preview_path = os.path.join(
                os.path.dirname(actual_path),
                f"preview_{os.path.basename(actual_path)}"
            )
            
            cmd = [
                'ffmpeg',
                '-i', actual_path,
                '-t', str(duration),
                '-c', 'copy',
                preview_path
            ]
            
            subprocess.run(cmd, 
                         capture_output=True, 
                         check=True)
            
            return preview_path

        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to create preview: {str(e)}")
            return None
