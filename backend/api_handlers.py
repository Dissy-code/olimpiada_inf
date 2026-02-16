import http.server
import json
import sqlite3
import mimetypes
import os
from urllib.parse import urlparse, parse_qs
import csv
import io
from datetime import datetime

from config import DB_FILE, FRONTEND_DIR, INDEX_PATH
from database import verify_password, hash_password

mimetypes.init()

class OlympiadHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, ws_server_instance=None, **kwargs):
        self.ws_server = ws_server_instance
        super().__init__(*args, **kwargs)
    
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
        elif path.startswith('/api/match/'):
            match_id = path.split('/')[-1]
            self.send_api_response(self.get_match_details(match_id))
        elif path == '/api/achievements':
            self.send_api_response(self.get_achievements())
        elif path.startswith('/api/user_achievements/'):
            user_id = path.split('/')[-1]
            self.send_api_response(self.get_user_achievements(user_id))
        elif path == '/api/export/problems':
            self.export_problems()
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
        elif path == '/api/admin/edit_problem':
            response = self.edit_problem(data)
        elif path == '/api/admin/delete_problem':
            response = self.delete_problem(data)
        elif path == '/api/admin/add_user':
            response = self.admin_add_user(data)
        elif path == '/api/admin/update_user':
            response = self.admin_update_user(data)
        elif path == '/api/admin/delete_user':
            response = self.admin_delete_user(data)
        elif path == '/api/admin/import_problems':
            response = self.import_problems(data)
        else:
            response = {'success': False, 'error': 'API endpoint not found'}
        
        self.send_api_response(response)
    
    def get_problems(self):
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
    
    def get_problem(self, problem_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, answer, difficulty, category, tags
            FROM problems WHERE id = ?
        """, (problem_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'success': False, 'error': 'Задача не найдена'}
        
        return {
            'success': True,
            'problem': {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'answer': row[3],
                'difficulty': row[4],
                'difficulty_text': ['Легкая', 'Средняя', 'Сложная'][row[4]-1] if row[4] in [1,2,3] else 'Неизвестно',
                'category': row[5],
                'tags': row[6].split(',') if row[6] else []
            }
        }
    
    def get_platform_stats(self):
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
        try:
            user_id = int(user_id)
        except:
            return {'success': False, 'error': 'Invalid user ID'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT username, rating, role, total_xp, level FROM users WHERE id = ?", (user_id,))
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
        
        cursor.execute("""
            SELECT 
                p.category,
                COUNT(*) as total,
                SUM(CASE WHEN s.is_correct THEN 1 ELSE 0 END) as correct
            FROM solutions s
            JOIN problems p ON s.problem_id = p.id
            WHERE s.user_id = ?
            GROUP BY p.category
            ORDER BY total DESC
        """, (user_id,))
        
        categories = []
        for row in cursor.fetchall():
            categories.append({
                'category': row[0],
                'total': row[1],
                'correct': row[2],
                'accuracy': round((row[2]/row[1]*100), 2) if row[1] > 0 else 0
            })
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_matches,
                SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins
            FROM matches
            WHERE (player1_id = ? OR player2_id = ?) AND status = 'finished'
        """, (user_id, user_id, user_id))
        
        pvp_stats = cursor.fetchone()
        total_matches = pvp_stats[0] or 0
        wins = pvp_stats[1] or 0
        
        conn.close()
        
        return {
            'success': True,
            'user': {
                'id': user_id,
                'username': user_info[0],
                'rating': user_info[1],
                'role': user_info[2],
                'xp': user_info[3],
                'level': user_info[4],
                'stats': {
                    'total_problems': total,
                    'correct_answers': correct,
                    'accuracy': round((correct/total*100), 2) if total > 0 else 0,
                    'avg_time': round(avg_time, 2),
                    'pvp_matches': total_matches,
                    'pvp_wins': wins,
                    'pvp_winrate': round((wins/total_matches*100), 2) if total_matches > 0 else 0
                },
                'categories': categories
            }
        }
    
    def get_leaderboard(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.rating, u.level,
                   COUNT(s.id) as solved,
                   SUM(CASE WHEN s.is_correct THEN 1 ELSE 0 END) as correct
            FROM users u
            LEFT JOIN solutions s ON u.id = s.user_id
            GROUP BY u.id
            ORDER BY u.rating DESC
            LIMIT 50
        """
        )
        
        leaderboard = []
        rank = 1
        for row in cursor.fetchall():
            total = row[4] or 0
            correct = row[5] or 0
            accuracy = round((correct/total*100), 2) if total > 0 else 0
            
            leaderboard.append({
                'rank': rank,
                'id': row[0],
                'username': row[1],
                'rating': row[2],
                'level': row[3],
                'solved': total,
                'correct': correct,
                'accuracy': accuracy
            })
            rank += 1
        
        conn.close()
        return {'success': True, 'leaderboard': leaderboard}
    
    def register_user(self, data):
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return {'success': False, 'error': 'Заполните все обязательные поля'}
        
        if len(password) < 6:
            return {'success': False, 'error': 'Пароль должен содержать минимум 6 символов'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'error': 'Пользователь с таким именем уже существует'}
        
        if email:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return {'success': False, 'error': 'Пользователь с таким email уже существует'}
        
        hashed_password = hash_password(password)
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
        
        if not verify_password(password, user[2]):
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
        
        xp_gained = 0
        if is_correct:
            rating_change = difficulty * 10
            xp_gained = difficulty * 50
            
            cursor.execute(
                "UPDATE users SET rating = rating + ?, total_xp = total_xp + ? WHERE id = ?",
                (rating_change, xp_gained, user_id)
            )
            
            cursor.execute("SELECT total_xp, level FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            current_xp = user_data[0]
            current_level = user_data[1]
            new_level = 1 + (current_xp // 1000)
            
            if new_level > current_level:
                cursor.execute("UPDATE users SET level = ? WHERE id = ?", (new_level, user_id))
            
            cursor.execute("""
                UPDATE user_stats 
                SET total_problems = total_problems + 1,
                    solved_problems = solved_problems + 1,
                    correct_answers = correct_answers + 1,
                    total_time_spent = total_time_spent + ?,
                    avg_time_per_problem = (total_time_spent + ?) / (total_problems + 1)
                WHERE user_id = ?
            """, (time_spent, time_spent, user_id))
            
            self.check_achievements(cursor, user_id)
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
            'rating_change': difficulty * 10 if is_correct else 0,
            'xp_gained': xp_gained
        }
    
    def check_achievements(self, cursor, user_id):
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM solutions WHERE user_id = ?
        """, (user_id,))
        stats = cursor.fetchone()
        total = stats[0] or 0
        correct = stats[1] or 0
        accuracy = (correct / total * 100) if total > 0 else 0
        
        cursor.execute("SELECT rating FROM users WHERE id = ?", (user_id,))
        rating = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM matches 
            WHERE winner_id = ? AND status = 'finished'
        """, (user_id,))
        pvp_wins = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, requirement_type, requirement_value FROM achievements")
        achievements = cursor.fetchall()
        
        for ach_id, req_type, req_value in achievements:
            should_unlock = False
            
            if req_type == 'problems_solved' and correct >= req_value:
                should_unlock = True
            elif req_type == 'accuracy' and accuracy >= req_value:
                should_unlock = True
            elif req_type == 'rating' and rating >= req_value:
                should_unlock = True
            elif req_type == 'pvp_wins' and pvp_wins >= req_value:
                should_unlock = True
            
            if should_unlock:
                try:
                    cursor.execute("""
                        INSERT INTO user_achievements (user_id, achievement_id) 
                        VALUES (?, ?)
                    """, (user_id, ach_id))
                except sqlite3.IntegrityError:
                    pass
    
    def get_achievements(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, icon, requirement_type, requirement_value
            FROM achievements
        """
        )
        
        achievements = []
        for row in cursor.fetchall():
            achievements.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'icon': row[3],
                'requirement_type': row[4],
                'requirement_value': row[5]
            })
        
        conn.close()
        return {'success': True, 'achievements': achievements}
    
    def get_user_achievements(self, user_id):
        try:
            user_id = int(user_id)
        except:
            return {'success': False, 'error': 'Invalid user ID'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.id, a.name, a.description, a.icon, ua.earned_at
            FROM achievements a
            JOIN user_achievements ua ON a.id = ua.achievement_id
            WHERE ua.user_id = ?
            ORDER BY ua.earned_at DESC
        """, (user_id,))
        
        achievements = []
        for row in cursor.fetchall():
            achievements.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'icon': row[3],
                'earned_at': row[4]
            })
        
        conn.close()
        return {'success': True, 'achievements': achievements}
    
    def get_users(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.rating, u.role, u.level,
                   COALESCE(us.solved_problems, 0) as solved,
                   COALESCE(us.correct_answers, 0) as correct
            FROM users u
            LEFT JOIN user_stats us ON u.id = us.user_id
            ORDER BY u.rating DESC
        """
        )
        
        users = []
        for row in cursor.fetchall():
            total = row[6] or 0
            correct = row[7] or 0
            accuracy = round((correct/total*100), 2) if total > 0 else 0
            
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2] or '',
                'rating': row[3],
                'role': row[4],
                'level': row[5],
                'solved': total,
                'correct': correct,
                'accuracy': accuracy
            })
        
        conn.close()
        return {'success': True, 'users': users}
    
    def add_problem(self, data):
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
    
    def edit_problem(self, data):
        user_id = data.get('user_id')
        problem_id = data.get('problem_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        cursor.execute(
            """UPDATE problems 
               SET title = ?, description = ?, answer = ?, difficulty = ?, category = ?, tags = ?
               WHERE id = ?""",
            (data.get('title'), data.get('description'), data.get('answer'),
             data.get('difficulty'), data.get('category'), data.get('tags'), problem_id)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Задача обновлена'}
    
    def delete_problem(self, data):
        user_id = data.get('user_id')
        problem_id = data.get('problem_id')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        cursor.execute("DELETE FROM solutions WHERE problem_id = ?", (problem_id,))
        cursor.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Задача удалена'}
    
    def admin_add_user(self, data):
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
        
        hashed_password = hash_password(password)
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
        cursor.execute("DELETE FROM user_achievements WHERE user_id = ?", (target_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (target_id,))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Пользователь {target_user[0]} удален'}
    
    def get_active_matches(self):
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
        """
        )
        
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
    
    def get_match_details(self, match_id):
        try:
            match_id = int(match_id)
        except:
            return {'success': False, 'error': 'Invalid match ID'}
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.id, m.status, m.problem_id, m.player1_id, m.player2_id,
                   m.player1_answer, m.player2_answer, m.player1_time, m.player2_time,
                   p.title, p.description, p.difficulty, p.category,
                   u1.username as player1_username,
                   u2.username as player2_username
            FROM matches m
            LEFT JOIN problems p ON m.problem_id = p.id
            LEFT JOIN users u1 ON m.player1_id = u1.id
            LEFT JOIN users u2 ON m.player2_id = u2.id
            WHERE m.id = ?
        """, (match_id,))
        
        match = cursor.fetchone()
        conn.close()
        
        if not match:
            return {'success': False, 'error': 'Матч не найден'}
        
        return {
            'success': True,
            'match': {
                'id': match[0],
                'status': match[1],
                'problem_id': match[2],
                'player1_id': match[3],
                'player2_id': match[4],
                'player1_answer': match[5],
                'player2_answer': match[6],
                'player1_time': match[7],
                'player2_time': match[8],
                'player1': match[13],
                'player2': match[14],
                'problem': {
                    'title': match[9],
                    'description': match[10],
                    'difficulty': match[11],
                    'category': match[12]
                } if match[9] else None
            }
        }
    
    def create_match(self, data):
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

        cursor.execute("""
            SELECT m.id, m.status, m.problem_id, m.player1_id, m.player2_id,
                   p.title, p.description, p.difficulty, p.category,
                   u1.username as player1_username,
                   u2.username as player2_username
            FROM matches m
            LEFT JOIN problems p ON m.problem_id = p.id
            LEFT JOIN users u1 ON m.player1_id = u1.id
            LEFT JOIN users u2 ON m.player2_id = u2.id
            WHERE m.id = ?
        """, (match_id,))
        updated_match = cursor.fetchone()

        if updated_match and self.ws_server:
            match_data = {
                'type': 'match_started',
                'match_id': updated_match[0],
                'player1_id': updated_match[3],
                'player2_id': updated_match[4],
                'player1_username': updated_match[9],
                'player2_username': updated_match[10],
                'problem': {
                    'title': updated_match[5],
                    'description': updated_match[6],
                    'difficulty': updated_match[7],
                    'category': updated_match[8]
                }
            }
            self.ws_server.broadcast_to_match(match_id, match_data)
        
        conn.close()
        
        return {'success': True, 'message': 'Вы присоединились к матчу!'}
    
    def submit_match_answer(self, data):
        user_id = data.get('user_id')
        match_id = data.get('match_id')
        answer = data.get('answer', '').strip()
        time_spent = data.get('time_spent', 0)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT player1_id, player2_id, problem_id, status, 
                   player1_answer, player2_answer, player1_time, player2_time
            FROM matches WHERE id = ?
        """, (match_id,))
        
        match = cursor.fetchone()
        
        if not match:
            conn.close()
            return {'success': False, 'error': 'Матч не найден'}
        
        if match[3] != 'active':
            conn.close()
            return {'success': False, 'error': 'Матч не активен'}
        
        player1_id, player2_id, problem_id, status, p1_answer, p2_answer, p1_time, p2_time = match
        
        if user_id != player1_id and user_id != player2_id:
            conn.close()
            return {'success': False, 'error': 'Вы не участник этого матча'}
        
        is_player1 = user_id == player1_id

        if is_player1 and p1_answer is not None:
            conn.close()
            return {'success': False, 'error': 'Вы уже ответили на вопрос.'}
        if not is_player1 and p2_answer is not None:
            conn.close()
            return {'success': False, 'error': 'Вы уже ответили на вопрос.'}
        
        answer_field = 'player1_answer' if is_player1 else 'player2_answer'
        time_field = 'player1_time' if is_player1 else 'player2_time'
        
        cursor.execute(f"""
            UPDATE matches 
            SET {answer_field} = ?, {time_field} = ?
            WHERE id = ?
        """, (answer, time_spent, match_id))
        
        conn.commit()

        cursor.execute("""
            SELECT player1_answer, player2_answer, player1_time, player2_time
            FROM matches WHERE id = ?
        """, (match_id,))
        updated_match_answers = cursor.fetchone()
        p1_answer, p2_answer, p1_time, p2_time = updated_match_answers
        
        response = {'success': True, 'message': 'Ответ отправлен'}

        if p1_answer is not None and p2_answer is not None:
            cursor.execute("SELECT answer FROM problems WHERE id = ?", (problem_id,))
            problem = cursor.fetchone()
            correct_answer = problem[0].strip().lower() if problem else ''
            
            p1_correct = p1_answer.strip().lower() == correct_answer
            p2_correct = p2_answer.strip().lower() == correct_answer
            
            winner_id = None
            if p1_correct and not p2_correct:
                winner_id = player1_id
            elif p2_correct and not p1_correct:
                winner_id = player2_id
            elif p1_correct and p2_correct:
                winner_id = player1_id if p1_time < p2_time else player2_id
            
            cursor.execute("""
                UPDATE matches 
                SET status = 'finished', winner_id = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (winner_id, match_id))
            
            cursor.execute("SELECT rating FROM users WHERE id IN (?, ?)", (player1_id, player2_id))
            ratings = cursor.fetchall()
            rating1 = ratings[0][0]
            rating2 = ratings[1][0]
            
            K = 32
            expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
            expected2 = 1 - expected1
            
            if winner_id == player1_id:
                score1, score2 = 1, 0
            elif winner_id == player2_id:
                score1, score2 = 0, 1
            else:
                score1, score2 = 0.5, 0.5
            
            new_rating1 = rating1 + K * (score1 - expected1)
            new_rating2 = rating2 + K * (score2 - expected2)
            
            cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (int(new_rating1), player1_id))
            cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (int(new_rating2), player2_id))
            
            if winner_id:
                self.check_achievements(cursor, winner_id)

            conn.commit()

            response['match_finished'] = True
            response['player1_correct'] = p1_correct
            response['player2_correct'] = p2_correct
            response['winner_id'] = winner_id
            response['new_rating1'] = int(new_rating1)
            response['new_rating2'] = int(new_rating2)
            response['message'] = 'Матч завершен!'
            
            if self.ws_server:
                self.ws_server.broadcast_to_match(match_id, {
                    'type': 'match_finished',
                    'match_id': match_id,
                    'winner_id': winner_id,
                    'player1_correct': p1_correct,
                    'player2_correct': p2_correct
                })
        
        conn.close()
        return response
    
    def import_problems(self, data):
        user_id = data.get('user_id')
        problems_data = data.get('problems', [])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user or user[0] != 'admin':
            conn.close()
            return {'success': False, 'error': 'Доступ запрещен'}
        
        imported = 0
        for problem in problems_data:
            try:
                cursor.execute("""
                    INSERT INTO problems (title, description, answer, difficulty, category, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    problem.get('title', ''),
                    problem.get('description', ''),
                    problem.get('answer', ''),
                    problem.get('difficulty', 1),
                    problem.get('category', 'Математика'),
                    problem.get('tags', '')
                ))
                imported += 1
            except:
                pass
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Импортировано задач: {imported}'}
    
    def export_problems(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, description, answer, difficulty, category, tags
            FROM problems
        """
        )
        
        problems = []
        for row in cursor.fetchall():
            problems.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'answer': row[3],
                'difficulty': row[4],
                'category': row[5],
                'tags': row[6]
            })
        
        conn.close()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Disposition', 'attachment; filename="problems.json"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(problems, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def send_api_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def serve_static_file(self, path):
        if path == '/':
            filename = INDEX_PATH
        else:
            filename = os.path.join(FRONTEND_DIR, path.lstrip('/'))
        
        if not os.path.exists(filename):
            if filename.endswith(('.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.ico', '.svg')):
                self.send_error(404)
                return
            else:
                filename = INDEX_PATH
        
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'text/html'
        
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
