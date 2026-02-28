/**
 * Dux Imports - JavaScript Principal
 * Utilitários globais: API, carrinho, autenticação, notificações
 */

// ─── CONFIGURAÇÃO DA API ─────────────────────────────────────────────────────
const API_BASE = '/api';

const api = {
  async request(method, endpoint, data = null, auth = false) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
      const token = localStorage.getItem('dux_token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    const config = { method, headers };
    if (data) config.body = JSON.stringify(data);

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, config);
      const json = await res.json();
      if (!res.ok) throw { status: res.status, message: json.error || 'Erro na requisição' };
      return json;
    } catch (err) {
      if (err.status) throw err;
      throw { status: 0, message: 'Erro de conexão com o servidor' };
    }
  },

  get: (endpoint, auth = false) => api.request('GET', endpoint, null, auth),
  post: (endpoint, data, auth = false) => api.request('POST', endpoint, data, auth),
  put: (endpoint, data, auth = false) => api.request('PUT', endpoint, data, auth),
  delete: (endpoint, auth = false) => api.request('DELETE', endpoint, null, auth),
};

// ─── AUTENTICAÇÃO ────────────────────────────────────────────────────────────
const auth = {
  getToken: () => localStorage.getItem('dux_token'),
  getUser: () => {
    try { return JSON.parse(localStorage.getItem('dux_user') || 'null'); }
    catch { return null; }
  },
  getAdminToken: () => localStorage.getItem('dux_admin_token'),
  getAdmin: () => {
    try { return JSON.parse(localStorage.getItem('dux_admin') || 'null'); }
    catch { return null; }
  },
  isLoggedIn: () => !!localStorage.getItem('dux_token'),
  isAdmin: () => !!localStorage.getItem('dux_admin_token'),

  login(token, user) {
    localStorage.setItem('dux_token', token);
    localStorage.setItem('dux_user', JSON.stringify(user));
    updateNavbar();
  },

  adminLogin(token, admin) {
    localStorage.setItem('dux_admin_token', token);
    localStorage.setItem('dux_admin', JSON.stringify(admin));
  },

  logout() {
    localStorage.removeItem('dux_token');
    localStorage.removeItem('dux_user');
    updateNavbar();
    window.location.href = '/';
  },

  adminLogout() {
    localStorage.removeItem('dux_admin_token');
    localStorage.removeItem('dux_admin');
    window.location.href = '/admin/login';
  }
};

// ─── CARRINHO ────────────────────────────────────────────────────────────────
const cart = {
  getItems: () => {
    try { return JSON.parse(localStorage.getItem('dux_cart') || '[]'); }
    catch { return []; }
  },

  saveItems(items) {
    localStorage.setItem('dux_cart', JSON.stringify(items));
    updateCartBadge();
    window.dispatchEvent(new CustomEvent('cartUpdated', { detail: items }));
  },

  add(product, quantity = 1) {
    const items = cart.getItems();
    const existing = items.find(i => i.id === product.id);
    if (existing) {
      existing.quantity = Math.min(existing.quantity + quantity, product.stock || 99);
    } else {
      items.push({
        id: product.id,
        name: product.name,
        price: product.price,
        image_url: product.image_url || '',
        slug: product.slug,
        stock: product.stock || 99,
        quantity
      });
    }
    cart.saveItems(items);
    toast.success(`"${product.name}" adicionado ao carrinho!`);
  },

  remove(productId) {
    const items = cart.getItems().filter(i => i.id !== productId);
    cart.saveItems(items);
  },

  updateQty(productId, quantity) {
    const items = cart.getItems();
    const item = items.find(i => i.id === productId);
    if (item) {
      if (quantity <= 0) {
        cart.remove(productId);
        return;
      }
      item.quantity = Math.min(quantity, item.stock);
      cart.saveItems(items);
    }
  },

  clear() {
    cart.saveItems([]);
  },

  getTotal() {
    return cart.getItems().reduce((sum, i) => sum + i.price * i.quantity, 0);
  },

  getCount() {
    return cart.getItems().reduce((sum, i) => sum + i.quantity, 0);
  }
};

// ─── TOAST NOTIFICATIONS ─────────────────────────────────────────────────────
const toast = {
  container: null,

  init() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = '', icon = '') {
    this.init();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `${icon ? `<span>${icon}</span>` : ''}<span>${message}</span>`;
    this.container.appendChild(el);
    setTimeout(() => {
      el.style.animation = 'fadeOut .3s ease forwards';
      setTimeout(() => el.remove(), 300);
    }, 3500);
  },

  success: (msg) => toast.show(msg, 'success', '✓'),
  error: (msg) => toast.show(msg, 'error', '✕'),
  warning: (msg) => toast.show(msg, 'warning', '⚠'),
  info: (msg) => toast.show(msg, '', 'ℹ'),
};

