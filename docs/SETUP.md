# Setup Guide for TapForNerd Radio

## Development Setup

### Prerequisites
- Python 3.x
- pip (Python package manager)
- Git
- SQLite3

### First Time Setup Steps

1. **Clone the Repository**
```bash
git clone [repository-url]
cd music_streaming_app
```

2. **Create and Activate Virtual Environment**
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
- Copy `.env.example` to `.env`
- Modify settings as needed:
  ```
  FLASK_APP=app.py
  FLASK_ENV=development  # Change to 'production' for production
  FLASK_DEBUG=1         # Set to 0 for production
  ```

5. **Initialize Database**
```bash
flask init-db
```

6. **Create Media Directory**
```bash
mkdir media
```

7. **Run Development Server**
```bash
flask run
```

### Development Guidelines
- Use the virtual environment for all development
- Run tests before committing changes
- Follow the existing code style and patterns

## Production Setup

### Additional Production Requirements
- Web server (e.g., Nginx, Apache)
- WSGI server (e.g., Gunicorn)
- SSL certificate for HTTPS

### Production Setup Steps

1. **Clone and Install**
- Follow steps 1-5 from Development Setup

2. **Production Environment Configuration**
```
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=0
```

3. **Web Server Configuration**
- Configure web server to proxy requests to the Flask application
- Set up SSL certificate
- Configure media file serving

4. **WSGI Server Setup**
```bash
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### Security Considerations
- Always use HTTPS in production
- Secure the admin interface
- Regular database backups
- Monitor system resources
- Keep dependencies updated

## Directory Structure
```
music_streaming_app/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── schema.sql          # Database schema
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── media/             # Media files directory
├── static/            # Static assets
│   ├── css/
│   └── js/
├── templates/         # HTML templates
└── docs/             # Documentation
```

## Maintenance Tasks
- Regular database backups
- Media library organization
- Log rotation
- System updates
- Security patches

## Troubleshooting
- Check logs for errors
- Verify database connections
- Confirm media directory permissions
- Test network connectivity
- Validate configuration settings
