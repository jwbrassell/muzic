import os
import re
import hashlib

def calculate_file_checksum(file_path):
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_filename(filename):
    """Clean filename to remove weird characters while preserving spaces."""
    # Remove file extension
    base = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    
    # Remove leading underscores from base name
    base = base.lstrip('_')
    
    # Keep alphanumeric, spaces, and common special characters
    cleaned = re.sub(r'[^\w\-\. ]', '', base)
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip('. ')
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return (cleaned if cleaned else 'unnamed') + ext

def clean_filepath(filepath):
    """Clean filepath to ensure consistent paths for comparison."""
    # Split path into directory and filename
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    
    # Clean the filename
    clean_name = clean_filename(filename)
    
    # Join back together
    return os.path.join(directory, clean_name)

def move_media_file(current_path, destination_folder):
    """
    Move a media file to a new location.
    
    Args:
        current_path: Current path of the media file
        destination_folder: Destination folder path
        
    Returns:
        str: New path of the moved file
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If destination folder can't be created or file can't be moved
    """
    if not os.path.exists(current_path):
        raise FileNotFoundError(f"Source file not found: {current_path}")
        
    # Create destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)
    
    # Get filename and construct new path
    filename = os.path.basename(current_path)
    new_path = os.path.join(destination_folder, filename)
    
    # If file already exists in destination, add number suffix
    base, ext = os.path.splitext(new_path)
    counter = 1
    while os.path.exists(new_path):
        new_path = f"{base}_{counter}{ext}"
        counter += 1
    
    # Move the file
    os.rename(current_path, new_path)
    
    return new_path
