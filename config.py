import os
from dotenv import load_dotenv

# Load variables from .env if it exists
load_dotenv()

class Config:
    """Base configuration."""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nirvana_heritage_fallback_key_2026')
    
    # Database
    # Fallback to local sqlite if DATABASE_URL isn't set in .env
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Management
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    PROCESSED_FOLDER = os.path.join('static', 'processed')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB Upload Limit
    
    # Email Configuration (Nirvana Heritage Support)
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'e23ai023@sdnbvc.edu.in')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'jbny qhgn kljc ajmf')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME', 'e23ai023@sdnbvc.edu.in')

class ProductionConfig(Config):
    """Production specific config."""
    DEBUG = False
    # In production, you'd strictly require the SECRET_KEY to be in .env
    SESSION_COOKIE_SECURE = True
    REMOTE_ADDR_HEADER = 'X-Forwarded-For'

class DevelopmentConfig(Config):
    """Development specific config."""
    DEBUG = True
    # Development often uses local sqlite and allows simple debugging