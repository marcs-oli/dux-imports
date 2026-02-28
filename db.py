"""
Módulo de gerenciamento do banco de dados SQLite para Dux Imports.
Responsável pela criação das tabelas e inicialização dos dados.
"""

import sqlite3
import os
import bcrypt
from datetime import datetime

# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dux_imports.db')


def get_connection():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Inicializa o banco de dados criando todas as tabelas necessárias."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            cpf TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Tabela de administradores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Tabela de categorias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            image_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            original_price REAL,
            category_id INTEGER,
            image_url TEXT,
            images TEXT,
            stock INTEGER DEFAULT 0,
            sku TEXT UNIQUE,
            brand TEXT,
            weight REAL,
            is_active INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Tabela de pedidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_number TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            subtotal REAL NOT NULL,
            shipping REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            total REAL NOT NULL,
            shipping_address TEXT,
            shipping_city TEXT,
            shipping_state TEXT,
            shipping_zip TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Tabela de itens do pedido
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Tabela de pagamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            amount REAL NOT NULL,
            transaction_id TEXT,
            installments INTEGER DEFAULT 1,
            card_last4 TEXT,
            pix_key TEXT,
            boleto_code TEXT,
            paid_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')

    # Tabela de histórico de estoque
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            previous_stock INTEGER NOT NULL,
            new_stock INTEGER NOT NULL,
            reference TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    conn.commit()

    # Inserir dados iniciais
    _seed_data(conn, cursor)

    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")


