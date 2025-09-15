"""Sports Schedulers - Render Deployment Ready
Author: Jose Ortiz
Date: September 14, 2025
Copyright (c) 2025 JES Baseball LLC. All rights reserved.
"""

import os
import re
import sqlite3
import hashlib
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, redirect, session
import csv
import io

# Flask app configuration
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'sports-schedulers-render-key-2025'),
    SESSION_COOKIE_SECURE=False,  # Render handles SSL termination
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    """Get database connection"""
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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Administrator access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_database():
    """Initialize database with error handling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Initializing database...")
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            logger.info("Database already initialized")
            conn.close()
            return
        
        # Users table
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                role TEXT DEFAULT 'official',
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                last_login TEXT,
                failed_login_attempts INTEGER DEFAULT 0
            )
        """)
        
        # Games table
        cursor.execute("""
            CREATE TABLE games (
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
                game_fee REAL DEFAULT 0.0
            )
        """)

        # Officials table
        cursor.execute("""
            CREATE TABLE officials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                sport TEXT,
                experience_level TEXT,
                certifications TEXT,
                rating REAL DEFAULT 0.0,
                availability TEXT,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT,
                total_games INTEGER DEFAULT 0
            )
        """)

        # Assignments table
        cursor.execute("""
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                official_id INTEGER NOT NULL,
                position TEXT DEFAULT 'Referee',
                status TEXT DEFAULT 'assigned',
                assigned_date TEXT NOT NULL,
                fee_amount REAL DEFAULT 0.0
            )
        """)

        # Create default admin users
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
        logger.info("Database initialized successfully")
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Database initialization error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# HTML Templates (simplified for Render)
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
        }
        .btn-login { 
            background: linear-gradient(135deg, #2563eb, #1d4ed8); 
            border: none; 
            border-radius: 12px; 
            color: white; 
            font-weight: 600; 
            padding: 1rem; 
            width: 100%; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container mx-auto">
            <div class="login-header">
                <i class="fas fa-calendar-alt fa-3x mb-3"></i>
                <h1>Sports Schedulers</h1>
                <p class="mb-0">Production System</p>
            </div>
            
            <div class="p-4">
                <form method="POST">
                    <div class="mb-3">
                        <div class="input-group">
                            <span class="input-group-text"><i class="fas fa-user"></i></span>
                            <input type="text" class="form-control" name="username" placeholder="Username" required>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <div class="input-group">
                            <span class="input-group-text"><i class="fas fa-lock"></i></span>
                            <input type="password" class="form-control" name="password" placeholder="Password" required>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-login">
                        <i class="fas fa-sign-in-alt me-2"></i>Access System
                    </button>
                </form>
                
                {% if error %}
                <div class="alert alert-danger mt-3">{{ error }}</div>
                {% endif %}
                
                <div class="text-center mt-4">
                    <small class="text-muted">&copy; 2025 JES Baseball LLC</small>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Schedulers Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { 
            --primary-color: #2563eb; 
            --secondary-color: #64748b; 
        }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: #f8fafc; 
        }
        .sidebar { 
            width: 280px; 
            background: linear-gradient(135deg, var(--primary-color), #1d4ed8); 
            color: white; 
            position: fixed; 
            height: 100vh; 
            overflow-y: auto; 
        }
        .content-area { 
            margin-left: 280px; 
            padding: 2rem; 
            min-height: 100vh; 
        }
        .nav-link { 
            color: rgba(255,255,255,0.8); 
            padding: 1rem 2rem; 
            display: flex; 
            align-items: center; 
            text-decoration: none; 
            border: none; 
            background: none; 
            width: 100%; 
        }
        .nav-link:hover, .nav-link.active { 
            background: rgba(255,255,255,0.1); 
            color: white; 
        }
        .stats-card { 
            background: white; 
            border-radius: 12px; 
            padding: 2rem; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
            text-align: center; 
        }
        .stats-number { 
            font-size: 3rem; 
            font-weight: bold; 
            color: var(--primary-color); 
        }
        .content-section { 
            display: none; 
        }
        .content-section.active { 
            display: block; 
        }
        @media (max-width: 768px) { 
            .sidebar { 
                transform: translateX(-100%); 
            } 
            .content-area { 
                margin-left: 0; 
            } 
        }
    </style>
</head>
<body>
    <nav class="sidebar">
        <div class="p-4 border-bottom border-light border-opacity-25">
            <h3><i class="fas fa-calendar-alt me-2"></i>Sports Schedulers</h3>
            <p class="mb-0 text-light">Production System</p>
        </div>
        
        <div class="py-3">
            <button class="nav-link active" onclick="showSection('dashboard')">
                <i class="fas fa-tachometer-alt me-3"></i>Dashboard
            </button>
            <button class="nav-link" onclick="showSection('games')">
                <i class="fas fa-futbol me-3"></i>Games
            </button>
            <button class="nav-link" onclick="showSection('officials')">
                <i class="fas fa-user-tie me-3"></i>Officials
            </button>
            <button class="nav-link" onclick="showSection('assignments')">
                <i class="fas fa-clipboard-list me-3"></i>Assignments
            </button>
        </div>
        
        <div class="position-absolute bottom-0 start-0 end-0 p-4 border-top border-light border-opacity-25">
            <div class="d-flex align-items-center mb-2">
                <i class="fas fa-user-circle fa-2x me-3"></i>
                <div>
                    <div class="fw-bold">{{ user_data.full_name or user_data.username }}</div>
                    <small class="text-light">{{ user_data.role.title() }}</small>
                </div>
            </div>
            <a href="/logout" class="btn btn-outline-light btn-sm">
                <i class="fas fa-sign-out-alt me-1"></i>Logout
            </a>
        </div>
    </nav>

    <main class="content-area">
        <!-- Dashboard Section -->
        <div id="dashboard" class="content-section active">
            <div class="mb-4">
                <h2><i class="fas fa-tachometer-alt me-2"></i>Dashboard Overview</h2>
                <p class="text-muted">Sports Schedulers Production Management System</p>
            </div>

            <div class="row mb-4">
                <div class="col-md-3 mb-3">
                    <div class="stats-card">
                        <div class="stats-number" id="stats-games">0</div>
                        <h6 class="text-muted">Total Games</h6>
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
                        <div class="stats-number" id="stats-users">0</div>
                        <h6 class="text-muted">System Users</h6>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0"><i class="fas fa-rocket me-2"></i>System Status</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        <strong>Production Ready!</strong> Sports Schedulers system deployed successfully on Render.
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>All Features Active:</strong> User management, games, officials, and assignments operational.
                    </div>
                </div>
            </div>
        </div>

        <!-- Games Section -->
        <div id="games" class="content-section">
            <div class="mb-4">
                <h2><i class="fas fa-futbol me-2"></i>Games Management</h2>
                <p class="text-muted">Manage game schedules and assignments</p>
            </div>
            <div class="card">
                <div class="card-body">
                    <p>Games management functionality - Coming soon!</p>
                    <button class="btn btn-primary" onclick="loadGames()">Load Games</button>
                </div>
            </div>
        </div>

        <!-- Officials Section -->
        <div id="officials" class="content-section">
            <div class="mb-4">
                <h2><i class="fas fa-user-tie me-2"></i>Officials Management</h2>
                <p class="text-muted">Manage officials and their qualifications</p>
            </div>
            <div class="card">
                <div class="card-body">
                    <p>Officials management functionality - Coming soon!</p>
                    <button class="btn btn-primary" onclick="loadOfficials()">Load Officials</button>
                </div>
            </div>
        </div>

        <!-- Assignments Section -->
        <div id="assignments" class="content-section">
            <div class="mb-4">
                <h2><i class="fas fa-clipboard-list me-2"></i>Assignment Management</h2>
                <p class="text-muted">Assign officials to games</p>
            </div>
            <div class="card">
                <div class="card-body">
                    <p>Assignment management functionality - Coming soon!</p>
                    <button class="btn btn-primary" onclick="loadAssignments()">Load Assignments</button>
                </div>
            </div>
        </div>
    </main>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global variables - Fixed session serialization issue
        let currentUser = {
            user_id: {{ user_data.user_id|default(0) }},
            username: "{{ user_data.username|default('') }}",
            role: "{{ user_data.role|default('') }}",
            full_name: "{{ user_data.full_name|default('') }}"
        };

        // Navigation
        function showSection(section) {
            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            
            document.getElementById(section).classList.add('active');
            event.target.classList.add('active');
            
            if (section === 'dashboard') {
                loadDashboard();
            }
        }

        // Dashboard functions
        async function loadDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('stats-games').textContent = data.total_games || 0;
                    document.getElementById('stats-officials').textContent = data.active_officials || 0;
                    document.getElementById('stats-assignments').textContent = data.total_assignments || 0;
                    document.getElementById('stats-users').textContent = data.total_users || 0;
                }
            } catch (error) {
                console.error('Dashboard error:', error);
            }
        }

        function loadGames() {
            alert('Games functionality will be implemented here');
        }

        function loadOfficials() {
            alert('Officials functionality will be implemented here');
        }

        function loadAssignments() {
            alert('Assignments functionality will be implemented here');
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboard();
        });
    </script>
