// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let currentSlide = 0;
let currentDishId = null;
let dishQuantity = 1;
let userAllergens = [];
let currentUser = null;
let userRole = 'user';
let isEditingProfile = false;

const slides = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.dot');
const track = document.getElementById('carouselTrack');
const API_URL = 'http://localhost:8000';

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Приложение запущено');
    checkServer();
    loadMenu();
    loadUser();
    loadCart();
    
    // Проверка параметра profile=open
    if (window.location.search.includes('profile=open')) {
        setTimeout(() => {
            goToSlide(3);
        }, 1000);
    }
    
    // Обновление статуса сервера каждые 5 секунд
    setInterval(checkServer, 5000);
});

// ==================== НАВИГАЦИЯ ====================
function navigateToHome(event) {
    event.preventDefault();
    window.location.href = '/';
    return false;
}

// ==================== МОДАЛЬНЫЕ ОКНА ====================
function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
}

function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
}

function showAddDishModal() {
    if (userRole !== 'admin') {
        showNotif('Только администраторы могут добавлять блюда', 'error');
        return;
    }
    document.getElementById('addDishModal').style.display = 'block';
}

function closeAddDishModal() {
    document.getElementById('addDishModal').style.display = 'none';
    document.getElementById('addDishForm').reset();
}

// Закрытие модального окна при клике вне его
window.onclick = function(event) {
    const loginModal = document.getElementById('loginModal');
    const addDishModal = document.getElementById('addDishModal');
    if (event.target == loginModal) {
        loginModal.style.display = 'none';
    }
    if (event.target == addDishModal) {
        addDishModal.style.display = 'none';
    }
}

// ==================== АВТОРИЗАЦИЯ ====================
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    const btn = event.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
    
    try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            localStorage.setItem('token', data.access_token);
            await loadUserData();
            closeLoginModal();
            showNotif('Вход выполнен успешно!', 'success');
        } else {
            showNotif(data.detail || 'Ошибка входа', 'error');
        }
    } catch (err) {
        showNotif('Ошибка соединения с сервером', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Войти';
    }
}

async function loadUserData() {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    try {
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (res.ok) {
            const userData = await res.json();
            
            currentUser = {
                id: userData.id,
                name: userData.full_name,
                email: userData.email,
                allergens: userData.allergens || [],
                diet: userData.diet || null
            };
            userRole = userData.role || 'user';
            userAllergens = userData.allergens || [];
            
            localStorage.setItem('user', JSON.stringify(currentUser));
            localStorage.setItem('userRole', userRole);
            
            updateUserInfo();
            updateProfileUI();
            updateAdminUI();
            
            return currentUser;
        } else {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('userRole');
            currentUser = null;
            userRole = 'user';
            userAllergens = [];
            return null;
        }
    } catch (err) {
        return null;
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

// ==================== КАРУСЕЛЬ ====================
function showSlide(index) {
    if (index < 0) index = 0;
    if (index >= slides.length) index = slides.length - 1;
    
    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    
    slides[index].classList.add('active');
    dots[index].classList.add('active');
    currentSlide = index;
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
}

function prevSlide() {
    currentSlide = (currentSlide - 1 + slides.length) % slides.length;
    showSlide(currentSlide);
}

function goToSlide(index) {
    showSlide(index);
}

// ==================== КОЛИЧЕСТВО ====================
function increaseQuantity() {
    const qtySpan = document.getElementById('dishQuantity');
    if (qtySpan) {
        dishQuantity = parseInt(qtySpan.textContent) + 1;
        qtySpan.textContent = dishQuantity;
    }
}

function decreaseQuantity() {
    const qtySpan = document.getElementById('dishQuantity');
    if (qtySpan) {
        let current = parseInt(qtySpan.textContent);
        if (current > 1) {
            dishQuantity = current - 1;
            qtySpan.textContent = dishQuantity;
        }
    }
}

// ==================== МЕНЮ ====================
async function loadMenu() {
    const listEl = document.getElementById('menuList');
    if (!listEl) return;
    
    listEl.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка меню...</div>';
    
    try {
        const res = await fetch(`${API_URL}/api/menu`);
        const data = await res.json();
        const items = data.data || [];
        
        if (!items.length) {
            listEl.innerHTML = '<div class="menu-item">Меню пусто</div>';
            return;
        }
        
        listEl.innerHTML = '';
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'menu-item';
            div.onclick = () => selectDish(item.id);
            
            const hasAllergens = item.allergens && item.allergens.length > 0;
            const hasUserAllergens = hasAllergens && userAllergens.length > 0 ? 
                item.allergens.some(a => userAllergens.includes(a)) : false;
            
            let allergenText = 'Безопасно';
            let allergenClass = 'safe';
            
            if (hasUserAllergens) {
                allergenText = '⚠ Содержит Ваши аллергены';
                allergenClass = 'danger';
            } else if (hasAllergens) {
                allergenText = 'ℹ Содержит аллергены';
                allergenClass = 'warning';
            }
            
            div.innerHTML = `
                <div class="item-row">
                    <span class="item-name">${item.name}</span>
                    <span class="item-price">${item.price} ₽</span>
                </div>
                <div class="item-allergen ${allergenClass}">
                    ${allergenText}
                </div>
            `;
            listEl.appendChild(div);
        });
    } catch (err) {
        listEl.innerHTML = '<div class="menu-item">Ошибка загрузки</div>';
    }
}

