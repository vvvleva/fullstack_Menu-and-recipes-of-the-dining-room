// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let currentUser = null;
let userRole = null;
let currentDishId = null;

const API_URL = 'http://localhost:8000';

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Админ панель загружена');
    checkServer();
    checkAdminAccess();
    
    // Добавляем обработчики поиска
    document.getElementById('dishSearch')?.addEventListener('input', filterDishes);
    document.getElementById('categoryFilter')?.addEventListener('change', filterDishes);
    document.getElementById('orderStatusFilter')?.addEventListener('change', loadOrders);
    document.getElementById('orderSearch')?.addEventListener('input', filterOrders);
    
    // Обновление статуса сервера каждые 5 секунд
    setInterval(checkServer, 5000);
});

// ==================== ПРОВЕРКА ДОСТУПА ====================
async function checkAdminAccess() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    
    try {
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (res.ok) {
            const userData = await res.json();
            currentUser = userData;
            userRole = userData.role;
            
            if (userRole !== 'admin') {
                showNotif('У вас нет прав доступа к админ панели', 'error');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
                return;
            }
            
            updateUserInfo();
            loadDishes();
            loadOrders();
            loadStats();
        } else {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/';
        }
    } catch (err) {
        console.error('Ошибка проверки доступа:', err);
        showNotif('Ошибка соединения с сервером', 'error');
    }
}

function updateUserInfo() {
    const infoDiv = document.getElementById('userInfo');
    const nameSpan = document.getElementById('userName');
    const roleSpan = document.getElementById('userRole');
    
    if (currentUser && infoDiv && nameSpan) {
        nameSpan.textContent = currentUser.full_name || 'Администратор';
        roleSpan.textContent = 'Администратор';
        infoDiv.style.display = 'block';
    }
}

// ==================== СЕРВЕР ====================
async function checkServer() {
    const statusEl = document.getElementById('serverStatus');
    if (!statusEl) return;
    
    try {
        const res = await fetch(`${API_URL}/health`);
        const indicator = statusEl.querySelector('.status-indicator');
        const text = statusEl.querySelector('.status-text');
        
        if (res.ok) {
            indicator.className = 'status-indicator online';
            text.textContent = 'Сервер онлайн';
        } else {
            throw new Error();
        }
    } catch (e) {
        const indicator = statusEl.querySelector('.status-indicator');
        const text = statusEl.querySelector('.status-text');
        indicator.className = 'status-indicator offline';
        text.textContent = 'Сервер офлайн';
    }
}