def _seed_data(conn, cursor):
    """Insere dados iniciais no banco de dados."""

    # Admin padrão
    cursor.execute("SELECT id FROM admins WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            INSERT INTO admins (username, password, name, email)
            VALUES (?, ?, ?, ?)
        ''', ('admin', hashed, 'Administrador', 'admin@duximports.com'))

    # Categorias
    categories = [
        ('Eletrônicos', 'eletronicos', 'Smartphones, tablets, notebooks e muito mais', '📱'),
        ('Informática', 'informatica', 'Computadores, periféricos e acessórios', '💻'),
        ('Áudio e Vídeo', 'audio-video', 'Fones, caixas de som e TVs', '🎧'),
        ('Games', 'games', 'Consoles, jogos e acessórios gamer', '🎮'),
        ('Câmeras', 'cameras', 'Câmeras fotográficas e filmadoras', '📷'),
        ('Acessórios', 'acessorios', 'Capas, carregadores e cabos', '🔌'),
    ]

    for cat in categories:
        cursor.execute("SELECT id FROM categories WHERE slug = ?", (cat[1],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO categories (name, slug, description)
                VALUES (?, ?, ?)
            ''', (cat[0], cat[1], cat[2]))

    conn.commit()

    # Buscar IDs das categorias
    cursor.execute("SELECT id, slug FROM categories")
    cat_map = {row['slug']: row['id'] for row in cursor.fetchall()}

    # Produtos iniciais
    products = [
        {
            'name': 'iPhone 15 Pro Max 256GB',
            'slug': 'iphone-15-pro-max-256gb',
            'description': 'O iPhone 15 Pro Max com chip A17 Pro, câmera de 48MP com zoom óptico 5x, tela Super Retina XDR de 6.7", titânio grau aeroespacial e bateria de longa duração.',
            'price': 8999.90,
            'original_price': 9999.90,
            'category_id': cat_map.get('eletronicos'),
            'image_url': 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&q=80',
            'stock': 15,
            'sku': 'IPH15PM256',
            'brand': 'Apple',
            'is_featured': 1
        },
        {
            'name': 'Samsung Galaxy S24 Ultra 512GB',
            'slug': 'samsung-galaxy-s24-ultra-512gb',
            'description': 'Galaxy S24 Ultra com S Pen integrada, câmera de 200MP, processador Snapdragon 8 Gen 3, tela Dynamic AMOLED 2X de 6.8" e 12GB de RAM.',
            'price': 7499.90,
            'original_price': 8499.90,
            'category_id': cat_map.get('eletronicos'),
            'image_url': 'https://images.unsplash.com/photo-1706439136197-1b0c7e4d6b3c?w=600&q=80',
            'stock': 20,
            'sku': 'SGS24U512',
            'brand': 'Samsung',
            'is_featured': 1
        },
        {
            'name': 'MacBook Pro 14" M3 Pro 512GB',
            'slug': 'macbook-pro-14-m3-pro-512gb',
            'description': 'MacBook Pro com chip M3 Pro, tela Liquid Retina XDR de 14.2", 18GB de memória unificada, 512GB SSD e até 18 horas de bateria.',
            'price': 16999.90,
            'original_price': 18999.90,
            'category_id': cat_map.get('informatica'),
            'image_url': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=80',
            'stock': 8,
            'sku': 'MBP14M3P512',
            'brand': 'Apple',
            'is_featured': 1
        },
        {
            'name': 'Dell XPS 15 Intel Core i9 RTX 4070',
            'slug': 'dell-xps-15-i9-rtx4070',
            'description': 'Notebook Dell XPS 15 com processador Intel Core i9-13900H, RTX 4070 8GB, 32GB DDR5, 1TB NVMe SSD e tela OLED 3.5K de 15.6".',
            'price': 14499.90,
            'original_price': 15999.90,
            'category_id': cat_map.get('informatica'),
            'image_url': 'https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=600&q=80',
            'stock': 5,
            'sku': 'DXPS15I9RTX',
            'brand': 'Dell',
            'is_featured': 0
        },
        {
            'name': 'AirPods Pro 2ª Geração',
            'slug': 'airpods-pro-2a-geracao',
            'description': 'AirPods Pro com cancelamento ativo de ruído, modo transparência adaptável, áudio espacial personalizado e até 30h de bateria com o estojo.',
            'price': 1899.90,
            'original_price': 2199.90,
            'category_id': cat_map.get('audio-video'),
            'image_url': 'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&q=80',
            'stock': 30,
            'sku': 'APPRO2G',
            'brand': 'Apple',
            'is_featured': 1
        },
        {
            'name': 'Sony WH-1000XM5 Headphone',
            'slug': 'sony-wh-1000xm5',
            'description': 'Headphone premium Sony com cancelamento de ruído líder do setor, 30h de bateria, suporte LDAC para áudio Hi-Res e microfone com IA.',
            'price': 2299.90,
            'original_price': 2799.90,
            'category_id': cat_map.get('audio-video'),
            'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80',
            'stock': 18,
            'sku': 'SNYWH1000XM5',
            'brand': 'Sony',
            'is_featured': 1
        },
        {
            'name': 'PlayStation 5 Slim + 2 Controles',
            'slug': 'playstation-5-slim-2-controles',
            'description': 'Console PlayStation 5 Slim com SSD de 1TB, leitor de disco, 2 controles DualSense e resolução 4K a 120fps com ray tracing.',
            'price': 4299.90,
            'original_price': 4799.90,
            'category_id': cat_map.get('games'),
            'image_url': 'https://images.unsplash.com/photo-1607853202273-797f1c22a38e?w=600&q=80',
            'stock': 12,
            'sku': 'PS5SLIM2CTR',
            'brand': 'Sony',
            'is_featured': 1
        },
        {
            'name': 'Xbox Series X 1TB',
            'slug': 'xbox-series-x-1tb',
            'description': 'Console Xbox Series X com 1TB SSD, processador AMD Zen 2, GPU de 12 teraflops, 4K a 120fps, Quick Resume e compatibilidade retroativa.',
            'price': 3999.90,
            'original_price': 4499.90,
            'category_id': cat_map.get('games'),
            'image_url': 'https://images.unsplash.com/photo-1621259182978-fbf93132d53d?w=600&q=80',
            'stock': 10,
            'sku': 'XBXS1TB',
            'brand': 'Microsoft',
            'is_featured': 0
        },
        {
            'name': 'Canon EOS R6 Mark II + Lente 24-105mm',
            'slug': 'canon-eos-r6-mark-ii-24-105mm',
            'description': 'Câmera mirrorless Canon EOS R6 Mark II com sensor full-frame de 24.2MP, gravação 4K 60fps RAW, estabilização IBIS 8 stops e lente 24-105mm f/4L.',
            'price': 18999.90,
            'original_price': 21999.90,
            'category_id': cat_map.get('cameras'),
            'image_url': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80',
            'stock': 4,
            'sku': 'CEOSR6MK2KIT',
            'brand': 'Canon',
            'is_featured': 0
        },
        {
            'name': 'iPad Pro 12.9" M2 256GB WiFi',
            'slug': 'ipad-pro-12-9-m2-256gb',
            'description': 'iPad Pro com chip M2, tela Liquid Retina XDR de 12.9" com ProMotion 120Hz, câmera TrueDepth 12MP, conector Thunderbolt e suporte ao Apple Pencil 2.',
            'price': 9499.90,
            'original_price': 10499.90,
            'category_id': cat_map.get('eletronicos'),
            'image_url': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&q=80',
            'stock': 9,
            'sku': 'IPADPRO129M2',
            'brand': 'Apple',
            'is_featured': 0
        },
        {
            'name': 'JBL Charge 5 Caixa Bluetooth',
            'slug': 'jbl-charge-5-bluetooth',
            'description': 'Caixa de som JBL Charge 5 com 20h de bateria, resistência IP67 à água e poeira, PartyBoost para conectar múltiplas caixas e carregador USB.',
            'price': 899.90,
            'original_price': 1099.90,
            'category_id': cat_map.get('audio-video'),
            'image_url': 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80',
            'stock': 25,
            'sku': 'JBLCHG5',
            'brand': 'JBL',
            'is_featured': 0
        },
        {
            'name': 'Logitech MX Master 3S Mouse',
            'slug': 'logitech-mx-master-3s',
            'description': 'Mouse premium Logitech MX Master 3S com sensor de 8000 DPI, scroll MagSpeed silencioso, 70 dias de bateria e compatibilidade multi-dispositivo.',
            'price': 599.90,
            'original_price': 699.90,
            'category_id': cat_map.get('informatica'),
            'image_url': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&q=80',
            'stock': 40,
            'sku': 'LGTMXM3S',
            'brand': 'Logitech',
            'is_featured': 0
        },
    ]

    for prod in products:
        cursor.execute("SELECT id FROM products WHERE slug = ?", (prod['slug'],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO products (name, slug, description, price, original_price, category_id,
                    image_url, stock, sku, brand, is_featured)
                VALUES (:name, :slug, :description, :price, :original_price, :category_id,
                    :image_url, :stock, :sku, :brand, :is_featured)
            ''', prod)

    conn.commit()
    print("✅ Dados iniciais inseridos com sucesso!")
