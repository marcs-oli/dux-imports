# 🛒 Dux Imports — Sistema de E-commerce

Sistema completo de e-commerce desenvolvido com Flask (Python) no backend e HTML/CSS/JS puro no frontend.

## 🚀 Como Executar

```bash
cd dux-imports
pip install -r requirements.txt
python app.py
```

Acesse: **http://localhost:5000**

## 🔐 Credenciais

| Tipo | Usuário/E-mail | Senha |
|------|---------------|-------|
| Admin | `admin` | `admin123` |
| Cliente (teste) | `joao@teste.com` | `123456` |

## 📁 Estrutura do Projeto

```
dux-imports/
├── app.py                    # Servidor Flask principal
├── requirements.txt          # Dependências Python
├── dux_imports.db            # Banco de dados SQLite (gerado automaticamente)
├── backend/
│   ├── database/
│   │   └── db.py             # Schema e dados iniciais
│   └── routes/
│       ├── auth.py           # Autenticação (usuários e admin)
│       ├── products.py       # Produtos e categorias
│       └── orders.py         # Pedidos, pagamentos e dashboard
└── frontend/
    ├── index.html            # Página inicial
    ├── css/main.css          # Estilos globais
    ├── js/app.js             # JavaScript utilitário
    └── pages/
        ├── loja.html         # Catálogo com filtros
        ├── produto.html      # Página de produto
        ├── carrinho.html     # Carrinho de compras
        ├── checkout.html     # Finalização de compra
        ├── login.html        # Login de usuário
        ├── cadastro.html     # Cadastro de usuário
        ├── conta.html        # Área do cliente
        ├── pedidos.html      # Histórico de pedidos
        ├── admin.html        # Painel administrativo
        └── admin-login.html  # Login do admin
```

## 🌟 Funcionalidades

### Loja
- Página inicial com hero, categorias, produtos em destaque e banners
- Catálogo com filtros por categoria, faixa de preço e ordenação
- Busca em tempo real com dropdown de sugestões
- Página de produto com galeria, preços, estoque e produtos relacionados
- Carrinho de compras persistente (localStorage)
- Barra de progresso para frete grátis (acima de R$299)

### Checkout
- Formulário de endereço com busca automática por CEP (ViaCEP)
- 3 métodos de pagamento: PIX (5% desconto), Cartão de Crédito (12x) e Boleto
- Simulação de pagamento com geração de chave PIX e código de boleto
- Confirmação com número de pedido

### Área do Cliente
- Cadastro e login com JWT
- Perfil editável
- Histórico de pedidos com rastreamento de status
- Timeline visual do status do pedido

### Painel Administrativo
- Dashboard com KPIs (pedidos, receita, clientes, produtos)
- Gráfico de receita mensal (Chart.js)
- Gráfico de distribuição de status dos pedidos
- Produtos mais vendidos
- Alertas de estoque baixo
- CRUD completo de produtos
- Gerenciamento de categorias
- Listagem e atualização de status de pedidos
- Listagem de clientes com total gasto

## 🔌 API RESTful

### Autenticação
- `POST /api/auth/register` — Cadastro de usuário
- `POST /api/auth/login` — Login de usuário
- `POST /api/auth/admin/login` — Login administrativo
- `GET /api/auth/profile` — Perfil do usuário (JWT)
- `PUT /api/auth/profile` — Atualizar perfil (JWT)

### Produtos
- `GET /api/products` — Listar produtos (filtros: category, search, featured, min_price, max_price, sort, order, page)
- `GET /api/products/<slug>` — Produto individual + relacionados
- `POST /api/products` — Criar produto (admin)
- `PUT /api/products/<id>` — Atualizar produto (admin)
- `DELETE /api/products/<id>` — Desativar produto (admin)

### Categorias
- `GET /api/categories` — Listar categorias
- `POST /api/categories` — Criar categoria (admin)
- `DELETE /api/categories/<id>` — Desativar categoria (admin)

### Pedidos
- `POST /api/orders` — Criar pedido (JWT)
- `GET /api/orders/my` — Meus pedidos (JWT)
- `GET /api/orders/<id>` — Detalhes do pedido (JWT)
- `GET /api/admin/orders` — Todos os pedidos (admin)
- `PUT /api/admin/orders/<id>/status` — Atualizar status (admin)
- `GET /api/admin/dashboard` — Dados do dashboard (admin)
- `GET /api/admin/users` — Listar clientes (admin)

## 🎨 Tecnologias

- **Backend:** Python 3, Flask, Flask-JWT-Extended, Flask-CORS, bcrypt, SQLite
- **Frontend:** HTML5, CSS3, JavaScript ES6+, Font Awesome, Chart.js
- **Banco de Dados:** SQLite com schema completo e dados de exemplo
