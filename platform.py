import http.server
import socketserver
import json
import sqlite3
import threading
import socket
import hashlib
import base64
import time
import random
from urllib.parse import urlparse, parse_qs
import os
from datetime import datetime
import mimetypes

PORT = 8080
DB_FILE = "olympiad_platform.db"
INDEX_PATH = r"D:\Студент\Downloads\Xray-windows-64\olimpiada\frontend\index.html"

mimetypes.init()

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
        last_login TIMESTAMP
    )
    ''')
    
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
        status TEXT DEFAULT 'waiting', -- waiting, active, finished, cancelled
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
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if cursor.fetchone()[0] == 0:
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", admin_pass, "admin")
        )
        print("Создан администратор: admin / admin123")
    
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
            ("Гипотенуза", "В прямоугольном треугольнике катеты 3 и 4. Найдите гипотенузу", "5", 3, "Геометрия", "теорема Пифагора")
        ]
        cursor.executemany(
            "INSERT INTO problems (title, description, answer, difficulty, category, tags) VALUES (?, ?, ?, ?, ?, ?)",
            test_problems
        )
        print("Добавлено 10 тестовых задач")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username='test'")
    if cursor.fetchone()[0] == 0:
        test_pass = hashlib.sha256("test123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("test", test_pass)
        )
        print("Создан тестовый пользователь: test / test123")
    
    conn.commit()
    conn.close()
    print(f"База данных инициализирована: {DB_FILE}")

class OlympiadHandler(http.server.BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/problems':
            self.send_api_response(self.get_problems())
        elif path == '/api/stats':
            self.send_api_response(self.get_platform_stats())
        elif path == '/api/users':
            self.send_api_response(self.get_users())
        elif path.startswith('/api/user/'):
            user_id = path.split('/')[-1]
            self.send_api_response(self.get_user_stats(user_id))
        elif path.startswith('/api/problem/'):
            try:
                problem_id = int(path.split('/')[-1])
                self.send_api_response(self.get_problem(problem_id))
            except:
                self.send_error(404)
        elif path == '/api/leaderboard':
            self.send_api_response(self.get_leaderboard())
        elif path == '/api/matches':
            self.send_api_response(self.get_active_matches())
        else:
            self.serve_static_file(path)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data)
        except:
            try:
                data = parse_qs(post_data)
                data = {k: v[0] for k, v in data.items()}
            except:
                data = {}
        
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/register':
            response = self.register_user(data)
        elif path == '/api/login':
            response = self.login_user(data)
        elif path == '/api/solve':
            response = self.submit_solution(data)
        elif path == '/api/match/create':
            response = self.create_match(data)
        elif path == '/api/match/join':
            response = self.join_match(data)
        elif path == '/api/match/submit':
            response = self.submit_match_answer(data)
        elif path == '/api/admin/add_problem':
            response = self.add_problem(data)
        elif path == '/api/admin/add_user':
            response = self.admin_add_user(data)
        elif path == '/api/admin/update_user':
            response = self.admin_update_user(data)
        elif path == '/api/admin/delete_user':
            response = self.admin_delete_user(data)
        else:
            response = {'success': False, 'error': 'API endpoint not found'}
        
        self.send_api_response(response)
    
    def get_problems(self):
        """Получить список задач с фильтрацией"""
        query_params = parse_qs(urlparse(self.path).query)
        category = query_params.get('category', [None])[0]
        difficulty = query_params.get('difficulty', [None])[0]
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        query = "SELECT id, title, description, difficulty, category, tags FROM problems WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if difficulty:
            query += " AND difficulty = ?"
            params.append(int(difficulty))
        
        query += " ORDER BY difficulty, id"
        cursor.execute(query, params)
        
        problems = []
        for row in cursor.fetchall():
            problems.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'difficulty': row[3],
                'difficulty_text': ['Легкая', 'Средняя', 'Сложная'][row[3]-1] if row[3] in [1,2,3] else 'Неизвестно',
                'category': row[4],
                'tags': row[5].split(',') if row[5] else []
            })
        
        conn.close()
        return {'success': True, 'problems': problems}
    
    def get_platform_stats(self):
        """Получить статистику платформы"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM problems")
        problems_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM solutions WHERE is_correct = 1")
        correct_solutions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'finished'")
        matches_played = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'success': True,
            'stats': {
                'users_count': users_count,
                'problems_count': problems_count,
                'correct_solutions': correct_solutions,
                'matches_played': matches_played
            }
        }
    
    def get_user_stats(self, user_id):
        """Получить статистику пользователя"""
        try:
            user_id = int(user_id)
        except:
            return {'success': False, 'error': 'Invalid user ID'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, rating, role FROM users WHERE id = ?", (user_id,))
        user_info = cursor.fetchone()
        
        if not user_info:
            conn.close()
            return {'success': False, 'error': 'User not found'}
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
                AVG(time_spent) as avg_time
            FROM solutions 
            WHERE user_id = ?
        """, (user_id,))
        
        stats = cursor.fetchone()
        total = stats[0] or 0
        correct = stats[1] or 0
        avg_time = stats[2] or 0
        
        conn.close()
        
        return {
            'success': True,
            'user': {
                'id': user_id,
                'username': user_info[0],
                'rating': user_info[1],
                'role': user_info[2],
                'stats': {
                    'total_problems': total,
                    'correct_answers': correct,
                    'accuracy': round((correct/total*100), 2) if total > 0 else 0,
                    'avg_time': round(avg_time, 2)
                }
            }
        }
    
    def get_leaderboard(self):
        """Получить таблицу лидеров"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.rating,
                   COUNT(s.id) as solved,
                   SUM(CASE WHEN s.is_correct THEN 1 ELSE 0 END) as correct
            FROM users u
            LEFT JOIN solutions s ON u.id = s.user_id
            GROUP BY u.id
            ORDER BY u.rating DESC
            LIMIT 50
        """)
        
        leaderboard = []
        rank = 1
        for row in cursor.fetchall():
            total = row[3] or 0
            correct = row[4] or 0
            accuracy = round((correct/total*100), 2) if total > 0 else 0
            
            leaderboard.append({
                'rank': rank,
                'id': row[0],
                'username': row[1],
                'rating': row[2],
                'solved': total,
                'correct': correct,
                'accuracy': accuracy
            })
            rank += 1
        
        conn.close()
        return {'success': True, 'leaderboard': leaderboard}
    
    def register_user(self, data):
        """Регистрация нового пользователя"""
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return {'success': False, 'error': 'Заполните все обязательные поля'}
        
        if len(password) < 6:
            return {'success': False, 'error': 'Пароль должен содержать минимум 6 символов'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Проверяем существование пользователя
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'error': 'Пользователь с таким именем уже существует'}
        
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return {'success': False, 'error': 'Пользователь с таким email уже существует'}
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
            (username, email if email else None, hashed_password)
        )
        
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO user_stats (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        
        cursor.execute("SELECT id, username, rating, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        
        return {
            'success': True,
            'message': 'Регистрация успешна!',
            'user': {
                'id': user[0],
                'username': user[1],
                'rating': user[2],
                'role': user[3]
            }
        }
    
    def login_user(self, data):
        """Аутентификация пользователя"""
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, password, rating, role FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {'success': False, 'error': 'Пользователь не найден'}
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if user[2] != hashed_password:
            conn.close()
            return {'success': False, 'error': 'Неверный пароль'}
        
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user[0],)
        )
        conn.commit()
        
        conn.close()
        
        return {
            'success': True,
            'user': {
                'id': user[0],
                'username': user[1],
                'rating': user[3],
                'role': user[4]
            }
        }
    
    def submit_solution(self, data):
        """Проверка решения задачи"""
        user_id = data.get('user_id')
        problem_id = data.get('problem_id')
        answer = data.get('answer', '').strip()
        time_spent = data.get('time_spent', 0)
        
        try:
            user_id = int(user_id)
            problem_id = int(problem_id)
        except:
            return {'success': False, 'error': 'Invalid IDs'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT answer, difficulty FROM problems WHERE id = ?", (problem_id,))
        problem = cursor.fetchone()
        
        if not problem:
            conn.close()
            return {'success': False, 'error': 'Задача не найдена'}
        
        correct_answer = str(problem[0]).strip().lower()
        user_answer = answer.strip().lower()
        difficulty = problem[1]
        
        is_correct = user_answer == correct_answer
        
        cursor.execute(
            """INSERT INTO solutions (user_id, problem_id, answer, is_correct, time_spent) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, problem_id, answer, is_correct, time_spent)
        )
        
        if is_correct:
            rating_change = difficulty * 10  
            cursor.execute(
                "UPDATE users SET rating = rating + ? WHERE id = ?",
                (rating_change, user_id)
            )
            
            cursor.execute("""
                UPDATE user_stats 
                SET total_problems = total_problems + 1,
                    solved_problems = solved_problems + 1,
                    correct_answers = correct_answers + 1,
                    total_time_spent = total_time_spent + ?,
                    avg_time_per_problem = (total_time_spent + ?) / (total_problems + 1)
                WHERE user_id = ?
            """, (time_spent, time_spent, user_id))
        else:
            cursor.execute("""
                UPDATE user_stats 
                SET total_problems = total_problems + 1,
                    total_time_spent = total_time_spent + ?,
                    avg_time_per_problem = (total_time_spent + ?) / (total_problems + 1)
                WHERE user_id = ?
            """, (time_spent, time_spent, user_id))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'correct': is_correct,
            'correct_answer': correct_answer,
            'rating_change': difficulty * 10 if is_correct else 0
        }
    
    def get_users(self):
        """Получить список пользователей (только для админа)"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.rating, u.role,
                   COALESCE(us.solved_problems, 0) as solved,
                   COALESCE(us.correct_answers, 0) as correct
            FROM users u
            LEFT JOIN user_stats us ON u.id = us.user_id
            ORDER BY u.rating DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            total = row[5] or 0
            correct = row[6] or 0
            accuracy = round((correct/total*100), 2) if total > 0 else 0
            
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2] or '',
                'rating': row[3],
                'role': row[4],
                'solved': total,
                'correct': correct,
                'accuracy': accuracy
            })
        
        conn.close()
        return {'success': True, 'users': users}
    
    def add_problem(self, data):
        """Добавить новую задачу (админ)"""
        user_id = data.get('user_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        answer = data.get('answer', '').strip()
        difficulty = data.get('difficulty', 1)
        category = data.get('category', 'Математика').strip()
        tags = data.get('tags', '').strip()
        
        if not title or not description or not answer:
            conn.close()
            return {'success': False, 'error': 'Заполните все обязательные поля'}
        
        try:
            difficulty = int(difficulty)
            if difficulty < 1 or difficulty > 3:
                difficulty = 1
        except:
            difficulty = 1
        
        cursor.execute(
            """INSERT INTO problems (title, description, answer, difficulty, category, tags, created_by) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, description, answer, difficulty, category, tags, user_id)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Задача успешно добавлена'}
    
    def admin_add_user(self, data):
        """Админ: добавить пользователя"""
        user_id = data.get('admin_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', 'user').strip()
        
        if not username or not password:
            conn.close()
            return {'success': False, 'error': 'Заполните имя пользователя и пароль'}
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'error': 'Пользователь уже существует'}
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email if email else None, hashed_password, role)
        )
        
        new_user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO user_stats (user_id) VALUES (?)",
            (new_user_id,)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Пользователь {username} создан'}
    
    def admin_update_user(self, data):
        """Админ: обновить пользователя"""
        user_id = data.get('admin_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        admin = cursor.fetchone()
        
        if not admin or admin[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        target_id = data.get('user_id')
        new_role = data.get('role', '').strip()
        new_rating = data.get('rating')
        
        if not target_id:
            conn.close()
            return {'success': False, 'error': 'Укажите ID пользователя'}
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (target_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            conn.close()
            return {'success': False, 'error': 'Пользователь не найден'}
        
        updates = []
        params = []
        
        if new_role and new_role in ['admin', 'user']:
            updates.append("role = ?")
            params.append(new_role)
        
        if new_rating is not None:
            try:
                rating = int(new_rating)
                updates.append("rating = ?")
                params.append(rating)
            except:
                pass
        
        if updates:
            params.append(target_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return {'success': True, 'message': 'Данные пользователя обновлены'}
    
    def admin_delete_user(self, data):
        """Админ: удалить пользователя"""
        user_id = data.get('admin_id')
        target_id = data.get('user_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        admin = cursor.fetchone()
        
        if not admin or admin[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        if not target_id:
            conn.close()
            return {'success': False, 'error': 'Укажите ID пользователя'}
        
        if user_id == target_id:
            conn.close()
            return {'success': False, 'error': 'Нельзя удалить самого себя'}
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (target_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            conn.close()
            return {'success': False, 'error': 'Пользователь не найден'}
        
        cursor.execute("DELETE FROM user_stats WHERE user_id = ?", (target_id,))
        cursor.execute("DELETE FROM solutions WHERE user_id = ?", (target_id,))
        cursor.execute("DELETE FROM matches WHERE player1_id = ? OR player2_id = ?", (target_id, target_id))
        cursor.execute("DELETE FROM users WHERE id = ?", (target_id,))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Пользователь {target_user[0]} удален'}
    
    def get_active_matches(self):
        """Получить активные матчи"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.id, m.status, m.started_at,
                   p1.username as player1,
                   p2.username as player2,
                   p.title as problem_title
            FROM matches m
            JOIN users p1 ON m.player1_id = p1.id
            LEFT JOIN users p2 ON m.player2_id = p2.id
            LEFT JOIN problems p ON m.problem_id = p.id
            WHERE m.status IN ('waiting', 'active')
            ORDER BY m.started_at DESC
            LIMIT 20
        """)
        
        matches = []
        for row in cursor.fetchall():
            matches.append({
                'id': row[0],
                'status': row[1],
                'started_at': row[2],
                'player1': row[3],
                'player2': row[4] or 'Ожидание...',
                'problem': row[5] or 'Не выбрана'
            })
        
        conn.close()
        return {'success': True, 'matches': matches}
    
    def create_match(self, data):
        """Создать PvP матч"""
        user_id = data.get('user_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM problems ORDER BY RANDOM() LIMIT 1")
        problem = cursor.fetchone()
        
        if not problem:
            conn.close()
            return {'success': False, 'error': 'Нет доступных задач'}
        
        problem_id = problem[0]
        
        cursor.execute(
            """INSERT INTO matches (player1_id, problem_id, status) 
               VALUES (?, ?, 'waiting')""",
            (user_id, problem_id)
        )
        
        match_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'match_id': match_id,
            'message': 'Матч создан. Ожидаем второго игрока...'
        }
    
    def join_match(self, data):
        """Присоединиться к матчу"""
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT player1_id, status FROM matches WHERE id = ?", (match_id,))
        match = cursor.fetchone()
        
        if not match:
            conn.close()
            return {'success': False, 'error': 'Матч не найден'}
        
        if match[1] != 'waiting':
            conn.close()
            return {'success': False, 'error': 'Матч уже начат или завершен'}
        
        if match[0] == user_id:
            conn.close()
            return {'success': False, 'error': 'Нельзя присоединиться к своему матчу'}
        
        cursor.execute(
            "UPDATE matches SET player2_id = ?, status = 'active', started_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id, match_id)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Вы присоединились к матчу!'}
    
    def submit_match_answer(self, data):
        """Отправить ответ в матче"""
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        answer = data.get('answer', '').strip()
        time_spent = data.get('time_spent', 0)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT player1_id, player2_id, problem_id, status, 
                   player1_answer, player2_answer
            FROM matches WHERE id = ?
        """, (match_id,))
        
        match = cursor.fetchone()
        
        if not match:
            conn.close()
            return {'success': False, 'error': 'Матч не найден'}
        
        if match[3] != 'active':
            conn.close()
            return {'success': False, 'error': 'Матч не активен'}
        
        player1_id, player2_id, problem_id, status, p1_answer, p2_answer = match
        
        if user_id != player1_id and user_id != player2_id:
            conn.close()
            return {'success': False, 'error': 'Вы не участник этого матча'}
        
        is_player1 = user_id == player1_id
        answer_field = 'player1_answer' if is_player1 else 'player2_answer'
        time_field = 'player1_time' if is_player1 else 'player2_time'
        
        cursor.execute(f"""
            UPDATE matches 
            SET {answer_field} = ?, {time_field} = ?
            WHERE id = ?
        """, (answer, time_spent, match_id))
        
        cursor.execute("""
            SELECT player1_answer, player2_answer 
            FROM matches WHERE id = ?
        """, (match_id,))
        
        updated_match = cursor.fetchone()
        p1_answer, p2_answer = updated_match
        
        if p1_answer is not None and p2_answer is not None:
            cursor.execute("SELECT answer FROM problems WHERE id = ?", (problem_id,))
            problem = cursor.fetchone()
            correct_answer = problem[0].strip().lower() if problem else ''
            p1_correct = p1_answer.strip().lower() == correct_answer
            p2_correct = p2_answer.strip().lower() == correct_answer
            if p1_correct and not p2_correct:
                winner_id = player1_id
            elif p2_correct and not p1_correct:
                winner_id = player2_id
            elif p1_correct and p2_correct:
                cursor.execute("SELECT player1_time, player2_time FROM matches WHERE id = ?", (match_id,))
                times = cursor.fetchone()
                winner_id = player1_id if times[0] < times[1] else player2_id
            else:
                winner_id = None
            
            cursor.execute("""
                UPDATE matches 
                SET status = 'finished', winner_id = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (winner_id, match_id))
            
            if winner_id:
                loser_id = player2_id if winner_id == player1_id else player1_id
                
                cursor.execute("SELECT rating FROM users WHERE id IN (?, ?)", (winner_id, loser_id))
                ratings = cursor.fetchall()
                winner_rating = ratings[0][0]
                loser_rating = ratings[1][0]
                
                K = 32
                expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
                expected_loser = 1 - expected_winner
                
                new_winner_rating = winner_rating + K * (1 - expected_winner)
                new_loser_rating = loser_rating + K * (0 - expected_loser)
                
                cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (new_winner_rating, winner_id))
                cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (new_loser_rating, loser_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Ответ отправлен'}
    
    def send_api_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def serve_static_file(self, path):
        if path == '/':
            filename = INDEX_PATH
        else:
            base_dir = os.path.dirname(INDEX_PATH)
            filename = os.path.join(base_dir, path.lstrip('/'))
        
        if not os.path.exists(filename):
            if filename.endswith(('.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.ico', '.svg')):
                self.send_error(404)
                return
            else:
                filename = INDEX_PATH
        
        content_type = 'text/html'
        if filename.endswith('.css'):
            content_type = 'text/css'
        elif filename.endswith('.js'):
            content_type = 'application/javascript'
        elif filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.ico'):
            content_type = 'image/x-icon'
        elif filename.endswith('.svg'):
            content_type = 'image/svg+xml'
        elif filename.endswith('.json'):
            content_type = 'application/json'
        
        try:
            with open(filename, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            print(f"Error serving file {filename}: {e}")
            self.send_error(500)

class WebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = {} 
        self.match_broadcasters = {}
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"🔥 WebSocket сервер запущен на ws://{self.host}:{self.port}")
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client,)).start()
    
    def handle_client(self, client):
        try:
            data = client.recv(1024).decode()
            if 'Sec-WebSocket-Key' in data:
                key_line = [line for line in data.split('\r\n') if 'Sec-WebSocket-Key:' in line][0]
                key = key_line.split(': ')[1]
                
                accept_key = base64.b64encode(
                    hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
                ).decode()
                
                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                )
                client.send(response.encode())
                
                while True:
                    try:
                        msg = self.receive_message(client)
                        if msg:
                            self.process_message(client, msg)
                    except:
                        break
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.remove_client(client)
    
    def process_message(self, client, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'auth':
                user_id = data.get('user_id')
                match_id = data.get('match_id')
                self.clients[client] = {'user_id': user_id, 'match_id': match_id}
                
                if match_id not in self.match_broadcasters:
                    self.match_broadcasters[match_id] = []
                if client not in self.match_broadcasters[match_id]:
                    self.match_broadcasters[match_id].append(client)
                
                self.broadcast_to_match(match_id, {
                    'type': 'player_joined',
                    'user_id': user_id,
                    'timestamp': time.time()
                }, exclude_client=client)
                
            elif msg_type == 'answer':
                match_id = data.get('match_id')
                answer = data.get('answer')
                self.broadcast_to_match(match_id, {
                    'type': 'answer_submitted',
                    'user_id': self.clients[client]['user_id'],
                    'answer': answer,
                    'timestamp': time.time()
                }, exclude_client=client)
                
            elif msg_type == 'chat':
                match_id = data.get('match_id')
                message = data.get('message')
                self.broadcast_to_match(match_id, {
                    'type': 'chat',
                    'user_id': self.clients[client]['user_id'],
                    'message': message,
                    'timestamp': time.time()
                })
                
        except json.JSONDecodeError:
            pass
    
    def broadcast_to_match(self, match_id, message, exclude_client=None):
        if match_id in self.match_broadcasters:
            msg_json = json.dumps(message)
            for client_socket in self.match_broadcasters[match_id]:
                if client_socket != exclude_client:
                    try:
                        self.send_message(client_socket, msg_json)
                    except:
                        pass
    
    def receive_message(self, client):
        try:
            data = client.recv(2)
            if len(data) < 2:
                return None
            
            first_byte, second_byte = data[0], data[1]
            fin = (first_byte & 0x80) != 0
            opcode = first_byte & 0x0F
            masked = (second_byte & 0x80) != 0
            payload_length = second_byte & 0x7F
            
            if payload_length == 126:
                data += client.recv(2)
                payload_length = int.from_bytes(data[2:4], 'big')
            elif payload_length == 127:
                data += client.recv(8)
                payload_length = int.from_bytes(data[2:10], 'big')
            
            if masked:
                mask_key = client.recv(4)
                encoded = client.recv(payload_length)
                decoded = bytes(encoded[i] ^ mask_key[i % 4] for i in range(len(encoded)))
            else:
                decoded = client.recv(payload_length)
            
            return decoded.decode('utf-8')
        except:
            return None
    
    def send_message(self, client, message):
        try:
            header = bytearray()
            header.append(0x81)  
            
            msg_bytes = message.encode('utf-8')
            length = len(msg_bytes)
            
            if length <= 125:
                header.append(length)
            elif length <= 65535:
                header.append(126)
                header.extend(length.to_bytes(2, 'big'))
            else:
                header.append(127)
                header.extend(length.to_bytes(8, 'big'))
            
            client.send(header + msg_bytes)
        except:
            pass
    
    def remove_client(self, client):
        if client in self.clients:
            client_info = self.clients[client]
            match_id = client_info.get('match_id')
            
            if match_id and match_id in self.match_broadcasters:
                if client in self.match_broadcasters[match_id]:
                    self.match_broadcasters[match_id].remove(client)
                
                self.broadcast_to_match(match_id, {
                    'type': 'player_left',
                    'user_id': client_info['user_id'],
                    'timestamp': time.time()
                })
            
            del self.clients[client]
        client.close()

def start_servers():
    init_database()
    
    ws_server = WebSocketServer()
    ws_thread = threading.Thread(target=ws_server.start, daemon=True)
    ws_thread.start()
    
    with socketserver.TCPServer(("", PORT), OlympiadHandler) as httpd:
        print(f"🚀 HTTP сервер запущен на http://localhost:{PORT}")
        print(f"🌐 Откройте браузер: http://localhost:{PORT}")
        print("👑 Администратор: admin / admin123")
        print("👤 Тестовый пользователь: test / test123")
        print("📊 База данных: olympiad_platform.db")
        print("⚡ Для остановки сервера нажмите Ctrl+C\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Сервер остановлен")
            httpd.server_close()

if __name__ == "__main__":
    start_servers()