"""
Delivery System Configuration
Standalone Configuration for Delivery Routing & Driver Management
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'delivery_system_secret_key_change_in_production'
    
    # --- SQLite Database ---
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'delivery_system.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask Configuration
    DEBUG = False
    TESTING = False
    ENV = 'development'
    
    # File Upload Settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Routing Service Configuration
    ROUTING_SERVICE_URL = os.environ.get('ROUTING_SERVICE_URL', 'http://localhost:8080')
    ROUTING_SERVICE_TIMEOUT = 30

    # Python Routing Service Configuration
    ROUTING_SERVICE_PYTHON_URL = os.environ.get('ROUTING_SERVICE_PYTHON_URL', 'http://localhost:5001')

    # Live Location Service Configuration
    LIVE_LOCATION_SERVICE_URL = os.environ.get('LIVE_LOCATION_SERVICE_URL', 'http://localhost:5001')
    
    # Cache Settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Reduced from 7 days for security
    SESSION_REFRESH_EACH_REQUEST = False
    
    # Email Settings (optional - for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'delivery-system@example.com')
    
    # Google Maps API (for geocoding fallback)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    
    # CORS Settings
    CORS_ORIGINS = ["*"]
    
    # Delivery Pricing (Bolt-like model)
    DEFAULT_BASE_FARE = 5.0  # Currency units
    DEFAULT_PER_KM_RATE = 1.5  # Per kilometer
    DEFAULT_DRIVER_COMMISSION_PERCENT = 75.0  # Driver gets 75% of base fare
    DEFAULT_PLATFORM_COMMISSION_PERCENT = 25.0  # Platform keeps 25%
    
    # Performance
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_POOL_RECYCLE = 3600


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'
    TESTING = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database
    MAIL_BACKEND = 'locmem'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'production_key_change_me')

    # Use PostgreSQL database from environment variable (Render provides this)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'delivery_system.db'))


# Select config based on environment
def get_config():
    """Get the appropriate configuration based on FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()
