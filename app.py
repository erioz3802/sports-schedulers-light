"""Sports Schedulers Light - Complete Web Application
Author: Jose Ortiz
Date: September 14, 2025
Copyright (c) 2025 Jose Ortiz. All rights reserved.

Simplified sports scheduling management system with basic functionalities."""

import re
import os
import csv
import io
from flask import Flask, make_response, render_template, render_template_string, request, jsonify, redirect, session
import sqlite3
import hashlib
import logging
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sports-schedulers-light-secret-key-2025-jose-ortiz'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect('scheduler.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Login required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Require admin role for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Login required'}), 401
        if session.get('role') not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_database():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            full_name TEXT,
            email TEXT,
            phone TEXT,
            created_date TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Games table
    cursor.execute('''
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
            created_by INTEGER REFERENCES users(id)
        )
    ''')
    
    # Officials table (simplified - uses users as officials)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS officials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            certifications TEXT,
            experience_level TEXT,
            availability TEXT,
            rating REAL DEFAULT 0.0,
            total_games INTEGER DEFAULT 0,
            created_date TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Assignments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            official_id INTEGER NOT NULL,
            position TEXT DEFAULT 'Official',
            status TEXT DEFAULT 'assigned',
            assigned_date TEXT NOT NULL,
            assigned_by INTEGER REFERENCES users(id),
            notes TEXT,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            FOREIGN KEY (official_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(game_id, official_id)
        )
    ''')
    
    # Leagues table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            sport TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_date TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id)
        )
    ''')
    
    # League levels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS league_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            level_name TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_date TEXT NOT NULL,
            FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE
        )
    ''')
    
    # Insert default admin user if doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, role, full_name, email, created_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', hash_password('admin123'), 'superadmin', 'System Administrator', 
              'admin@sportsschedulers.com', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

# ==================== LOGIN TEMPLATE ====================
LOGIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Schedulers Light - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
        }
        .login-container { 
            background: white; 
            padding: 40px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
            width: 400px; 
            max-width: 90%; 
        }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header h1 { color: #333; margin-bottom: 10px; font-size: 2rem; }
        .login-header p { color: #666; }
        .form-group { margin-bottom: 20px; }
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #333; 
        }
        .form-group input { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 16px; 
            transition: all 0.3s; 
        }
        .form-group input:focus { 
            outline: none; 
            border-color: #667eea; 
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); 
        }
        .login-btn { 
            width: 100%; 
            padding: 15px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            border: none; 
            border-radius: 8px; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s; 
        }
        .login-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3); 
        }
        .alert { 
            padding: 15px; 
            margin-bottom: 20px; 
            border-radius: 8px; 
            background: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
        }
        .test-credentials { 
            text-align: center; 
            margin-top: 25px; 
            padding: 20px; 
            background: #e3f2fd; 
            border-radius: 8px; 
            color: #1976d2; 
            font-size: 14px; 
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>Sports Schedulers Light</h1>
            <p>Simplified Sports Management System</p>
        </div>
        {% if error %}
            <div class="alert">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required autocomplete="current-password">
            </div>
            <button type="submit" class="login-btn">Login to System</button>
        </form>
        <div class="test-credentials">
            <strong>Default Login:</strong><br>
            Username: <code>admin</code><br>
            Password: <code>admin123</code>
        </div>
    </div>
</body>
</html>'''

# ==================== ROUTES ====================