async function selectDish(id) {
    try {
        const res = await fetch(`${API_URL}/api/menu/${id}`);
        const data = await res.json();
        const dish = data.data;
        if (!dish) return;
        
        currentDishId = dish.id;
        dishQuantity = 1;
        document.getElementById('dishQuantity').textContent = '1';
        
        document.getElementById('dishTitle').innerHTML = `<i class="fas fa-info-circle"></i> ${dish.name}`;
        document.getElementById('dishPrice').textContent = dish.price + ' ₽';
        document.getElementById('dishMeta').textContent = dish.weight + ' г · ' + dish.calories + ' ккал';
        
        const dishAllergens = dish.allergens || [];
        const userMatches = dishAllergens.filter(a => userAllergens.includes(a));
        const aiBlock = document.getElementById('aiBlock');
        const aiTitle = document.getElementById('aiTitle');
        const aiMsg = document.getElementById('aiMessage');
        
        if (userMatches.length > 0) {
            aiBlock.className = 'ai-analysis danger';
            aiTitle.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Обнаружены ваши аллергены';
            aiMsg.textContent = 'Внимание! Блюдо содержит: ' + userMatches.join(', ');
        } else if (dishAllergens.length > 0) {
            aiBlock.className = 'ai-analysis warning';
            aiTitle.innerHTML = '<i class="fas fa-exclamation-circle"></i> Блюдо содержит аллергены';
            aiMsg.textContent = 'Состав: ' + dishAllergens.join(', ');
        } else {
            aiBlock.className = 'ai-analysis safe';
            aiTitle.innerHTML = '<i class="fas fa-check-circle"></i> Безопасно';
            aiMsg.textContent = 'Аллергены не обнаружены';
        }
        
        const ingList = document.getElementById('ingredientsList');
        ingList.innerHTML = '';
        (dish.ingredients || []).forEach(ing => {
            const li = document.createElement('li');
            li.textContent = ing;
            if (dishAllergens.some(a => ing.toLowerCase().includes(a))) {
                li.className = 'allergen-item';
            }
            ingList.appendChild(li);
        });
        
        goToSlide(1);
    } catch (err) {
        showNotif('Ошибка загрузки блюда', 'error');
    }
}

