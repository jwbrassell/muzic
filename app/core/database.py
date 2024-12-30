import sqlite3
import os
import json
from flask import current_app, g
from app.core.config import get_settings
from app.core.files import clean_filepath

def dict_from_row(row):
    """Convert a sqlite3.Row to a dictionary."""
    if row is None:
        return None
    return dict(zip(row.keys(), row))

class Database:
    """Database wrapper class for SQLite operations."""
    
    def __init__(self, db_path):
        """Initialize database connection."""
        self.db_path = db_path
        self._connection = None

    @property
    def connection(self):
        """Get database connection, creating it if needed."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def execute(self, query, params=()):
        """Execute a query and return the cursor."""
        return self.connection.execute(query, params)

    def fetch_one(self, query, params=()):
        """Execute a query and fetch one result."""
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetch_all(self, query, params=()):
        """Execute a query and fetch all results."""
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def insert(self, table, data):
        """Insert a record into a table."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, list(data.values()))
        self.connection.commit()
        return cursor.lastrowid

    def update(self, table, values, where):
        """Update records in a table."""
        set_clause = ', '.join([f"{k} = ?" for k in values.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = list(values.values()) + list(where.values())
        cursor = self.execute(query, params)
        self.connection.commit()
        return cursor.rowcount > 0

    def delete(self, table, where):
        """Delete records from a table."""
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        cursor = self.execute(query, list(where.values()))
        self.connection.commit()
        return cursor.rowcount > 0

    def commit(self):
        """Commit the current transaction."""
        if self._connection:
            self._connection.commit()

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

def get_db():
    """Get database connection."""
    if 'db' not in g:
        try:
            settings = get_settings()
            # Create instance directory if it doesn't exist
            os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
            
            # Check if database exists, if not initialize it
            db_exists = os.path.exists(settings.DATABASE_PATH)
            
            print(f"Connecting to database at: {settings.DATABASE_PATH}")
            g.db = sqlite3.connect(settings.DATABASE_PATH)
            g.db.row_factory = sqlite3.Row
            
            # Initialize database if it doesn't exist
            if not db_exists:
                print("Database doesn't exist, initializing...")
                init_db()
                print("Database initialized successfully")
            
            # Test the connection
            cursor = g.db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print("Available tables:", [table[0] for table in tables])
            
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            raise
            
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with required tables."""
    db = get_db()
    schema_path = os.path.join(current_app.root_path, '..', 'schema.sql')
    with open(schema_path, mode='r') as f:
        db.cursor().executescript(f.read())
    
    # Add checksum column if it doesn't exist
    try:
        db.execute('ALTER TABLE media ADD COLUMN checksum TEXT')
        print("Added checksum column to media table")
    except sqlite3.OperationalError:
        print("Checksum column already exists")
    
    db.commit()

def file_exists_by_checksum(checksum, clean_path):
    """Check if a file with the same checksum or cleaned path exists in the database."""
    db = get_db()
    cursor = db.execute('SELECT id FROM media WHERE checksum = ? OR file_path = ?', 
                       [checksum, clean_path])
    return cursor.fetchone() is not None

def get_playlist_state():
    """Get current playlist state from database."""
    db = get_db()
    state = db.execute('SELECT * FROM playlist_state ORDER BY id DESC LIMIT 1').fetchone()
    if state:
        return {
            'current_playlist': state['playlist_id'],
            'current_position': state['current_position'],
            'last_ad_position': state['last_ad_position'],
            'is_repeat': bool(state['is_repeat']),
            'is_shuffle': bool(state['is_shuffle']),
            'shuffle_queue': json.loads(state['shuffle_queue']) if state['shuffle_queue'] else []
        }
    return {
        'current_playlist': None,
        'current_position': 0,
        'last_ad_position': 0,
        'is_repeat': True,
        'is_shuffle': False,
        'shuffle_queue': []
    }

def save_playlist_state(state):
    """Save current playlist state to database."""
    db = get_db()
    db.execute('DELETE FROM playlist_state')  # Clear old state
    db.execute('''
        INSERT INTO playlist_state 
        (playlist_id, current_position, last_ad_position, is_repeat, is_shuffle, shuffle_queue)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [
        state['current_playlist'],
        state['current_position'],
        state['last_ad_position'],
        state['is_repeat'],
        state['is_shuffle'],
        json.dumps(state['shuffle_queue'])
    ])
    db.commit()

def init_app(app):
    """Initialize database hooks with the Flask app."""
    app.teardown_appcontext(close_db)
