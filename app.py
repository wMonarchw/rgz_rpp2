from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import datetime
from Db.models import Expense, Users, AuditLog
from Db import db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = '123'
user_db = 'ilya_rpp5'
host_ip = '127.0.0.1'
host_port = '5432'
database_name = 'rpp5'
password = '123'

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Login manager
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Роуты
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    if Users.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    hashPassword = generate_password_hash(password, method='pbkdf2')

    new_user = Users(
        username=username,
        password=(hashPassword)
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user = Users.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password): 
        return jsonify({'error': 'Invalid username or password'}), 401

    login_user(user)
    return jsonify({'message': 'Login successful'}), 200


@app.route('/add', methods=['POST'])
@login_required
def add_expense():
    data = request.json
    new_expense = Expense(
        user_id=current_user.id,
        amount=data['amount'],
        category=data['category'],
        description=data.get('description', '')
    )
    db.session.add(new_expense)
    db.session.commit()

    log_action('add', new_expense.id)
    return jsonify({'message': 'Expense added successfully'}), 201

@app.route('/list', methods=['GET'])
@login_required
def list_expenses():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': e.id,
        'amount': e.amount,
        'category': e.category,
        'description': e.description,
        'created_at': e.created_at
    } for e in expenses])

@app.route('/edit', methods=['POST'])
@login_required
def edit_expense():
    data = request.json
    expense = Expense.query.filter_by(id=data['id'], user_id=current_user.id).first()
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    expense.amount = data.get('amount', expense.amount)
    expense.category = data.get('category', expense.category)
    expense.description = data.get('description', expense.description)
    db.session.commit()

    log_action('edit', expense.id)
    return jsonify({'message': 'Expense updated successfully'})

@app.route('/delete', methods=['POST'])
@login_required
def delete_expense():
    data = request.json
    expense = Expense.query.filter_by(id=data['id'], user_id=current_user.id).first()
    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    db.session.delete(expense)
    db.session.commit()

    log_action('delete', data['id'])
    return jsonify({'message': 'Expense deleted successfully'})

# Логирование
def log_action(action, expense_id):
    audit_log = AuditLog(
        user_id=current_user.id,
        action=action,
        expense_id=expense_id
    )
    db.session.add(audit_log)
    db.session.commit()

# with app.app_context():
#         db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
