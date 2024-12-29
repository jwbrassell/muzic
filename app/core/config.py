import os
from typing import Any, Dict
from dataclasses import dataclass
import json

@dataclass
class DatabaseConfig:
    path: str
    schema_path: str

@dataclass
class MediaConfig:
    upload_path: str
    allowed_extensions: set[str]
    max_file_size: int  # in bytes

@dataclass
class AdConfig:
    min_frequency: int
    max_frequency: int
    default_weight: int
    asset_path: str

@dataclass
class CacheConfig:
    redis_host: str
    redis_port: int
    redis_db: int
    default_timeout: int  # in seconds

@dataclass
class AppConfig:
    debug: bool
    host: str
    port: int
    secret_key: str

class Config:
    """Configuration management for the application."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration from environment and optional config file."""
        self.config_path = config_path
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from environment and config file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Base configuration
        self.database = DatabaseConfig(
            path=os.getenv('DB_PATH', os.path.join(base_dir, 'instance', 'database.db')),
            schema_path=os.getenv('SCHEMA_PATH', 'schema.sql')
        )

        self.media = MediaConfig(
            upload_path=os.getenv('MEDIA_UPLOAD_PATH', os.path.join(base_dir, 'media')),
            allowed_extensions={'mp3', 'wav', 'ogg', 'm4a', 'mp4', 'webm', 'mkv'},
            max_file_size=int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB default
        )

        self.ads = AdConfig(
            min_frequency=int(os.getenv('AD_MIN_FREQUENCY', 3)),
            max_frequency=int(os.getenv('AD_MAX_FREQUENCY', 10)),
            default_weight=int(os.getenv('AD_DEFAULT_WEIGHT', 1)),
            asset_path=os.getenv('AD_ASSET_PATH', 'media/ads/')
        )

        self.cache = CacheConfig(
            redis_host=os.getenv('CACHE_REDIS_HOST', 'localhost'),
            redis_port=int(os.getenv('CACHE_REDIS_PORT', 6379)),
            redis_db=int(os.getenv('CACHE_REDIS_DB', 0)),
            default_timeout=int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes default
        )

        self.app = AppConfig(
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', 5000)),
            secret_key=os.getenv('SECRET_KEY', 'dev')
        )

        # Override with config file if provided
        if self.config_path and os.path.exists(self.config_path):
            self._load_from_file()

    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            config_data = json.load(f)
            
            # Update configurations if present in file
            if 'database' in config_data:
                self.database = DatabaseConfig(**config_data['database'])
            if 'media' in config_data:
                self.media = MediaConfig(**config_data['media'])
            if 'ads' in config_data:
                self.ads = AdConfig(**config_data['ads'])
            if 'cache' in config_data:
                self.cache = CacheConfig(**config_data['cache'])
            if 'app' in config_data:
                self.app = AppConfig(**config_data['app'])

    def save_to_file(self, path: str = None) -> None:
        """Save current configuration to a JSON file."""
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No config file path specified")

        config_data = {
            'database': {
                'path': self.database.path,
                'schema_path': self.database.schema_path
            },
            'media': {
                'upload_path': self.media.upload_path,
                'allowed_extensions': list(self.media.allowed_extensions),
                'max_file_size': self.media.max_file_size
            },
            'ads': {
                'min_frequency': self.ads.min_frequency,
                'max_frequency': self.ads.max_frequency,
                'default_weight': self.ads.default_weight,
                'asset_path': self.ads.asset_path
            },
            'cache': {
                'redis_host': self.cache.redis_host,
                'redis_port': self.cache.redis_port,
                'redis_db': self.cache.redis_db,
                'default_timeout': self.cache.default_timeout
            },
            'app': {
                'debug': self.app.debug,
                'host': self.app.host,
                'port': self.app.port,
                'secret_key': self.app.secret_key
            }
        }

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w') as f:
            json.dump(config_data, f, indent=4)

    def get_database_url(self) -> str:
        """Get the database URL."""
        return f"sqlite:///{self.database.path}"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            os.path.dirname(self.database.path),
            self.media.upload_path,
            self.ads.asset_path
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    # Properties to maintain compatibility with root config.py
    @property
    def DATABASE_PATH(self) -> str:
        return self.database.path

    @property
    def MEDIA_DIRS(self) -> list[str]:
        return [self.media.upload_path]

    @property
    def AUDIO_EXTENSIONS(self) -> set[str]:
        return {'mp3', 'wav', 'ogg', 'm4a'}

    @property
    def VIDEO_EXTENSIONS(self) -> set[str]:
        return {'mp4', 'webm', 'mkv'}

    @property
    def HOST(self) -> str:
        return self.app.host

    @property
    def PORT(self) -> int:
        return self.app.port

# Singleton configuration instance
_config_instance = None

def get_settings() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
