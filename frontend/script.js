// Глобальные переменные
let currentSlide = 0;
const slides = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.dot');
const track = document.getElementById('carouselTrack');
const API_URL = 'http://localhost:8000';

// Состояния приложения
let currentDishId = null;
let dishQuantity = 1;
let currentUser = null;
let userAllergens = [];
let authToken = localStorage.getItem('token');

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('Страница загружена, инициализация...');
    checkServerStatus();
    setInterval(checkServerStatus, 5000);
    loadMenuFromApi();
    loadUserProfile();
    loadCart();
    updateAuthUI();
});

// ==================== УПРАВЛЕНИЕ КАРУСЕЛЬЮ ====================

function showSlide(index) {
    if (index < 0) index = 0;
    if (index >= slides.length) index = slides.length - 1;
    
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    
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

// ==================== УПРАВЛЕНИЕ КОЛИЧЕСТВОМ ====================

function increaseQuantity() {
    console.log('Увеличение количества');
    const quantitySpan = document.getElementById('dishQuantity');
    if (quantitySpan) {
        dishQuantity = parseInt(quantitySpan.textContent) + 1;
        quantitySpan.textContent = dishQuantity;
        console.log('Новое количество:', dishQuantity);
    }
}

function decreaseQuantity() {
    console.log('Уменьшение количества');
    const quantitySpan = document.getElementById('dishQuantity');
    if (quantitySpan) {
        let currentQty = parseInt(quantitySpan.textContent);
        if (currentQty > 1) {
            dishQuantity = currentQty - 1;
            quantitySpan.textContent = dishQuantity;
            console.log('Новое количество:', dishQuantity);
        }
    }
}

// ==================== РАБОТА С СЕРВЕРОМ ====================

async function checkServerStatus() {
    const statusEl = document.getElementById('serverStatus');
    if (!statusEl) return;
    
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('.status-text');
    
    try {
        const response = await fetch(`${API_URL}/health`);
        
        if (response.ok) {
            indicator.className = 'status-indicator online';
            text.textContent = 'Сервер подключен';
        } else {
            throw new Error();
        }
    } catch (error) {
        indicator.className = 'status-indicator offline';
        text.textContent = 'Сервер не доступен';
    }
}

// ==================== ЗАГРУЗКА МЕНЮ ====================

async function loadMenuFromApi() {
    const listEl = document.getElementById('menuList');
    if (!listEl) return;

    listEl.innerHTML = '<div class="menu-item"><div class="item-row"><span class="item-name">Загрузка меню...</span></div></div>';

    try {
        const response = await fetch(`${API_URL}/api/menu`);
        if (!response.ok) {
            throw new Error(`Ошибка загрузки меню: ${response.status}`);
        }
        const payload = await response.json();
        const items = payload.data || [];

        if (!items.length) {
            listEl.innerHTML = '<div class="menu-item"><div class="item-row"><span class="item-name">Меню пусто</span></div></div>';
            return;
        }

        listEl.innerHTML = '';
        items.forEach((item) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'menu-item';
            wrapper.onclick = () => selectDish(item.id);

            const row = document.createElement('div');
            row.className = 'item-row';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'item-name';
            nameSpan.textContent = item.name;

            const priceSpan = document.createElement('span');
            priceSpan.className = 'item-price';
            priceSpan.textContent = `${item.price} ₽`;

            row.appendChild(nameSpan);
            row.appendChild(priceSpan);

            const allergenDiv = document.createElement('div');
            allergenDiv.className = 'item-allergen';
            
            const hasAllergens = Array.isArray(item.allergens) && item.allergens.length > 0;
            const hasUserAllergens = hasAllergens && userAllergens.length > 0 ? 
                item.allergens.some(a => userAllergens.includes(a)) : false;
            
            if (hasUserAllergens) {
                allergenDiv.classList.add('warning');
                allergenDiv.textContent = 'Содержит ваши аллергены';
            } else if (hasAllergens) {
                allergenDiv.classList.add('warning');
                allergenDiv.textContent = 'Содержит аллергены';
            } else {
                allergenDiv.classList.add('safe');
                allergenDiv.textContent = 'Безопасно';
            }

            wrapper.appendChild(row);
            wrapper.appendChild(allergenDiv);

            listEl.appendChild(wrapper);
        });
    } catch (error) {
        listEl.innerHTML = `<div class="menu-item"><div class="item-row"><span class="item-name">Ошибка: ${error.message}</span></div></div>`;
    }
}

