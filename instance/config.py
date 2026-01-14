import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me-in-production'

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    f"sqlite:///{os.path.join(BASE_DIR, '', 'school_cafeteria.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

SESSION_PROTECTION = 'strong'
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
TESTING = False

ITEMS_PER_PAGE = 20

TEMPLATE_FOLDER = os.path.join(BASE_DIR, '../templates')
STATIC_FOLDER = os.path.join(BASE_DIR, '../static')
UPLOAD_FOLDER = os.path.join(BASE_DIR, '../uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)