"""
Rotas de produtos e categorias para a loja Dux Imports.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.database.db import get_connection

products_bp = Blueprint('products', __name__, url_prefix='/api')


def admin_required(fn):
    """Decorator para verificar se o usuário é administrador."""
    from functools import wraps
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Acesso restrito a administradores'}), 403
        return fn(*args, **kwargs)
    return wrapper


# ─── CATEGORIAS ─────────────────────────────────────────────────────────────

@products_bp.route('/categories', methods=['GET'])
def get_categories():
    """Lista todas as categorias ativas."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT c.*, COUNT(p.id) as product_count
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
            WHERE c.is_active = 1
            GROUP BY c.id
            ORDER BY c.name
        ''')
        categories = [dict(row) for row in cursor.fetchall()]
        return jsonify(categories)
    finally:
        conn.close()


@products_bp.route('/categories', methods=['POST'])
@admin_required
def create_category():
    """Cria uma nova categoria."""
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Nome é obrigatório'}), 400

    slug = data['name'].lower().replace(' ', '-').replace('ã', 'a').replace('ç', 'c').replace('é', 'e').replace('ê', 'e').replace('ó', 'o').replace('ô', 'o').replace('á', 'a').replace('í', 'i').replace('ú', 'u')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)",
                       (data['name'], slug, data.get('description', '')))
        conn.commit()
        return jsonify({'message': 'Categoria criada!', 'id': cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': 'Erro ao criar categoria ou nome já existe'}), 400
    finally:
        conn.close()


@products_bp.route('/categories/<int:cat_id>', methods=['PUT'])
@admin_required
def update_category(cat_id):
    """Atualiza uma categoria."""
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE categories SET name=?, description=?, is_active=? WHERE id=?",
                       (data.get('name'), data.get('description'), data.get('is_active', 1), cat_id))
        conn.commit()
        return jsonify({'message': 'Categoria atualizada!'})
    finally:
        conn.close()


@products_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@admin_required
def delete_category(cat_id):
    """Desativa uma categoria."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE categories SET is_active = 0 WHERE id = ?", (cat_id,))
        conn.commit()
        return jsonify({'message': 'Categoria removida!'})
    finally:
        conn.close()


# ─── PRODUTOS ────────────────────────────────────────────────────────────────

@products_bp.route('/products', methods=['GET'])
def get_products():
    """Lista produtos com filtros e paginação."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    featured = request.args.get('featured', '')
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'DESC')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')

    offset = (page - 1) * per_page

    conn = get_connection()
    cursor = conn.cursor()

    try:
        where_clauses = ["p.is_active = 1"]
        params = []

        if category:
            where_clauses.append("c.slug = ?")
            params.append(category)

        if search:
            where_clauses.append("(p.name LIKE ? OR p.description LIKE ? OR p.brand LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

        if featured:
            where_clauses.append("p.is_featured = 1")

        if min_price:
            where_clauses.append("p.price >= ?")
            params.append(float(min_price))

        if max_price:
            where_clauses.append("p.price <= ?")
            params.append(float(max_price))

        where_sql = " AND ".join(where_clauses)

        # Contar total
        cursor.execute(f'''
            SELECT COUNT(*) as total FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE {where_sql}
        ''', params)
        total = cursor.fetchone()['total']

        # Validar ordenação
        valid_sorts = ['price', 'name', 'created_at', 'stock']
        valid_orders = ['ASC', 'DESC']
        sort = sort if sort in valid_sorts else 'created_at'
        order = order if order in valid_orders else 'DESC'

        cursor.execute(f'''
            SELECT p.*, c.name as category_name, c.slug as category_slug
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE {where_sql}
            ORDER BY p.{sort} {order}
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset])

        products = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'products': products,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })

    finally:
        conn.close()


