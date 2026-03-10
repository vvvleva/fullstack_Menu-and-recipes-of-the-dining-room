let currentSlide = 0;
const slides = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.dot');
const track = document.getElementById('carouselTrack');
const API_URL = 'http://localhost:8000';

// Хранилище состояний
let currentDishId = null;
let dishQuantity = 1;
let dishImages = {}; // Кэш для изображений

document.addEventListener('DOMContentLoaded', function() {
    checkServerStatus();
    setInterval(checkServerStatus, 5000);
    loadMenuFromApi();
    initializeQuantityControls();
    preloadDishImages(); // Предзагрузка изображений
});

// Инициализация обработчиков для кнопок количества
function initializeQuantityControls() {
    const quantityBtns = document.querySelectorAll('.quantity-btn');
    const addBtn = document.querySelector('.add-btn');
    
    // Используем делегирование событий для динамических элементов
    document.addEventListener('click', function(e) {
        // Обработка кнопок + и -
        if (e.target.classList.contains('quantity-btn')) {
            const quantitySpan = document.querySelector('.quantity');
            if (!quantitySpan) return;
            
            let currentQty = parseInt(quantitySpan.textContent) || 1;
            
            if (e.target.textContent === '+') {
                currentQty++;
            } else if (e.target.textContent === '−' && currentQty > 1) {
                currentQty--;
            }
            
            quantitySpan.textContent = currentQty;
            dishQuantity = currentQty;
        }
        
        // Обработка кнопки "Добавить"
        if (e.target.classList.contains('add-btn')) {
            addToCart();
        }
    });
}

// Функция добавления в корзину
function addToCart() {
    if (!currentDishId) {
        alert('Сначала выберите блюдо');
        return;
    }
    
    const dishName = document.getElementById('dishTitle').textContent;
    const dishPrice = document.getElementById('dishPrice').textContent;
    
    // Создаем уведомление
    showNotification(`Добавлено: ${dishName} x${dishQuantity} = ${parseInt(dishPrice) * dishQuantity} ₽`);
    
    // Здесь можно добавить логику сохранения в корзину
    console.log('Добавлено в корзину:', {
        id: currentDishId,
        name: dishName,
        quantity: dishQuantity,
        price: dishPrice
    });
}

// Показ уведомления
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #333;
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Предзагрузка изображений блюд
async function preloadDishImages() {
    try {
        const response = await fetch(`${API_URL}/api/menu`);
        const payload = await response.json();
        const items = payload.data || [];
        
        // Создаем заглушки для изображений на основе названий блюд
        items.forEach(item => {
            const imageUrl = generateDishImageUrl(item.name, item.id);
            dishImages[item.id] = imageUrl;
            
            // Предзагружаем изображение
            const img = new Image();
            img.src = imageUrl;
        });
    } catch (error) {
        console.error('Ошибка предзагрузки изображений:', error);
    }
}

// Генерация URL изображения для блюда
function generateDishImageUrl(dishName, dishId) {
     return `/images/dishes/${dishId}.jpg`;
}

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

async function checkServerStatus() {
    const statusEl = document.getElementById('serverStatus');
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

// --- Динамическое меню и состав блюда ---

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
            const hasAllergens = Array.isArray(item.allergens) && item.allergens.length > 0;
            allergenDiv.className = 'item-allergen ' + (hasAllergens ? 'warning' : 'safe');
            allergenDiv.textContent = hasAllergens ? 'Содержит потенциальные аллергены' : 'Безопасно';

            wrapper.appendChild(row);
            wrapper.appendChild(allergenDiv);

            listEl.appendChild(wrapper);
        });
    } catch (error) {
        listEl.innerHTML = `<div class="menu-item"><div class="item-row"><span class="item-name">Ошибка: ${error.message}</span></div></div>`;
    }
}

