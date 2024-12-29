from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
import os

from .core.config import get_settings
from .core.logging import app_logger, log_function_call
from .core.database import Database

# Import blueprints
from .api.media import media_api
from .api.playlist import playlist_api
from .api.ads import ads_api
from .admin import admin

@log_function_call(app_logger)
def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../templates')),
                static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../static')))
    
    # Enable CORS
    CORS(app)
    
    # Load configuration
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        settings = get_settings()
        app.config.from_mapping(
            SECRET_KEY=settings.app.secret_key,
            DATABASE=settings.database.path,
            UPLOAD_FOLDER=settings.media.upload_path,
            MAX_CONTENT_LENGTH=settings.media.max_file_size
        )
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Initialize database
    db = Database(app.config['DATABASE'])
    
    # Ensure required directories exist
    settings.ensure_directories()
    
    # Register API blueprints with distinct prefixes
    app.register_blueprint(media_api, url_prefix='/api/v1/media')
    app.register_blueprint(playlist_api, url_prefix='/api/v1/playlists')
    app.register_blueprint(ads_api, url_prefix='/api/v1/ads')
    
    # Register admin blueprint
    app.register_blueprint(admin)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    # Register error handlers
    @app.errorhandler(400)
    def bad_request(e):
        app_logger.error(f"Bad request: {str(e)}")
        return {'error': 'Bad request'}, 400

    @app.errorhandler(404)
    def not_found(e):
        app_logger.error(f"Not found: {str(e)}")
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def server_error(e):
        app_logger.error(f"Server error: {str(e)}")
        return {'error': 'Internal server error'}, 500

    # Register routes
    @app.route('/')
    def index():
        """Admin interface."""
        return redirect(url_for('admin.dashboard'))

    @app.route('/display')
    def display():
        """Display interface for OBS."""
        return render_template('display.html')

    @app.route('/media-display')
    def media_display():
        """Media display interface that supports both audio and video playback."""
        return render_template('media_display.html')

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}

    # Initialize database schema
    with app.app_context():
        try:
            db.initialize_schema(settings.database.schema_path)
            app_logger.info("Database schema initialized successfully")
        except Exception as e:
            app_logger.error(f"Error initializing database schema: {str(e)}")
            raise

    return app

def init_app():
    """Initialize the application for command line interface."""
    app = create_app()
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    settings = get_settings()
    app.run(
        host=settings.app.host,
        port=settings.app.port,
        debug=settings.app.debug
    )
