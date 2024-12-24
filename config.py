import os

class Config:
    HOST = '0.0.0.0'
    PORT = 5000
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
    MEDIA_DIRS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')]
    AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    VIDEO_EXTENSIONS = {'mp4', 'webm', 'mkv'}
