"""Authentication and authorization module."""
from functools import wraps
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import jwt
import bcrypt
from flask import request, jsonify, current_app, g
from werkzeug.security import safe_str_cmp

from .database import Database
from .logging import auth_logger, log_function_call, log_error

# Initialize database
db = Database(current_app.config['DATABASE_PATH'])

class Role:
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    USER = 'user'

    @staticmethod
    def get_all() -> List[str]:
        return [Role.ADMIN, Role.MODERATOR, Role.USER]

class Permission:
    # Media permissions
    UPLOAD_MEDIA = 'upload_media'
    DELETE_MEDIA = 'delete_media'
    EDIT_MEDIA = 'edit_media'
    VIEW_MEDIA = 'view_media'
    
    # Playlist permissions
    CREATE_PLAYLIST = 'create_playlist'
    DELETE_PLAYLIST = 'delete_playlist'
    EDIT_PLAYLIST = 'edit_playlist'
    VIEW_PLAYLIST = 'view_playlist'
    
    # User management permissions
    MANAGE_USERS = 'manage_users'
    VIEW_USERS = 'view_users'
    
    # System permissions
    VIEW_SYSTEM = 'view_system'
    MANAGE_SYSTEM = 'manage_system'

    @staticmethod
    def get_all() -> List[str]:
        return [attr for attr in dir(Permission) 
                if not attr.startswith('_') and isinstance(getattr(Permission, attr), str)]

# Role-based permissions
ROLE_PERMISSIONS = {
    Role.ADMIN: Permission.get_all(),  # Admins have all permissions
    Role.MODERATOR: [
        Permission.UPLOAD_MEDIA,
        Permission.EDIT_MEDIA,
        Permission.VIEW_MEDIA,
        Permission.CREATE_PLAYLIST,
        Permission.EDIT_PLAYLIST,
        Permission.VIEW_PLAYLIST,
        Permission.VIEW_USERS,
        Permission.VIEW_SYSTEM
    ],
    Role.USER: [
        Permission.VIEW_MEDIA,
        Permission.CREATE_PLAYLIST,
        Permission.EDIT_PLAYLIST,
        Permission.VIEW_PLAYLIST
    ]
}

def hash_password(password: str) -> bytes:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    """Check if a password matches its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def generate_token(user_id: int, role: str, expiry: Optional[timedelta] = None) -> str:
    """Generate a JWT token for a user."""
    if expiry is None:
        expiry = timedelta(days=1)  # Default to 1 day
        
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + expiry
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token."""
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return None

@log_function_call(auth_logger)
def create_user(username: str, password: str, role: str = Role.USER) -> Optional[int]:
    """Create a new user."""
    try:
        # Validate role
        if role not in Role.get_all():
            raise ValueError(f"Invalid role: {role}")
            
        # Check if username exists
        existing = db.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )
        if existing:
            raise ValueError("Username already exists")
            
        # Hash password and create user
        hashed = hash_password(password)
        user_id = db.insert('users', {
            'username': username,
            'password': hashed,
            'role': role,
            'created_at': datetime.utcnow().isoformat(),
            'last_login': None
        })
        
        return user_id

    except Exception as e:
        auth_logger.error(f"Failed to create user: {str(e)}")
        return None

@log_function_call(auth_logger)
def authenticate(username: str, password: str) -> Optional[Dict]:
    """Authenticate a user and return user info with token."""
    try:
        user = db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        
        if not user or not check_password(password, user['password']):
            return None
            
        # Update last login
        db.update(
            'users',
            {'last_login': datetime.utcnow().isoformat()},
            {'id': user['id']}
        )
        
        # Generate token
        token = generate_token(user['id'], user['role'])
        
        return {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'token': token
        }

    except Exception as e:
        auth_logger.error(f"Failed to authenticate user: {str(e)}")
        return None

def get_token_from_header() -> Optional[str]:
    """Extract token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ')[1]

def login_required(f):
    """Decorator to require valid token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return jsonify({'error': 'No token provided'}), 401
            
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
            
        # Store user info in g for route handlers
        g.user_id = payload['user_id']
        g.role = payload['role']
        
        return f(*args, **kwargs)
    return decorated

def require_permissions(*required_permissions):
    """Decorator to require specific permissions."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            role = g.role
            if role not in ROLE_PERMISSIONS:
                return jsonify({'error': 'Invalid role'}), 403
                
            user_permissions = ROLE_PERMISSIONS[role]
            if not all(perm in user_permissions for perm in required_permissions):
                return jsonify({'error': 'Insufficient permissions'}), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator

@log_function_call(auth_logger)
def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change a user's password."""
    try:
        user = db.fetch_one(
            "SELECT password FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not user or not check_password(old_password, user['password']):
            return False
            
        hashed = hash_password(new_password)
        db.update(
            'users',
            {'password': hashed},
            {'id': user_id}
        )
        
        return True

    except Exception as e:
        auth_logger.error(f"Failed to change password: {str(e)}")
        return False

@log_function_call(auth_logger)
def update_user_role(user_id: int, new_role: str) -> bool:
    """Update a user's role."""
    try:
        if new_role not in Role.get_all():
            raise ValueError(f"Invalid role: {new_role}")
            
        result = db.update(
            'users',
            {'role': new_role},
            {'id': user_id}
        )
        
        return result > 0

    except Exception as e:
        auth_logger.error(f"Failed to update user role: {str(e)}")
        return False

@log_function_call(auth_logger)
def delete_user(user_id: int) -> bool:
    """Delete a user."""
    try:
        result = db.delete('users', {'id': user_id})
        return result > 0

    except Exception as e:
        auth_logger.error(f"Failed to delete user: {str(e)}")
        return False

@log_function_call(auth_logger)
def get_user(user_id: int) -> Optional[Dict]:
    """Get user details."""
    try:
        user = db.fetch_one(
            """
            SELECT id, username, role, created_at, last_login
            FROM users WHERE id = ?
            """,
            (user_id,)
        )
        return dict(user) if user else None

    except Exception as e:
        auth_logger.error(f"Failed to get user: {str(e)}")
        return None

@log_function_call(auth_logger)
def list_users(page: int = 1, per_page: int = 20) -> Dict:
    """List users with pagination."""
    try:
        # Get total count
        total = db.fetch_one(
            "SELECT COUNT(*) as count FROM users"
        )['count']
        
        # Get paginated users
        users = db.fetch_all(
            """
            SELECT id, username, role, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, (page - 1) * per_page)
        )
        
        return {
            'users': [dict(u) for u in users],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

    except Exception as e:
        auth_logger.error(f"Failed to list users: {str(e)}")
        return {'users': [], 'pagination': {}}

def init_db():
    """Initialize authentication tables."""
    try:
        # Create users table
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password BLOB NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)
        
        # Create default admin user if none exists
        admin = db.fetch_one(
            "SELECT id FROM users WHERE role = ?",
            (Role.ADMIN,)
        )
        if not admin:
            create_user('admin', 'admin', Role.ADMIN)

    except Exception as e:
        auth_logger.error(f"Failed to initialize auth database: {str(e)}")
        raise
