import sqlite3
from core.db import get_connection

def list_users():
    """Показать всех пользователей"""
    with get_connection() as conn:
        users = conn.execute(
            "SELECT id, email, full_name, role, is_active FROM users"
        ).fetchall()
        
        print("\n=== Список пользователей ===")
        for user in users:
            print(f"ID: {user['id']}, Email: {user['email']}, Имя: {user['full_name']}, Роль: {user['role']}, Активен: {user['is_active']}")

def make_admin(email):
    """Сделать пользователя администратором"""
    with get_connection() as conn:
        # Проверяем, существует ли пользователь
        user = conn.execute(
            "SELECT id, email, role FROM users WHERE email = ?", 
            (email,)
        ).fetchone()
        
        if user:
            print(f"Текущая роль пользователя {email}: {user['role']}")
            
            # Обновляем роль
            conn.execute(
                "UPDATE users SET role = 'admin' WHERE email = ?",
                (email,)
            )
            conn.commit()  # Важно! Фиксируем изменения
            
            # Проверяем, что роль действительно изменилась
            updated = conn.execute(
                "SELECT role FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            
            print(f"Новая роль пользователя {email}: {updated['role']}")
            print(f"Пользователь {email} теперь администратор!")
        else:
            print(f"Пользователь с email {email} не найден")
            
        # Показываем обновленный список
        list_users()

if __name__ == "__main__":
    print("1. Показать всех пользователей")
    print("2. Сделать пользователя администратором")
    
    choice = input("Выберите действие (1 или 2): ")
    
    if choice == "1":
        list_users()
    elif choice == "2":
        email = input("Введите email пользователя: ")
        make_admin(email)
    else:
        print("Неверный выбор")