// ==================== АДМИН ФУНКЦИИ ====================
async function handleAddDish(event) {
    event.preventDefault();
    
    if (userRole !== 'admin') {
        showNotif('Только администраторы могут добавлять блюда', 'error');
        closeAddDishModal();
        return;
    }
    
    const token = localStorage.getItem('token');
    if (!token) {
        showNotif('Необходимо авторизоваться', 'error');
        closeAddDishModal();
        return;
    }
    
    // Убрана обработка аллергенов - они будут определяться нейросетью
    
    const ingredientsStr = document.getElementById('dishIngredients').value;
    const ingredients = ingredientsStr.split(',').map(i => i.trim()).filter(i => i);
    
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
    
    const btn = event.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Добавление...';
    
    try {
        const res = await fetch(`${API_URL}/api/menu`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(dishData)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showNotif('Блюдо успешно добавлено!', 'success');
            closeAddDishModal();
            loadMenu();
        } else {
            showNotif(data.detail || 'Ошибка при добавлении блюда', 'error');
        }
    } catch (err) {
        showNotif('Ошибка соединения с сервером', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-plus-circle"></i> Добавить блюдо';
    }
}

function updateAdminUI() {
    const adminBtn = document.getElementById('adminAddBtn');
    if (adminBtn) {
        adminBtn.style.display = userRole === 'admin' ? 'inline-flex' : 'none';
    }
    
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        let adminLink = document.getElementById('adminNavLink');
        if (userRole === 'admin') {
            if (!adminLink) {
                adminLink = document.createElement('a');
                adminLink.id = 'adminNavLink';
                adminLink.href = '/admin.html';
                adminLink.className = 'nav-link';
                adminLink.innerHTML = '<i class="fas fa-crown"></i> Админ панель';
                navLinks.appendChild(adminLink);
            }
        } else {
            if (adminLink) {
                adminLink.remove();
            }
        }
    }
}

