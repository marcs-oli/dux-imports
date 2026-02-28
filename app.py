import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta

# Importar banco de dados e rotas
from backend.database.db import init_db
from backend.routes.auth import auth_bp
from backend.routes.products import products_bp
from backend.routes.orders import orders_bp

# ─── CONFIGURAÇÃO DA APLICAÇÃO ────────────────────────────────────────────────

app = Flask(__name__, static_folder='frontend', static_url_path='')

# Configurações
app.config['SECRET_KEY'] = 'dux-imports-secret-key-2024-ultra-secure'
app.config['JWT_SECRET_KEY'] = 'dux-imports-jwt-secret-2024'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# Extensões
CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(orders_bp)

# ─── ROTAS FRONTEND ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/loja')
def loja():
    return send_from_directory('frontend/pages', 'loja.html')

@app.route('/produto/<slug>')
def produto(slug):
    return send_from_directory('frontend/pages', 'produto.html')

@app.route('/carrinho')
def carrinho():
    return send_from_directory('frontend/pages', 'carrinho.html')

@app.route('/checkout')
def checkout():
    return send_from_directory('frontend/pages', 'checkout.html')

@app.route('/conta')
def conta():
    return send_from_directory('frontend/pages', 'conta.html')

@app.route('/login')
def login_page():
    return send_from_directory('frontend/pages', 'login.html')

@app.route('/cadastro')
def cadastro():
    return send_from_directory('frontend/pages', 'cadastro.html')

@app.route('/pedidos')
def pedidos():
    return send_from_directory('frontend/pages', 'pedidos.html')

@app.route('/admin')
def admin():
    return send_from_directory('frontend/pages', 'admin.html')

@app.route('/admin/login')
def admin_login_page():
    return send_from_directory('frontend/pages', 'admin-login.html')

# ─── TRATAMENTO DE ERROS ──────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return send_from_directory('frontend', 'index.html')

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Erro interno do servidor'}), 500

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token expirado. Faça login novamente.'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Token inválido'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Token de autenticação necessário'}), 401

# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

if __name__ == '__main__': app.run
