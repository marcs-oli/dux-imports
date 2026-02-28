"""
Rotas de pedidos e pagamentos para a loja Dux Imports.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import uuid
import random
import string
from datetime import datetime
from backend.database.db import get_connection

orders_bp = Blueprint('orders', __name__, url_prefix='/api')


def generate_order_number():
    """Gera um número de pedido único."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"DUX-{timestamp}-{suffix}"


def generate_pix_key():
    """Simula uma chave PIX."""
    return ''.join(random.choices(string.digits, k=32))


def generate_boleto_code():
    """Simula um código de boleto."""
    parts = [''.join(random.choices(string.digits, k=5)) for _ in range(5)]
    return '.'.join(parts)


# ─── PEDIDOS DO USUÁRIO ──────────────────────────────────────────────────────

@orders_bp.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    """Cria um novo pedido."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    if claims.get('role') != 'user':
        return jsonify({'error': 'Acesso negado'}), 403

    data = request.get_json()

    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'Carrinho vazio'}), 400

    if not data.get('payment_method'):
        return jsonify({'error': 'Método de pagamento é obrigatório'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        subtotal = 0
        order_items = []

        # Validar e calcular itens
        for item in data['items']:
            cursor.execute("SELECT * FROM products WHERE id = ? AND is_active = 1", (item['product_id'],))
            product = cursor.fetchone()

            if not product:
                return jsonify({'error': f'Produto ID {item["product_id"]} não encontrado'}), 404

            if product['stock'] < item['quantity']:
                return jsonify({'error': f'Estoque insuficiente para {product["name"]}'}), 400

            item_subtotal = product['price'] * item['quantity']
            subtotal += item_subtotal
            order_items.append({
                'product_id': product['id'],
                'product_name': product['name'],
                'product_price': product['price'],
                'quantity': item['quantity'],
                'subtotal': item_subtotal
            })

        shipping = 0 if subtotal >= 299 else 29.90
        discount = data.get('discount', 0)
        total = subtotal + shipping - discount

        order_number = generate_order_number()

        # Criar pedido
        cursor.execute('''
            INSERT INTO orders (user_id, order_number, status, subtotal, shipping, discount, total,
                shipping_address, shipping_city, shipping_state, shipping_zip, notes)
            VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, order_number, subtotal, shipping, discount, total,
            data.get('address', ''), data.get('city', ''),
            data.get('state', ''), data.get('zip_code', ''),
            data.get('notes', '')
        ))

        order_id = cursor.lastrowid

        # Inserir itens e atualizar estoque
        for item in order_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, product_price, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, item['product_id'], item['product_name'],
                  item['product_price'], item['quantity'], item['subtotal']))

            # Atualizar estoque
            cursor.execute("SELECT stock FROM products WHERE id = ?", (item['product_id'],))
            old_stock = cursor.fetchone()['stock']
            new_stock = old_stock - item['quantity']

            cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, item['product_id']))

            cursor.execute('''
                INSERT INTO stock_history (product_id, type, quantity, previous_stock, new_stock, reference)
                VALUES (?, 'saida', ?, ?, ?, ?)
            ''', (item['product_id'], item['quantity'], old_stock, new_stock, f'Pedido {order_number}'))

        # Processar pagamento simulado
        payment_method = data['payment_method']
        payment_data = {
            'order_id': order_id,
            'method': payment_method,
            'amount': total,
            'installments': data.get('installments', 1)
        }

        if payment_method == 'pix':
            payment_data['pix_key'] = generate_pix_key()
            payment_data['status'] = 'approved'
            payment_data['paid_at'] = datetime.now().isoformat()
            # Atualizar status do pedido para pago
            cursor.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))

        elif payment_method == 'boleto':
            payment_data['boleto_code'] = generate_boleto_code()
            payment_data['status'] = 'pending'

        elif payment_method == 'credit_card':
            payment_data['card_last4'] = data.get('card_last4', '0000')
            payment_data['status'] = 'approved'
            payment_data['paid_at'] = datetime.now().isoformat()
            cursor.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))

        cursor.execute('''
            INSERT INTO payments (order_id, method, status, amount, installments,
                card_last4, pix_key, boleto_code, paid_at)
            VALUES (:order_id, :method, :status, :amount, :installments,
                :card_last4, :pix_key, :boleto_code, :paid_at)
        ''', {
            'order_id': payment_data['order_id'],
            'method': payment_data['method'],
            'status': payment_data['status'],
            'amount': payment_data['amount'],
            'installments': payment_data.get('installments', 1),
            'card_last4': payment_data.get('card_last4'),
            'pix_key': payment_data.get('pix_key'),
            'boleto_code': payment_data.get('boleto_code'),
            'paid_at': payment_data.get('paid_at')
        })

        conn.commit()

        return jsonify({
            'message': 'Pedido realizado com sucesso!',
            'order_id': order_id,
            'order_number': order_number,
            'total': total,
            'payment': payment_data
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Erro ao criar pedido: {str(e)}'}), 500
    finally:
        conn.close()


@orders_bp.route('/orders/my', methods=['GET'])
@jwt_required()
def get_my_orders():
    """Lista pedidos do usuário autenticado."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    if claims.get('role') != 'user':
        return jsonify({'error': 'Acesso negado'}), 403

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT o.*, p.method as payment_method, p.status as payment_status
            FROM orders o
            LEFT JOIN payments p ON p.order_id = o.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
        ''', (user_id,))

        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            cursor.execute('''
                SELECT oi.*, pr.image_url FROM order_items oi
                LEFT JOIN products pr ON pr.id = oi.product_id
                WHERE oi.order_id = ?
            ''', (order['id'],))
            order['items'] = [dict(item) for item in cursor.fetchall()]
            orders.append(order)

        return jsonify(orders)

    finally:
        conn.close()


@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Retorna detalhes de um pedido."""
    user_id = get_jwt_identity()
    claims = get_jwt()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if claims.get('role') == 'admin':
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        else:
            cursor.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id))

        order = cursor.fetchone()
        if not order:
            return jsonify({'error': 'Pedido não encontrado'}), 404

        order = dict(order)

        cursor.execute('''
            SELECT oi.*, pr.image_url FROM order_items oi
            LEFT JOIN products pr ON pr.id = oi.product_id
            WHERE oi.order_id = ?
        ''', (order_id,))
        order['items'] = [dict(item) for item in cursor.fetchall()]

        cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
        payment = cursor.fetchone()
        order['payment'] = dict(payment) if payment else None

        return jsonify(order)

    finally:
        conn.close()


# ─── PAINEL ADMIN ────────────────────────────────────────────────────────────

@orders_bp.route('/admin/orders', methods=['GET'])
@jwt_required()
def admin_get_orders():
    """Lista todos os pedidos (admin)."""
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = request.args.get('status', '')
    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()

    try:
        where = "WHERE 1=1"
        params = []
        if status:
            where += " AND o.status = ?"
            params.append(status)

        cursor.execute(f'''
            SELECT COUNT(*) as total FROM orders o {where}
        ''', params)
        total = cursor.fetchone()['total']

        cursor.execute(f'''
            SELECT o.*, u.name as user_name, u.email as user_email,
                   p.method as payment_method, p.status as payment_status
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN payments p ON p.order_id = o.id
            {where}
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset])

        orders = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'orders': orders,
            'total': total,
            'page': page,
            'pages': (total + per_page - 1) // per_page
        })

    finally:
        conn.close()