async function selectDish(id) {
    try {
        const response = await fetch(`${API_URL}/api/menu/${id}`);
        if (!response.ok) {
            throw new Error(`Ошибка загрузки блюда: ${response.status}`);
        }
        const payload = await response.json();
        const dish = payload.data;
        if (!dish) return;

        currentDishId = dish.id;
        dishQuantity = 1; // Сбрасываем количество
        document.querySelector('.quantity').textContent = '1';
        
        renderDishDetails(dish);
        goToSlide(1);
    } catch (error) {
        console.error(error);
    }
}

function renderDishDetails(dish) {
    const titleEl = document.getElementById('dishTitle');
    const ingredientsEl = document.getElementById('ingredientsList');
    const metaEl = document.getElementById('dishMeta');
    const priceEl = document.getElementById('dishPrice');
    const imagePlaceholder = document.querySelector('.image-placeholder');
    const aiBlock = document.getElementById('aiBlock');
    const aiTitle = document.getElementById('aiTitle');
    const aiMessage = document.getElementById('aiMessage');

    if (titleEl) titleEl.textContent = dish.name;
    if (priceEl) priceEl.textContent = `${dish.price} ₽`;
    if (metaEl) metaEl.textContent = `${dish.weight} г · ${dish.calories} ккал`;

    // Загружаем изображение
    if (imagePlaceholder) {
        const imageUrl = dishImages[dish.id] || generateDishImageUrl(dish.name, dish.id);
        imagePlaceholder.innerHTML = `<img src="${imageUrl}" alt="${dish.name}" style="width:100%;height:100%;object-fit:cover;">`;
        imagePlaceholder.style.background = 'none';
    }

    // AI анализ
    if (aiBlock && aiTitle && aiMessage) {
        if (dish.allergens && dish.allergens.length > 0) {
            aiBlock.className = 'ai-analysis danger';
            aiTitle.textContent = 'AI-анализ: обнаружены аллергены';
            aiMessage.textContent = `Внимание! Блюдо содержит: ${dish.allergens.join(', ')}`;
        } else {
            aiBlock.className = 'ai-analysis safe';
            aiTitle.textContent = 'AI-анализ: безопасно';
            aiMessage.textContent = 'Аллергены не обнаружены';
        }
    }

    // Ингредиенты
    if (ingredientsEl) {
        ingredientsEl.innerHTML = '';
        const ingredients = Array.isArray(dish.ingredients) ? dish.ingredients : [];
        const allergens = new Set(Array.isArray(dish.allergens) ? dish.allergens : []);

        if (!ingredients.length) {
            const li = document.createElement('li');
            li.textContent = 'Состав не указан';
            ingredientsEl.appendChild(li);
        } else {
            ingredients.forEach((ing) => {
                const li = document.createElement('li');
                li.textContent = ing;
                const lower = (ing || '').toLowerCase();
                const isAllergen = Array.from(allergens).some(a => lower.includes(a.toLowerCase()));
                if (isAllergen) {
                    li.classList.add('allergen-item');
                }
                ingredientsEl.appendChild(li);
            });
        }
    }
}

async function testAI() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>Выполняется AI анализ...</pre>';
    
    try {
        const response = await fetch(`${API_URL}/api/analyze/1/орехи,лактоза`);
        const data = await response.json();
        
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

// CRUD (ЛР №4)
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
        loadMenuFromApi(); // Обновляем меню
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

async function testUpdate() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>PUT /api/menu/1 — обновление блюда...</pre>';
    
    const body = {
        name: "Цезарь с курицей (обновлённый)",
        price: 380,
        weight: 280,
        category: "салаты",
        ingredients: ["курица", "салат айсберг", "соус", "пармезан", "грецкий орех", "гренки"],
        allergens: ["орехи", "глютен", "лактоза"],
        calories: 450,
        available: true
    };
    
    try {
        const response = await fetch(`${API_URL}/api/menu/1`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        loadMenuFromApi(); // Обновляем меню
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

async function testDelete() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>DELETE /api/menu/5 — удаление блюда...</pre>';
    
    try {
        const response = await fetch(`${API_URL}/api/menu/5`, { method: "DELETE" });
        const data = await response.json();
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        loadMenuFromApi(); // Обновляем меню
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

// Клавиши для карусели
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        prevSlide();
    } else if (e.key === 'ArrowRight') {
        nextSlide();
    }
});

// Свайпы для мобильных
let touchStartX = 0;
let touchEndX = 0;

track.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].screenX;
});

