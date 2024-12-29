import sqlite3
from contextlib import contextmanager
from typing import Generator, Any, Optional
import os
from datetime import datetime
from app.core.cache import cached, invalidate_cache, CacheError
from app.core.config import get_settings

class Database:
    def __init__(self, db_path: str):
        """Initialize database connection."""
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic closing."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Get a database cursor with automatic closing."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query and return the cursor."""
        with self.get_cursor() as cursor:
            return cursor.execute(query, params)

    def execute_many(self, query: str, params_list: list[tuple]) -> None:
        """Execute many queries at once."""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)

    def _generate_cache_key(self, query: str, params: tuple = ()) -> str:
        """Generate a cache key from a query and its parameters."""
        param_str = ':'.join(str(p) for p in params)
        return f"db:{hash(query)}:{hash(param_str)}"

    @cached(key_prefix='db_query', timeout=get_settings().cache.default_timeout)
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Fetch a single row with caching."""
        with self.get_cursor() as cursor:
            row = cursor.execute(query, params).fetchone()
            return dict_from_row(row) if row else None

    @cached(key_prefix='db_query', timeout=get_settings().cache.default_timeout)
    def fetch_all(self, query: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows with caching."""
        with self.get_cursor() as cursor:
            rows = cursor.execute(query, params).fetchall()
            return [dict_from_row(row) for row in rows]

    @invalidate_cache('db_query:*')
    def insert(self, table: str, data: dict) -> int:
        """Insert a row into a table and return the id."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        
        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    @invalidate_cache('db_query:*')
    def update(self, table: str, data: dict, where: dict) -> None:
        """Update rows in a table."""
        set_clause = ', '.join(f'{k} = ?' for k in data.keys())
        where_clause = ' AND '.join(f'{k} = ?' for k in where.keys())
        query = f'UPDATE {table} SET {set_clause} WHERE {where_clause}'
        
        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()) + tuple(where.values()))

    @invalidate_cache('db_query:*')
    def delete(self, table: str, where: dict) -> None:
        """Delete rows from a table."""
        where_clause = ' AND '.join(f'{k} = ?' for k in where.keys())
        query = f'DELETE FROM {table} WHERE {where_clause}'
        
        with self.get_cursor() as cursor:
            cursor.execute(query, tuple(where.values()))

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        return bool(self.fetch_one(query, (table_name,)))

    def initialize_schema(self, schema_path: str) -> None:
        """Initialize the database schema from a SQL file."""
        with open(schema_path, 'r') as f:
            schema = f.read()
            
        with self.get_connection() as conn:
            conn.executescript(schema)

class DatabaseSession:
    """Context manager for database operations."""
    def __init__(self, db: Database):
        self.db = db
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Utility functions for common database operations
def dict_from_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a dictionary."""
    return dict(zip(row.keys(), row))

def timestamp_to_datetime(timestamp: str) -> datetime:
    """Convert a SQLite timestamp to a datetime object."""
    return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

def datetime_to_timestamp(dt: datetime) -> str:
    """Convert a datetime object to a SQLite timestamp string."""
    return dt.strftime('%Y-%m-%d %H:%M:%S')