// ==================== ВЫБОР БЛЮДА ====================

async function selectDish(id) {
    console.log('Выбрано блюдо с ID:', id);
    try {
        const response = await fetch(`${API_URL}/api/menu/${id}`);
        if (!response.ok) {
            throw new Error(`Ошибка загрузки блюда: ${response.status}`);
        }
        const payload = await response.json();
        const dish = payload.data;
        if (!dish) return;

        currentDishId = dish.id;
        dishQuantity = 1;
        const quantitySpan = document.getElementById('dishQuantity');
        if (quantitySpan) quantitySpan.textContent = '1';
        
        renderDishDetails(dish);
        goToSlide(1);
    } catch (error) {
        console.error(error);
        showNotification(error.message, 'error');
    }
}

function renderDishDetails(dish) {
    const titleEl = document.getElementById('dishTitle');
    const ingredientsEl = document.getElementById('ingredientsList');
    const metaEl = document.getElementById('dishMeta');
    const priceEl = document.getElementById('dishPrice');
    const aiBlock = document.getElementById('aiBlock');
    const aiTitle = document.getElementById('aiTitle');
    const aiMessage = document.getElementById('aiMessage');

    if (titleEl) titleEl.textContent = dish.name;
    if (priceEl) priceEl.textContent = `${dish.price} ₽`;
    if (metaEl) metaEl.textContent = `${dish.weight} г · ${dish.calories} ккал`;

    if (aiBlock && aiTitle && aiMessage) {
        const dishAllergens = Array.isArray(dish.allergens) ? dish.allergens : [];
        const matchingAllergens = dishAllergens.filter(a => userAllergens.includes(a));
        
        if (matchingAllergens.length > 0) {
            aiBlock.className = 'ai-analysis danger';
            aiTitle.textContent = 'AI-анализ: обнаружены ваши аллергены';
            aiMessage.textContent = `Внимание! Блюдо содержит: ${matchingAllergens.join(', ')}`;
        } else if (dishAllergens.length > 0) {
            aiBlock.className = 'ai-analysis warning';
            aiTitle.textContent = 'AI-анализ: блюдо содержит аллергены';
            aiMessage.textContent = `Блюдо содержит: ${dishAllergens.join(', ')} (нет ваших аллергенов)`;
        } else {
            aiBlock.className = 'ai-analysis safe';
            aiTitle.textContent = 'AI-анализ: безопасно';
            aiMessage.textContent = 'Аллергены не обнаружены';
        }
    }

    if (ingredientsEl) {
        ingredientsEl.innerHTML = '';
        const ingredients = Array.isArray(dish.ingredients) ? dish.ingredients : [];
        const dishAllergens = new Set(Array.isArray(dish.allergens) ? dish.allergens : []);

        if (!ingredients.length) {
            const li = document.createElement('li');
            li.textContent = 'Состав не указан';
            ingredientsEl.appendChild(li);
        } else {
            ingredients.forEach((ing) => {
                const li = document.createElement('li');
                li.textContent = ing;
                const lower = (ing || '').toLowerCase();
                const isAllergen = Array.from(dishAllergens).some(a => 
                    lower.includes(a.toLowerCase()) || a.toLowerCase().includes(lower)
                );
                if (isAllergen) {
                    li.classList.add('allergen-item');
                }
                ingredientsEl.appendChild(li);
            });
        }
    }
}

// ==================== РАБОТА С КОРЗИНОЙ ====================

