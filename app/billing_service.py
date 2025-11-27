import stripe
import json
from flask import current_app, redirect, url_for, request, jsonify
from app.models import User
from app import db # Імпорт бази даних
from datetime import datetime, timedelta

# Ініціалізація Stripe
# Stripe Key береться з конфігурації Flask
stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
STRIPE_PRICE_ID = current_app.config['STRIPE_PRICE_ID']
WEBHOOK_SECRET = current_app.config['STRIPE_WEBHOOK_SECRET']


def create_stripe_checkout(user: User):
    """
    Створює нову сесію оформлення замовлення Stripe для підписки на $100 євро.
    """
    try:
        # 1. Створення Stripe Customer, якщо його ще немає
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id
            db.session.commit()

        # 2. Створення сесії оформлення замовлення
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': STRIPE_PRICE_ID,  # ID ціни з вашого config.py
                'quantity': 1,
            }],
            # URL, куди Stripe перенаправить користувача після успіху/скасування
            success_url=url_for('dashboard', _external=True),
            cancel_url=url_for('pricing', _external=True),
        )
        
        # Перенаправляємо користувача на сторінку оплати Stripe
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print(f"Помилка створення Checkout Session: {e}")
        # Якщо сталася помилка, перенаправляємо на головну сторінку
        return redirect(url_for('home'))

def handle_stripe_webhook():
    """
    Обробляє події (вебхуки) від Stripe для оновлення статусу підписки.
    """
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    event = None

    try:
        # Перевірка підпису вебхука для безпеки
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError as e:
        # Неправильний пейлоад
        return jsonify({'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        # Неправильний підпис
        return jsonify({'error': str(e)}), 400

    # Обробка подій
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            # Оновлюємо користувача, підписка активована
            user.stripe_subscription_id = subscription_id
            user.subscription_status = 'active'
            # Якщо користувач мав пробний період, повертаємо кредити на 0
            user.free_credits = 0 
            db.session.commit()
            print(f"Підписка для користувача {user.email} успішно активована.")
            
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user and user.subscription_status == 'active':
            # Підписка скасована (автоматично, або вручну користувачем)
            user.subscription_status = 'canceled'
            user.stripe_subscription_id = None
            db.session.commit()
            print(f"Підписка для користувача {user.email} скасована.")

    # Повертаємо відповідь, що обробка пройшла успішно
    return jsonify({'status': 'success'}), 200  