track.addEventListener('touchend', function(e) {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
});

function handleSwipe() {
    const threshold = 50;
    if (touchEndX < touchStartX - threshold) {
        nextSlide();
    }
    if (touchEndX > touchStartX + threshold) {
        prevSlide();
    }
}

// React компоненты остаются без изменений
const { BrowserRouter, Routes, Route, NavLink } = ReactRouterDOM;

function Navigation() {
  return (
    <nav className="spa-nav">
      <NavLink to="/" end className="spa-link">
        Меню
      </NavLink>
      <NavLink to="/profile" className="spa-link">
        Профиль
      </NavLink>
      <NavLink to="/about" className="spa-link">
        О проекте
      </NavLink>
    </nav>
  );
}

function Layout() {
  return (
    <div className="spa-card">
      <header className="spa-header">
        <div className="spa-title">SPA-панель столовой</div>
        <div className="spa-description">
          Демонстрация клиентской маршрутизации (React Router) для будущих CRUD, авторизации и интеграции с API.
        </div>
      </header>

      <Navigation />

      <main className="spa-main">
        <Routes>
          <Route path="/" element={<MenuPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  );
}

function MenuPage() {
  return (
    <section>
      <h3>Меню на сегодня</h3>
      <p className="spa-text">
        Здесь в следующих лабораторных (ЛР №4 и №7) будут отображаться реальные данные из эндпоинтов
        <code> /api/menu </code> и <code>/api/menu/&lt;id&gt;</code> c обработкой загрузки и ошибок.
      </p>
      <ul className="spa-list">
        <li>Список блюд с ценой, весом и категорией</li>
        <li>Метка «Безопасно»/«Опасно» по результатам анализа аллергенов</li>
        <li>Кнопка перехода к подробной карточке блюда</li>
      </ul>
    </section>
  );
}

function ProfilePage() {
  return (
    <section>
      <h3>Профиль и аллергены</h3>
      <p className="spa-text">
        Экран для хранения предпочтений пользователя: аллергены, диета, история выборов.
        В дальнейших ЛР (№5–6) здесь появятся авторизация и защита маршрутов.
      </p>
      <ul className="spa-list">
        <li>Выбор аллергенов (орехи, лактоза, глютен, морепродукты)</li>
        <li>Выбор диеты (веган, безглютеновая и др.)</li>
        <li>Сохранение настроек после входа в систему</li>
      </ul>
    </section>
  );
}

function AboutPage() {
  return (
    <section>
      <h3>О проекте</h3>
      <p className="spa-text">
        Проект "Столовая #2049" разрабатывается в рамках лабораторных работ.
        Основные технологии: FastAPI, SQLite, React, React Router.
      </p>
      <ul className="spa-list">
        <li>ЛР №1-2: Проектирование UI/UX + Развёртывание сервера</li>
        <li>ЛР №3: SPA и маршрутизация на React Router</li>
        <li>ЛР №4: CRUD операции, работа с БД</li>
        <li>ЛР №5-6: Авторизация и аутентификация</li>
        <li>ЛР №7: Интеграция и тестирование</li>
      </ul>
    </section>
  );
}

function App() {
  return (
    <ReactRouterDOM.BrowserRouter>
      <Layout />
    </ReactRouterDOM.BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById("spa-root"));
root.render(<App />);

// Добавляем анимации для уведомлений
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
    
    .notification {
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
`;
document.head.appendChild(style);