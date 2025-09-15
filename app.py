"""Sports Schedulers Light - Clean Working Version
Author: Jose Ortiz
Date: September 14, 2025
Company: JES Baseball LLC"""

import os
import re
import secrets
import logging
import csv
import io
from flask import Flask, render_template_string, request, jsonify, redirect, session, make_response
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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
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
        .table-responsive { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .btn-custom { border-radius: 8px; padding: 0.5rem 1rem; }
        .modal-content { border-radius: 12px; }
        .form-control { border-radius: 8px; }
    </style>
</head>
<body>
    <nav class="sidebar">
        <div class="sidebar-header">
            <h3><i class="fas fa-calendar-alt me-2"></i>Sports Schedulers</h3>
            <p class="mb-0 text-light">JES Baseball LLC</p>
        </div>
        
        <div class="sidebar-nav">
            <button class="nav-link active" onclick="showSection('dashboard')" data-section="dashboard">
                <i class="fas fa-tachometer-alt"></i>Dashboard
            </button>
            <button class="nav-link" onclick="showSection('games')" data-section="games">
                <i class="fas fa-football-ball"></i>Games
            </button>
            <button class="nav-link" onclick="showSection('officials')" data-section="officials">
                <i class="fas fa-users"></i>Officials
            </button>
            <button class="nav-link" onclick="showSection('assignments')" data-section="assignments">
                <i class="fas fa-clipboard-list"></i>Assignments
            </button>
            <button class="nav-link" onclick="showSection('users')" data-section="users">
                <i class="fas fa-user-cog"></i>Users
            </button>
            <button class="nav-link" onclick="showSection('leagues')" data-section="leagues">
                <i class="fas fa-trophy"></i>Leagues
            </button>
            <button class="nav-link" onclick="showSection('reports')" data-section="reports">
                <i class="fas fa-chart-bar"></i>Reports
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
        <div id="main-content">
            <!-- Dashboard Section -->
            <div id="dashboard-section" class="content-section">
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
            </div>

            <!-- Games Section -->
            <div id="games-section" class="content-section" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2><i class="fas fa-football-ball me-2"></i>Games Management</h2>
                        <p class="text-muted">Manage all games and schedules</p>
                    </div>
                    <div>
                        <button class="btn btn-success btn-custom me-2" onclick="exportGames()">
                            <i class="fas fa-download me-1"></i>Export CSV
                        </button>
                        <button class="btn btn-primary btn-custom" onclick="showAddGameModal()">
                            <i class="fas fa-plus me-1"></i>Add Game
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Teams</th>
                                <th>Sport</th>
                                <th>Location</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="games-table-body">
                            <tr>
                                <td colspan="7" class="text-center">Loading games...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Officials Section -->
            <div id="officials-section" class="content-section" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2><i class="fas fa-users me-2"></i>Officials Management</h2>
                        <p class="text-muted">Manage officials and their information</p>
                    </div>
                    <div>
                        <button class="btn btn-success btn-custom me-2" onclick="exportOfficials()">
                            <i class="fas fa-download me-1"></i>Export CSV
                        </button>
                        <button class="btn btn-primary btn-custom" onclick="showAddOfficialModal()">
                            <i class="fas fa-plus me-1"></i>Add Official
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Experience</th>
                                <th>Rating</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="officials-table-body">
                            <tr>
                                <td colspan="7" class="text-center">Loading officials...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Assignments Section -->
            <div id="assignments-section" class="content-section" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2><i class="fas fa-clipboard-list me-2"></i>Assignments Management</h2>
                        <p class="text-muted">Assign officials to games</p>
                    </div>
                    <button class="btn btn-primary btn-custom" onclick="showAddAssignmentModal()">
                        <i class="fas fa-plus me-1"></i>Create Assignment
                    </button>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Game</th>
                                <th>Date</th>
                                <th>Official</th>
                                <th>Position</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="assignments-table-body">
                            <tr>
                                <td colspan="6" class="text-center">Loading assignments...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Users Section -->
            <div id="users-section" class="content-section" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2><i class="fas fa-user-cog me-2"></i>Users Management</h2>
                        <p class="text-muted">Manage system users and permissions</p>
                    </div>
                    <button class="btn btn-primary btn-custom" onclick="showAddUserModal()">
                        <i class="fas fa-plus me-1"></i>Add User
                    </button>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Username</th>
                                <th>Full Name</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Status</th>
                                <th>Last Login</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body">
                            <tr>
                                <td colspan="7" class="text-center">Loading users...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Leagues Section -->
            <div id="leagues-section" class="content-section" style="display: none;">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h2><i class="fas fa-trophy me-2"></i>Leagues Management</h2>
                        <p class="text-muted">Manage leagues and competition levels</p>
                    </div>
                    <button class="btn btn-primary btn-custom" onclick="showAddLeagueModal()">
                        <i class="fas fa-plus me-1"></i>Add League
                    </button>
                </div>

                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>League Name</th>
                                <th>Sport</th>
                                <th>Season</th>
                                <th>Levels</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="leagues-table-body">
                            <tr>
                                <td colspan="6" class="text-center">Loading leagues...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Reports Section -->
            <div id="reports-section" class="content-section" style="display: none;">
                <div class="page-header mb-4">
                    <h2><i class="fas fa-chart-bar me-2"></i>Reports & Analytics</h2>
                    <p class="text-muted">Export data and view system statistics</p>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-download me-2"></i>Data Export</h5>
                            </div>
                            <div class="card-body">
                                <div class="d-grid gap-2">
                                    <button class="btn btn-outline-primary" onclick="exportGames()">
                                        <i class="fas fa-football-ball me-2"></i>Export Games
                                    </button>
                                    <button class="btn btn-outline-success" onclick="exportOfficials()">
                                        <i class="fas fa-users me-2"></i>Export Officials
                                    </button>
                                    <button class="btn btn-outline-info" onclick="exportAssignments()">
                                        <i class="fas fa-clipboard-list me-2"></i>Export Assignments
                                    </button>
                                    <button class="btn btn-outline-warning" onclick="exportUsers()">
                                        <i class="fas fa-user-cog me-2"></i>Export Users
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-chart-pie me-2"></i>Quick Stats</h5>
                            </div>
                            <div class="card-body">
                                <div class="row text-center">
                                    <div class="col-6 mb-3">
                                        <h4 class="text-primary" id="report-games">0</h4>
                                        <small>Total Games</small>
                                    </div>
                                    <div class="col-6 mb-3">
                                        <h4 class="text-success" id="report-officials">0</h4>
                                        <small>Officials</small>
                                    </div>
                                    <div class="col-6">
                                        <h4 class="text-info" id="report-assignments">0</h4>
                                        <small>Assignments</small>
                                    </div>
                                    <div class="col-6">
                                        <h4 class="text-warning" id="report-leagues">0</h4>
                                        <small>Leagues</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Add Game Modal -->
    <div class="modal fade" id="addGameModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Add New Game</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="addGameForm">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Date</label>
                                <input type="date" class="form-control" name="date" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Time</label>
                                <input type="time" class="form-control" name="time" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Home Team</label>
                                <input type="text" class="form-control" name="home_team" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Away Team</label>
                                <input type="text" class="form-control" name="away_team" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Sport</label>
                                <select class="form-control" name="sport" required>
                                    <option value="">Select Sport</option>
                                    <option value="Baseball">Baseball</option>
                                    <option value="Basketball">Basketball</option>
                                    <option value="Football">Football</option>
                                    <option value="Soccer">Soccer</option>
                                    <option value="Softball">Softball</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Location</label>
                                <input type="text" class="form-control" name="location">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">League</label>
                                <input type="text" class="form-control" name="league">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Level</label>
                                <input type="text" class="form-control" name="level">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" name="notes" rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="addGame()">Add Game</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/js/bootstrap.bundle.min.js"></script>
    <script>
        // Navigation
        function showSection(sectionName) {
            // Hide all sections
            document.querySelectorAll('.content-section').forEach(section => {
                section.style.display = 'none';
            });
            
            // Remove active class from all nav links
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            
            // Show selected section
            document.getElementById(sectionName + '-section').style.display = 'block';
            
            // Add active class to clicked nav link
            document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');
            
            // Load section data
            loadSectionData(sectionName);
        }

        function loadSectionData(section) {
            switch(section) {
                case 'dashboard':
                    loadDashboard();
                    break;
                case 'games':
                    loadGames();
                    break;
                case 'officials':
                    loadOfficials();
                    break;
                case 'assignments':
                    loadAssignments();
                    break;
                case 'users':
                    loadUsers();
                    break;
                case 'leagues':
                    loadLeagues();
                    break;
                case 'reports':
                    loadReports();
                    break;
            }
        }

        // Dashboard
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

        // Games
        async function loadGames() {
            try {
                const response = await fetch('/api/games');
                const data = await response.json();
                const tbody = document.getElementById('games-table-body');
                
                if (data.success && data.games) {
                    tbody.innerHTML = '';
                    data.games.forEach(game => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${game.date}</td>
                                <td>${game.time}</td>
                                <td><strong>${game.home_team}</strong> vs ${game.away_team}</td>
                                <td>${game.sport}</td>
                                <td>${game.location || 'TBD'}</td>
                                <td><span class="badge bg-success">${game.status}</span></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editGame(${game.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteGame(${game.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No games found</td></tr>';
                }
            } catch (error) {
                console.error('Games loading error:', error);
            }
        }

        // Officials
        async function loadOfficials() {
            try {
                const response = await fetch('/api/officials');
                const data = await response.json();
                const tbody = document.getElementById('officials-table-body');
                
                if (data.success && data.officials) {
                    tbody.innerHTML = '';
                    data.officials.forEach(official => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${official.full_name || official.username}</td>
                                <td>${official.email || 'N/A'}</td>
                                <td>${official.phone || 'N/A'}</td>
                                <td>${official.experience_level || 'N/A'}</td>
                                <td>${official.rating || 0}/5</td>
                                <td><span class="badge bg-${official.is_active ? 'success' : 'secondary'}">${official.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editOfficial(${official.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteOfficial(${official.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No officials found</td></tr>';
                }
            } catch (error) {
                console.error('Officials loading error:', error);
            }
        }

        // Assignments
        async function loadAssignments() {
            try {
                const response = await fetch('/api/assignments');
                const data = await response.json();
                const tbody = document.getElementById('assignments-table-body');
                
                if (data.success && data.assignments) {
                    tbody.innerHTML = '';
                    data.assignments.forEach(assignment => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${assignment.home_team} vs ${assignment.away_team}</td>
                                <td>${assignment.date}</td>
                                <td>${assignment.official_name}</td>
                                <td>${assignment.position}</td>
                                <td><span class="badge bg-info">${assignment.status}</span></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteAssignment(${assignment.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No assignments found</td></tr>';
                }
            } catch (error) {
                console.error('Assignments loading error:', error);
            }
        }

        // Users
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                const tbody = document.getElementById('users-table-body');
                
                if (data.success && data.users) {
                    tbody.innerHTML = '';
                    data.users.forEach(user => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${user.username}</td>
                                <td>${user.full_name}</td>
                                <td>${user.email}</td>
                                <td><span class="badge bg-primary">${user.role}</span></td>
                                <td><span class="badge bg-${user.is_active ? 'success' : 'secondary'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editUser(${user.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No users found</td></tr>';
                }
            } catch (error) {
                console.error('Users loading error:', error);
            }
        }

        // Leagues
        async function loadLeagues() {
            try {
                const response = await fetch('/api/leagues');
                const data = await response.json();
                const tbody = document.getElementById('leagues-table-body');
                
                if (data.success && data.leagues) {
                    tbody.innerHTML = '';
                    data.leagues.forEach(league => {
                        tbody.innerHTML += `
                            <tr>
                                <td>${league.name}</td>
                                <td>${league.sport}</td>
                                <td>${league.season}</td>
                                <td>${league.levels || 'N/A'}</td>
                                <td><span class="badge bg-${league.is_active ? 'success' : 'secondary'}">${league.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editLeague(${league.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteLeague(${league.id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No leagues found</td></tr>';
                }
            } catch (error) {
                console.error('Leagues loading error:', error);
            }
        }

        // Reports
        async function loadReports() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('report-games').textContent = data.upcoming_games || 0;
                    document.getElementById('report-officials').textContent = data.active_officials || 0;
                    document.getElementById('report-assignments').textContent = data.total_assignments || 0;
                    document.getElementById('report-leagues').textContent = data.active_leagues || 0;
                }
            } catch (error) {
                console.error('Reports loading error:', error);
            }
        }

        // Modal functions
        function showAddGameModal() {
            new bootstrap.Modal(document.getElementById('addGameModal')).show();
        }

        function showAddOfficialModal() {
            alert('Add Official modal will be implemented');
        }

        function showAddAssignmentModal() {
            alert('Add Assignment modal will be implemented');
        }

        function showAddUserModal() {
            alert('Add User modal will be implemented');
        }

        function showAddLeagueModal() {
            alert('Add League modal will be implemented');
        }

        // CRUD operations
        async function addGame() {
            const form = document.getElementById('addGameForm');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/api/games', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    bootstrap.Modal.getInstance(document.getElementById('addGameModal')).hide();
                    form.reset();
                    loadGames();
                    alert('Game added successfully!');
                } else {
                    alert('Error adding game');
                }
            } catch (error) {
                console.error('Add game error:', error);
                alert('Error adding game');
            }
        }

        async function deleteGame(id) {
            if (confirm('Are you sure you want to delete this game?')) {
                try {
                    const response = await fetch(`/api/games/${id}`, { method: 'DELETE' });
                    if (response.ok) {
                        loadGames();
                        alert('Game deleted successfully!');
                    } else {
                        alert('Error deleting game');
                    }
                } catch (error) {
                    console.error('Delete game error:', error);
                    alert('Error deleting game');
                }
            }
        }

        // Export functions
        function exportGames() {
            window.location.href = '/api/export/games';
        }

        function exportOfficials() {
            window.location.href = '/api/export/officials';
        }

        function exportAssignments() {
            window.location.href = '/api/export/assignments';
        }

        function exportUsers() {
            window.location.href = '/api/export/users';
        }

        // Edit functions (placeholders)
        function editGame(id) {
            alert('Edit Game functionality will be implemented');
        }

        function editOfficial(id) {
            alert('Edit Official functionality will be implemented');
        }

        function editUser(id) {
            alert('Edit User functionality will be implemented');
        }

        function editLeague(id) {
            alert('Edit League functionality will be implemented');
        }

        function deleteOfficial(id) {
            alert('Delete Official functionality will be implemented');
        }

        function deleteAssignment(id) {
            alert('Delete Assignment functionality will be implemented');
        }

        function deleteUser(id) {
            alert('Delete User functionality will be implemented');
        }

        function deleteLeague(id) {
            alert('Delete League functionality will be implemented');
        }

        // Initialize
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

# Games API
@app.route('/api/games', methods=['GET'])
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
        app.logger.error(f"Get games error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games', methods=['POST'])
@login_required
def create_game():
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO games (date, time, home_team, away_team, location, sport, league, level, notes, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['date'], data['time'], data['home_team'], data['away_team'],
            data.get('location', ''), data['sport'], data.get('league', ''),
            data.get('level', ''), data.get('notes', ''),
            datetime.now().isoformat(), session['user_id']
        ))
        
        game_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': game_id})
    except Exception as e:
        app.logger.error(f"Create game error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@login_required
def delete_game(game_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM assignments WHERE game_id = ?", (game_id,))
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Delete game error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Officials API
@app.route('/api/officials', methods=['GET'])
@login_required
def get_officials():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.is_active,
                   o.experience_level, o.rating, o.certifications
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            WHERE u.is_active = 1
            ORDER BY u.full_name
        """)
        officials = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'officials': officials})
    except Exception as e:
        app.logger.error(f"Get officials error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Assignments API
@app.route('/api/assignments', methods=['GET'])
@login_required
def get_assignments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.position, a.status, g.date, g.home_team, g.away_team,
                   u.full_name as official_name
            FROM assignments a
            JOIN games g ON a.game_id = g.id
            JOIN users u ON a.official_id = u.id
            ORDER BY g.date DESC
        """)
        assignments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'assignments': assignments})
    except Exception as e:
        app.logger.error(f"Get assignments error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Users API
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, full_name, email, phone, role, is_active, last_login
            FROM users
            ORDER BY full_name
        """)
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        app.logger.error(f"Get users error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Leagues API
@app.route('/api/leagues', methods=['GET'])
@login_required
def get_leagues():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leagues WHERE is_active = 1 ORDER BY name")
        leagues = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'leagues': leagues})
    except Exception as e:
        app.logger.error(f"Get leagues error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Export APIs
@app.route('/api/export/games')
@login_required
def export_games():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games ORDER BY date DESC")
        games = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Username', 'Full Name', 'Email', 'Phone', 'Role', 'Status', 'Created Date', 'Last Login'])
        
        for user in users:
            writer.writerow([
                user['username'], user['full_name'] or '', user['email'] or '',
                user['phone'] or '', user['role'], user['status'],
                user['created_date'], user['last_login'] or 'Never'
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=users_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
    except Exception as e:
        app.logger.error(f"Export users error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)IO()
        writer = csv.writer(output)
        
        writer.writerow(['Date', 'Time', 'Home Team', 'Away Team', 'Sport', 'Location', 'League', 'Level', 'Notes'])
        
        for game in games:
            writer.writerow([
                game['date'], game['time'], game['home_team'], game['away_team'],
                game['sport'], game['location'] or '', game['league'] or '',
                game['level'] or '', game['notes'] or ''
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=games_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
    except Exception as e:
        app.logger.error(f"Export games error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/officials')
@login_required
def export_officials():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, u.full_name, u.email, u.phone, u.role,
                   o.experience_level, o.rating, o.certifications,
                   CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            ORDER BY u.full_name
        """)
        officials = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Username', 'Full Name', 'Email', 'Phone', 'Role', 'Experience', 'Rating', 'Certifications', 'Status'])
        
        for official in officials:
            writer.writerow([
                official['username'], official['full_name'] or '', official['email'] or '',
                official['phone'] or '', official['role'], official['experience_level'] or '',
                official['rating'] or 0, official['certifications'] or '', official['status']
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=officials_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
    except Exception as e:
        app.logger.error(f"Export officials error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/assignments')
@login_required
def export_assignments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.date, g.time, g.home_team, g.away_team, g.sport, g.location,
                   u.full_name as official_name, a.position, a.status
            FROM assignments a
            JOIN games g ON a.game_id = g.id
            JOIN users u ON a.official_id = u.id
            ORDER BY g.date DESC
        """)
        assignments = cursor.fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Date', 'Time', 'Home Team', 'Away Team', 'Sport', 'Location', 'Official', 'Position', 'Status'])
        
        for assignment in assignments:
            writer.writerow([
                assignment['date'], assignment['time'], assignment['home_team'],
                assignment['away_team'], assignment['sport'], assignment['location'] or '',
                assignment['official_name'], assignment['position'], assignment['status']
            ])
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=assignments_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
    except Exception as e:
        app.logger.error(f"Export assignments error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/users')
@login_required
def export_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, full_name, email, phone, role,
                   CASE WHEN is_active = 1 THEN 'Active' ELSE 'Inactive' END as status,
                   created_date, last_login
            FROM users
            ORDER BY full_name
        """)
        users = cursor.fetchall()
        conn.close()
        
        output = io.String
