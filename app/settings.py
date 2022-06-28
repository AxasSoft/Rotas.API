import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:

    PROJECT_NAME = 'Bed Time Stories'
    PROJECT_VERSION = '0.0.1'

    JSON_SORT_KEYS = False
    SECRET_KEY = 'TakovNashParol-NaEzhaSelGoloyZhopoyKorol!!1'

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

    DB_EXPORT = ['csv', 'json', 'xls', 'xlsx', 'yaml', 'df', 'html', 'ods']

    SAI_URL = '/admin'

    # APPLE ID

    SOCIAL_AUTH_APPLE_KEY_ID = 'Q86AM34WJ7'
    SOCIAL_AUTH_APPLE_TEAM_ID = 'Z44STKB729'
    SOCIAL_AUTH_APPLE_CLIENT_ID = 'ru.skinallergic.CheckSkin'
    SOCIAL_AUTH_APPLE_PRIVATE_KEY = '''-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgMKWawIm1F8LBtTKl
xU8HbpiZ7U0eYUNMQBZ+48cVMFGgCgYIKoZIzj0DAQehRANCAASaRlbsfWlQh2Jr
wQiYs0OWU+Ypfsul4ounSgyH9yBjubAfOOBrtYJgEwy+Bn1F6jSeudKLRG3QMIjZ
Qkx4nCxk
-----END PRIVATE KEY-----'''
    SOCIAL_AUTH_APPLE_AUD = 'https://appleid.apple.com'
    SOCIAL_AUTH_APPLE_GRANT_TYPE = 'authorization_code'
    SOCIAL_AUTH_APPLE_REDIRECT_URL = None  # or 'https://network.axas.online/auth/apple'

    FIREBASE_API_KEY = 'AAAAOCvQxFo:APA91bH_tTBEP2DX8a17VqqB5t4KrjLD3PO3EfM-z5ohvheKVl0fjAWSpiIZwt5VGCg8-3QGG50OEmbzpCzlXNg9qk84YA2SltvtwapFY4SqyTPrTdHYe5uH3FnAfnUoJ9C0Tx06NnxC'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USERNAME = 'v.rudomakha@gmail.com'
    MAIL_PASSWORD = 'yvzvbkmcdlcrlkpn'
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True

    BASIC_AUTH_USERNAME = 'axas'
    BASIC_AUTH_PASSWORD = 'exJGAeKb2M5V4Z7q'

    SCHEDULER_API_ENABLED = True


class DevConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    PAGE_SIZE = 30


class ProductConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PAGE_SIZE = 30
