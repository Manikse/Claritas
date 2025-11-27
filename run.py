from app import app, db # <--- Тут ми імпортуємо
from app.models import User 

if __name__ == '__main__':
    # ...
    app.run(debug=True)