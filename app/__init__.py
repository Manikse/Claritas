from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config # Імпорт налаштувань

# Ініціалізація Flask
app = Flask(__name__)
# Застосування конфігурації
app.config.from_object(Config)

# Ініціалізація Бази Даних
db = SQLAlchemy(app)

# Ініціалізація Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Куди перенаправляти, якщо користувач не авторизований
login_manager.login_message_category = 'info' # Категорія для flash-повідомлень

# Імпортуємо маршрути та моделі в кінці, щоб уникнути циклічних імпортів
# ЗМІНЕНО: тепер імпортуємо окремі файли, а не модуль "app"
from . import routes, models