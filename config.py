import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'steg2026_pv_v17_refresh'
    DEBUG = True
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    JSON_SORT_KEYS = False
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    DATABASE_NAME = 'photovoltaique.db'
    DATA_DIR = 'data'
