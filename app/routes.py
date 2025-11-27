from flask import render_template, url_for, flash, redirect, request
from app import app, db, login_manager 
from app.forms import LoginForm, RegistrationForm 
from app.models import User 
from app.ai_service import generate_campaign_copy 
from app.billing_service import create_stripe_checkout, handle_stripe_webhook 
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime, timedelta

# --- Маршрути Авторизації ---

@app.route("/")
@app.route("/home")
def home():
    # Головна сторінка з інформацією про тарифи та закликом до реєстрації
    return render_template('index.html') 

@app.route("/login", methods=['GET', 'POST'])
def login():
    # Обробка входу та реєстрації в одному маршруті
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Створюємо дві окремі форми для використання в одному шаблоні
    login_form = LoginForm()
    registration_form = RegistrationForm()

    if request.method == 'POST':
        # Перевіряємо, яку форму відправив користувач, за допомогою кнопки submit
        
        # Обробка форми входу
        if login_form.validate_on_submit() and login_form.submit.data:
            user = User.query.filter_by(email=login_form.email.data).first()
            if user and user.check_password(login_form.password.data):
                login_user(user, remember=login_form.remember.data)
                flash('Успішний вхід!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Вхід не відбувся. Перевірте email та пароль.', 'danger')
        
        # Обробка форми реєстрації
        elif registration_form.validate_on_submit() and registration_form.submit.data:
            try:
                user = User(email=registration_form.email.data)
                user.set_password(registration_form.password.data)
                
                # Ініціалізація пробного періоду: 7 днів з 5 кредитами
                user.trial_ends_at = datetime.utcnow() + timedelta(days=7) 
                # free_credits за замовчуванням: 5 (встановлено в models.py)

                db.session.add(user)
                db.session.commit()
                flash(f'Обліковий запис {user.email} створено! Почніть безкоштовний пробний період.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash('Помилка реєстрації. Спробуйте пізніше.', 'danger')
                print(f"Registration Error: {e}")

    # Передача обох форм у шаблон login.html
    return render_template('login.html', login_form=login_form, registration_form=registration_form)

@app.route("/logout")
def logout():
    # Вихід користувача із системи
    logout_user()
    flash('Ви вийшли з системи.', 'info')
    return redirect(url_for('home'))

# --- Маршрут Інструменту (Захищений) ---

@app.route("/dashboard", methods=['GET', 'POST'])
@login_required # Доступ тільки для авторизованих користувачів
def dashboard():
    copy_result = None
    
    # 1. Перевірка доступу: якщо немає підписки і пробний період закінчився/вичерпано
    if not current_user.is_subscribed and not current_user.has_free_trial:
        flash('Доступ заборонено. Будь ласка, активуйте підписку.', 'danger')
        return redirect(url_for('home')) 
    
    if request.method == 'POST':
        # 2. Перевірка кредитів перед викликом AI (тільки для пробного періоду)
        if current_user.has_free_trial and current_user.free_credits <= 0:
            flash('Ваш безкоштовний пробний період закінчився (кредити вичерпано)! Будь ласка, оформіть підписку.', 'danger')
            return redirect(url_for('home')) 
        
        # 3. Отримання даних з форми
        topic = request.form.get('topic') 
        audience = request.form.get('audience') 
        benefit = request.form.get('benefit') 
        placement = request.form.get('placement')
        
        if topic and audience and benefit and placement:
            try:
                # 4. Виклик AI-сервісу (generate_campaign_copy імпортовано)
                copy_result = generate_campaign_copy(topic, audience, benefit, placement)
                
                # 5. ЛОГІКА: Віднімання 1 кредиту, якщо користувач на безкоштовному плані
                if current_user.has_free_trial:
                    current_user.free_credits -= 1
                    db.session.commit()
                    flash(f"Контент згенеровано. Залишилося кредитів: {current_user.free_credits}", 'info')
                
            except Exception as e:
                flash('Помилка генерації AI. Перевірте, чи правильно налаштовано API-ключ OpenAI.', 'danger')
                print(f"AI Generation Error: {e}")
                
        else:
            flash('Будь ласка, заповніть усі поля для генерації.', 'warning')
            
    return render_template('dashboard.html', result=copy_result)

# --- Маршрути Білінгу (Stripe) ---

@app.route("/create-checkout-session", methods=['POST'])
@login_required
def checkout():
    # Перенаправлення користувача на сторінку оплати Stripe
    flash('Перенаправлення на сторінку оплати...', 'info')
    return create_stripe_checkout(current_user)

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    # Маршрут для обробки подій від Stripe (оновлення статусу підписки)
    return handle_stripe_webhook()