// ==================== УПРАВЛЕНИЕ ВКЛАДКАМИ ====================
function switchTab(tabName) {
    // Обновляем классы кнопок
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Обновляем классы контента
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// ==================== УПРАВЛЕНИЕ БЛЮДАМИ ====================
async function loadDishes() {
    const container = document.getElementById('adminDishesList');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
    
    try {
        const res = await fetch(`${API_URL}/api/menu`);
        const data = await res.json();
        const dishes = data.data || [];
        
        window.allDishes = dishes; // Сохраняем для фильтрации
        displayDishes(dishes);
    } catch (err) {
        console.error('Ошибка загрузки блюд:', err);
        container.innerHTML = '<div class="error-message">Ошибка загрузки блюд</div>';
    }
}

function displayDishes(dishes) {
    const container = document.getElementById('adminDishesList');
    
    if (dishes.length === 0) {
        container.innerHTML = '<div class="empty-message">Блюда не найдены</div>';
        return;
    }
    
    let html = '';
    dishes.forEach(dish => {
        html += `
            <div class="admin-dish-item" data-dish-id="${dish.id}">
                <div class="admin-dish-info">
                    <span class="admin-dish-name">${dish.name}</span>
                    <span class="admin-dish-price">${dish.price} ₽</span>
                    <span class="admin-dish-category">${dish.category}</span>
                    <span class="admin-dish-status ${dish.available ? 'available' : 'unavailable'}">
                        ${dish.available ? 'Доступно' : 'Недоступно'}
                    </span>
                    <span class="admin-dish-allergens" title="Аллергены определяются нейросетью">
                        <i class="fas fa-robot" style="color: #667eea;"></i>
                    </span>
                </div>
                <div class="admin-dish-actions">
                    <button class="admin-dish-edit" onclick="editDish(${dish.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="admin-dish-delete" onclick="deleteDish(${dish.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function filterDishes() {
    const searchTerm = document.getElementById('dishSearch').value.toLowerCase();
    const category = document.getElementById('categoryFilter').value;
    
    const filtered = window.allDishes.filter(dish => {
        const matchesSearch = dish.name.toLowerCase().includes(searchTerm);
        const matchesCategory = !category || dish.category === category;
        return matchesSearch && matchesCategory;
    });
    
    displayDishes(filtered);
}

function showAddDishModal() {
    document.getElementById('dishModalTitle').innerHTML = '<i class="fas fa-plus-circle"></i> Добавить блюдо';
    document.getElementById('dishForm').reset();
    document.getElementById('dishId').value = '';
    document.getElementById('dishModal').style.display = 'block';
}

async function editDish(id) {
    try {
        const res = await fetch(`${API_URL}/api/menu/${id}`);
        const data = await res.json();
        const dish = data.data;
        
        document.getElementById('dishModalTitle').innerHTML = '<i class="fas fa-edit"></i> Редактировать блюдо';
        document.getElementById('dishId').value = dish.id;
        document.getElementById('dishName').value = dish.name;
        document.getElementById('dishPrice').value = dish.price;
        document.getElementById('dishWeight').value = dish.weight;
        document.getElementById('dishCategory').value = dish.category;
        document.getElementById('dishCalories').value = dish.calories;
        document.getElementById('dishIngredients').value = dish.ingredients.join(', ');
        document.getElementById('dishAvailable').checked = dish.available;
        
        document.getElementById('dishModal').style.display = 'block';
    } catch (err) {
        console.error('Ошибка загрузки блюда:', err);
        showNotif('Ошибка загрузки блюда', 'error');
    }
}

function closeDishModal() {
    document.getElementById('dishModal').style.display = 'none';
}

async function handleSaveDish(event) {
    event.preventDefault();
    
    const token = localStorage.getItem('token');
    const dishId = document.getElementById('dishId').value;
    
    // Разбираем ингредиенты
    const ingredients = document.getElementById('dishIngredients').value
        .split(',')
        .map(i => i.trim())
        .filter(i => i);
    
    const dishData = {
        name: document.getElementById('dishName').value,
        price: parseInt(document.getElementById('dishPrice').value),
        weight: parseInt(document.getElementById('dishWeight').value),
        category: document.getElementById('dishCategory').value,
        calories: parseInt(document.getElementById('dishCalories').value),
        ingredients: ingredients,
        allergens: [], // Пустой массив - аллергены будут определяться нейросетью
        available: document.getElementById('dishAvailable').checked
    };
    
    const btn = document.getElementById('saveDishBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
    
    try {
        const url = dishId ? `${API_URL}/api/menu/${dishId}` : `${API_URL}/api/menu`;
        const method = dishId ? 'PUT' : 'POST';
        
        const res = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(dishData)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showNotif(dishId ? 'Блюдо обновлено' : 'Блюдо добавлено', 'success');
            closeDishModal();
            loadDishes();
        } else {
            showNotif(data.detail || 'Ошибка сохранения', 'error');
        }
    } catch (err) {
        console.error('Ошибка сохранения:', err);
        showNotif('Ошибка соединения с сервером', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save"></i> Сохранить';
    }
}

async function deleteDish(id) {
    if (!confirm('Вы уверены, что хотите удалить это блюдо?')) return;
    
    const token = localStorage.getItem('token');
    
    try {
        const res = await fetch(`${API_URL}/api/menu/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (res.ok) {
            showNotif('Блюдо удалено', 'success');
            loadDishes();
        } else {
            const data = await res.json();
            showNotif(data.detail || 'Ошибка удаления', 'error');
        }
    } catch (err) {
        console.error('Ошибка удаления:', err);
        showNotif('Ошибка соединения с сервером', 'error');
    }
}

// ==================== УПРАВЛЕНИЕ ЗАКАЗАМИ ====================
async function loadOrders() {
    const container = document.getElementById('adminOrdersList');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
    
    const token = localStorage.getItem('token');
    const status = document.getElementById('orderStatusFilter').value;
    
    try {
        let url = `${API_URL}/api/orders/admin/all?page=1&size=100`;
        if (status) {
            url += `&status=${status}`;
        }
        
        const res = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await res.json();
        const orders = data.items || [];
        
        window.allOrders = orders;
        displayOrders(orders);
    } catch (err) {
        console.error('Ошибка загрузки заказов:', err);
        container.innerHTML = '<div class="error-message">Ошибка загрузки заказов</div>';
    }
}

function displayOrders(orders) {
    const container = document.getElementById('adminOrdersList');
    
    if (orders.length === 0) {
        container.innerHTML = '<div class="empty-message">Заказы не найдены</div>';
        return;
    }
    
    let html = '';
    orders.forEach(order => {
        const statusClass = getStatusClass(order.status);
        const statusText = getStatusText(order.status);
        const date = new Date(order.created_at).toLocaleString();
        
        html += `
            <div class="admin-order-item" data-order-id="${order.id}">
                <div class="admin-order-header">
                    <span class="order-id">Заказ #${order.id}</span>
                    <span class="order-date">${date}</span>
                    <span class="order-status ${statusClass}">${statusText}</span>
                </div>
                <div class="admin-order-body">
                    <div class="order-customer">
                        <i class="fas fa-user"></i> ${order.user_email}
                    </div>
                    <div class="order-items">
                        ${order.items.map(item => `
                            <div class="order-item">
                                <span>${item.dish_name} x${item.quantity}</span>
                                <span>${item.subtotal} ₽</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="order-total">
                        Итого: <strong>${order.total_price} ₽</strong>
                    </div>
                </div>
                <div class="admin-order-actions">
                    <select class="status-select" onchange="updateOrderStatus(${order.id}, this.value)">
                        <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Ожидает</option>
                        <option value="confirmed" ${order.status === 'confirmed' ? 'selected' : ''}>Подтвержден</option>
                        <option value="preparing" ${order.status === 'preparing' ? 'selected' : ''}>Готовится</option>
                        <option value="ready" ${order.status === 'ready' ? 'selected' : ''}>Готов</option>
                        <option value="completed" ${order.status === 'completed' ? 'selected' : ''}>Выполнен</option>
                        <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Отменен</option>
                    </select>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function filterOrders() {
    const searchTerm = document.getElementById('orderSearch').value.toLowerCase();
    
    if (!window.allOrders) return;
    
    const filtered = window.allOrders.filter(order => {
        return order.user_email.toLowerCase().includes(searchTerm) ||
               order.id.toString().includes(searchTerm);
    });
    
    displayOrders(filtered);
}

async function updateOrderStatus(orderId, status) {
    const token = localStorage.getItem('token');
    
    try {
        const res = await fetch(`${API_URL}/api/orders/${orderId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: status })
        });
        
        if (res.ok) {
            showNotif('Статус заказа обновлен', 'success');
            loadOrders();
        } else {
            const data = await res.json();
            showNotif(data.detail || 'Ошибка обновления', 'error');
        }
    } catch (err) {
        console.error('Ошибка обновления статуса:', err);
        showNotif('Ошибка соединения с сервером', 'error');
    }
}

function getStatusClass(status) {
    const classes = {
        'pending': 'status-pending',
        'confirmed': 'status-confirmed',
        'preparing': 'status-preparing',
        'ready': 'status-ready',
        'completed': 'status-completed',
        'cancelled': 'status-cancelled'
    };
    return classes[status] || '';
}

function getStatusText(status) {
    const texts = {
        'pending': 'Ожидает',
        'confirmed': 'Подтвержден',
        'preparing': 'Готовится',
        'ready': 'Готов',
        'completed': 'Выполнен',
        'cancelled': 'Отменен'
    };
    return texts[status] || status;
}

// ==================== СТАТИСТИКА ====================
async function loadStats() {
    const container = document.getElementById('adminStats');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка...</div>';
    
    const token = localStorage.getItem('token');
    
    try {
        const res = await fetch(`${API_URL}/api/admin/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await res.json();
        const stats = data.data || {};
        
        const html = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-users"></i></div>
                    <div class="stat-info">
                        <span class="stat-value">${stats.users?.total || 0}</span>
                        <span class="stat-label">Пользователей</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-utensils"></i></div>
                    <div class="stat-info">
                        <span class="stat-value">${stats.dishes?.total || 0}</span>
                        <span class="stat-label">Блюд</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-shopping-bag"></i></div>
                    <div class="stat-info">
                        <span class="stat-value">${stats.orders?.today?.count || 0}</span>
                        <span class="stat-label">Заказов сегодня</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon"><i class="fas fa-ruble-sign"></i></div>
                    <div class="stat-info">
                        <span class="stat-value">${stats.orders?.today?.revenue || 0} ₽</span>
                        <span class="stat-label">Выручка сегодня</span>
                    </div>
                </div>
            </div>
            
            <div class="stats-section">
                <h3>Статусы заказов</h3>
                <div class="status-stats">
                    ${Object.entries(stats.orders?.by_status || {}).map(([status, count]) => `
                        <div class="status-stat">
                            <span class="status-name">${getStatusText(status)}</span>
                            <span class="status-count">${count}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="stats-section">
                <h3>Популярные блюда</h3>
                <div class="popular-dishes">
                    ${(stats.popular_dishes || []).map(dish => `
                        <div class="popular-dish">
                            <span class="dish-name">${dish.name}</span>
                            <span class="dish-orders">${dish.ordered} заказов</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    } catch (err) {
        console.error('Ошибка загрузки статистики:', err);
        container.innerHTML = '<div class="error-message">Ошибка загрузки статистики</div>';
    }
}

// ==================== ВЫХОД ====================
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    window.location.href = '/';
}

// ==================== УВЕДОМЛЕНИЯ ====================
function showNotif(msg, type) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const colors = { 
        success: '#28a745', 
        error: '#dc3545', 
        warning: '#ffc107', 
        info: '#17a2b8' 
    };
    
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    
    const notif = document.createElement('div');
    notif.innerHTML = `<i class="fas fa-${icons[type]}"></i> ${msg}`;
    notif.style.cssText = `
        background: ${colors[type] || colors.info};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 250px;
        z-index: 9999;
    `;
    container.appendChild(notif);
    
    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}