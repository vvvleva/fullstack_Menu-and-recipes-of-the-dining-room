const API_URL = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', function() {
    console.log('Страница регистрации загружена');
    checkServerStatus();
    
    const form = document.getElementById('registerForm');
    const password = document.getElementById('password');
    const confirm = document.getElementById('confirmPassword');
    
    if (password) {
        password.addEventListener('input', checkPasswordStrength);
        password.addEventListener('input', validateMatch);
    }
    
    if (confirm) {
        confirm.addEventListener('input', validateMatch);
    }
    
    if (form) {
        form.addEventListener('submit', handleRegister);
    }
});

async function checkServerStatus() {
    try {
        console.log('Проверка сервера...');
        const res = await fetch(`${API_URL}/health`);
        console.log('Ответ от сервера:', res.status);
        
        const statusEl = document.getElementById('serverStatus');
        if (!statusEl) return;
        
        const indicator = statusEl.querySelector('.status-indicator');
        const text = statusEl.querySelector('.status-text');
        
        if (res.ok) {
            indicator.className = 'status-indicator online';
            text.textContent = 'Сервер онлайн';
            console.log('Сервер доступен');
        } else {
            throw new Error(`HTTP ${res.status}`);
        }
    } catch (e) {
        console.error('Ошибка подключения к серверу:', e);
        const statusEl = document.getElementById('serverStatus');
        if (statusEl) {
            statusEl.querySelector('.status-indicator').className = 'status-indicator offline';
            statusEl.querySelector('.status-text').textContent = 'Сервер офлайн';
        }
    }
}

function checkPasswordStrength() {
    const password = document.getElementById('password').value;
    const bars = document.querySelectorAll('.strength-bar');
    
    bars.forEach(bar => bar.className = 'strength-bar');
    
    if (!password) return;
    
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    bars.forEach((bar, i) => {
        if (i < Math.min(strength, 3)) {
            if (strength <= 2) {
                bar.classList.add('weak');
            } else if (strength <= 4) {
                bar.classList.add('medium');
            } else {
                bar.classList.add('strong');
            }
        }
    });
}

function validateMatch() {
    const pwd = document.getElementById('password').value;
    const confirm = document.getElementById('confirmPassword');
    
    if (confirm.value) {
        if (pwd !== confirm.value) {
            confirm.classList.add('error');
        } else {
            confirm.classList.remove('error');
        }
    } else {
        confirm.classList.remove('error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const name = document.getElementById('fullName').value.trim();
    const email = document.getElementById('email').value.trim();
    const pwd = document.getElementById('password').value;
    const confirm = document.getElementById('confirmPassword').value;
    
    if (!name) {
        showNotification('Введите имя', 'error');
        return;
    }
    
    if (!email || !email.includes('@')) {
        showNotification('Введите корректный email', 'error');
        return;
    }
    
    if (pwd !== confirm) {
        showNotification('Пароли не совпадают', 'error');
        return;
    }
    
    if (pwd.length < 6) {
        showNotification('Пароль должен быть минимум 6 символов', 'error');
        return;
    }
    
    const btn = document.getElementById('registerBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Регистрация...';
    
    // Данные для отправки
    const userData = {
        full_name: name,
        email: email,
        password: pwd,
        allergens: [],
        diet: null
    };
    
    console.log('Отправка данных на сервер:', userData);
    console.log('URL:', `${API_URL}/auth/register`);
    
    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(userData)
        });
        
        console.log('Статус ответа:', res.status);
        
        const data = await res.json();
        console.log('Ответ от сервера:', data);
        
        if (res.ok) {
            showNotification('Регистрация успешна!', 'success');
            
            localStorage.setItem('user', JSON.stringify({
                name: data.full_name || name,
                email: data.email || email,
                allergens: [],
                diet: null
            }));
            
            setTimeout(() => {
                window.location.href = '/?profile=open';
            }, 1500);
        } else {
            const errorMsg = data.detail || data.message || 'Ошибка регистрации';
            showNotification(errorMsg, 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-user-plus"></i> Зарегистрироваться';
        }
    } catch (err) {
        console.error('Ошибка при запросе:', err);
        showNotification('Ошибка соединения с сервером.', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-user-plus"></i> Зарегистрироваться';
    }
}

function showNotification(msg, type) {
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