@app.route('/')
def home():
    """Home route - redirect to login if not authenticated"""
    if 'user_id' not in session:
        return redirect('/login')
    
    try:
        return render_template('index.html')
    except:
        # Return inline template if index.html not found
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sports Schedulers Light</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        </head>
        <body>
            <div id="app">
                <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
                    <div class="container">
                        <a class="navbar-brand" href="#"><i class="fas fa-calendar-check me-2"></i>Sports Schedulers Light</a>
                        <div class="navbar-nav ms-auto">
                            <span class="navbar-text me-3">Welcome, {{session.full_name or session.username}}</span>
                            <a class="btn btn-outline-light btn-sm" href="/logout">Logout</a>
                        </div>
                    </div>
                </nav>
                
                <div class="container-fluid">
                    <div class="row">
                        <div class="col-md-2 bg-light vh-100">
                            <div class="list-group list-group-flush mt-3">
                                <a href="#" class="list-group-item list-group-item-action active" onclick="showSection('dashboard')">
                                    <i class="fas fa-tachometer-alt me-2"></i>Dashboard
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('games')">
                                    <i class="fas fa-football-ball me-2"></i>Games
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('officials')">
                                    <i class="fas fa-users me-2"></i>Officials
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('assignments')">
                                    <i class="fas fa-clipboard-list me-2"></i>Assignments
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('users')">
                                    <i class="fas fa-user-cog me-2"></i>Users
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('leagues')">
                                    <i class="fas fa-trophy me-2"></i>Leagues
                                </a>
                                <a href="#" class="list-group-item list-group-item-action" onclick="showSection('reports')">
                                    <i class="fas fa-chart-bar me-2"></i>Reports
                                </a>
                            </div>
                        </div>
                        
                        <div class="col-md-10">
                            <div class="container mt-4">
                                <div id="content">
                                    <h2>Loading...</h2>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                // Simple SPA functionality
                function showSection(section) {
                    document.querySelectorAll('.list-group-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    event.target.closest('.list-group-item').classList.add('active');
                    
                    const content = document.getElementById('content');
                    content.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Loading...</p></div>';
                    
                    // Load section content
                    if (section === 'dashboard') {
                        loadDashboard();
                    } else if (section === 'games') {
                        loadGames();
                    } else if (section === 'officials') {
                        loadOfficials();
                    } else if (section === 'assignments') {
                        loadAssignments();
                    } else if (section === 'users') {
                        loadUsers();
                    } else if (section === 'leagues') {
                        loadLeagues();
                    } else if (section === 'reports') {
                        loadReports();
                    }
                }
                
                async function loadDashboard() {
                    try {
                        const response = await fetch('/api/dashboard');
                        const data = await response.json();
                        
                        document.getElementById('content').innerHTML = `
                            <h2><i class="fas fa-tachometer-alt me-2"></i>Dashboard</h2>
                            <div class="row">
                                <div class="col-md-3">
                                    <div class="card bg-primary text-white">
                                        <div class="card-body">
                                            <h3>${data.stats?.total_games || 0}</h3>
                                            <p>Total Games</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-success text-white">
                                        <div class="card-body">
                                            <h3>${data.stats?.total_officials || 0}</h3>
                                            <p>Officials</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-info text-white">
                                        <div class="card-body">
                                            <h3>${data.stats?.total_assignments || 0}</h3>
                                            <p>Assignments</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <div class="card bg-warning text-white">
                                        <div class="card-body">
                                            <h3>${data.stats?.total_leagues || 0}</h3>
                                            <p>Leagues</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="mt-4">
                                <h4>Welcome to Sports Schedulers Light!</h4>
                                <p>This is a simplified version with basic functionality for managing sports schedules, officials, and assignments.</p>
                            </div>
                        `;
                    } catch (error) {
                        document.getElementById('content').innerHTML = '<div class="alert alert-danger">Error loading dashboard</div>';
                    }
                }
                
                async function loadGames() {
                    try {
                        const response = await fetch('/api/games');
                        const data = await response.json();
                        
                        let gamesHTML = `
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h2><i class="fas fa-football-ball me-2"></i>Games Management</h2>
                                <div>
                                    <button class="btn btn-success me-2" onclick="exportGames()"><i class="fas fa-download me-1"></i>Export</button>
                                    <button class="btn btn-primary" onclick="showAddGameModal()"><i class="fas fa-plus me-1"></i>Add Game</button>
                                </div>
                            </div>
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
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
                                    <tbody>
                        `;
                        
                        if (data.success && data.games) {
                            data.games.forEach(game => {
                                gamesHTML += `
                                    <tr>
                                        <td>${game.date}</td>
                                        <td>${game.time}</td>
                                        <td>${game.home_team} vs ${game.away_team}</td>
                                        <td>${game.sport}</td>
                                        <td>${game.location || 'TBD'}</td>
                                        <td><span class="badge bg-success">${game.status}</span></td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary" onclick="editGame(${game.id})">Edit</button>
                                            <button class="btn btn-sm btn-outline-danger" onclick="deleteGame(${game.id})">Delete</button>
                                        </td>
                                    </tr>
                                `;
                            });
                        } else {
                            gamesHTML += '<tr><td colspan="7" class="text-center">No games found</td></tr>';
                        }
                        
                        gamesHTML += '</tbody></table></div>';
                        document.getElementById('content').innerHTML = gamesHTML;
                    } catch (error) {
                        document.getElementById('content').innerHTML = '<div class="alert alert-danger">Error loading games</div>';
                    }
                }
                
                async function loadOfficials() {
                    try {
                        const response = await fetch('/api/officials');
                        const data = await response.json();
                        
                        let officialsHTML = `
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h2><i class="fas fa-users me-2"></i>Officials Management</h2>
                                <div>
                                    <button class="btn btn-success me-2" onclick="exportOfficials()"><i class="fas fa-download me-1"></i>Export</button>
                                    <button class="btn btn-primary" onclick="showAddOfficialModal()"><i class="fas fa-plus me-1"></i>Add Official</button>
                                </div>
                            </div>
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
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
                                    <tbody>
                        `;
                        
                        if (data.success && data.officials) {
                            data.officials.forEach(official => {
                                officialsHTML += `
                                    <tr>
                                        <td>${official.full_name || official.username}</td>
                                        <td>${official.email || 'N/A'}</td>
                                        <td>${official.phone || 'N/A'}</td>
                                        <td>${official.experience_level || 'N/A'}</td>
                                        <td>${official.rating || 0}/5</td>
                                        <td><span class="badge bg-${official.is_active ? 'success' : 'secondary'}">${official.is_active ? 'Active' : 'Inactive'}</span></td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-primary" onclick="editOfficial(${official.id})">Edit</button>
                                            <button class="btn btn-sm btn-outline-danger" onclick="deleteOfficial(${official.id})">Delete</button>
                                        </td>
                                    </tr>
                                `;
                            });
                        } else {
                            officialsHTML += '<tr><td colspan="7" class="text-center">No officials found</td></tr>';
                        }
                        
                        officialsHTML += '</tbody></table></div>';
                        document.getElementById('content').innerHTML = officialsHTML;
                    } catch (error) {
                        document.getElementById('content').innerHTML = '<div class="alert alert-danger">Error loading officials</div>';
                    }
                }
                
                async function loadAssignments() {
                    document.getElementById('content').innerHTML = `
                        <h2><i class="fas fa-clipboard-list me-2"></i>Assignments Management</h2>
                        <p>Assignment functionality will be implemented here.</p>
                        <div class="alert alert-info">This section allows you to assign officials to games.</div>
                    `;
                }
                
                async function loadUsers() {
                    document.getElementById('content').innerHTML = `
                        <h2><i class="fas fa-user-cog me-2"></i>Users Management</h2>
                        <p>User management functionality will be implemented here.</p>
                        <div class="alert alert-info">This section allows you to manage system users.</div>
                    `;
                }
                
                async function loadLeagues() {
                    document.getElementById('content').innerHTML = `
                        <h2><i class="fas fa-trophy me-2"></i>Leagues Management</h2>
                        <p>League management functionality will be implemented here.</p>
                        <div class="alert alert-info">This section allows you to manage leagues and their levels.</div>
                    `;
                }
                
                async function loadReports() {
                    document.getElementById('content').innerHTML = `
                        <h2><i class="fas fa-chart-bar me-2"></i>Reports</h2>
                        <p>Basic reporting functionality will be implemented here.</p>
                        <div class="alert alert-info">This section provides basic reports and data export capabilities.</div>
                    `;
                }
                
                // Utility functions
                function exportGames() {
                    window.location.href = '/api/export/games';
                }
                
                function exportOfficials() {
                    window.location.href = '/api/export/officials';
                }
                
                function showAddGameModal() {
                    alert('Add Game modal will be implemented');
                }
                
                function editGame(id) {
                    alert('Edit Game functionality will be implemented');
                }
                
                function deleteGame(id) {
                    if (confirm('Are you sure you want to delete this game?')) {
                        fetch('/api/games/' + id, { method: 'DELETE' })
                            .then(() => loadGames());
                    }
                }
                
                // Load dashboard on page load
                document.addEventListener('DOMContentLoaded', function() {
                    loadDashboard();
                });
            </script>
        </body>
        </html>
        """, session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error='Please enter username and password')
        
        try:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT * FROM users WHERE username = ? AND is_active = 1', 
                (username,)
            ).fetchone()
            
            if user and user['password'] == hash_password(password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                
                # Update last login
                conn.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                           (datetime.now().isoformat(), user['id']))
                conn.commit()
                conn.close()
                return redirect('/')
            else:
                conn.close()
                return render_template_string(LOGIN_TEMPLATE, error='Invalid username or password')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template_string(LOGIN_TEMPLATE, error='Database error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    return redirect('/login')

# ==================== API ROUTES ====================

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    """Dashboard statistics API"""
    try:
        conn = get_db_connection()
        
        stats = {}
        
        # Get total games
        try:
            stats['total_games'] = conn.execute('SELECT COUNT(*) as count FROM games').fetchone()['count']
        except:
            stats['total_games'] = 0
            
        # Get total officials
        try:
            stats['total_officials'] = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1').fetchone()['count']
        except:
            stats['total_officials'] = 0
            
        # Get total assignments
        try:
            stats['total_assignments'] = conn.execute('SELECT COUNT(*) as count FROM assignments').fetchone()['count']
        except:
            stats['total_assignments'] = 0
            
        # Get total leagues
        try:
            stats['total_leagues'] = conn.execute('SELECT COUNT(*) as count FROM leagues WHERE is_active = 1').fetchone()['count']
        except:
            stats['total_leagues'] = 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games', methods=['GET'])
@login_required
def api_get_games():
    """Get all games"""
    try:
        conn = get_db_connection()
        games = conn.execute('SELECT * FROM games ORDER BY date DESC, time DESC').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'games': [dict(game) for game in games]
        })
        
    except Exception as e:
        logger.error(f"Games fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games', methods=['POST'])
@login_required
def api_create_game():
    """Create new game"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'time', 'home_team', 'away_team', 'sport']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO games (date, time, home_team, away_team, location, sport, league, level, 
                             officials_needed, notes, status, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['date'], data['time'], data['home_team'], data['away_team'],
            data.get('location', ''), data['sport'], data.get('league', ''),
            data.get('level', ''), data.get('officials_needed', 1),
            data.get('notes', ''), data.get('status', 'scheduled'),
            datetime.now().isoformat(), session.get('user_id')
        ))
        
        game_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': game_id, 'message': 'Game created successfully'})
        
    except Exception as e:
        logger.error(f"Game creation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@login_required
def api_delete_game(game_id):
    """Delete game"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete related assignments first
        cursor.execute("DELETE FROM assignments WHERE game_id = ?", (game_id,))
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Game deleted successfully'})
        
    except Exception as e:
        logger.error(f"Game deletion error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/officials', methods=['GET'])
@login_required
def api_get_officials():
    """Get all officials (users)"""
    try:
        conn = get_db_connection()
        officials = conn.execute('''
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.role, u.is_active,
                   o.experience_level, o.rating, o.total_games, o.certifications
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            WHERE u.is_active = 1
            ORDER BY u.full_name, u.username
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'officials': [dict(official) for official in officials]
        })
        
    except Exception as e:
        logger.error(f"Officials fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    """Get all users"""
    try:
        conn = get_db_connection()
        users = conn.execute('''
            SELECT id, username, full_name, email, phone, role, is_active, 
                   created_date, last_login
            FROM users 
            ORDER BY full_name, username
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'users': [dict(user) for user in users]
        })
        
    except Exception as e:
        logger.error(f"Users fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@admin_required
def api_create_user():
    """Create new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (username, password, role, full_name, email, phone, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['username'], hash_password(data['password']), 
            data.get('role', 'user'), data.get('full_name', ''),
            data.get('email', ''), data.get('phone', ''),
            datetime.now().isoformat()
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': user_id, 'message': 'User created successfully'})
        
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    except Exception as e:
        logger.error(f"User creation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/assignments', methods=['GET'])
@login_required
def api_get_assignments():
    """Get all assignments"""
    try:
        conn = get_db_connection()
        assignments = conn.execute('''
            SELECT a.id, a.position, a.status, a.assigned_date, a.notes,
                   g.date, g.time, g.home_team, g.away_team, g.sport, g.location,
                   u.full_name as official_name, u.username
            FROM assignments a
            JOIN games g ON a.game_id = g.id
            JOIN users u ON a.official_id = u.id
            ORDER BY g.date DESC, g.time DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'assignments': [dict(assignment) for assignment in assignments]
        })
        
    except Exception as e:
        logger.error(f"Assignments fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/leagues', methods=['GET'])
@login_required
def api_get_leagues():
    """Get all leagues"""
    try:
        conn = get_db_connection()
        leagues = conn.execute('''
            SELECT l.*, 
                   GROUP_CONCAT(ll.level_name) as levels
            FROM leagues l
            LEFT JOIN league_levels ll ON l.id = ll.league_id AND ll.is_active = 1
            WHERE l.is_active = 1
            GROUP BY l.id
            ORDER BY l.name
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'leagues': [dict(league) for league in leagues]
        })
        
    except Exception as e:
        logger.error(f"Leagues fetch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/leagues', methods=['POST'])
@admin_required
def api_create_league():
    """Create new league"""
    try:
        data = request.get_json()
        
        if not data.get('name') or not data.get('sport'):
            return jsonify({'success': False, 'error': 'Name and sport are required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO leagues (name, sport, description, created_date, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'], data['sport'], data.get('description', ''),
            datetime.now().isoformat(), session.get('user_id')
        ))
        
        league_id = cursor.lastrowid
        
        # Add levels if provided
        if data.get('levels'):
            for level in data['levels']:
                cursor.execute('''
                    INSERT INTO league_levels (league_id, level_name, description, created_date)
                    VALUES (?, ?, ?, ?)
                ''', (league_id, level.get('name', ''), level.get('description', ''),
                     datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': league_id, 'message': 'League created successfully'})
        
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'League name already exists'}), 400
    except Exception as e:
        logger.error(f"League creation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== EXPORT ROUTES ====================

@app.route('/api/export/games')
@login_required
def export_games():
    """Export games to CSV"""
    try:
        conn = get_db_connection()
        games = conn.execute('SELECT * FROM games ORDER BY date DESC').fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Date', 'Time', 'Home Team', 'Away Team', 'Sport', 
                        'Location', 'League', 'Level', 'Officials Needed', 'Status', 'Notes'])
        
        # Write data
        for game in games:
            writer.writerow([
                game['id'], game['date'], game['time'], game['home_team'], 
                game['away_team'], game['sport'], game['location'] or '',
                game['league'] or '', game['level'] or '', 
                game['officials_needed'], game['status'], game['notes'] or ''
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=games_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Games export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/officials')
@login_required
def export_officials():
    """Export officials to CSV"""
    try:
        conn = get_db_connection()
        officials = conn.execute('''
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.role,
                   o.experience_level, o.rating, o.total_games, o.certifications,
                   CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            ORDER BY u.full_name, u.username
        ''').fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Phone', 'Role',
                        'Experience Level', 'Rating', 'Total Games', 'Certifications', 'Status'])
        
        # Write data
        for official in officials:
            writer.writerow([
                official['id'], official['username'], official['full_name'] or '',
                official['email'] or '', official['phone'] or '', official['role'],
                official['experience_level'] or '', official['rating'] or 0,
                official['total_games'] or 0, official['certifications'] or '',
                official['status']
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=officials_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Officials export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import/games', methods=['POST'])
@admin_required
def import_games():
    """Import games from CSV"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'File must be CSV format'}), 400
        
        # Read and process CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        for row in csv_input:
            try:
                cursor.execute('''
                    INSERT INTO games (date, time, home_team, away_team, location, sport, 
                                     league, level, officials_needed, notes, status, created_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('Date', ''), row.get('Time', ''), 
                    row.get('Home Team', ''), row.get('Away Team', ''),
                    row.get('Location', ''), row.get('Sport', ''),
                    row.get('League', ''), row.get('Level', ''),
                    int(row.get('Officials Needed', 1)), row.get('Notes', ''),
                    row.get('Status', 'scheduled'), datetime.now().isoformat(),
                    session.get('user_id')
                ))
                imported_count += 1
            except Exception as e:
                logger.warning(f"Error importing row: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully imported {imported_count} games'
        })
        
    except Exception as e:
        logger.error(f"Import error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import/officials', methods=['POST'])
@admin_required
def import_officials():
    """Import officials from CSV"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'File must be CSV format'}), 400
        
        # Read and process CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        for row in csv_input:
            try:
                # Create user first
                cursor.execute('''
                    INSERT INTO users (username, password, role, full_name, email, phone, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('Username', ''), hash_password(row.get('Password', 'default123')),
                    row.get('Role', 'user'), row.get('Full Name', ''),
                    row.get('Email', ''), row.get('Phone', ''),
                    datetime.now().isoformat()
                ))
                
                user_id = cursor.lastrowid
                
                # Create official record
                cursor.execute('''
                    INSERT INTO officials (user_id, experience_level, rating, total_games, 
                                         certifications, created_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, row.get('Experience Level', ''),
                    float(row.get('Rating', 0)), int(row.get('Total Games', 0)),
                    row.get('Certifications', ''), datetime.now().isoformat()
                ))
                
                imported_count += 1
            except Exception as e:
                logger.warning(f"Error importing official: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully imported {imported_count} officials'
        })
        
    except Exception as e:
        logger.error(f"Import error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    print("🏀 Starting Sports Schedulers Light...")
    print("📅 Copyright (c) 2025 JES Baseball LLC. All rights reserved.")
    
    # Initialize database
    init_database()
    
    print("✅ Server starting on http://localhost:5000")
    print("🚀 Sports Schedulers Light ready!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
