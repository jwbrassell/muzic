# TapForNerd Radio System

A modern music streaming system with advanced ad management capabilities.

## Features

- Performance Optimization
  - Redis caching system for improved response times
  - Automated database optimization and indexing
  - Query performance monitoring
  - System health monitoring and reporting

- Media Management
  - Automatic media scanning and metadata extraction
  - Support for multiple audio formats (MP3, WAV, OGG, FLAC)
  - Media file processing and normalization
  - Hierarchical storage organization

- Playlist Management
  - Dynamic playlist creation and modification
  - Shuffle and repeat modes
  - Position tracking and state management
  - Smart media queuing

- Ad Management
  - Campaign creation and scheduling
  - Asset management with multiple media types
  - Targeting and frequency controls
  - Performance analytics and reporting

- RESTful API
  - Comprehensive endpoints for all features
  - Error handling and logging
  - CORS support
  - Health monitoring

## System Requirements

- Python 3.9+
- FFmpeg
- Redis (for caching and background tasks)
- SQLite3

## First Time Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/music_streaming_app.git
cd music_streaming_app
```

2. Run the setup script with administrator privileges:

On macOS/Linux:
```bash
sudo python setup.py
```

On Windows (Run PowerShell as Administrator):
```powershell
python setup.py
```

The setup script automatically:
- Checks and installs Python requirements
- Installs and configures Redis and FFmpeg
- Creates virtual environment and installs dependencies
- Sets up environment variables
- Initializes the database
- Starts all required services
- Launches the application

3. Access the application at http://localhost:5000

The setup script handles everything - no manual installation or configuration required!

## Project Structure

```
music_streaming_app/
├── app/
│   ├── core/
│   │   ├── database.py    # Database operations
│   │   ├── config.py      # Configuration management
│   │   ├── logging.py     # Logging setup
│   │   ├── cache.py       # Redis caching system
│   │   └── optimization.py # Database optimization
│   ├── media/
│   │   ├── scanner.py     # Media file scanning
│   │   ├── processor.py   # Media processing
│   │   └── storage.py     # File storage management
│   ├── playlist/
│   │   ├── manager.py     # Playlist operations
│   │   └── scheduler.py   # Ad scheduling
│   ├── ads/
│   │   ├── campaign.py    # Campaign management
│   │   └── analytics.py   # Ad performance analytics
│   └── api/
│       ├── media.py       # Media endpoints
│       ├── playlist.py    # Playlist endpoints
│       └── ads.py         # Ad management endpoints
├── instance/              # Instance-specific files
├── logs/                  # Application logs
├── media/                 # Media storage
│   ├── uploads/          
│   ├── processed/
│   └── archive/
├── tests/                 # Test suite
├── .env.example          # Environment template
├── config.py             # Application config
├── requirements.txt      # Dependencies
└── schema.sql           # Database schema
```

## Configuration

The system can be configured through environment variables or a configuration file. Key settings include:

- `DATABASE_PATH`: Path to SQLite database
- `MEDIA_UPLOAD_PATH`: Directory for media storage
- `MAX_FILE_SIZE`: Maximum upload file size
- `AD_MIN_FREQUENCY`: Minimum ads per session
- `AD_MAX_FREQUENCY`: Maximum ads per session
- `LOG_LEVEL`: Logging verbosity

### Performance Settings

- `CACHE_TYPE`: Cache backend type (redis)
- `CACHE_REDIS_HOST`: Redis server host
- `CACHE_REDIS_PORT`: Redis server port
- `CACHE_REDIS_DB`: Redis database number
- `CACHE_DEFAULT_TIMEOUT`: Default cache entry timeout
- `DB_POOL_SIZE`: Database connection pool size
- `DB_MAX_OVERFLOW`: Maximum pool overflow
- `DB_POOL_TIMEOUT`: Pool timeout in seconds

See `.env.example` for all available options.

## API Documentation

### Media Endpoints

- `GET /api/media`: List media files
- `POST /api/media`: Upload new media
- `GET /api/media/<id>`: Get media details
- `PUT /api/media/<id>`: Update media metadata
- `DELETE /api/media/<id>`: Delete media
- `POST /api/media/scan`: Scan for new media

### Playlist Endpoints

- `GET /api/playlists`: List playlists
- `POST /api/playlists`: Create playlist
- `GET /api/playlists/<id>`: Get playlist details
- `PUT /api/playlists/<id>`: Update playlist
- `DELETE /api/playlists/<id>`: Delete playlist
- `POST /api/playlists/<id>/items`: Add items
- `DELETE /api/playlists/<id>/items`: Remove items
- `POST /api/playlists/<id>/next`: Get next item

### Ad Campaign Endpoints

- `GET /api/campaigns`: List campaigns
- `POST /api/campaigns`: Create campaign
- `GET /api/campaigns/<id>`: Get campaign details
- `PUT /api/campaigns/<id>`: Update campaign
- `POST /api/campaigns/<id>/assets`: Add asset
- `GET /api/campaigns/<id>/metrics`: Get metrics
- `GET /api/campaigns/<id>/report`: Generate report

## Development

1. Set up development environment:
```bash
pip install -r requirements.txt
```

2. Start Redis server:
```bash
redis-server
```

3. Run tests:
```bash
pytest
```

4. Start development server:
```bash
flask run --debug
```

### Performance Monitoring

The system includes built-in performance monitoring tools:

1. Database Optimization:
```bash
flask db optimize  # Run manual database optimization
```

2. Cache Management:
```bash
flask cache clear  # Clear cache
flask cache stats  # View cache statistics
```

3. System Health Check:
```bash
flask health-check  # Run system health check
```

The health check provides detailed metrics on:
- Database performance and statistics
- Cache hit rates and connection status
- Storage usage and availability
- Memory utilization

## Production Deployment

1. Set up production environment:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
export FLASK_ENV=production
export FLASK_APP=app
# Set other production variables
```

3. Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