@orders_bp.route('/admin/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    """Atualiza o status de um pedido (admin)."""
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403

    data = request.get_json()
    valid_statuses = ['pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled']

    if data.get('status') not in valid_statuses:
        return jsonify({'error': 'Status inválido'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                       (data['status'], order_id))
        conn.commit()
        return jsonify({'message': 'Status atualizado!'})
    finally:
        conn.close()


@orders_bp.route('/admin/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Retorna dados do dashboard administrativo."""
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Totais gerais
        cursor.execute("SELECT COUNT(*) as total, SUM(total) as revenue FROM orders WHERE status != 'cancelled'")
        orders_data = dict(cursor.fetchone())

        cursor.execute("SELECT COUNT(*) as total FROM users")
        users_data = dict(cursor.fetchone())

        cursor.execute("SELECT COUNT(*) as total FROM products WHERE is_active = 1")
        products_data = dict(cursor.fetchone())

        cursor.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'")
        pending_data = dict(cursor.fetchone())

        # Pedidos por mês (últimos 6 meses)
        cursor.execute('''
            SELECT strftime('%Y-%m', created_at) as month,
                   COUNT(*) as count,
                   SUM(total) as revenue
            FROM orders
            WHERE status != 'cancelled'
            AND created_at >= date('now', '-6 months')
            GROUP BY month
            ORDER BY month
        ''')
        monthly = [dict(row) for row in cursor.fetchall()]

        # Produtos mais vendidos
        cursor.execute('''
            SELECT p.name, p.image_url, SUM(oi.quantity) as sold, SUM(oi.subtotal) as revenue
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status != 'cancelled'
            GROUP BY p.id
            ORDER BY sold DESC
            LIMIT 5
        ''')
        top_products = [dict(row) for row in cursor.fetchall()]

        # Pedidos recentes
        cursor.execute('''
            SELECT o.order_number, o.total, o.status, o.created_at,
                   u.name as user_name
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')
        recent_orders = [dict(row) for row in cursor.fetchall()]

        # Distribuição por status
        cursor.execute('''
            SELECT status, COUNT(*) as count FROM orders GROUP BY status
        ''')
        status_dist = [dict(row) for row in cursor.fetchall()]

        # Produtos com estoque baixo
        cursor.execute('''
            SELECT id, name, stock, sku FROM products
            WHERE is_active = 1 AND stock <= 5
            ORDER BY stock ASC
            LIMIT 5
        ''')
        low_stock = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'summary': {
                'total_orders': orders_data['total'] or 0,
                'total_revenue': orders_data['revenue'] or 0,
                'total_users': users_data['total'],
                'total_products': products_data['total'],
                'pending_orders': pending_data['total']
            },
            'monthly_data': monthly,
            'top_products': top_products,
            'recent_orders': recent_orders,
            'status_distribution': status_dist,
            'low_stock': low_stock
        })

    finally:
        conn.close()


@orders_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def admin_get_users():
    """Lista todos os usuários (admin)."""
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT u.id, u.name, u.email, u.phone, u.created_at, u.is_active,
                   COUNT(o.id) as order_count, SUM(o.total) as total_spent
            FROM users u
            LEFT JOIN orders o ON o.user_id = u.id AND o.status != 'cancelled'
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''')
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify(users)
    finally:
        conn.close()
