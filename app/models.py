from datetime import datetime, timedelta
from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Функція для завантаження користувача (потрібна Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # --- Білінгова Інформація ---
    
    # Stripe Customer ID потрібен для створення сесій оплати
    stripe_customer_id = db.Column(db.String(100), index=True) 
    
    # Stripe Subscription ID потрібен для ідентифікації активної підписки
    stripe_subscription_id = db.Column(db.String(100), index=True)
    
    # Статус підписки: 'active', 'canceled', 'trialing'
    subscription_status = db.Column(db.String(20), default='trialing')
    
    # --- Логіка Кредитів/Пробного Періоду ---
    
    # Дата закінчення пробного періоду
    trial_ends_at = db.Column(db.DateTime, default=None) 
    
    # Залишок кредитів для пробного періоду. За замовчуванням 5, як ми домовились.
    free_credits = db.Column(db.Integer, default=5) 

    # --- Хелпери (Властивості) ---

    @property
    def is_subscribed(self):
        """Перевіряє, чи є користувач активним платним підписником."""
        # Користувач активний, якщо статус "active" і є ID підписки
        return self.subscription_status == 'active' and self.stripe_subscription_id is not None

    @property
    def has_free_trial(self):
        """Перевіряє, чи має користувач активний пробний період."""
        now = datetime.utcnow()
        
        # 1. Перевіряємо, чи має він пробний статус
        is_trialing = self.subscription_status == 'trialing'
        
        # 2. Перевіряємо, чи не закінчився термін
        is_not_expired = self.trial_ends_at is not None and self.trial_ends_at > now
        
        # 3. Перевіряємо, чи не вичерпані кредити
        has_credits = self.free_credits > 0

        # Пробний період активний, якщо всі умови (крім subscribed) виконані
        return is_trialing and is_not_expired and has_credits

    # --- Функції Аутентифікації ---

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.email}', Status:'{self.subscription_status}')"