from app.core.config import get_settings
from app.core.database import Database
import os

def main():
    settings = get_settings()
    
    # Ensure instance directory exists
    os.makedirs(os.path.dirname(settings.database.path), exist_ok=True)
    
    # Remove existing database if it exists
    if os.path.exists(settings.database.path):
        os.remove(settings.database.path)
        print(f"Removed existing database at {settings.database.path}")
    
    # Initialize new database
    db = Database(settings.database.path)
    db.initialize_schema('schema.sql')
    print("Database reinitialized successfully")

if __name__ == '__main__':
    main()