function addToCart() {
    console.log('Добавление в корзину');
    if (!currentDishId) {
        showNotification('Сначала выберите блюдо', 'warning');
        return;
    }
    
    const dishName = document.getElementById('dishTitle').textContent;
    const priceText = document.getElementById('dishPrice').textContent;
    const dishPrice = parseInt(priceText) || 0;
    const quantity = dishQuantity;
    const total = dishPrice * quantity;
    
    const cartItem = {
        id: currentDishId,
        name: dishName,
        quantity: quantity,
        price: dishPrice,
        total: total,
        timestamp: new Date().toISOString()
    };
    
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    const existingItem = cart.find(item => item.id === currentDishId);
    if (existingItem) {
        existingItem.quantity += quantity;
        existingItem.total = existingItem.price * existingItem.quantity;
    } else {
        cart.push(cartItem);
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    
    showNotification(`Добавлено: ${dishName} x${quantity} = ${total} ₽`, 'success');
    loadCart();
}

function loadCart() {
    const cartItemsEl = document.getElementById('cartItems');
    const cartTotalEl = document.getElementById('cartTotal');
    if (!cartItemsEl) return;
    
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    if (cart.length === 0) {
        cartItemsEl.innerHTML = '<p class="empty-cart">Корзина пуста</p>';
        if (cartTotalEl) cartTotalEl.textContent = '';
        return;
    }
    
    let html = '';
    let total = 0;
    
    cart.forEach((item, index) => {
        total += item.total;
        html += `
            <div class="cart-item">
                <div class="cart-item-info">
                    <span class="cart-item-name">${item.name}</span>
                    <span class="cart-item-price">${item.price} ₽ x ${item.quantity}</span>
                </div>
                <div class="cart-item-total">${item.total} ₽</div>
                <button class="cart-item-remove" onclick="removeFromCart(${index})">Удалить</button>
            </div>
        `;
    });
    
    cartItemsEl.innerHTML = html;
    if (cartTotalEl) cartTotalEl.textContent = `Итого: ${total} ₽`;
}

function removeFromCart(index) {
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    cart.splice(index, 1);
    localStorage.setItem('cart', JSON.stringify(cart));
    loadCart();
    showNotification('Товар удален из корзины', 'info');
}

function checkout() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    if (cart.length === 0) {
        showNotification('Корзина пуста', 'warning');
        return;
    }
    
    if (!authToken) {
        showNotification('Необходимо авторизоваться', 'warning');
        showLoginForm();
        return;
    }
    
    createOrder();
}

async function createOrder() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    const orderData = {
        items: cart.map(item => ({
            dish_id: item.id,
            quantity: item.quantity,
            special_requests: ''
        })),
        comments: 'Заказ через веб-интерфейс'
    };
    
    try {
        const response = await fetch(`${API_URL}/api/orders/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(orderData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Заказ успешно создан', 'success');
            localStorage.removeItem('cart');
            loadCart();
        } else {
            showNotification(data.detail?.message || 'Ошибка при создании заказа', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

// ==================== АВТОРИЗАЦИЯ ====================

function showLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.style.display = 'flex';
    }
}

function hideLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.style.display = 'none';
    }
}

async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.access_token;
            localStorage.setItem('token', authToken);
            
            showNotification('Вход выполнен успешно', 'success');
            hideLoginForm();
            
            await loadCurrentUser();
            updateAuthUI();
        } else {
            showNotification('Неверный email или пароль', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
    }
}

async function loadCurrentUser() {
    if (!authToken) return;
    
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            currentUser = userData;
            userAllergens = userData.allergens || [];
            updateProfileUI();
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('token');
    currentUser = null;
    userAllergens = [];
    updateAuthUI();
    showNotification('Вы вышли из системы', 'info');
}

function updateAuthUI() {
    const userInfo = document.getElementById('userInfo');
    const profileName = document.getElementById('profileName');
    const profileEmail = document.getElementById('profileEmail');
    const profileAvatar = document.getElementById('profileAvatar');
    
    if (authToken && currentUser) {
        if (userInfo) userInfo.style.display = 'block';
        if (profileName) profileName.textContent = currentUser.full_name || 'Пользователь';
        if (profileEmail) profileEmail.textContent = currentUser.email;
        if (profileAvatar) profileAvatar.textContent = (currentUser.full_name || 'Г').charAt(0).toUpperCase();
    } else {
        if (userInfo) userInfo.style.display = 'none';
        if (profileName) profileName.textContent = 'Гость';
        if (profileEmail) profileEmail.textContent = 'не авторизован';
        if (profileAvatar) profileAvatar.textContent = 'Г';
    }
}

// ==================== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ====================

function loadUserProfile() {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        userAllergens = currentUser.allergens || [];
        updateProfileUI();
    }
}

function updateProfileUI() {
    const checkboxes = document.querySelectorAll('.profile-section input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = userAllergens.includes(cb.value);
    });
}

function saveProfile() {
    const selectedAllergens = [];
    const checkboxes = document.querySelectorAll('.profile-section input[type="checkbox"]:checked');
    checkboxes.forEach(cb => {
        selectedAllergens.push(cb.value);
    });
    
    let diet = '';
    const dietRadios = document.querySelectorAll('input[name="diet"]');
    for (let radio of dietRadios) {
        if (radio.checked) {
            diet = radio.value;
            break;
        }
    }
    
    if (!authToken) {
        currentUser = {
            name: 'Гость',
            email: 'guest@local',
            allergens: selectedAllergens,
            diet: diet,
            lastLogin: new Date().toISOString()
        };
        
        localStorage.setItem('user', JSON.stringify(currentUser));
        userAllergens = selectedAllergens;
        
        showNotification('Настройки сохранены локально', 'success');
    } else {
        // Здесь можно добавить сохранение на сервер
        showNotification('Настройки сохранены', 'success');
    }
    
    loadMenuFromApi();
}

// ==================== API ТЕСТИРОВАНИЕ ====================

async function testAPI(endpoint) {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>Отправка запроса...</pre>';
    
    try {
        let url = `${API_URL}/api/${endpoint}`;
        if (endpoint === 'health') {
            url = `${API_URL}/health`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

async function testAI() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>Выполняется AI анализ...</pre>';
    
    try {
        const userAllergensStr = userAllergens.length > 0 ? userAllergens.join(',') : 'нет';
        const response = await fetch(`${API_URL}/api/analyze/1/${userAllergensStr}`);
        const data = await response.json();
        
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

async function testCreate() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>POST /api/menu — создание блюда...</pre>';
    
    const body = {
        name: "Тыквенный суп",
        price: 320,
        weight: 300,
        category: "супы",
        ingredients: ["тыква", "сливки", "лук", "чеснок"],
        allergens: ["лактоза"],
        calories: 150,
        available: true
    };
    
    try {
        const response = await fetch(`${API_URL}/api/menu`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        loadMenuFromApi();
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

// ==================== УПРАВЛЕНИЕ СЕКЦИЯМИ ====================

function showSection(sectionId) {
    const mainContent = document.getElementById('mainContent');
    const loginForm = document.getElementById('loginForm');
    
    if (sectionId === 'main') {
        if (mainContent) mainContent.style.display = 'block';
        if (loginForm) loginForm.style.display = 'none';
    }
}

// ==================== УВЕДОМЛЕНИЯ ====================

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    const colors = {
        success: '#00a86b',
        warning: '#b85c00',
        error: '#dc3545',
        info: '#0066cc'
    };
    
    notification.style.cssText = `
        background: ${colors[type] || colors.info};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==================== НАВИГАЦИЯ ====================

let touchStartX = 0;
let touchEndX = 0;

if (track) {
    track.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });

    track.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
}

function handleSwipe() {
    const threshold = 50;
    if (touchEndX < touchStartX - threshold) {
        nextSlide();
    }
    if (touchEndX > touchStartX + threshold) {
        prevSlide();
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        prevSlide();
    } else if (e.key === 'ArrowRight') {
        nextSlide();
    }
});

// Добавляем стили для уведомлений
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .login-form {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    }
    
    .login-card {
        background: white;
        padding: 30px;
        border-radius: 8px;
        width: 100%;
        max-width: 400px;
    }
    
    .login-card h2 {
        margin-bottom: 20px;
        text-align: center;
    }
    
    .login-button, .cancel-button {
        width: 100%;
        padding: 10px;
        margin-top: 10px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }
    
    .login-button {
        background: #333;
        color: white;
    }
    
    .cancel-button {
        background: #f0f0f0;
        color: #333;
    }
    
    .user-info {
        background: white;
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .user-info-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .logout-btn {
        padding: 5px 15px;
        background: #dc3545;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    
    .cart-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px;
        border-bottom: 1px solid #eee;
    }
    
    .cart-item-info {
        flex: 1;
    }
    
    .cart-item-name {
        display: block;
        font-weight: 500;
    }
    
    .cart-item-price {
        font-size: 12px;
        color: #666;
    }
    
    .cart-item-total {
        font-weight: 600;
        margin-right: 10px;
    }
    
    .cart-item-remove {
        padding: 3px 8px;
        background: #f0f0f0;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    }
    
    .cart-total {
        font-size: 18px;
        font-weight: 600;
        text-align: right;
        margin: 15px 0;
        padding-top: 10px;
        border-top: 2px solid #eee;
    }
    
    .checkout-btn {
        width: 100%;
        padding: 12px;
        background: #00a86b;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 500;
    }
    
    .checkout-btn:hover {
        background: #00875a;
    }
    
    .empty-cart {
        text-align: center;
        color: #666;
        padding: 20px;
    }
`;
document.head.appendChild(style);