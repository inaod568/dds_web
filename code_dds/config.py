"""Configuration handling code"""

from os import environ

class Config:
    """Set Flask configuration from ENV variables"""

    # General Config
    SECRET_KEY = environ.get('SECRET_KEY')
    SITE_NAME = 'Data Delivery System'
    DDS_S3_CONFIG = environ.get('DDS_S3_CONFIG')
    
    # FLASK_APP = environ.get('FLASK_APP')
    FLASK_ENV = environ.get('FLASK_ENV')

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # For dev purpose, should be removed later
    USE_LOCAL_DB = environ.get('USE_LOCAL_DB')
    
    # File upload related
    DDS_CLI_CONFIG = environ.get('DDS_CLI_CONFIG')
    UPLOAD_FOLDER = environ.get('DDS_UPLOAD_FOLDER')
    MAX_CONTENT_LENGTH = int(environ.get('DDS_MAX_UPLOAD_SIZE'))