// ─── FORMATAÇÃO ──────────────────────────────────────────────────────────────
const fmt = {
  currency: (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0),
  date: (str) => {
    if (!str) return '-';
    return new Date(str).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  },
  datetime: (str) => {
    if (!str) return '-';
    return new Date(str).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  },
  discount: (original, current) => {
    if (!original || original <= current) return null;
    return Math.round((1 - current / original) * 100);
  },
  statusLabel: (status) => {
    const map = {
      pending: 'Aguardando', paid: 'Pago', processing: 'Processando',
      shipped: 'Enviado', delivered: 'Entregue', cancelled: 'Cancelado'
    };
    return map[status] || status;
  },
  paymentLabel: (method) => {
    const map = { pix: 'PIX', credit_card: 'Cartão de Crédito', boleto: 'Boleto' };
    return map[method] || method;
  }
};

// ─── NAVBAR ──────────────────────────────────────────────────────────────────
function updateNavbar() {
  const user = auth.getUser();
  const loginBtn = document.getElementById('nav-login-btn');
  const userMenu = document.getElementById('nav-user-menu');
  const userName = document.getElementById('nav-user-name');

  if (loginBtn && userMenu) {
    if (user) {
      loginBtn.classList.add('hidden');
      userMenu.classList.remove('hidden');
      if (userName) userName.textContent = user.name.split(' ')[0];
    } else {
      loginBtn.classList.remove('hidden');
      userMenu.classList.add('hidden');
    }
  }
}

function updateCartBadge() {
  const badge = document.getElementById('cart-badge');
  if (badge) {
    const count = cart.getCount();
    badge.textContent = count;
    badge.style.display = count > 0 ? 'flex' : 'none';
  }
}

// ─── BUSCA ────────────────────────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('navbar-search');
  const dropdown = document.getElementById('search-dropdown');
  if (!input || !dropdown) return;

  let timeout;
  input.addEventListener('input', () => {
    clearTimeout(timeout);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.classList.remove('show'); return; }
    timeout = setTimeout(() => performSearch(q), 300);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = input.value.trim();
      if (q) window.location.href = `/loja?search=${encodeURIComponent(q)}`;
    }
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('show');
    }
  });
}

async function performSearch(query) {
  const dropdown = document.getElementById('search-dropdown');
  if (!dropdown) return;

  try {
    const data = await api.get(`/products?search=${encodeURIComponent(query)}&per_page=5`);
    const products = data.products || [];

    if (products.length === 0) {
      dropdown.innerHTML = '<div style="padding:1rem;text-align:center;color:#64748b;font-size:.88rem;">Nenhum produto encontrado</div>';
    } else {
      dropdown.innerHTML = products.map(p => `
        <a href="/produto/${p.slug}" class="search-result-item">
          <img src="${p.image_url || 'https://via.placeholder.com/44'}" alt="${p.name}" onerror="this.src='https://via.placeholder.com/44'">
          <div class="info">
            <h4>${p.name}</h4>
            <span>${fmt.currency(p.price)}</span>
          </div>
        </a>
      `).join('') + `<a href="/loja?search=${encodeURIComponent(query)}" style="display:block;padding:.75rem 1rem;text-align:center;font-size:.82rem;color:#1a56db;font-weight:600;border-top:1px solid #f1f5f9;">Ver todos os resultados</a>`;
    }
    dropdown.classList.add('show');
  } catch (e) {
    dropdown.classList.remove('show');
  }
}

// ─── INICIALIZAÇÃO GLOBAL ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateNavbar();
  updateCartBadge();
  initSearch();

  // Logout
  const logoutBtn = document.getElementById('nav-logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', auth.logout);

  // Mobile menu toggle
  const menuToggle = document.getElementById('menu-toggle');
  const mobileMenu = document.getElementById('mobile-menu');
  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', () => {
      mobileMenu.classList.toggle('show');
    });
  }
});

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function requireAuth(redirectTo = '/login') {
  if (!auth.isLoggedIn()) {
    window.location.href = `${redirectTo}?redirect=${encodeURIComponent(window.location.pathname)}`;
    return false;
  }
  return true;
}

function requireAdmin() {
  if (!auth.isAdmin()) {
    window.location.href = '/admin/login';
    return false;
  }
  return true;
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function debounce(fn, delay) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

function slugify(text) {
  return text.toLowerCase()
    .replace(/[ãâà]/g, 'a').replace(/[éê]/g, 'e').replace(/[íî]/g, 'i')
    .replace(/[óôõ]/g, 'o').replace(/[úû]/g, 'u').replace(/ç/g, 'c')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
