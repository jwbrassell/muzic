import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
from .config import get_settings

class CustomFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

class AppLogger:
    """Application logger with file and console output."""
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG
    ):
        self.name = name
        self.log_dir = log_dir
        self.console_level = console_level
        self.file_level = file_level
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up and configure the logger."""
        # Create logger
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)  # Capture all levels

        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)

        # Add handlers if they don't exist
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.console_level)
            console_handler.setFormatter(CustomFormatter())
            logger.addHandler(console_handler)

            # File handler - daily rotating
            log_file = os.path.join(
                self.log_dir,
                f"{self.name}.log"
            )
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when='midnight',
                interval=1,
                backupCount=30,  # Keep 30 days of logs
                encoding='utf-8'
            )
            file_handler.setLevel(self.file_level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(file_handler)

        return logger

    def get_logger(self) -> logging.Logger:
        """Get the configured logger."""
        return self.logger

class LoggerFactory:
    """Factory for creating loggers with consistent configuration."""
    
    _loggers: dict[str, logging.Logger] = {}
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        log_dir: Optional[str] = None,
        console_level: Optional[int] = None,
        file_level: Optional[int] = None
    ) -> logging.Logger:
        """Get or create a logger with the given name and configuration."""
        if name not in cls._loggers:
            settings = get_settings()
            app_logger = AppLogger(
                name=name,
                log_dir=log_dir or "logs",
                console_level=console_level or (
                    logging.DEBUG if settings.app.debug else logging.INFO
                ),
                file_level=file_level or logging.DEBUG
            )
            cls._loggers[name] = app_logger.get_logger()
        
        return cls._loggers[name]

# Create default loggers
app_logger = LoggerFactory.get_logger('app')
db_logger = LoggerFactory.get_logger('db')
media_logger = LoggerFactory.get_logger('media')
ad_logger = LoggerFactory.get_logger('ads')
api_logger = LoggerFactory.get_logger('api')
system_logger = LoggerFactory.get_logger('system')

def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with parameters and return values."""
    def decorator(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name} with args={args}, kwargs={kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} returned: {result}")
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func_name}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator

def log_error(logger: logging.Logger):
    """Decorator to log exceptions."""
    def decorator(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator
