"""Безопасность и хеширование паролей."""
import hashlib
import secrets
import base64

def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием PBKDF2-HMAC-SHA256.
    
    Args:
        password: пароль для хеширования
    
    Returns:
        строка вида: pbkdf2_sha256$iterations$salt$hash
    """
    # Генерируем случайную соль (16 байт)
    salt = secrets.token_bytes(16)
    iterations = 260000  # Рекомендуемое количество итераций для PBKDF2
    
    # Хешируем пароль
    password_bytes = password.encode('utf-8')
    hash_bytes = hashlib.pbkdf2_hmac(
        'sha256',
        password_bytes,
        salt,
        iterations
    )
    
    # Кодируем соль и хеш в base64 для хранения
    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(hash_bytes).decode('ascii')
    
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"

def verify_password(password: str, hashed: str) -> bool:
    """
    Проверяет пароль против хеша.
    
    Args:
        password: проверяемый пароль
        hashed: сохраненный хеш в формате pbkdf2_sha256$iterations$salt$hash
    
    Returns:
        True если пароль верный
    """
    try:
        # Разбираем хеш
        algorithm, iterations_str, salt_b64, hash_b64 = hashed.split('$')
        
        if algorithm != 'pbkdf2_sha256':
            return False
        
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode('ascii'))
        expected_hash = base64.b64decode(hash_b64.encode('ascii'))
        
        # Вычисляем хеш для проверяемого пароля
        password_bytes = password.encode('utf-8')
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password_bytes,
            salt,
            iterations
        )
        
        # Сравниваем хеши (constant-time сравнение)
        return secrets.compare_digest(hash_bytes, expected_hash)
        
    except Exception as e:
        print(f"Ошибка при проверке пароля: {e}")
        return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Проверяет сложность пароля.
    
    Returns:
        (True, "") если пароль достаточно сложный
        (False, "причина") если пароль слишком простой
    """
    if len(password) < 6:
        return False, "Пароль должен быть минимум 6 символов"
    
    if len(password) > 72:
        return False, "Пароль не может быть длиннее 72 символов"
    
    # Проверяем наличие разных типов символов
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    if not (has_lower and has_upper and has_digit):
        return False, "Пароль должен содержать заглавные, строчные буквы и цифры"
    
    return True, ""