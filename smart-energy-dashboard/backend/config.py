# backend/config.py - Configuration Settings
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smart-energy-meter-secret-key-2025'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Server settings
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 8080))
    
    # Database settings
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data/meter_data.db')
    DATABASE_BACKUP_INTERVAL = int(os.environ.get('DATABASE_BACKUP_INTERVAL', 3600))  # seconds
    DATABASE_CLEANUP_DAYS = int(os.environ.get('DATABASE_CLEANUP_DAYS', 30))
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'data/logs/flask_app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Data validation settings
    VOLTAGE_RANGE = (0, 500)  # Volts
    CURRENT_RANGE = (0, 1000)  # Amperes
    POWER_FACTOR_RANGE = (0, 1)  # Power factor
    LOAD_MIN = 0  # kW
    KWH_MIN = 0  # kWh
    FREQUENCY_RANGE = (45, 65)  # Hz
    
    # Carbon footprint settings
    EMISSION_FACTOR = float(os.environ.get('EMISSION_FACTOR', 0.82))  # kg CO₂ per kWh
    
    # Rate limiting settings
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Security settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 1048576))  # 1MB
    
    # API settings
    API_VERSION = os.environ.get('API_VERSION', 'v1')
    MAX_QUERY_LIMIT = int(os.environ.get('MAX_QUERY_LIMIT', 10000))
    DEFAULT_QUERY_LIMIT = int(os.environ.get('DEFAULT_QUERY_LIMIT', 1000))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_PER_MINUTE = 30

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # In-memory database for testing
    LOG_LEVEL = 'DEBUG'

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env_name='default'):
    """Get configuration based on environment name"""
    return config_map.get(env_name, DevelopmentConfig)