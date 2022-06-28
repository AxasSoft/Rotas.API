"""
Основной модуль приложения
"""
import inspect

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from pyfcm import FCMNotification
from flask_basicauth import BasicAuth


from app.settings import ProductConfig, DevConfig
from utils import terminal

from utils.validation import RequestValidator

app = Flask(__name__)

# применение конфига
app.config.from_object(DevConfig)
app.url_map.strict_slashes = app.config.get('STRICT_SLASHES', True)

request_validator = RequestValidator()

# CORS. Без этого расширения не будут работать запросы от фронта
CORS(app)

# настойка ORM.
db = SQLAlchemy(app)
migrate = Migrate(app, db)
basic_auth = BasicAuth(app)

# подгрузка роутов
from app import models, views, errors

# Вывод актуального конфига на момент подгрузки приложения и всех расширений.
# print(app.config)
# print(app.url_map)
