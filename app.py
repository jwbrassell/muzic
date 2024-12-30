from flask import Flask
from flask_cors import CORS
from flask_sock import Sock
import os
from app.core.config import get_settings
from app.core.database import init_db
from app.api.media import media_api
from app.api.playlist import playlist_api
from app.api.tags import tags_api
from app.api.ads import ads_api
from app.admin import admin
from app.routes import routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static')
    settings = get_settings()
    
    # Configure app
    app.config.from_mapping(
        DATABASE_PATH=settings.DATABASE_PATH,
        MEDIA_DIRS=settings.MEDIA_DIRS,
        AUDIO_EXTENSIONS=settings.AUDIO_EXTENSIONS,
        VIDEO_EXTENSIONS=settings.VIDEO_EXTENSIONS,
        HOST=settings.HOST,
        PORT=settings.PORT
    )

    # Initialize CORS
    CORS(app)
    CORS(app, resources={
        r"/ws/*": {"origins": "*"},
        r"/api/*": {"origins": "*"}
    })

    # Initialize Flask-Sock
    sock = Sock(app)

    # Register blueprints
    app.register_blueprint(routes)
    app.register_blueprint(media_api, url_prefix='/api/v1/media')
    app.register_blueprint(playlist_api, url_prefix='/api/v1/playlist')
    app.register_blueprint(tags_api, url_prefix='/api/v1')
    app.register_blueprint(ads_api, url_prefix='/api/v1')
    app.register_blueprint(admin, url_prefix='/admin')

    # Import and register WebSocket blueprint
    from app.api.websocket import ws_api, sock as ws_sock
    app.register_blueprint(ws_api)
    ws_sock.init_app(app)

    # CLI Commands
    @app.cli.command('init-db')
    def init_db_command():
        """Clear existing data and create new tables."""
        os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
        init_db()
        print('Initialized the database.')

    @app.cli.command('scan-media')
    def scan_media_command():
        """Scan configured directories for media files."""
        from app.media.scanner import scan_media
        result = scan_media()
        if 'error' in result:
            print(f"Error during scan: {result['error']}")
        else:
            print(f"\nMedia scan complete. Added {result['files_found']} files to database.")
            if result.get('errors'):
                print("\nErrors encountered:")
                for error in result['errors']:
                    print(f"  - {error}")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'])