// ==================== КОРЗИНА ====================
function addToCart() {
    if (!currentDishId) {
        showNotif('Сначала выберите блюдо', 'warning');
        return;
    }
    
    if (!currentUser) {
        showNotif('Для добавления в корзину необходимо войти', 'warning');
        showLoginModal();
        return;
    }
    
    const name = document.getElementById('dishTitle').textContent.replace('', '').trim();
    const priceText = document.getElementById('dishPrice').textContent;
    const price = parseInt(priceText.replace('₽', '').trim());
    const total = price * dishQuantity;
    
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const existing = cart.find(item => item.id === currentDishId);
    
    if (existing) {
        existing.quantity += dishQuantity;
        existing.total = existing.price * existing.quantity;
    } else {
        cart.push({
            id: currentDishId,
            name: name,
            quantity: dishQuantity,
            price: price,
            total: total
        });
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    showNotif(`Добавлено: ${name} x${dishQuantity}`, 'success');
    loadCart();
}

function loadCart() {
    const cartEl = document.getElementById('cartItems');
    const totalEl = document.getElementById('cartTotal');
    if (!cartEl) return;
    
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        cartEl.innerHTML = '<div class="empty-cart"><i class="fas fa-shopping-basket"></i><br>Корзина пуста</div>';
        if (totalEl) totalEl.innerHTML = '';
        return;
    }
    
    let html = '';
    let total = 0;
    
    cart.forEach((item, i) => {
        total += item.total;
        html += `
            <div class="cart-item">
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-details">
                        <span>${item.price} ₽ × ${item.quantity}</span>
                    </div>
                </div>
                <div class="cart-item-price">${item.total} ₽</div>
                <button class="cart-item-remove" onclick="removeFromCart(${i})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    });
    
    cartEl.innerHTML = html;
    if (totalEl) totalEl.innerHTML = `<i class="fas fa-calculator"></i> Итого: ${total} ₽`;
}

function removeFromCart(index) {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const removed = cart[index];
    cart.splice(index, 1);
    localStorage.setItem('cart', JSON.stringify(cart));
    loadCart();
    showNotif(`Удалено: ${removed.name}`, 'info');
}

async function checkout() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    if (cart.length === 0) {
        showNotif('Корзина пуста', 'warning');
        return;
    }
    
    if (!currentUser) {
        showNotif('Для оформления заказа необходимо войти', 'warning');
        showLoginModal();
        return;
    }
    
    const token = localStorage.getItem('token');
    if (!token) {
        showNotif('Необходимо авторизоваться', 'error');
        showLoginModal();
        return;
    }
    
    const orderData = {
        items: cart.map(item => ({
            dish_id: item.id,
            quantity: item.quantity,
            special_requests: ''
        })),
        delivery_time: null,
        comments: ''
    };
    
    const btn = document.querySelector('.checkout-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Оформление...';
    
    try {
        const res = await fetch(`${API_URL}/api/orders/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(orderData)
        });
        
        if (res.ok) {
            localStorage.removeItem('cart');
            loadCart();
            showNotif('Заказ успешно оформлен!', 'success');
            loadOrderHistory();
            setTimeout(() => goToSlide(3), 2000);
        } else {
            const data = await res.json();
            showNotif(data.detail || 'Ошибка при оформлении заказа', 'error');
        }
    } catch (err) {
        showNotif('Ошибка соединения с сервером', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function loadOrderHistory() {
    if (!currentUser) return;
    
    const token = localStorage.getItem('token');
    if (!token) return;
    
    const container = document.getElementById('orderHistoryContainer');
    if (!container) return;
    
    try {
        const res = await fetch(`${API_URL}/api/orders/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (res.ok) {
            const data = await res.json();
            const orders = data.items || [];
            
            if (orders.length === 0) {
                container.innerHTML = `
                    <div class="profile-section">
                        <div class="section-title">
                            <i class="fas fa-history"></i> История заказов
                        </div>
                        <p class="empty-orders">У вас пока нет заказов</p>
                    </div>
                `;
                return;
            }
            
            const ordersHtml = `
                <div class="profile-section">
                    <div class="section-title">
                        <i class="fas fa-history"></i> Последние заказы
                    </div>
                    <div class="orders-list">
                        ${orders.slice(0, 5).map(order => `
                            <div class="order-item">
                                <div class="order-info">
                                    <strong>Заказ #${order.id}</strong>
                                    <div class="order-date">${new Date(order.created_at).toLocaleDateString()}</div>
                                </div>
                                <div class="order-total">${order.total_price} ₽</div>
                                <div class="order-status ${order.status}">${getStatusText(order.status)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            
            container.innerHTML = ordersHtml;
        }
    } catch (err) {}
}

function getStatusText(status) {
    const map = {
        'pending': 'Ожидает',
        'confirmed': 'Подтвержден',
        'preparing': 'Готовится',
        'ready': 'Готов',
        'completed': 'Выполнен',
        'cancelled': 'Отменен'
    };
    return map[status] || status;
}

// ==================== ПОЛЬЗОВАТЕЛЬ ====================
function loadUser() {
    const saved = localStorage.getItem('user');
    const savedRole = localStorage.getItem('userRole');
    const token = localStorage.getItem('token');
    
    if (saved && token) {
        try {
            currentUser = JSON.parse(saved);
            userRole = savedRole || 'user';
            userAllergens = currentUser.allergens || [];
        } catch (e) {}
    } else if (token) {
        loadUserData();
        return;
    }
    
    updateUserInfo();
    updateProfileUI();
    updateAdminUI();
}

function updateUserInfo() {
    const infoDiv = document.getElementById('userInfo');
    const nameSpan = document.getElementById('userName');
    const roleSpan = document.getElementById('userRole');
    
    if (!infoDiv || !nameSpan || !roleSpan) return;
    
    if (currentUser) {
        nameSpan.textContent = currentUser.name || 'Пользователь';
        roleSpan.textContent = userRole === 'admin' ? 'Администратор' : 'Пользователь';
        roleSpan.style.backgroundColor = userRole === 'admin' ? '#ff6b6b' : '#667eea';
        infoDiv.style.display = 'block';
    } else {
        infoDiv.style.display = 'none';
    }
}

function toggleEditMode() {
    isEditingProfile = !isEditingProfile;
    updateProfileUI();
}

function cancelEdit() {
    isEditingProfile = false;
    updateProfileUI();
}

function updateProfileUI() {
    const profileCard = document.getElementById('profileCard');
    if (!profileCard) return;
    
    if (!currentUser) {
        profileCard.innerHTML = `
            <div class="profile-empty">
                <i class="fas fa-user-circle" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                <p>Для заполнения профиля <a href="/register.html">зарегистрируйтесь</a> или <a href="#" onclick="showLoginModal()">войдите</a></p>
            </div>
        `;
        return;
    }
    
    const diets = [
        { value: '', label: 'Нет', icon: 'times-circle' },
        { value: 'веган', label: 'Веган', icon: 'leaf' },
        { value: 'вегетарианец', label: 'Вегетарианец', icon: 'carrot' },
        { value: 'безглютеновая', label: 'Безглютеновая', icon: 'wheat-alt' }
    ];
    
    const allergens = ['орехи', 'арахис', 'лактоза', 'глютен', 'морепродукты', 'яйца', 'соя'];
    
    if (isEditingProfile) {
        const allergenCheckboxes = allergens.map(a => 
            `<label class="option">
                <input type="checkbox" value="${a}" ${userAllergens.includes(a) ? 'checked' : ''}> 
                <i class="fas fa-${getAllergenIcon(a)}"></i> ${a}
            </label>`
        ).join('');
        
        const dietRadios = diets.map(d => 
            `<label class="option">
                <input type="radio" name="diet" value="${d.value}" ${currentUser.diet === d.value ? 'checked' : ''}> 
                <i class="fas fa-${d.icon}"></i> ${d.label}
            </label>`
        ).join('');
        
        const roleBadge = userRole === 'admin' 
            ? '<span class="profile-role"><i class="fas fa-crown"></i> Администратор</span>' : '';
        
        profileCard.innerHTML = `
            <div class="profile-header">
                <div class="avatar">${(currentUser.name || 'П').charAt(0).toUpperCase()}</div>
                <div class="profile-info">
                    <div class="profile-name">${currentUser.name || 'Пользователь'}</div>
                    <div class="profile-email">${currentUser.email}</div>
                    ${roleBadge}
                </div>
            </div>
            <div class="profile-section">
                <div class="section-title">Ваши аллергены</div>
                <div class="options-group" id="allergensGroup">${allergenCheckboxes}</div>
            </div>
            <div class="profile-section">
                <div class="section-title">Диета</div>
                <div class="options-group">${dietRadios}</div>
            </div>
            <div class="profile-actions">
                <button class="save-btn" onclick="saveProfile()">Сохранить</button>
                <button class="cancel-btn" onclick="cancelEdit()">Отмена</button>
            </div>
            <div id="orderHistoryContainer"></div>
            ${userRole === 'admin' ? `
            <div class="admin-section">
                <h4><i class="fas fa-crown"></i> Панель администратора</h4>
                <button class="save-btn" onclick="window.location.href='/admin.html'">Перейти в админ панель</button>
            </div>` : ''}
        `;
    } else {
        const selectedAllergens = userAllergens.length > 0 
            ? userAllergens.map(a => `<span class="allergen-tag"><i class="fas fa-${getAllergenIcon(a)}"></i> ${a}</span>`).join('')
            : '<span class="no-data">Не указаны</span>';
        
        const dietText = currentUser.diet 
            ? diets.find(d => d.value === currentUser.diet)?.label || currentUser.diet
            : 'Не указана';
        
        const dietIcon = currentUser.diet 
            ? diets.find(d => d.value === currentUser.diet)?.icon || 'question-circle'
            : 'times-circle';
        
        const roleBadge = userRole === 'admin' 
            ? '<span class="profile-role"><i class="fas fa-crown"></i> Администратор</span>' : '';
        
        profileCard.innerHTML = `
            <div class="profile-header">
                <div class="avatar">${(currentUser.name || 'П').charAt(0).toUpperCase()}</div>
                <div class="profile-info">
                    <div class="profile-name">${currentUser.name || 'Пользователь'}</div>
                    <div class="profile-email">${currentUser.email}</div>
                    ${roleBadge}
                </div>
            </div>
            <div class="profile-section">
                <div class="section-title"><i class="fas fa-allergies"></i> Ваши аллергены</div>
                <div class="allergens-display">${selectedAllergens}</div>
            </div>
            <div class="profile-section">
                <div class="section-title"><i class="fas fa-utensils"></i> Диета</div>
                <div class="diet-display"><i class="fas fa-${dietIcon}"></i> ${dietText}</div>
            </div>
            <button class="edit-btn" onclick="toggleEditMode()"><i class="fas fa-edit"></i> Изменить профиль</button>
            <div id="orderHistoryContainer"></div>
            ${userRole === 'admin' ? `
            <div class="admin-section">
                <h4><i class="fas fa-crown"></i> Панель администратора</h4>
                <button class="save-btn" onclick="window.location.href='/admin.html'"><i class="fas fa-cog"></i> Перейти в админ панель</button>
            </div>` : ''}
        `;
    }
    
    setTimeout(() => loadOrderHistory(), 100);
}

function getAllergenIcon(allergen) {
    const icons = {
        'орехи': 'nut',
        'арахис': 'peanut',
        'лактоза': 'milk',
        'глютен': 'wheat',
        'морепродукты': 'fish',
        'яйца': 'egg',
        'соя': 'seedling'
    };
    return icons[allergen] || 'exclamation-circle';
}

async function saveProfile() {
    // Собираем выбранные аллергены
    const selected = [];
    document.querySelectorAll('#allergensGroup input:checked').forEach(cb => {
        selected.push(cb.value);
    });
    
    // Собираем выбранную диету
    let diet = '';
    document.querySelectorAll('input[name="diet"]').forEach(r => {
        if (r.checked) diet = r.value;
    });
    
    if (!currentUser) return;
    
    const token = localStorage.getItem('token');
    
    if (token) {
        try {
            const res = await fetch(`${API_URL}/auth/me`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    full_name: currentUser.name,
                    allergens: selected,
                    diet: diet || null
                })
            });
            
            if (res.ok) {
                const data = await res.json();
                currentUser = {
                    id: data.id,
                    name: data.full_name,
                    email: data.email,
                    allergens: data.allergens || [],
                    diet: data.diet || null
                };
                userAllergens = data.allergens || [];
                localStorage.setItem('user', JSON.stringify(currentUser));
                showNotif('Настройки сохранены', 'success');
                isEditingProfile = false;
                updateProfileUI();
                loadMenu(); // Перезагружаем меню для обновления индикации аллергенов
            } else {
                const error = await res.json();
                showNotif(error.detail || 'Ошибка при сохранении', 'error');
            }
        } catch (err) {
            console.error('Ошибка сохранения:', err);
            showNotif('Ошибка соединения с сервером', 'error');
        }
    }
}

function logout() {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('cart');
    currentUser = null;
    userAllergens = [];
    userRole = 'user';
    isEditingProfile = false;
    
    updateUserInfo();
    updateProfileUI();
    updateAdminUI();
    loadMenu();
    loadCart();
    showNotif('Вы вышли из системы', 'info');
}

// ==================== API ТЕСТЫ ====================
async function testAPI(endpoint) {
    const respEl = document.getElementById('apiResponse');
    respEl.innerHTML = '<div class="loading-spinner">Запрос...</div>';
    
    try {
        const url = endpoint === 'health' ? `${API_URL}/health` : `${API_URL}/api/${endpoint}`;
        const res = await fetch(url);
        const data = await res.json();
        respEl.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    } catch (err) {
        respEl.innerHTML = '<pre>Ошибка: ' + err.message + '</pre>';
    }
}

async function testAI() {
    const respEl = document.getElementById('apiResponse');
    respEl.innerHTML = '<div class="loading-spinner">Анализ...</div>';
    
    try {
        const allergens = userAllergens.length ? userAllergens.join(',') : 'нет';
        const res = await fetch(`${API_URL}/api/analyze/1/${allergens}`);
        const data = await res.json();
        respEl.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    } catch (err) {
        respEl.innerHTML = '<pre>Ошибка: ' + err.message + '</pre>';
    }
}

// ==================== УВЕДОМЛЕНИЯ ====================
function showNotif(msg, type) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const colors = { success: '#28a745', error: '#dc3545', warning: '#ffc107', info: '#17a2b8' };
    const icons = { success: 'check-circle', error: 'exclamation-circle', warning: 'exclamation-triangle', info: 'info-circle' };
    
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

// ==================== СВАЙПЫ ====================
if (track) {
    let touchStart = 0;
    track.addEventListener('touchstart', e => touchStart = e.changedTouches[0].screenX);
    track.addEventListener('touchend', e => {
        const diff = e.changedTouches[0].screenX - touchStart;
        if (Math.abs(diff) > 50) diff > 0 ? prevSlide() : nextSlide();
    });
}

document.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') prevSlide();
    if (e.key === 'ArrowRight') nextSlide();
});