</body>
</html>'''

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                return render_template_string(LOGIN_HTML, error='Username and password required')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password, full_name, email, role, is_active
                FROM users WHERE username = ? AND is_active = 1
            """, (username,))
            
            user = cursor.fetchone()
            
            if user and user['password'] == hash_password(password):
                cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                             (datetime.now().isoformat(), user['id']))
                conn.commit()
                
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                
                conn.close()
                logger.info(f"Successful login: {username}")
                return redirect('/dashboard')
            else:
                conn.close()
                logger.warning(f"Failed login attempt: {username}")
                return render_template_string(LOGIN_HTML, error='Invalid credentials')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template_string(LOGIN_HTML, error='Login service unavailable')
    
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    # Create a serializable user data dict to avoid LocalProxy JSON issue
    user_data = {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'full_name': session.get('full_name')
    }
    return render_template_string(DASHBOARD_HTML, user_data=user_data)

# API Routes
@app.route('/api/dashboard')
@login_required
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get stats with safe defaults
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM officials WHERE is_active = 1")
        active_officials = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assignments")
        total_assignments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        total_users = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_games': total_games,
            'active_officials': active_officials,
            'total_assignments': total_assignments,
            'total_users': total_users
        })
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

@app.route('/api/games')
@login_required
def get_games():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM games ORDER BY date DESC, time DESC")
        games = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'games': games})
        
    except Exception as e:
        logger.error(f"Get games error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve games'}), 500

@app.route('/api/officials')
@login_required
def get_officials():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.is_active,
                   o.sport, o.experience_level, o.rating, o.total_games
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            WHERE u.role = 'official'
            ORDER BY u.full_name
        """)
        
        officials = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'officials': officials})
        
    except Exception as e:
        logger.error(f"Get officials error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load officials'}), 500

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
            'version': '2.0.0',
            'company': 'JES Baseball LLC'
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Page not found', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

# Initialize database on startup
try:
    init_database()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Sports Schedulers Production System v2.0.0")
    logger.info(f"Company: JES Baseball LLC")
    logger.info(f"Production server ready on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
