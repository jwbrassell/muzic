# Music Streaming App

A Flask-based music streaming application with playlist management, subscriber tracking, and ad integration capabilities.

## Features

- Music streaming with visualizer
- Playlist management
- Subscriber system
- Ad integration
- Admin interface
- Multiple visualization styles (bars, circles, waves)

## Setup

### Prerequisites

- Python 3.x
- SQLite3

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd music_streaming_app
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

5. Initialize the database:
```bash
sqlite3 instance/database.db < schema.sql
```

6. Create media directory:
```bash
mkdir -p media
```

## Development

1. Start the development server:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Production Configuration

For production deployment:

1. Update `.env`:
```
FLASK_ENV=production
FLASK_DEBUG=0
```

2. Use a production WSGI server:
```bash
gunicorn app:app
```

## Project Structure

- `/static` - Static assets (JS, CSS, images)
  - `/js` - JavaScript files including visualizer
  - `/css` - Stylesheets
- `/templates` - HTML templates
- `/media` - Music files storage (created during setup)
- `/docs` - Project documentation
- `app.py` - Main application file
- `config.py` - Configuration settings
- `schema.sql` - Database schema

## Documentation

Additional documentation can be found in the `/docs` directory:
- [API Documentation](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Feature Details](docs/FEATURES.md)
- [Setup Guide](docs/SETUP.md)

## License

[Your License Here]
