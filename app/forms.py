from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User

# --- Форма Реєстрації ---
class RegistrationForm(FlaskForm):
    # Поле Email: обов'язкове, має бути валідним email, унікальним
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    
    # Поле Пароль: обов'язкове, мінімальна довжина 6 символів
    password = PasswordField('Пароль', 
                             validators=[DataRequired(), Length(min=6)])
    
    # Поле Підтвердження Пароля: має збігатися з першим паролем
    confirm_password = PasswordField('Підтвердити Пароль',
                                     validators=[DataRequired(), EqualTo('password', message='Паролі повинні співпадати')])
    
    # Кнопка відправки
    submit = SubmitField('Створити обліковий запис')

    # Кастомний валідатор: перевіряє, чи не зайнятий email
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Цей Email вже використовується. Увійдіть або оберіть інший.')

# --- Форма Входу ---
class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    
    password = PasswordField('Пароль', 
                             validators=[DataRequired()])
    
    # Запам'ятати мене (для тривалої сесії)
    remember = BooleanField('Запам\'ятати мене')
    
    submit = SubmitField('Увійти')