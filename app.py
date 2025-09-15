"""Sports Schedulers Light - Clean Working Version
Author: Jose Ortiz
Date: September 14, 2025
Company: JES Baseball LLC"""

import os
import re
import secrets
import logging
from flask import Flask, render_template_string, request, jsonify, redirect, session
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'sports-schedulers-light-production-key-2025'),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def hash_password(password):
    salt = hashlib.sha256(password.encode()).hexdigest()[:16]
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def verify_password(stored_password, provided_password):
    try:
        salt = hashlib.sha256(provided_password.encode()).hexdigest()[:16]
        test_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt.encode(), 100000).hex()
        return test_hash == stored_password
    except:
        return False

def get_db_connection():
    conn = sqlite3.connect('scheduler_light.db', timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        app.logger.info("Initializing production database...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                role TEXT DEFAULT 'official',
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                last_login TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                location TEXT,
                sport TEXT NOT NULL,
                league TEXT,
                level TEXT,
                officials_needed INTEGER DEFAULT 1,
                notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_date TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                sport TEXT,
                experience_level TEXT,
                certifications TEXT,
                rating REAL DEFAULT 0.0,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                official_id INTEGER NOT NULL,
                position TEXT DEFAULT 'Referee',
                status TEXT DEFAULT 'assigned',
                assigned_date TEXT NOT NULL,
                notes TEXT,
                assigned_by INTEGER,
                FOREIGN KEY (game_id) REFERENCES games (id),
                FOREIGN KEY (official_id) REFERENCES officials (id),
                UNIQUE(game_id, official_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sport TEXT NOT NULL,
                season TEXT NOT NULL,
                levels TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                contact_person TEXT,
                contact_phone TEXT,
                capacity INTEGER,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'superadmin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (username, password, full_name, email, role, is_active, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'jose_1',
                hash_password('Josu2398-1'),
                'Jose Ortiz',
                'jose@sportsschedulers.com',
                'superadmin',
                1,
                datetime.now().isoformat()
            ))
            
            cursor.execute("""
                INSERT INTO users (username, password, full_name, email, role, is_active, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'admin',
                hash_password('admin123'),
                'System Administrator',
                'admin@sportsschedulers.com',
                'superadmin',
                1,
                datetime.now().isoformat()
            ))

        conn.commit()
        app.logger.info("Production database initialized successfully")
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sports Schedulers</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .login-container { 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); 
            max-width: 400px; 
            width: 100%;
        }
        .login-header { 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            color: white; 
            padding: 3rem 2rem 2rem; 
            text-align: center; 
            border-radius: 20px 20px 0 0; 
        }
        .form-control { 
            border-radius: 12px; 
            border: 2px solid #e2e8f0; 
            padding: 1rem; 
            transition: all 0.3s ease;
        }
        .form-control:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        .btn-login { 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            border: none; 
            border-radius: 12px; 
            color: white; 
            font-weight: 600; 
            padding: 1rem; 
            width: 100%; 
            transition: all 0.3s ease;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
            color: white;
        }
        .welcome-message { 
            background: #f8fafc; 
            border: 1px solid #e2e8f0; 
            border-radius: 12px; 
            padding: 1.5rem; 
            margin-bottom: 1.5rem; 
            text-align: center;
        }
        .input-group-text {
            background: transparent;
            border: 2px solid #e2e8f0;
            border-right: none;
            border-radius: 12px 0 0 12px;
        }
        .input-group .form-control {
            border-left: none;
            border-radius: 0 12px 12px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container mx-auto">
            <div class="login-header">
                <i class="fas fa-calendar-alt fa-3x mb-3"></i>
                <h1>Sports Schedulers</h1>
                <p class="mb-0">Professional Management System</p>
            </div>
            
            <div class="p-4">
                <div class="welcome-message">
                    <h5><i class="fas fa-shield-alt me-2 text-primary"></i>Secure Access Portal</h5>
                    <p class="mb-0 text-muted">Enter your authorized credentials to access the system</p>
                </div>
                
                <form id="loginForm">
                    <div class="mb-3">
                        <div class="input-group">
                            <span class="input-group-text"><i class="fas fa-user"></i></span>
                            <input type="text" class="form-control" name="username" placeholder="Enter username" required autocomplete="off">
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="input-group">
                            <span class="input-group-text"><i class="fas fa-lock"></i></span>
                            <input type="password" class="form-control" name="password" placeholder="Enter password" required autocomplete="off">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-login">
                        <i class="fas fa-sign-in-alt me-2"></i>Access System
                    </button>
                </form>
                
                <div class="text-center mt-4">
                    <small class="text-muted">&copy; 2025 JES Baseball LLC. All rights reserved.</small>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = result.redirect;
                } else {
                    alert('Access denied: ' + result.error);
                }
            } catch (error) {
                alert('System error: ' + error.message);
            }
        });
    </script>
</body>
</html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Sports Schedulers</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; }
        .sidebar { width: 280px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; position: fixed; height: 100vh; overflow-y: auto; }
        .sidebar-header { padding: 2rem; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .nav-link { color: rgba(255,255,255,0.8); padding: 1rem 2rem; display: flex; align-items: center; text-decoration: none; transition: all 0.3s ease; border: none; background: none; width: 100%; }
        .nav-link:hover, .nav-link.active { background: rgba(255,255,255,0.1); color: white; }
        .nav-link i { margin-right: 0.75rem; width: 20px; }
        .content-area { margin-left: 280px; padding: 2rem; }
        .stats-card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
        .stats-number { font-size: 3rem; font-weight: bold; color: #2563eb; }
        .user-info { position: absolute; bottom: 2rem; left: 2rem; right: 2rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1); }
    </style>
</head>
<body>
    <nav class="sidebar">
        <div class="sidebar-header">
            <h3><i class="fas fa-calendar-alt me-2"></i>Sports Schedulers</h3>
            <p class="mb-0 text-light">JES Baseball LLC</p>
        </div>
        
        <div class="sidebar-nav">
            <button class="nav-link active" onclick="showSection('dashboard')">
                <i class="fas fa-tachometer-alt"></i>Dashboard
            </button>
        </div>
        
        <div class="user-info">
            <div class="d-flex align-items-center">
                <i class="fas fa-user-circle fa-2x me-3"></i>
                <div>
                    <div class="fw-bold">{{ session.full_name or session.username }}</div>
                    <small class="text-light">{{ session.role.title() }}</small>
                </div>
            </div>
            <div class="mt-2">
                <a href="/logout" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-sign-out-alt me-1"></i>Logout
                </a>
            </div>
        </div>
    </nav>

    <main class="content-area">
        <div class="page-header mb-4">
            <h2><i class="fas fa-tachometer-alt me-2"></i>Dashboard Overview</h2>
            <p class="text-muted">Welcome to Sports Schedulers - JES Baseball LLC</p>
        </div>

        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <div class="stats-number" id="stats-games">0</div>
                    <h6 class="text-muted">Upcoming Games</h6>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <div class="stats-number" id="stats-officials">0</div>
                    <h6 class="text-muted">Active Officials</h6>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <div class="stats-number" id="stats-assignments">0</div>
                    <h6 class="text-muted">Total Assignments</h6>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <div class="stats-number" id="stats-leagues">0</div>
                    <h6 class="text-muted">Active Leagues</h6>
                </div>
            </div>
        </div>

        <div class="alert alert-success">
            <i class="fas fa-check-circle me-2"></i>
            <strong>Success!</strong> Sports Schedulers is now live on sportsschedulers.com for JES Baseball LLC
        </div>
    </main>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('stats-games').textContent = data.upcoming_games || 0;
                    document.getElementById('stats-officials').textContent = data.active_officials || 0;
                    document.getElementById('stats-assignments').textContent = data.total_assignments || 0;
                    document.getElementById('stats-leagues').textContent = data.active_leagues || 0;
                }
            } catch (error) {
                console.error('Dashboard error:', error);
            }
        }

        function showSection(section) {
            if (section === 'dashboard') {
                loadDashboard();
            }
        }

        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>'''

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML)
    
    try:
        data = request.get_json() or request.form
        username = data.get('username', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, password, full_name, email, role, is_active
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        
        user = cursor.fetchone()
        
        if user and verify_password(user['password'], password):
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                         (datetime.now().isoformat(), user['id']))
            conn.commit()
            
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            conn.close()
            app.logger.info(f"Successful login: {username}")
            return jsonify({'success': True, 'redirect': '/dashboard'})
        else:
            conn.close()
            app.logger.warning(f"Failed login attempt: {username}")
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Authentication service unavailable'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML, session=session)

@app.route('/api/dashboard')
@login_required
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE date >= date('now')")
        upcoming_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM officials WHERE is_active = 1")
        active_officials = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assignments")
        total_assignments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leagues WHERE is_active = 1")
        active_leagues = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'upcoming_games': upcoming_games,
            'active_officials': active_officials,
            'total_assignments': total_assignments,
            'active_leagues': active_leagues
        })
        
    except Exception as e:
        app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

@app.route('/health')
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'company': 'JES Baseball LLC'
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

try:
    init_database()
except Exception as e:
    app.logger.error(f"Failed to initialize database: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Starting Sports Schedulers Light v1.0.0 for JES Baseball LLC")
    app.logger.info(f"Server will run on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
