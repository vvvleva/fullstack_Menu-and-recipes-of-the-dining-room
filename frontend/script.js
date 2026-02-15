let currentSlide = 0;
const slides = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.dot');
const track = document.getElementById('carouselTrack');
const API_URL = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', function() {
    checkServerStatus();
    setInterval(checkServerStatus, 5000);
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