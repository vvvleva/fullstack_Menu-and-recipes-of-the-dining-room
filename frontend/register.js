const API_URL = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const loginLink = document.getElementById('loginLink');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', checkPasswordStrength);
        passwordInput.addEventListener('input', validatePasswordsMatch);
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', validatePasswordsMatch);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    if (loginLink) {
        loginLink.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/';
        });
    }
    
    checkServerStatus();
});

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

function checkPasswordStrength() {
    const password = document.getElementById('password').value;
    const strengthBars = document.querySelectorAll('.strength-bar');
    
    let strength = 0;
    
    if (password.length >= 6) strength++;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    strengthBars.forEach((bar, index) => {
        bar.className = 'strength-bar';
        if (index < strength) {
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

function validatePasswordsMatch() {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const confirmInput = document.getElementById('confirmPassword');
    
    if (confirmPassword && password !== confirmPassword) {
        confirmInput.classList.add('error');
    } else {
        confirmInput.classList.remove('error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const fullName = document.getElementById('fullName').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const diet = document.getElementById('diet').value;
    
    const allergenCheckboxes = document.querySelectorAll('input[name="allergens"]:checked');
    const allergens = Array.from(allergenCheckboxes).map(cb => cb.value);
    
    if (password !== confirmPassword) {
        showNotification('Пароли не совпадают', 'error');
        return;
    }
    
    if (password.length < 6) {
        showNotification('Пароль должен содержать минимум 6 символов', 'error');
        return;
    }
    
    const registerButton = document.querySelector('.register-button');
    registerButton.disabled = true;
    registerButton.textContent = 'Регистрация...';
    
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                full_name: fullName,
                email: email,
                password: password,
                allergens: allergens,
                diet: diet || null
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Регистрация успешна! Теперь вы можете войти', 'success');
            
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            const errorMessage = data.detail || data.message || 'Ошибка при регистрации';
            showNotification(errorMessage, 'error');
            registerButton.disabled = false;
            registerButton.textContent = 'Зарегистрироваться';
        }
    } catch (error) {
        showNotification('Ошибка соединения с сервером', 'error');
        registerButton.disabled = false;
        registerButton.textContent = 'Зарегистрироваться';
    }
}

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