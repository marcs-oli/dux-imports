"""
Rotas de autenticação para usuários e administradores.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import bcrypt
import re
from backend.database.db import get_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth_bp.route('/register', methods=['POST'])
def register():
    """Cadastro de novo usuário."""
    data = request.get_json()

    # Validações
    required = ['name', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} é obrigatório'}), 400

    if not validate_email(data['email']):
        return jsonify({'error': 'E-mail inválido'}), 400

    if len(data['password']) < 6:
        return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verificar se e-mail já existe
        cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'].lower(),))
        if cursor.fetchone():
            return jsonify({'error': 'E-mail já cadastrado'}), 409

        # Hash da senha
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute('''
            INSERT INTO users (name, email, password, phone, cpf)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['email'].lower(),
            hashed,
            data.get('phone', ''),
            data.get('cpf', '')
        ))
        conn.commit()

        user_id = cursor.lastrowid
        token = create_access_token(
            identity=str(user_id),
            additional_claims={'role': 'user', 'name': data['name']}
        )

        return jsonify({
            'message': 'Cadastro realizado com sucesso!',
            'token': token,
            'user': {
                'id': user_id,
                'name': data['name'],
                'email': data['email'].lower()
            }
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Erro ao cadastrar usuário'}), 500
    finally:
        conn.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login de usuário."""
    data = request.get_json()

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'E-mail e senha são obrigatórios'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (data['email'].lower(),))
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({'error': 'E-mail ou senha incorretos'}), 401

        token = create_access_token(
            identity=str(user['id']),
            additional_claims={'role': 'user', 'name': user['name']}
        )

        return jsonify({
            'message': 'Login realizado com sucesso!',
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email']
            }
        })

    except Exception as e:
        return jsonify({'error': 'Erro ao realizar login'}), 500
    finally:
        conn.close()


@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Login administrativo."""
    data = request.get_json()

    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Usuário e senha são obrigatórios'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM admins WHERE username = ? AND is_active = 1", (data['username'],))
        admin = cursor.fetchone()

        if not admin or not bcrypt.checkpw(data['password'].encode('utf-8'), admin['password'].encode('utf-8')):
            return jsonify({'error': 'Usuário ou senha incorretos'}), 401

        token = create_access_token(
            identity=str(admin['id']),
            additional_claims={'role': 'admin', 'name': admin['name']}
        )

        return jsonify({
            'message': 'Login administrativo realizado com sucesso!',
            'token': token,
            'admin': {
                'id': admin['id'],
                'name': admin['name'],
                'username': admin['username']
            }
        })

    except Exception as e:
        return jsonify({'error': 'Erro ao realizar login'}), 500
    finally:
        conn.close()


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Retorna perfil do usuário autenticado."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    if claims.get('role') != 'user':
        return jsonify({'error': 'Acesso negado'}), 403

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, email, phone, cpf, address, city, state, zip_code, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        return jsonify(dict(user))

    finally:
        conn.close()


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Atualiza perfil do usuário."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    if claims.get('role') != 'user':
        return jsonify({'error': 'Acesso negado'}), 403

    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE users SET name=?, phone=?, cpf=?, address=?, city=?, state=?, zip_code=?
            WHERE id=?
        ''', (
            data.get('name'), data.get('phone'), data.get('cpf'),
            data.get('address'), data.get('city'), data.get('state'),
            data.get('zip_code'), user_id
        ))
        conn.commit()
        return jsonify({'message': 'Perfil atualizado com sucesso!'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Erro ao atualizar perfil'}), 500
    finally:
        conn.close()
