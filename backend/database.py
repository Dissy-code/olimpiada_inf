import sqlite3
import hashlib
from config import DB_FILE

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("⚠️ bcrypt not installed. Using SHA256 (less secure).")

def hash_password(password):
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    if BCRYPT_AVAILABLE and hashed.startswith('$2b$'):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    else:
        return hashlib.sha256(password.encode()).hexdigest() == hashed

def migrate_database(conn):
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'total_xp' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN total_xp INTEGER DEFAULT 0")
    
    if 'level' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
    
    conn.commit()

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        password TEXT NOT NULL,
        rating INTEGER DEFAULT 1000,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        total_xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    )
    ''')
    
    migrate_database(conn)
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty INTEGER DEFAULT 1,
        category TEXT DEFAULT 'Математика',
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS solutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL,
        answer TEXT,
        is_correct BOOLEAN,
        time_spent INTEGER,
        solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (problem_id) REFERENCES problems(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER NOT NULL,
        player2_id INTEGER,
        problem_id INTEGER,
        status TEXT DEFAULT 'waiting',
        player1_answer TEXT,
        player2_answer TEXT,
        player1_time INTEGER,
        player2_time INTEGER,
        winner_id INTEGER,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        FOREIGN KEY (player1_id) REFERENCES users(id),
        FOREIGN KEY (player2_id) REFERENCES users(id),
        FOREIGN KEY (problem_id) REFERENCES problems(id),
        FOREIGN KEY (winner_id) REFERENCES users(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        total_problems INTEGER DEFAULT 0,
        solved_problems INTEGER DEFAULT 0,
        correct_answers INTEGER DEFAULT 0,
        total_time_spent INTEGER DEFAULT 0,
        avg_time_per_problem REAL DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        icon TEXT,
        requirement_type TEXT,
        requirement_value INTEGER
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_id INTEGER NOT NULL,
        earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (achievement_id) REFERENCES achievements(id),
        UNIQUE(user_id, achievement_id)
    )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if cursor.fetchone()[0] == 0:
        admin_pass = hash_password("admin123456")
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", admin_pass, "admin")
        )
    
    cursor.execute("SELECT COUNT(*) FROM problems")
    if cursor.fetchone()[0] == 0:
        test_problems = [
            ("Сумма чисел", "Чему равно 2 + 2?", "4", 1, "Математика", "арифметика"),
            ("Квадрат числа", "Чему равен квадрат числа 7?", "49", 2, "Математика", "алгебра"),
            ("Простое число", "Является ли число 29 простым? (ответ: да/нет)", "да", 2, "Математика", "теория чисел"),
            ("Периметр квадрата", "Найдите периметр квадрата со стороной 8 см", "32", 2, "Геометрия", "периметр"),
            ("Площадь круга", "Найдите площадь круга с радиусом 5 (π≈3.14)", "78.5", 3, "Геометрия", "площадь"),
            ("Уравнение", "Решите уравнение: 3x - 7 = 14", "7", 3, "Алгебра", "уравнения"),
            ("Процент", "20% от числа 150 равно?", "30", 1, "Математика", "проценты"),
            ("Степень числа", "Вычислите 2⁵", "32", 2, "Математика", "степени"),
            ("Факториал", "Найдите 5!", "120", 3, "Математика", "факториал"),
            ("Гипотенуза", "В прямоугольном треугольнике катеты 3 и 4. Найдите гипотенузу", "5", 3, "Геометрия", "теорема Пифагора"),
            ("Логика", "Если все A - это B, и все B - это C, то все A - это C. Верно? (да/нет)", "да", 2, "Логика", "логика"),
            ("Комбинаторика", "Сколькими способами можно расставить 3 книги на полке?", "6", 3, "Комбинаторика", "перестановки"),
        ]
        cursor.executemany(
            "INSERT INTO problems (title, description, answer, difficulty, category, tags) VALUES (?, ?, ?, ?, ?, ?)",
            test_problems
        )
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='test'")
    if cursor.fetchone()[0] == 0:
        test_pass = hash_password("test123")
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("test", test_pass)
        )
    
    cursor.execute("SELECT COUNT(*) FROM achievements")
    if cursor.fetchone()[0] == 0:
        achievements = [
            ("Первые шаги", "Решите первую задачу", "🎯", "problems_solved", 1),
            ("Математик", "Решите 10 задач", "📐", "problems_solved", 10),
            ("Мастер", "Решите 50 задач", "🏆", "problems_solved", 50),
            ("Легенда", "Решите 100 задач", "👑", "problems_solved", 100),
            ("Точность 90%", "Достигните 90% точности", "🎯", "accuracy", 90),
            ("Боец", "Выиграйте первый PvP матч", "⚔️", "pvp_wins", 1),
            ("Гладиатор", "Выиграйте 10 PvP матчей", "🛡️", "pvp_wins", 10),
            ("Рейтинг 1500", "Достигните рейтинга 1500", "⭐", "rating", 1500),
        ]
        cursor.executemany(
            "INSERT INTO achievements (name, description, icon, requirement_type, requirement_value) VALUES (?, ?, ?, ?, ?)",
            achievements
        )
    
    conn.commit()
    conn.close()
