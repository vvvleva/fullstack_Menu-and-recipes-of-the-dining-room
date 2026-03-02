let currentSlide = 0;
const slides = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.dot');
const track = document.getElementById('carouselTrack');
const API_URL = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', function() {
    checkServerStatus();
    setInterval(checkServerStatus, 5000);
    loadMenuFromApi();
});

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

    if (titleEl) titleEl.textContent = dish.name;
    if (priceEl) priceEl.textContent = `${dish.price} ₽`;
    if (metaEl) metaEl.textContent = `${dish.weight} г · ${dish.calories} ккал`;

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
                const isAllergen =
                    ['орех', 'орехи', 'глютен', 'лактоза', 'сметана', 'сыр', 'молоко'].some((token) =>
                        lower.includes(token)
                    ) || Array.from(allergens).some((a) => lower.includes(a));
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
    } catch (error) {
        responseEl.innerHTML = `<pre>Ошибка: ${error.message}</pre>`;
    }
}

async function testDelete() {
    const responseEl = document.getElementById('apiResponse');
    responseEl.innerHTML = '<pre>DELETE /api/menu/5 — удаление блюда (создайте сначала через POST)...</pre>';
    
    try {
        const response = await fetch(`${API_URL}/api/menu/5`, { method: "DELETE" });
        const data = await response.json();
        responseEl.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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