@products_bp.route('/products/<slug>', methods=['GET'])
def get_product(slug):
    """Retorna um produto pelo slug."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT p.*, c.name as category_name, c.slug as category_slug
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.slug = ? AND p.is_active = 1
        ''', (slug,))
        product = cursor.fetchone()

        if not product:
            return jsonify({'error': 'Produto não encontrado'}), 404

        # Produtos relacionados
        cursor.execute('''
            SELECT id, name, slug, price, original_price, image_url, stock
            FROM products
            WHERE category_id = ? AND id != ? AND is_active = 1
            LIMIT 4
        ''', (product['category_id'], product['id']))
        related = [dict(row) for row in cursor.fetchall()]

        result = dict(product)
        result['related'] = related
        return jsonify(result)

    finally:
        conn.close()


@products_bp.route('/products', methods=['POST'])
@admin_required
def create_product():
    """Cria um novo produto."""
    data = request.get_json()

    required = ['name', 'price', 'stock']
    for field in required:
        if data.get(field) is None:
            return jsonify({'error': f'Campo {field} é obrigatório'}), 400

    import re
    slug = re.sub(r'[^a-z0-9-]', '', data['name'].lower().replace(' ', '-')
                  .replace('ã', 'a').replace('ç', 'c').replace('é', 'e')
                  .replace('ê', 'e').replace('ó', 'o').replace('ô', 'o')
                  .replace('á', 'a').replace('í', 'i').replace('ú', 'u')
                  .replace('à', 'a').replace('â', 'a').replace('õ', 'o'))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Garantir slug único
        base_slug = slug
        counter = 1
        while True:
            cursor.execute("SELECT id FROM products WHERE slug = ?", (slug,))
            if not cursor.fetchone():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        cursor.execute('''
            INSERT INTO products (name, slug, description, price, original_price,
                category_id, image_url, stock, sku, brand, is_featured, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            data['name'], slug, data.get('description', ''),
            data['price'], data.get('original_price'),
            data.get('category_id'), data.get('image_url', ''),
            data['stock'], data.get('sku', ''), data.get('brand', ''),
            data.get('is_featured', 0)
        ))

        product_id = cursor.lastrowid

        # Registrar no histórico de estoque
        cursor.execute('''
            INSERT INTO stock_history (product_id, type, quantity, previous_stock, new_stock, reference)
            VALUES (?, 'entrada', ?, 0, ?, 'Cadastro inicial')
        ''', (product_id, data['stock'], data['stock']))

        conn.commit()
        return jsonify({'message': 'Produto criado!', 'id': product_id, 'slug': slug}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Erro ao criar produto: {str(e)}'}), 400
    finally:
        conn.close()


@products_bp.route('/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    """Atualiza um produto."""
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verificar estoque anterior
        cursor.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
        old = cursor.fetchone()
        if not old:
            return jsonify({'error': 'Produto não encontrado'}), 404

        old_stock = old['stock']
        new_stock = data.get('stock', old_stock)

        cursor.execute('''
            UPDATE products SET name=?, description=?, price=?, original_price=?,
                category_id=?, image_url=?, stock=?, sku=?, brand=?,
                is_featured=?, is_active=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            data.get('name'), data.get('description'), data.get('price'),
            data.get('original_price'), data.get('category_id'),
            data.get('image_url'), new_stock, data.get('sku'),
            data.get('brand'), data.get('is_featured', 0),
            data.get('is_active', 1), product_id
        ))

        # Registrar mudança de estoque
        if new_stock != old_stock:
            diff = new_stock - old_stock
            tipo = 'entrada' if diff > 0 else 'saida'
            cursor.execute('''
                INSERT INTO stock_history (product_id, type, quantity, previous_stock, new_stock, reference)
                VALUES (?, ?, ?, ?, ?, 'Ajuste manual')
            ''', (product_id, tipo, abs(diff), old_stock, new_stock))

        conn.commit()
        return jsonify({'message': 'Produto atualizado!'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Erro ao atualizar: {str(e)}'}), 400
    finally:
        conn.close()


@products_bp.route('/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    """Desativa um produto."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        conn.commit()
        return jsonify({'message': 'Produto removido!'})
    finally:
        conn.close()
