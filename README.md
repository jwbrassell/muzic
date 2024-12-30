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

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Initialize database:
```bash
flask init-db
```

6. Start Redis server:
```bash
redis-server
```

7. Run the application:
```bash
flask run
```

## Development

### Running Tests

The project includes comprehensive test suites:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit  # Unit tests
pytest tests/integration  # Integration tests
pytest tests/performance  # Performance tests

# Run with coverage report
pytest --cov=app --cov-report=html
```

### System Monitoring

The system includes built-in monitoring tools:

1. Health Check:
```bash
curl http://localhost:5000/api/system/health
```

2. System Metrics:
```bash
curl http://localhost:5000/api/system/metrics
```

3. Performance Analysis:
```bash
curl http://localhost:5000/api/system/slow-queries
```

### Database Optimization

Run database optimization:
```bash
curl -X POST http://localhost:5000/api/system/optimize
```

## Project Structure

```
music_streaming_app/
├── app/
│   ├── core/
│   │   ├── cache.py       # Redis caching system
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database operations
│   │   ├── monitoring.py  # System monitoring
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
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── performance/      # Performance tests
├── instance/             # Instance-specific files
├── logs/                 # Application logs
├── media/                # Media storage
├── static/               # Static assets
├── templates/            # HTML templates
├── .env.example         # Environment template
├── config.py            # Application config
├── pytest.ini           # Test configuration
├── requirements.txt     # Dependencies
└── schema.sql          # Database schema
```

## Performance Optimization

The system includes several performance optimization features:

1. Redis Caching
   - Response caching
   - Query result caching
   - Session data caching
   - Cache invalidation strategies

2. Database Optimization
   - Automatic index management
   - Query performance analysis
   - Connection pooling
   - Regular maintenance tasks

3. System Monitoring
   - Resource usage tracking
   - Performance metrics
   - Error monitoring
   - Health checks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
