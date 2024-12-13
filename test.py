import unittest
from flask import json
from app import app, db
from Db.models import Users, Expense
from werkzeug.security import generate_password_hash

class AppTestCase(unittest.TestCase):

    def setUp(self):
        # Конфигурация тестового приложения
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Используем в-памяти SQLite для тестов
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Создание тестового пользователя, если он еще не существует
            existing_user = Users.query.filter_by(username="testuser").first()
            if not existing_user:
                test_user = Users(
                    username='testuser',
                    password=generate_password_hash('password123', method='pbkdf2')
                )
                db.session.add(test_user)
                db.session.commit()

    def tearDown(self):
        # Очистка базы данных после каждого теста
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        response = self.client.post('/login', json={'username': username, 'password': password})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Login successful', response.get_data(as_text=True))
        return response

    def test_register(self):
        response = self.client.post('/register', json={
            'username': 'newuser',
            'password': 'newpassword'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('User registered successfully', response.get_data(as_text=True))

    def test_login(self):
        response = self.login('testuser', 'password123')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Login successful', response.get_data(as_text=True))

    def test_add_expense(self):
        with self.client:
            self.client.post('/login', json={
                'username': 'testuser',
                'password': 'password123'
            })
            response = self.client.post('/add', json={
                'amount': 51,
                'category': 'Food',
                'description': 'Test description'
            })
            self.assertEqual(response.status_code, 201)
            self.assertIn('Expense added successfully', response.json['message'])

    def test_list_expenses(self):
        with self.client:
            self.client.post('/login', json={
                'username': 'testuser',
                'password': 'password123'
            })

            self.client.post('/add', json={
                'amount': 51,
                'category': 'Food',
                'description': 'Test description'
            })

            response = self.client.get('/list')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json), 1)
            self.assertEqual(response.json[0]['category'], 'Food')

    def test_edit_expense(self):
        with app.app_context():
            # Логинимся
            self.client.post('/login', json={
                'username': 'testuser',
                'password': 'password123'
            })

            # Добавляем расход
            add_response = self.client.post('/add', json={
                'amount': 55,
                'category': 'Food',
                'description': 'Test description'
            })
            self.assertEqual(add_response.status_code, 201)

            # Ищем добавленный расход в базе данных
            expense = Expense.query.filter_by(user_id=1, amount=55, category='Food', description='Test description').first()
            self.assertIsNotNone(expense)  # Убедимся, что расход был добавлен

            # Редактируем расход
            edit_response = self.client.post('/edit', json={
                'id': expense.id,  # Используем ID из базы данных
                'amount': 60.0,
                'category': 'Travel',
                'description': 'Travel test'
            })
            self.assertEqual(edit_response.status_code, 200)
            self.assertIn('Expense updated successfully', edit_response.json['message'])

            # Проверяем, что расход был обновлен
            updated_expense = db.session.get(Expense, (expense.id))
            self.assertEqual(updated_expense.amount, 60.0)
            self.assertEqual(updated_expense.category, 'Travel')
            self.assertEqual(updated_expense.description, 'Travel test')

    def test_delete_expense(self):
        with app.app_context():
            # Логинимся
            self.client.post('/login', json={
                'username': 'testuser',
                'password': 'password123'
            })

            # Добавляем расход
            add_response = self.client.post('/add', json={
                'amount': 50,
                'category': 'Food',
                'description': 'test'
            })
            self.assertEqual(add_response.status_code, 201)

            # Ищем добавленный расход в базе данных
            expense = Expense.query.filter_by(user_id=1, amount=50, category='Food', description='test').first()
            self.assertIsNotNone(expense)  # Убедимся, что расход был добавлен

            # Удаляем расход
            delete_response = self.client.post('/delete', json={
                'id': expense.id  
            })
            self.assertEqual(delete_response.status_code, 200)
            self.assertIn('Expense deleted successfully', delete_response.json['message'])

            # Проверяем, что расход был удален
            deleted_expense = db.session.get(Expense, (expense.id))
            self.assertIsNone(deleted_expense)  

if __name__ == '__main__':
    unittest.main()
