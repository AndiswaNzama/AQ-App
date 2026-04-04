import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///photographer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PayFast
    PAYFAST_MERCHANT_ID = os.environ.get('PAYFAST_MERCHANT_ID', '10000100')   # sandbox default
    PAYFAST_MERCHANT_KEY = os.environ.get('PAYFAST_MERCHANT_KEY', '46f0cd694581a')  # sandbox default
    PAYFAST_PASSPHRASE = os.environ.get('PAYFAST_PASSPHRASE', '')
    PAYFAST_SANDBOX = os.environ.get('PAYFAST_SANDBOX', 'true').lower() == 'true'

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    PHOTOGRAPHER_NAME = os.environ.get('PHOTOGRAPHER_NAME', 'Aubrey Qualities')
    PHOTOGRAPHER_EMAIL = os.environ.get('PHOTOGRAPHER_EMAIL', '')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
