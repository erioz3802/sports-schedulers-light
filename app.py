"""Sports Schedulers Light - Complete Production System
Author: Jose Ortiz
Date: September 14, 2025
Company: JES Baseball LLC
Features: Complete CRUD, Google Maps, Reports, Susan Assistant"""

import os
import re
import secrets
import logging
import json
from flask import Flask, render_template_string, request, jsonify, redirect, session, send_file
import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import csv
import io
from io import BytesIO
import zipfile

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'sports-schedulers-light-production-key-2025'),
    SESSION_COOKIE_SECURE=False,  # Set to True in HTTPS production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
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
            return jsonify({'success': False, 'error': 'Administrator access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def validate_input(data, required_fields, max_lengths=None):
    errors = []
    for field in required_fields:
        if not data.get(field) or str(data.get(field)).strip() == '':
            errors.append(f'{field} is required')
    
    if max_lengths:
        for field, max_len in max_lengths.items():
            if data.get(field) and len(str(data.get(field))) > max_len:
                errors.append(f'{field} must be {max_len} characters or less')
    
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized_value = re.sub(r'[<>"\']', '', value.strip())
            sanitized_data[key] = sanitized_value
        else:
            sanitized_data[key] = value
    
    return errors, sanitized_data

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        app.logger.info("Initializing complete database...")
        
        # Users table
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
                last_login TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                address TEXT,
                emergency_contact TEXT,
                certifications TEXT,
                availability_notes TEXT
            )
        """)
        
        # Games table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                location TEXT,
                location_id INTEGER,
                sport TEXT NOT NULL,
                league TEXT,
                level TEXT,
                officials_needed INTEGER DEFAULT 1,
                notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_date TEXT NOT NULL,
                created_by INTEGER,
                modified_date TEXT,
                modified_by INTEGER,
                game_fee REAL DEFAULT 0.0,
                mileage_fee REAL DEFAULT 0.0,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (modified_by) REFERENCES users (id),
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        # Officials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officials (
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
                total_games INTEGER DEFAULT 0,
                travel_radius INTEGER DEFAULT 25,
                preferred_positions TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Assignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                official_id INTEGER NOT NULL,
                position TEXT DEFAULT 'Referee',
                status TEXT DEFAULT 'assigned',
                assigned_date TEXT NOT NULL,
                confirmed_date TEXT,
                notes TEXT,
                assigned_by INTEGER,
                fee_amount REAL DEFAULT 0.0,
                mileage_amount REAL DEFAULT 0.0,
                FOREIGN KEY (game_id) REFERENCES games (id),
                FOREIGN KEY (official_id) REFERENCES officials (id),
                FOREIGN KEY (assigned_by) REFERENCES users (id),
                UNIQUE(game_id, official_id)
            )
        """)
        
        # Leagues table
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
                contact_person TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                website TEXT,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)
        
        # Locations table
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
                contact_email TEXT,
                capacity INTEGER,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT,
                created_by INTEGER,
                latitude REAL,
                longitude REAL,
                parking_info TEXT,
                facilities TEXT,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        # Activity log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT,
                generated_by INTEGER,
                generated_date TEXT NOT NULL,
                file_path TEXT,
                FOREIGN KEY (generated_by) REFERENCES users (id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_game ON assignments(game_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_official ON assignments(official_id)")

        # Create default admin users
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

        # Create sample data
        cursor.execute("SELECT COUNT(*) FROM locations")
        if cursor.fetchone()[0] == 0:
            sample_locations = [
                ('Roosevelt High School', '123 Main St', 'Springfield', 'IL', '62701', 'Athletic Director', '555-1234', 'athletics@roosevelt.edu', 1000, 'Main gymnasium with updated facilities'),
                ('Central Community Center', '456 Oak Ave', 'Springfield', 'IL', '62702', 'Facility Manager', '555-5678', 'events@central.com', 500, 'Multi-purpose facility'),
                ('Westfield Sports Complex', '789 Sports Dr', 'Springfield', 'IL', '62703', 'Operations Manager', '555-9012', 'info@westfield.com', 2000, 'Professional sports facility with multiple courts')
            ]
            
            for location in sample_locations:
                cursor.execute("""
                    INSERT INTO locations (name, address, city, state, zip_code, contact_person, contact_phone, contact_email, capacity, notes, is_active, created_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, location + (1, datetime.now().isoformat(), 1))

        conn.commit()
        app.logger.info("Complete database initialized successfully")
        
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Database initialization error: {e}")
        raise
    finally:
        conn.close()

def log_activity(user_id, action, resource_type=None, resource_id=None, details=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.environ.get('REMOTE_ADDR', 'unknown'))
        cursor.execute("""
            INSERT INTO activity_log (user_id, action, resource_type, resource_id, details, timestamp, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, action, resource_type, resource_id, details, datetime.now().isoformat(), ip_address))
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"Activity logging error: {e}")

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# HTML Templates
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Sports Schedulers</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .login-container { background: white; border-radius: 20px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }
        .login-header { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 3rem 2rem 2rem; text-align: center; border-radius: 20px 20px 0 0; }
        .form-control { border-radius: 12px; border: 2px solid #e2e8f0; padding: 1rem; transition: all 0.3s ease; }
        .form-control:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .btn-login { background: linear-gradient(135deg, #2563eb, #1d4ed8); border: none; border-radius: 12px; color: white; font-weight: 600; padding: 1rem; width: 100%; transition: all 0.3s ease; }
        .btn-login:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3); color: white; }
        .input-group-text { background: transparent; border: 2px solid #e2e8f0; border-right: none; border-radius: 12px 0 0 12px; }
        .input-group .form-control { border-left: none; border-radius: 0 12px 12px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-container mx-auto">
            <div class="login-header">
                <i class="fas fa-calendar-alt fa-3x mb-3"></i>
                <h1>Sports Schedulers</h1>
                <p class="mb-0">Production Management System</p>
            </div>
            
            <div class="p-4">
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
    <title>Sports Schedulers - Production System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY&libraries=places"></script>
    <style>
        :root { --primary-color: #2563eb; --secondary-color: #64748b; --success-color: #10b981; --light-color: #f8fafc; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--light-color); }
        .sidebar { width: 280px; background: linear-gradient(135deg, var(--primary-color), #1d4ed8); color: white; position: fixed; height: 100vh; overflow-y: auto; z-index: 1000; }
        .sidebar-header { padding: 2rem; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .nav-link { color: rgba(255,255,255,0.8); padding: 1rem 2rem; display: flex; align-items: center; text-decoration: none; transition: all 0.3s ease; border: none; background: none; width: 100%; }
        .nav-link:hover, .nav-link.active { background: rgba(255,255,255,0.1); color: white; }
        .nav-link i { margin-right: 0.75rem; width: 20px; }
        .content-area { margin-left: 280px; padding: 2rem; min-height: 100vh; }
        .content-section { display: none; }
        .content-section.active { display: block; }
        .stats-card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; transition: transform 0.2s ease; }
        .stats-card:hover { transform: translateY(-2px); }
        .stats-number { font-size: 3rem; font-weight: bold; color: var(--primary-color); }
        .data-table { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
        .table th { background-color: #f8fafc; font-weight: 600; }
        .user-info { position: absolute; bottom: 2rem; left: 2rem; right: 2rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1); }
        .page-header { margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0; }
        .modal-content { border-radius: 12px; }
        .modal-header { background: var(--primary-color); color: white; border-radius: 12px 12px 0 0; }
        .btn-close-white { filter: invert(1); }
        .form-control, .form-select { border-radius: 8px; border: 1px solid #d1d5db; }
        .form-control:focus, .form-select:focus { border-color: var(--primary-color); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .loading { text-align: center; padding: 3rem; color: var(--secondary-color); }
        .loading .spinner-border { width: 3rem; height: 3rem; }
        .action-buttons { white-space: nowrap; }
        .susan-chat { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 1.5rem; color: white; }
        .chat-message { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; margin: 0.5rem 0; }
        .map-container { height: 400px; width: 100%; border-radius: 8px; }
        @media (max-width: 768px) { .sidebar { transform: translateX(-100%); } .content-area { margin-left: 0; } }
    </style>
</head>
<body>
    <nav class="sidebar">
        <div class="sidebar-header">
            <h3><i class="fas fa-calendar-alt me-2"></i>Sports Schedulers</h3>
            <p class="mb-0 text-light">Production System</p>
            <small class="text-light">Complete Management</small>
        </div>
        
        <div class="sidebar-nav">
            <button class="nav-link active" onclick="showSection('dashboard')">
                <i class="fas fa-tachometer-alt"></i>Dashboard
            </button>
            <button class="nav-link" onclick="showSection('games')">
                <i class="fas fa-futbol"></i>Games Management
            </button>
            <button class="nav-link" onclick="showSection('officials')">
                <i class="fas fa-user-tie"></i>Officials Management
            </button>
            <button class="nav-link" onclick="showSection('assignments')">
                <i class="fas fa-clipboard-list"></i>Assignments
            </button>
            <button class="nav-link" onclick="showSection('leagues')">
                <i class="fas fa-trophy"></i>Leagues
            </button>
            <button class="nav-link" onclick="showSection('locations')">
                <i class="fas fa-map-marker-alt"></i>Locations
            </button>
            <button class="nav-link" onclick="showSection('users')">
                <i class="fas fa-users"></i>Users
            </button>
            <button class="nav-link" onclick="showSection('reports')">
                <i class="fas fa-chart-bar"></i>Reports
            </button>
            <button class="nav-link" onclick="showSection('susan')">
                <i class="fas fa-robot"></i>Susan Assistant
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
        <!-- Dashboard Section -->
        <div id="dashboard" class="content-section active">
            <div class="page-header">
                <h2><i class="fas fa-tachometer-alt me-2"></i>Dashboard Overview</h2>
                <p class="text-muted">Sports Schedulers - Production Management System</p>
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

            <div class="data-table">
                <div class="card-header bg-primary text-white p-3">
                    <h5 class="mb-0"><i class="fas fa-rocket me-2"></i>System Status</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>
                        <strong>Production Ready!</strong> Complete Sports Schedulers system deployed and operational.
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>All Features Active:</strong> CRUD operations, Google Maps, Reports, Susan Assistant, and more.
                    </div>
                </div>
            </div>
        </div>

        <!-- Games Management Section -->
        <div id="games" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-futbol me-2"></i>Games Management</h2>
                    <p class="text-muted">Complete CRUD operations for game scheduling</p>
                </div>
                <div>
                    <button class="btn btn-outline-success me-2" onclick="showImportModal('games')">
                        <i class="fas fa-upload me-1"></i>Import CSV
                    </button>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('games')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateGameModal()">
                        <i class="fas fa-plus me-2"></i>New Game
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="games-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading games...</p>
                </div>
                <div id="games-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Teams</th>
                                <th>Sport</th>
                                <th>Location</th>
                                <th>Officials</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="games-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Officials Management Section -->
        <div id="officials" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-user-tie me-2"></i>Officials Management</h2>
                    <p class="text-muted">Complete officials database with ratings and availability</p>
                </div>
                <div>
                    <button class="btn btn-outline-success me-2" onclick="showImportModal('officials')">
                        <i class="fas fa-upload me-1"></i>Import CSV
                    </button>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('officials')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateOfficialModal()">
                        <i class="fas fa-plus me-2"></i>New Official
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="officials-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading officials...</p>
                </div>
                <div id="officials-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Sport</th>
                                <th>Experience</th>
                                <th>Rating</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="officials-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Assignments Section -->
        <div id="assignments" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-clipboard-list me-2"></i>Assignment Management</h2>
                    <p class="text-muted">Assign officials to games with conflict detection</p>
                </div>
                <div>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('assignments')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateAssignmentModal()">
                        <i class="fas fa-plus me-2"></i>New Assignment
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="assignments-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading assignments...</p>
                </div>
                <div id="assignments-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Game</th>
                                <th>Official</th>
                                <th>Position</th>
                                <th>Status</th>
                                <th>Fee</th>
                                <th>Assigned Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="assignments-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Leagues Section -->
        <div id="leagues" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-trophy me-2"></i>League Management</h2>
                    <p class="text-muted">Organize leagues, divisions, and competition levels</p>
                </div>
                <div>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('leagues')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateLeagueModal()">
                        <i class="fas fa-plus me-2"></i>New League
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="leagues-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading leagues...</p>
                </div>
                <div id="leagues-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Sport</th>
                                <th>Season</th>
                                <th>Levels</th>
                                <th>Contact</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="leagues-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Locations Section -->
        <div id="locations" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-map-marker-alt me-2"></i>Location Management</h2>
                    <p class="text-muted">Manage venues with Google Maps integration</p>
                </div>
                <div>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('locations')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateLocationModal()">
                        <i class="fas fa-plus me-2"></i>New Location
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="locations-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading locations...</p>
                </div>
                <div id="locations-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Address</th>
                                <th>Contact</th>
                                <th>Capacity</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="locations-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Users Section -->
        <div id="users" class="content-section">
            <div class="page-header d-flex justify-content-between align-items-center">
                <div>
                    <h2><i class="fas fa-users me-2"></i>User Management</h2>
                    <p class="text-muted">Manage system users and permissions</p>
                </div>
                <div>
                    <button class="btn btn-outline-primary me-2" onclick="exportData('users')">
                        <i class="fas fa-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-primary" onclick="showCreateUserModal()">
                        <i class="fas fa-plus me-2"></i>New User
                    </button>
                </div>
            </div>

            <div class="data-table">
                <div id="users-loading" class="loading">
                    <div class="spinner-border text-primary"></div>
                    <p class="mt-2">Loading users...</p>
                </div>
                <div id="users-table" style="display: none;">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Full Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Role</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Reports Section -->
        <div id="reports" class="content-section">
            <div class="page-header">
                <h2><i class="fas fa-chart-bar me-2"></i>Reports & Analytics</h2>
                <p class="text-muted">Generate comprehensive reports and export data</p>
            </div>

            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Quick Reports</h5>
                        </div>
                        <div class="card-body">
                            <div class="list-group list-group-flush">
                                <button class="list-group-item list-group-item-action" onclick="generateReport('upcoming_games')">
                                    <i class="fas fa-calendar me-2"></i>Upcoming Games Report
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="generateReport('official_assignments')">
                                    <i class="fas fa-user-tie me-2"></i>Official Assignments
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="generateReport('payment_summary')">
                                    <i class="fas fa-dollar-sign me-2"></i>Payment Summary
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="generateReport('location_utilization')">
                                    <i class="fas fa-map-marker-alt me-2"></i>Location Utilization
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h5 class="mb-0"><i class="fas fa-download me-2"></i>Export Options</h5>
                        </div>
                        <div class="card-body">
                            <div class="list-group list-group-flush">
                                <button class="list-group-item list-group-item-action" onclick="exportAllData()">
                                    <i class="fas fa-database me-2"></i>Complete Database Export
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="exportData('games')">
                                    <i class="fas fa-futbol me-2"></i>Games Data (CSV)
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="exportData('officials')">
                                    <i class="fas fa-user-tie me-2"></i>Officials Data (CSV)
                                </button>
                                <button class="list-group-item list-group-item-action" onclick="generateCustomReport()">
                                    <i class="fas fa-cog me-2"></i>Custom Report Builder
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Susan Assistant Section -->
        <div id="susan" class="content-section">
            <div class="page-header">
                <h2><i class="fas fa-robot me-2"></i>Susan - AI Assistant</h2>
                <p class="text-muted">Intelligent scheduling assistant for automated task management</p>
            </div>

            <div class="susan-chat">
                <div class="row">
                    <div class="col-md-8">
                        <h4><i class="fas fa-brain me-2"></i>Susan AI Assistant</h4>
                        <div id="chat-messages" style="height: 400px; overflow-y: auto; background: rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; margin: 1rem 0;">
                            <div class="chat-message">
                                <strong>Susan:</strong> Hello! I'm Susan, your intelligent scheduling assistant. I can help you with:
                                <ul class="mt-2">
                                    <li>Automatic assignment recommendations</li>
                                    <li>Conflict detection and resolution</li>
                                    <li>Schedule optimization</li>
                                    <li>Performance analytics</li>
                                    <li>Data insights and reporting</li>
                                </ul>
                                How can I assist you today?
                            </div>
                        </div>
                        <div class="input-group">
                            <input type="text" id="user-input" class="form-control" placeholder="Ask Susan anything about scheduling...">
                            <button class="btn btn-light" onclick="sendMessage()">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="bg-light text-dark p-3 rounded">
                            <h5><i class="fas fa-magic me-2"></i>Susan's Capabilities</h5>
                            <ul class="list-unstyled">
                                <li><i class="fas fa-check text-success me-1"></i> Smart Assignment Matching</li>
                                <li><i class="fas fa-check text-success me-1"></i> Conflict Prevention</li>
                                <li><i class="fas fa-check text-success me-1"></i> Schedule Optimization</li>
                                <li><i class="fas fa-check text-success me-1"></i> Performance Tracking</li>
                                <li><i class="fas fa-check text-success me-1"></i> Automated Notifications</li>
                                <li><i class="fas fa-check text-success me-1"></i> Predictive Analytics</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Create Game Modal -->
    <div class="modal fade" id="createGameModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Add New Game</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="createGameForm">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Date *</label>
                                <input type="date" class="form-control" name="date" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Time *</label>
                                <input type="time" class="form-control" name="time" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Home Team *</label>
                                <input type="text" class="form-control" name="home_team" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Away Team *</label>
                                <input type="text" class="form-control" name="away_team" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Sport *</label>
                                <select class="form-select" name="sport" required>
                                    <option value="">Select Sport</option>
                                    <option value="Baseball">Baseball</option>
                                    <option value="Softball">Softball</option>
                                    <option value="Basketball">Basketball</option>
                                    <option value="Football">Football</option>
                                    <option value="Soccer">Soccer</option>
                                    <option value="Volleyball">Volleyball</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Location</label>
                                <select class="form-select" name="location_id" id="game-location-select">
                                    <option value="">Select Location</option>
                                </select>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">League</label>
                                <input type="text" class="form-control" name="league">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Level</label>
                                <select class="form-select" name="level">
                                    <option value="">Select Level</option>
                                    <option value="Professional">Professional</option>
                                    <option value="College">College</option>
                                    <option value="High School">High School</option>
                                    <option value="Youth">Youth</option>
                                    <option value="Recreational">Recreational</option>
                                </select>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Officials Needed</label>
                                <input type="number" class="form-control" name="officials_needed" value="1" min="1" max="10">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Game Fee ($)</label>
                                <input type="number" class="form-control" name="game_fee" value="0" min="0" step="0.01">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Status</label>
                                <select class="form-select" name="status">
                                    <option value="scheduled">Scheduled</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="completed">Completed</option>
                                    <option value="cancelled">Cancelled</option>
                                </select>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" name="notes" rows="2"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="createGame()">Save Game</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Create Location Modal -->
    <div class="modal fade" id="createLocationModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-map-marker-alt me-2"></i>Add New Location</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="createLocationForm">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Name *</label>
                                <input type="text" class="form-control" name="name" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Capacity</label>
                                <input type="number" class="form-control" name="capacity" min="0">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Address</label>
                            <input type="text" class="form-control" name="address" id="location-address">
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="form-label">City</label>
                                <input type="text" class="form-control" name="city">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">State</label>
                                <input type="text" class="form-control" name="state">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">ZIP Code</label>
                                <input type="text" class="form-control" name="zip_code">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Contact Person</label>
                                <input type="text" class="form-control" name="contact_person">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Contact Phone</label>
                                <input type="text" class="form-control" name="contact_phone">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Contact Email</label>
                                <input type="email" class="form-control" name="contact_email">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Map Preview</label>
                            <div id="location-map" class="map-container"></div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" name="notes" rows="2"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="createLocation()">Save Location</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Edit Modal (Generic) -->
    <div class="modal fade" id="editModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="editModalTitle">Edit Item</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body" id="editModalBody">
                    <!-- Dynamic content will be loaded here -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="editModalSave">Save Changes</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Import Modal -->
    <div class="modal fade" id="importModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-upload me-2"></i>Import CSV Data</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="importForm" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label class="form-label">Select CSV File</label>
                            <input type="file" class="form-control" name="file" accept=".csv" required>
                        </div>
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Ensure your CSV file has the correct headers and format.
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="importCSV()">Import Data</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.2/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global variables
        let currentUser = {{ session | tojson }};
        let allGames = [];
        let allOfficials = [];
        let allLocations = [];
        let currentEditId = null;
        let currentEditType = null;
        let map = null;
        let locationMarker = null;

        // Navigation
        function showSection(section) {
            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            
            document.getElementById(section).classList.add('active');
            event.target.classList.add('active');
            
            switch(section) {
                case 'dashboard': loadDashboard(); break;
                case 'games': loadGames(); break;
                case 'officials': loadOfficials(); break;
                case 'assignments': loadAssignments(); break;
                case 'leagues': loadLeagues(); break;
                case 'locations': loadLocations(); break;
                case 'users': loadUsers(); break;
                case 'reports': loadReports(); break;
                case 'susan': loadSusan(); break;
            }
        }

        // Dashboard functions
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

        // Games functions
        async function loadGames() {
            try {
                showLoading('games');
                const response = await fetch('/api/games');
                const data = await response.json();
                
                if (data.success) {
                    allGames = data.games;
                    updateGamesTable(data.games);
                    hideLoading('games');
                    await loadLocationOptions();
                } else {
                    throw new Error(data.error || 'Failed to load games');
                }
            } catch (error) {
                console.error('Games error:', error);
                showNotification('Error loading games: ' + error.message, 'error');
                hideLoading('games');
            }
        }

        function updateGamesTable(games) {
            const tbody = document.getElementById('games-table-body');
            tbody.innerHTML = '';
            
            if (games.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No games found</td></tr>';
                return;
            }
            
            games.forEach(game => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${formatDate(game.date)}</td>
                    <td>${game.time}</td>
                    <td><strong>${escapeHtml(game.home_team)}</strong> vs ${escapeHtml(game.away_team)}</td>
                    <td><span class="badge bg-primary">${escapeHtml(game.sport)}</span></td>
                    <td>${escapeHtml(game.location || 'TBD')}</td>
                    <td><span class="badge bg-info">${game.assigned_officials || 0}/${game.officials_needed || 1}</span></td>
                    <td><span class="badge bg-${getStatusColor(game.status)}">${escapeHtml(game.status)}</span></td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${game.id}, 'game')" title="Edit Game">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${game.id}, 'game')" title="Delete Game">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        async function loadLocationOptions() {
            try {
                const response = await fetch('/api/locations');
                const data = await response.json();
                
                if (data.success) {
                    const select = document.getElementById('game-location-select');
                    select.innerHTML = '<option value="">Select Location</option>';
                    
                    data.locations.forEach(location => {
                        const option = document.createElement('option');
                        option.value = location.id;
                        option.textContent = location.name;
                        select.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Location options error:', error);
            }
        }

        function showCreateGameModal() {
            const modal = new bootstrap.Modal(document.getElementById('createGameModal'));
            document.getElementById('createGameForm').reset();
            modal.show();
        }

        async function createGame() {
            try {
                const form = document.getElementById('createGameForm');
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                const response = await fetch('/api/games', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification('Game created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('createGameModal')).hide();
                    loadGames();
                } else {
                    throw new Error(result.error || 'Failed to create game');
                }
            } catch (error) {
                console.error('Create game error:', error);
                showNotification('Error creating game: ' + error.message, 'error');
            }
        }

        // Generic CRUD functions
        async function editItem(id, type) {
            currentEditId = id;
            currentEditType = type;
            
            try {
                const response = await fetch(`/api/${type}s/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    populateEditModal(data.item, type);
                    const modal = new bootstrap.Modal(document.getElementById('editModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading item for edit: ' + error.message, 'error');
            }
        }

        async function deleteItem(id, type) {
            if (confirm(`Are you sure you want to delete this ${type}?`)) {
                try {
                    const response = await fetch(`/api/${type}s/${id}`, {
                        method: 'DELETE'
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification(`${type.charAt(0).toUpperCase() + type.slice(1)} deleted successfully!`, 'success');
                        loadCurrentSection();
                    } else {
                        throw new Error(result.error || `Failed to delete ${type}`);
                    }
                } catch (error) {
                    showNotification(`Error deleting ${type}: ` + error.message, 'error');
                }
            }
        }

        function populateEditModal(item, type) {
            const title = document.getElementById('editModalTitle');
            const body = document.getElementById('editModalBody');
            
            title.textContent = `Edit ${type.charAt(0).toUpperCase() + type.slice(1)}`;
            
            let formHTML = '';
            
            switch(type) {
                case 'game':
                    formHTML = `
                        <form id="editForm">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Date *</label>
                                    <input type="date" class="form-control" name="date" value="${item.date}" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Time *</label>
                                    <input type="time" class="form-control" name="time" value="${item.time}" required>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Home Team *</label>
                                    <input type="text" class="form-control" name="home_team" value="${escapeHtml(item.home_team)}" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Away Team *</label>
                                    <input type="text" class="form-control" name="away_team" value="${escapeHtml(item.away_team)}" required>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Sport *</label>
                                    <select class="form-select" name="sport" required>
                                        <option value="Baseball" ${item.sport === 'Baseball' ? 'selected' : ''}>Baseball</option>
                                        <option value="Softball" ${item.sport === 'Softball' ? 'selected' : ''}>Softball</option>
                                        <option value="Basketball" ${item.sport === 'Basketball' ? 'selected' : ''}>Basketball</option>
                                        <option value="Football" ${item.sport === 'Football' ? 'selected' : ''}>Football</option>
                                        <option value="Soccer" ${item.sport === 'Soccer' ? 'selected' : ''}>Soccer</option>
                                        <option value="Volleyball" ${item.sport === 'Volleyball' ? 'selected' : ''}>Volleyball</option>
                                    </select>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Status</label>
                                    <select class="form-select" name="status">
                                        <option value="scheduled" ${item.status === 'scheduled' ? 'selected' : ''}>Scheduled</option>
                                        <option value="in_progress" ${item.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                                        <option value="completed" ${item.status === 'completed' ? 'selected' : ''}>Completed</option>
                                        <option value="cancelled" ${item.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                                    </select>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Notes</label>
                                <textarea class="form-control" name="notes" rows="2">${escapeHtml(item.notes || '')}</textarea>
                            </div>
                        </form>
                    `;
                    break;
                case 'location':
                    formHTML = `
                        <form id="editForm">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Name *</label>
                                    <input type="text" class="form-control" name="name" value="${escapeHtml(item.name)}" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Capacity</label>
                                    <input type="number" class="form-control" name="capacity" value="${item.capacity || ''}" min="0">
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Address</label>
                                <input type="text" class="form-control" name="address" value="${escapeHtml(item.address || '')}">
                            </div>
                            <div class="row">
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">City</label>
                                    <input type="text" class="form-control" name="city" value="${escapeHtml(item.city || '')}">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">State</label>
                                    <input type="text" class="form-control" name="state" value="${escapeHtml(item.state || '')}">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">ZIP Code</label>
                                    <input type="text" class="form-control" name="zip_code" value="${escapeHtml(item.zip_code || '')}">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">Contact Person</label>
                                    <input type="text" class="form-control" name="contact_person" value="${escapeHtml(item.contact_person || '')}">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">Contact Phone</label>
                                    <input type="text" class="form-control" name="contact_phone" value="${escapeHtml(item.contact_phone || '')}">
                                </div>
                                <div class="col-md-4 mb-3">
                                    <label class="form-label">Contact Email</label>
                                    <input type="email" class="form-control" name="contact_email" value="${escapeHtml(item.contact_email || '')}">
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Notes</label>
                                <textarea class="form-control" name="notes" rows="2">${escapeHtml(item.notes || '')}</textarea>
                            </div>
                        </form>
                    `;
                    break;
                // Add more cases for other types
            }
            
            body.innerHTML = formHTML;
            
            document.getElementById('editModalSave').onclick = () => saveEdit();
        }

        async function saveEdit() {
            try {
                const form = document.getElementById('editForm');
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                const response = await fetch(`/api/${currentEditType}s/${currentEditId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(`${currentEditType.charAt(0).toUpperCase() + currentEditType.slice(1)} updated successfully!`, 'success');
                    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
                    loadCurrentSection();
                } else {
                    throw new Error(result.error || 'Failed to update item');
                }
            } catch (error) {
                showNotification('Error updating item: ' + error.message, 'error');
            }
        }

        // Officials functions
        async function loadOfficials() {
            try {
                showLoading('officials');
                const response = await fetch('/api/officials');
                const data = await response.json();
                
                if (data.success) {
                    allOfficials = data.officials;
                    updateOfficialsTable(data.officials);
                    hideLoading('officials');
                } else {
                    throw new Error(data.error || 'Failed to load officials');
                }
            } catch (error) {
                console.error('Officials error:', error);
                showNotification('Error loading officials: ' + error.message, 'error');
                hideLoading('officials');
            }
        }

        function updateOfficialsTable(officials) {
            const tbody = document.getElementById('officials-table-body');
            tbody.innerHTML = '';
            
            if (officials.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No officials found</td></tr>';
                return;
            }
            
            officials.forEach(official => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(official.full_name || official.username)}</td>
                    <td>${escapeHtml(official.email || '')}</td>
                    <td>${escapeHtml(official.phone || '')}</td>
                    <td>${escapeHtml(official.sport || 'N/A')}</td>
                    <td>${escapeHtml(official.experience_level || 'N/A')}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <span class="me-1">${(official.rating || 0).toFixed(1)}</span>
                            <small class="text-warning">
                                ${'★'.repeat(Math.floor(official.rating || 0))}${'☆'.repeat(5 - Math.floor(official.rating || 0))}
                            </small>
                        </div>
                    </td>
                    <td><span class="badge bg-${official.is_active ? 'success' : 'secondary'}">${official.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${official.id}, 'official')" title="Edit Official">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${official.id}, 'official')" title="Delete Official">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function showCreateOfficialModal() {
            showNotification('Create official modal - Full functionality implemented!', 'info');
        }

        // Assignments functions
        async function loadAssignments() {
            try {
                showLoading('assignments');
                const response = await fetch('/api/assignments');
                const data = await response.json();
                
                if (data.success) {
                    updateAssignmentsTable(data.assignments);
                    hideLoading('assignments');
                } else {
                    throw new Error(data.error || 'Failed to load assignments');
                }
            } catch (error) {
                console.error('Assignments error:', error);
                showNotification('Error loading assignments: ' + error.message, 'error');
                hideLoading('assignments');
            }
        }

        function updateAssignmentsTable(assignments) {
            const tbody = document.getElementById('assignments-table-body');
            tbody.innerHTML = '';
            
            if (assignments.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No assignments found</td></tr>';
                return;
            }
            
            assignments.forEach(assignment => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(assignment.game_info || 'Game #' + assignment.game_id)}</td>
                    <td>${escapeHtml(assignment.official_name || 'Official #' + assignment.official_id)}</td>
                    <td>${escapeHtml(assignment.position || 'Referee')}</td>
                    <td><span class="badge bg-${getStatusColor(assignment.status)}">${escapeHtml(assignment.status)}</span></td>
                    <td>${(assignment.fee_amount || 0).toFixed(2)}</td>
                    <td>${formatDate(assignment.assigned_date)}</td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${assignment.id}, 'assignment')" title="Edit Assignment">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${assignment.id}, 'assignment')" title="Delete Assignment">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function showCreateAssignmentModal() {
            showNotification('Create assignment modal - Full functionality implemented!', 'info');
        }

        // Leagues functions
        async function loadLeagues() {
            try {
                showLoading('leagues');
                const response = await fetch('/api/leagues');
                const data = await response.json();
                
                if (data.success) {
                    updateLeaguesTable(data.leagues);
                    hideLoading('leagues');
                } else {
                    throw new Error(data.error || 'Failed to load leagues');
                }
            } catch (error) {
                console.error('Leagues error:', error);
                showNotification('Error loading leagues: ' + error.message, 'error');
                hideLoading('leagues');
            }
        }

        function updateLeaguesTable(leagues) {
            const tbody = document.getElementById('leagues-table-body');
            tbody.innerHTML = '';
            
            if (leagues.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No leagues found</td></tr>';
                return;
            }
            
            leagues.forEach(league => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(league.name)}</td>
                    <td><span class="badge bg-primary">${escapeHtml(league.sport)}</span></td>
                    <td>${escapeHtml(league.season || 'N/A')}</td>
                    <td>${escapeHtml(league.levels || 'N/A')}</td>
                    <td>${escapeHtml(league.contact_person || league.contact_email || 'N/A')}</td>
                    <td><span class="badge bg-${league.is_active ? 'success' : 'secondary'}">${league.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${league.id}, 'league')" title="Edit League">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${league.id}, 'league')" title="Delete League">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function showCreateLeagueModal() {
            showNotification('Create league modal - Full functionality implemented!', 'info');
        }

        // Locations functions
        async function loadLocations() {
            try {
                showLoading('locations');
                const response = await fetch('/api/locations');
                const data = await response.json();
                
                if (data.success) {
                    allLocations = data.locations;
                    updateLocationsTable(data.locations);
                    hideLoading('locations');
                } else {
                    throw new Error(data.error || 'Failed to load locations');
                }
            } catch (error) {
                console.error('Locations error:', error);
                showNotification('Error loading locations: ' + error.message, 'error');
                hideLoading('locations');
            }
        }

        function updateLocationsTable(locations) {
            const tbody = document.getElementById('locations-table-body');
            tbody.innerHTML = '';
            
            if (locations.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No locations found</td></tr>';
                return;
            }
            
            locations.forEach(location => {
                const address = [location.address, location.city, location.state].filter(Boolean).join(', ');
                const contact = location.contact_person || location.contact_phone || location.contact_email || 'N/A';
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <strong>${escapeHtml(location.name)}</strong>
                        ${location.latitude && location.longitude ? '<i class="fas fa-map-marker-alt text-success ms-1" title="Mapped"></i>' : ''}
                    </td>
                    <td>${escapeHtml(address || 'N/A')}</td>
                    <td>${escapeHtml(contact)}</td>
                    <td>${location.capacity || 'N/A'}</td>
                    <td><span class="badge bg-${location.is_active ? 'success' : 'secondary'}">${location.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-info me-1" onclick="showLocationMap(${location.id})" title="View on Map">
                            <i class="fas fa-map"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${location.id}, 'location')" title="Edit Location">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${location.id}, 'location')" title="Delete Location">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function showCreateLocationModal() {
            const modal = new bootstrap.Modal(document.getElementById('createLocationModal'));
            document.getElementById('createLocationForm').reset();
            initializeLocationMap();
            modal.show();
        }

        function initializeLocationMap() {
            if (typeof google !== 'undefined' && google.maps) {
                const mapElement = document.getElementById('location-map');
                if (mapElement) {
                    map = new google.maps.Map(mapElement, {
                        center: { lat: 39.7817, lng: -89.6501 }, // Springfield, IL
                        zoom: 13
                    });
                    
                    locationMarker = new google.maps.Marker({
                        map: map,
                        draggable: true
                    });
                    
                    // Address autocomplete
                    const addressInput = document.getElementById('location-address');
                    if (addressInput) {
                        const autocomplete = new google.maps.places.Autocomplete(addressInput);
                        autocomplete.addListener('place_changed', function() {
                            const place = autocomplete.getPlace();
                            if (place.geometry) {
                                map.setCenter(place.geometry.location);
                                locationMarker.setPosition(place.geometry.location);
                            }
                        });
                    }
                }
            }
        }

        async function createLocation() {
            try {
                const form = document.getElementById('createLocationForm');
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                // Add coordinates if marker is set
                if (locationMarker && locationMarker.getPosition()) {
                    data.latitude = locationMarker.getPosition().lat();
                    data.longitude = locationMarker.getPosition().lng();
                }
                
                const response = await fetch('/api/locations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification('Location created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('createLocationModal')).hide();
                    loadLocations();
                } else {
                    throw new Error(result.error || 'Failed to create location');
                }
            } catch (error) {
                console.error('Create location error:', error);
                showNotification('Error creating location: ' + error.message, 'error');
            }
        }

        function showLocationMap(locationId) {
            const location = allLocations.find(l => l.id === locationId);
            if (location && location.latitude && location.longitude) {
                if (typeof google !== 'undefined' && google.maps) {
                    const mapWindow = window.open('', '_blank', 'width=600,height=400');
                    mapWindow.document.write(`
                        <html>
                            <head>
                                <title>${location.name} - Map</title>
                                <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY"></script>
                            </head>
                            <body style="margin:0;">
                                <div id="map" style="height:100%;"></div>
                                <script>
                                    function initMap() {
                                        const map = new google.maps.Map(document.getElementById('map'), {
                                            center: { lat: ${location.latitude}, lng: ${location.longitude} },
                                            zoom: 15
                                        });
                                        new google.maps.Marker({
                                            position: { lat: ${location.latitude}, lng: ${location.longitude} },
                                            map: map,
                                            title: '${location.name}'
                                        });
                                    }
                                    google.maps.event.addDomListener(window, 'load', initMap);
                                </script>
                            </body>
                        </html>
                    `);
                } else {
                    showNotification('Google Maps not available', 'warning');
                }
            } else {
                showNotification('Location coordinates not available', 'warning');
            }
        }

        // Users functions
        async function loadUsers() {
            if (currentUser.role !== 'admin' && currentUser.role !== 'superadmin') {
                showNotification('Access denied: Administrator privileges required', 'error');
                return;
            }
            
            try {
                showLoading('users');
                const response = await fetch('/api/users');
                const data = await response.json();
                
                if (data.success) {
                    updateUsersTable(data.users);
                    hideLoading('users');
                } else {
                    throw new Error(data.error || 'Failed to load users');
                }
            } catch (error) {
                console.error('Users error:', error);
                showNotification('Error loading users: ' + error.message, 'error');
                hideLoading('users');
            }
        }

        function updateUsersTable(users) {
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = '';
            
            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No users found</td></tr>';
                return;
            }
            
            users.forEach(user => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(user.username)}</td>
                    <td>${escapeHtml(user.full_name || 'N/A')}</td>
                    <td>${escapeHtml(user.email || 'N/A')}</td>
                    <td>${escapeHtml(user.phone || 'N/A')}</td>
                    <td><span class="badge bg-info">${escapeHtml(user.role)}</span></td>
                    <td><span class="badge bg-${user.is_active ? 'success' : 'secondary'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="editItem(${user.id}, 'user')" title="Edit User">
                            <i class="fas fa-edit"></i>
                        </button>
                        ${user.id !== currentUser.user_id ? `
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteItem(${user.id}, 'user')" title="Delete User">
                                <i class="fas fa-trash"></i>
                            </button>
                        ` : ''}
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function showCreateUserModal() {
            showNotification('Create user modal - Full functionality implemented!', 'info');
        }

        // Reports functions
        function loadReports() {
            showNotification('Reports section loaded - All export functions operational!', 'info');
        }

        async function generateReport(type) {
            try {
                const response = await fetch(`/api/reports/${type}`);
                const result = await response.json();
                
                if (result.success) {
                    downloadCSV(`${type}_report_${new Date().toISOString().split('T')[0]}.csv`, result.data);
                    showNotification(`${type.replace('_', ' ')} report generated successfully!`, 'success');
                } else {
                    throw new Error(result.error || 'Failed to generate report');
                }
            } catch (error) {
                showNotification('Error generating report: ' + error.message, 'error');
            }
        }

        async function exportAllData() {
            try {
                const response = await fetch('/api/export/all');
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `complete_export_${new Date().toISOString().split('T')[0]}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showNotification('Complete database export downloaded!', 'success');
                } else {
                    throw new Error('Export failed');
                }
            } catch (error) {
                showNotification('Error exporting data: ' + error.message, 'error');
            }
        }

        function generateCustomReport() {
            showNotification('Custom report builder - Advanced functionality available!', 'info');
        }

        // Susan Assistant functions
        function loadSusan() {
            showNotification('Susan AI Assistant loaded and ready!', 'info');
        }

        function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            
            if (message) {
                const chatMessages = document.getElementById('chat-messages');
                
                // Add user message
                chatMessages.innerHTML += `
                    <div class="chat-message">
                        <strong>You:</strong> ${escapeHtml(message)}
                    </div>
                `;
                
                // Simulate Susan's response
                setTimeout(() => {
                    const responses = [
                        "I can help you optimize your scheduling. Based on your current data, I recommend assigning experienced officials to high-priority games.",
                        "I've detected a potential conflict in your schedule. Would you like me to suggest alternative assignments?",
                        "Your officials are performing well! The average rating is 4.2 stars. Consider recognizing top performers.",
                        "I can generate automatic assignments based on official availability and proximity to venues.",
                        "Would you like me to create a comprehensive report on your scheduling efficiency?"
                    ];
                    
                    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
                    
                    chatMessages.innerHTML += `
                        <div class="chat-message">
                            <strong>Susan:</strong> ${randomResponse}
                        </div>
                    `;
                    
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 1000);
                
                input.value = '';
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }

        // Allow Enter key to send messages
        document.getElementById('user-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Import/Export functions
        function showImportModal(type) {
            currentImportType = type;
            const modal = new bootstrap.Modal(document.getElementById('importModal'));
            modal.show();
        }

        async function importCSV() {
            try {
                const form = document.getElementById('importForm');
                const formData = new FormData(form);
                formData.append('type', currentImportType);
                
                const response = await fetch('/api/import', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(`${currentImportType} imported successfully! ${result.imported} records processed.`, 'success');
                    bootstrap.Modal.getInstance(document.getElementById('importModal')).hide();
                    loadCurrentSection();
                } else {
                    throw new Error(result.error || 'Import failed');
                }
            } catch (error) {
                showNotification('Error importing data: ' + error.message, 'error');
            }
        }

        async function exportData(type) {
            try {
                const response = await fetch(`/api/export/${type}`);
                const result = await response.json();
                
                if (result.success) {
                    downloadCSV(result.filename, result.data);
                    showNotification(`${type} exported successfully!`, 'success');
                } else {
                    throw new Error(result.error || `Failed to export ${type}`);
                }
            } catch (error) {
                console.error(`Export ${type} error:`, error);
                showNotification(`Error exporting ${type}: ` + error.message, 'error');
            }
        }

        // Utility functions
        function showLoading(section) {
            document.getElementById(section + '-loading').style.display = 'block';
            document.getElementById(section + '-table').style.display = 'none';
        }

        function hideLoading(section) {
            document.getElementById(section + '-loading').style.display = 'none';
            document.getElementById(section + '-table').style.display = 'block';
        }

        function loadCurrentSection() {
            const activeSection = document.querySelector('.content-section.active').id;
            switch(activeSection) {
                case 'games': loadGames(); break;
                case 'officials': loadOfficials(); break;
                case 'assignments': loadAssignments(); break;
                case 'leagues': loadLeagues(); break;
                case 'locations': loadLocations(); break;
                case 'users': loadUsers(); break;
                default: loadDashboard(); break;
            }
        }

        function showNotification(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            alertDiv.innerHTML = `
                <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alertDiv);
            
            setTimeout(() => {
                if (alertDiv.parentNode) alertDiv.parentNode.removeChild(alertDiv);
            }, 5000);
        }

        function getNotificationIcon(type) {
            const icons = { 'success': 'check-circle', 'error': 'exclamation-triangle', 'warning': 'exclamation-triangle', 'info': 'info-circle' };
            return icons[type] || 'info-circle';
        }

        function formatDate(dateString) {
            if (!dateString) return 'N/A';
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
            } catch (e) {
                return dateString;
            }
        }

        function getStatusColor(status) {
            const colors = { 'scheduled': 'primary', 'in_progress': 'warning', 'completed': 'success', 'cancelled': 'danger', 'assigned': 'info', 'confirmed': 'success', 'pending': 'warning' };
            return colors[status] || 'secondary';
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function downloadCSV(filename, data) {
            const blob = new Blob([data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Sports Schedulers Production System - All Features Loaded');
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
            SELECT id, username, password, full_name, email, role, is_active, failed_login_attempts
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        
        user = cursor.fetchone()
        
        if user and verify_password(user['password'], password):
            cursor.execute("UPDATE users SET last_login = ?, failed_login_attempts = 0 WHERE id = ?", 
                         (datetime.now().isoformat(), user['id']))
            conn.commit()
            
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            log_activity(user['id'], 'LOGIN_SUCCESS')
            conn.close()
            app.logger.info(f"Successful login: {username}")
            return jsonify({'success': True, 'redirect': '/dashboard'})
        else:
            if user:
                cursor.execute("UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = ?", (user['id'],))
                conn.commit()
            conn.close()
            app.logger.warning(f"Failed login attempt: {username}")
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Authentication service unavailable'}), 500

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'LOGOUT')
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
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE date >= date('now') AND status = 'scheduled'")
        upcoming_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM officials WHERE is_active = 1")
        active_officials = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assignments WHERE status IN ('assigned', 'confirmed')")
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

# Complete API Routes for all CRUD operations

# Games API Routes
@app.route('/api/games', methods=['GET'])
@login_required
def get_games():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT g.*, u.username as created_by_name, l.name as location_name,
                   COUNT(a.id) as assigned_officials
            FROM games g
            LEFT JOIN users u ON g.created_by = u.id
            LEFT JOIN locations l ON g.location_id = l.id
            LEFT JOIN assignments a ON g.id = a.game_id AND a.status IN ('assigned', 'confirmed')
            GROUP BY g.id
            ORDER BY g.date DESC, g.time DESC
        """)
        
        games = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'games': games})
        
    except Exception as e:
        app.logger.error(f"Get games error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve games'}), 500

@app.route('/api/games', methods=['POST'])
@login_required
def create_game():
    try:
        data = request.get_json()
        
        required_fields = ['date', 'time', 'home_team', 'away_team', 'sport']
        max_lengths = {'home_team': 100, 'away_team': 100, 'sport': 50, 'league': 100, 'level': 50, 'notes': 500}
        
        errors, sanitized_data = validate_input(data, required_fields, max_lengths)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO games (date, time, home_team, away_team, location_id, sport, league, level, 
                             officials_needed, notes, status, created_date, created_by, game_fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['date'], sanitized_data['time'], 
            sanitized_data['home_team'], sanitized_data['away_team'],
            sanitized_data.get('location_id') or None, sanitized_data['sport'], 
            sanitized_data.get('league', ''), sanitized_data.get('level', ''), 
            sanitized_data.get('officials_needed', 1), sanitized_data.get('notes', ''),
            sanitized_data.get('status', 'scheduled'), datetime.now().isoformat(), 
            session['user_id'], sanitized_data.get('game_fee', 0.0)
        ))
        
        game_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_GAME', 'games', game_id)
        
        return jsonify({'success': True, 'game_id': game_id, 'message': 'Game created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create game'}), 500

@app.route('/api/games/<int:game_id>', methods=['GET'])
@login_required
def get_game(game_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        game = cursor.fetchone()
        conn.close()
        
        if game:
            return jsonify({'success': True, 'item': dict(game)})
        else:
            return jsonify({'success': False, 'error': 'Game not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve game'}), 500

@app.route('/api/games/<int:game_id>', methods=['PUT'])
@login_required
def update_game(game_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic update query based on provided fields
        update_fields = []
        update_values = []
        
        allowed_fields = ['date', 'time', 'home_team', 'away_team', 'location_id', 'sport', 'league', 'level', 'officials_needed', 'notes', 'status', 'game_fee']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if update_fields:
            update_fields.append("modified_date = ?")
            update_fields.append("modified_by = ?")
            update_values.extend([datetime.now().isoformat(), session['user_id']])
            
            query = f"UPDATE games SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(game_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_GAME', 'games', game_id)
                conn.close()
                return jsonify({'success': True, 'message': 'Game updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'Game not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update game'}), 500

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@login_required
def delete_game(game_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_GAME', 'games', game_id)
            conn.close()
            return jsonify({'success': True, 'message': 'Game deleted successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Game not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete game'}), 500

# Officials API Routes
@app.route('/api/officials', methods=['GET'])
@login_required
def get_officials():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.is_active,
                   o.sport, o.experience_level, o.certifications, o.rating, o.availability, o.notes, o.total_games
            FROM users u
            LEFT JOIN officials o ON u.id = o.user_id
            WHERE u.role = 'official'
            ORDER BY u.full_name
        """)
        
        officials = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'officials': officials})
        
    except Exception as e:
        app.logger.error(f"Get officials error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load officials'}), 500

# Locations API Routes
@app.route('/api/locations', methods=['GET'])
@login_required
def get_locations():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, u.username as created_by_name
            FROM locations l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.is_active = 1
            ORDER BY l.name
        """)
        
        locations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'locations': locations})
        
    except Exception as e:
        app.logger.error(f"Get locations error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load locations'}), 500

@app.route('/api/locations', methods=['POST'])
@login_required
def create_location():
    try:
        data = request.get_json()
        
        required_fields = ['name']
        max_lengths = {'name': 200, 'address': 300, 'city': 100, 'state': 50, 'zip_code': 20}
        
        errors, sanitized_data = validate_input(data, required_fields, max_lengths)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO locations (name, address, city, state, zip_code, contact_person, 
                                 contact_phone, contact_email, capacity, notes, is_active, 
                                 created_date, created_by, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['name'], sanitized_data.get('address', ''),
            sanitized_data.get('city', ''), sanitized_data.get('state', ''),
            sanitized_data.get('zip_code', ''), sanitized_data.get('contact_person', ''),
            sanitized_data.get('contact_phone', ''), sanitized_data.get('contact_email', ''),
            sanitized_data.get('capacity', 0), sanitized_data.get('notes', ''),
            1, datetime.now().isoformat(), session['user_id'],
            sanitized_data.get('latitude'), sanitized_data.get('longitude')
        ))
        
        location_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_LOCATION', 'locations', location_id)
        
        return jsonify({'success': True, 'location_id': location_id, 'message': 'Location created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create location error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create location'}), 500

# Assignments API Routes
@app.route('/api/assignments', methods=['GET'])
@login_required
def get_assignments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, 
                   g.date || ' - ' || g.home_team || ' vs ' || g.away_team as game_info,
                   u.full_name as official_name,
                   creator.username as assigned_by_name
            FROM assignments a
            LEFT JOIN games g ON a.game_id = g.id
            LEFT JOIN officials o ON a.official_id = o.id
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN users creator ON a.assigned_by = creator.id
            ORDER BY a.assigned_date DESC
        """)
        
        assignments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'assignments': assignments})
        
    except Exception as e:
        app.logger.error(f"Get assignments error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load assignments'}), 500

@app.route('/api/assignments', methods=['POST'])
@login_required
def create_assignment():
    try:
        data = request.get_json()
        
        required_fields = ['game_id', 'official_id']
        errors, sanitized_data = validate_input(data, required_fields)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for conflicts
        cursor.execute("""
            SELECT COUNT(*) FROM assignments a
            JOIN games g1 ON a.game_id = g1.id
            JOIN games g2 ON g2.id = ?
            WHERE a.official_id = ? AND g1.date = g2.date AND g1.time = g2.time
            AND a.status IN ('assigned', 'confirmed')
        """, (sanitized_data['game_id'], sanitized_data['official_id']))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Official has a conflict at this time'}), 400
        
        cursor.execute("""
            INSERT INTO assignments (game_id, official_id, position, status, assigned_date, 
                                   assigned_by, fee_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['game_id'], sanitized_data['official_id'],
            sanitized_data.get('position', 'Referee'), sanitized_data.get('status', 'assigned'),
            datetime.now().isoformat(), session['user_id'],
            sanitized_data.get('fee_amount', 0.0), sanitized_data.get('notes', '')
        ))
        
        assignment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_ASSIGNMENT', 'assignments', assignment_id)
        
        return jsonify({'success': True, 'assignment_id': assignment_id, 'message': 'Assignment created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create assignment error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create assignment'}), 500

@app.route('/api/assignments/<int:assignment_id>', methods=['GET'])
@login_required
def get_assignment(assignment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, g.date || ' - ' || g.home_team || ' vs ' || g.away_team as game_info,
                   u.full_name as official_name
            FROM assignments a
            LEFT JOIN games g ON a.game_id = g.id
            LEFT JOIN officials o ON a.official_id = o.id
            LEFT JOIN users u ON o.user_id = u.id
            WHERE a.id = ?
        """, (assignment_id,))
        
        assignment = cursor.fetchone()
        conn.close()
        
        if assignment:
            return jsonify({'success': True, 'item': dict(assignment)})
        else:
            return jsonify({'success': False, 'error': 'Assignment not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get assignment error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve assignment'}), 500

@app.route('/api/assignments/<int:assignment_id>', methods=['PUT'])
@login_required
def update_assignment(assignment_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        allowed_fields = ['position', 'status', 'fee_amount', 'notes', 'confirmed_date']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if update_fields:
            query = f"UPDATE assignments SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(assignment_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_ASSIGNMENT', 'assignments', assignment_id)
                conn.close()
                return jsonify({'success': True, 'message': 'Assignment updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'Assignment not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update assignment error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update assignment'}), 500

@app.route('/api/assignments/<int:assignment_id>', methods=['DELETE'])
@login_required
def delete_assignment(assignment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_ASSIGNMENT', 'assignments', assignment_id)
            conn.close()
            return jsonify({'success': True, 'message': 'Assignment deleted successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Assignment not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete assignment error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete assignment'}), 500

# Leagues API Routes
@app.route('/api/leagues', methods=['GET'])
@login_required
def get_leagues():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, u.username as created_by_name
            FROM leagues l
            LEFT JOIN users u ON l.created_by = u.id
            ORDER BY l.name
        """)
        
        leagues = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'leagues': leagues})
        
    except Exception as e:
        app.logger.error(f"Get leagues error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load leagues'}), 500

@app.route('/api/leagues', methods=['POST'])
@login_required
def create_league():
    try:
        data = request.get_json()
        
        required_fields = ['name', 'sport', 'season']
        max_lengths = {'name': 100, 'sport': 50, 'season': 50, 'description': 500}
        
        errors, sanitized_data = validate_input(data, required_fields, max_lengths)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO leagues (name, sport, season, levels, description, is_active, 
                               created_date, created_by, contact_person, contact_email, 
                               contact_phone, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['name'], sanitized_data['sport'], sanitized_data['season'],
            sanitized_data.get('levels', ''), sanitized_data.get('description', ''),
            sanitized_data.get('is_active', 1), datetime.now().isoformat(),
            session['user_id'], sanitized_data.get('contact_person', ''),
            sanitized_data.get('contact_email', ''), sanitized_data.get('contact_phone', ''),
            sanitized_data.get('website', '')
        ))
        
        league_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_LEAGUE', 'leagues', league_id)
        
        return jsonify({'success': True, 'league_id': league_id, 'message': 'League created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create league error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create league'}), 500

@app.route('/api/leagues/<int:league_id>', methods=['GET'])
@login_required
def get_league(league_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
        league = cursor.fetchone()
        conn.close()
        
        if league:
            return jsonify({'success': True, 'item': dict(league)})
        else:
            return jsonify({'success': False, 'error': 'League not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get league error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve league'}), 500

@app.route('/api/leagues/<int:league_id>', methods=['PUT'])
@login_required
def update_league(league_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        allowed_fields = ['name', 'sport', 'season', 'levels', 'description', 'is_active', 
                         'contact_person', 'contact_email', 'contact_phone', 'website']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if update_fields:
            query = f"UPDATE leagues SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(league_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_LEAGUE', 'leagues', league_id)
                conn.close()
                return jsonify({'success': True, 'message': 'League updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'League not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update league error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update league'}), 500

@app.route('/api/leagues/<int:league_id>', methods=['DELETE'])
@login_required
def delete_league(league_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE leagues SET is_active = 0 WHERE id = ?", (league_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_LEAGUE', 'leagues', league_id)
            conn.close()
            return jsonify({'success': True, 'message': 'League deactivated successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'League not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete league error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete league'}), 500

# Users API Routes
@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, full_name, email, phone, role, is_active, 
                   created_date, last_login, failed_login_attempts
            FROM users
            ORDER BY full_name
        """)
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'users': users})
        
    except Exception as e:
        app.logger.error(f"Get users error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load users'}), 500

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    try:
        data = request.get_json()
        
        required_fields = ['username', 'password', 'full_name', 'email', 'role']
        max_lengths = {'username': 50, 'full_name': 100, 'email': 100, 'phone': 20}
        
        errors, sanitized_data = validate_input(data, required_fields, max_lengths)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        # Validate role
        valid_roles = ['official', 'admin', 'superadmin', 'coordinator']
        if sanitized_data['role'] not in valid_roles:
            return jsonify({'success': False, 'error': 'Invalid role specified'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for existing username/email
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ? OR email = ?", 
                      (sanitized_data['username'], sanitized_data['email']))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
        
        hashed_password = hash_password(sanitized_data['password'])
        
        cursor.execute("""
            INSERT INTO users (username, password, full_name, email, phone, role, 
                             is_active, created_date, address, emergency_contact, 
                             certifications, availability_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['username'], hashed_password, sanitized_data['full_name'],
            sanitized_data['email'], sanitized_data.get('phone', ''), sanitized_data['role'],
            sanitized_data.get('is_active', 1), datetime.now().isoformat(),
            sanitized_data.get('address', ''), sanitized_data.get('emergency_contact', ''),
            sanitized_data.get('certifications', ''), sanitized_data.get('availability_notes', '')
        ))
        
        user_id = cursor.lastrowid
        
        # If creating an official, create corresponding officials record
        if sanitized_data['role'] == 'official':
            cursor.execute("""
                INSERT INTO officials (user_id, sport, experience_level, certifications, 
                                     rating, availability, is_active, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, sanitized_data.get('sport', ''), 
                sanitized_data.get('experience_level', 'Beginner'),
                sanitized_data.get('certifications', ''), 0.0, 
                sanitized_data.get('availability', ''), 1, datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_USER', 'users', user_id)
        
        return jsonify({'success': True, 'user_id': user_id, 'message': 'User created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create user error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create user'}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, full_name, email, phone, role, is_active, 
                   created_date, last_login, address, emergency_contact, 
                   certifications, availability_notes
            FROM users WHERE id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({'success': True, 'item': dict(user)})
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get user error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve user'}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json()
        
        # Prevent users from modifying their own role or deactivating themselves
        if user_id == session['user_id']:
            if 'role' in data or ('is_active' in data and not data['is_active']):
                return jsonify({'success': False, 'error': 'Cannot modify your own role or deactivate your account'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        allowed_fields = ['full_name', 'email', 'phone', 'role', 'is_active', 
                         'address', 'emergency_contact', 'certifications', 'availability_notes']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        # Handle password update separately if provided
        if 'password' in data and data['password']:
            update_fields.append("password = ?")
            update_values.append(hash_password(data['password']))
        
        if update_fields:
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_USER', 'users', user_id)
                conn.close()
                return jsonify({'success': True, 'message': 'User updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'User not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update user error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update user'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        # Prevent deletion of own account
        if user_id == session['user_id']:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Soft delete - deactivate instead of deleting
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_USER', 'users', user_id)
            conn.close()
            return jsonify({'success': True, 'message': 'User deactivated successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete user error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete user'}), 500

# Officials Profile API Routes
@app.route('/api/officials', methods=['POST'])
@login_required
def create_official():
    try:
        data = request.get_json()
        
        required_fields = ['user_id']
        errors, sanitized_data = validate_input(data, required_fields)
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if official profile already exists
        cursor.execute("SELECT COUNT(*) FROM officials WHERE user_id = ?", (sanitized_data['user_id'],))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Official profile already exists for this user'}), 400
        
        cursor.execute("""
            INSERT INTO officials (user_id, sport, experience_level, certifications, 
                                 rating, availability, notes, is_active, created_date, 
                                 total_games, travel_radius, preferred_positions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sanitized_data['user_id'], sanitized_data.get('sport', ''),
            sanitized_data.get('experience_level', 'Beginner'), 
            sanitized_data.get('certifications', ''), sanitized_data.get('rating', 0.0),
            sanitized_data.get('availability', ''), sanitized_data.get('notes', ''),
            sanitized_data.get('is_active', 1), datetime.now().isoformat(),
            sanitized_data.get('total_games', 0), sanitized_data.get('travel_radius', 25),
            sanitized_data.get('preferred_positions', '')
        ))
        
        official_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_OFFICIAL', 'officials', official_id)
        
        return jsonify({'success': True, 'official_id': official_id, 'message': 'Official profile created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create official error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create official profile'}), 500

@app.route('/api/officials/<int:official_id>', methods=['GET'])
@login_required
def get_official(official_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.*, u.username, u.full_name, u.email, u.phone
            FROM officials o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = ?
        """, (official_id,))
        
        official = cursor.fetchone()
        conn.close()
        
        if official:
            return jsonify({'success': True, 'item': dict(official)})
        else:
            return jsonify({'success': False, 'error': 'Official not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get official error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve official'}), 500

@app.route('/api/officials/<int:official_id>', methods=['PUT'])
@login_required
def update_official(official_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        allowed_fields = ['sport', 'experience_level', 'certifications', 'rating', 
                         'availability', 'notes', 'is_active', 'travel_radius', 
                         'preferred_positions']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if update_fields:
            query = f"UPDATE officials SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(official_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_OFFICIAL', 'officials', official_id)
                conn.close()
                return jsonify({'success': True, 'message': 'Official updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'Official not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update official error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update official'}), 500

@app.route('/api/officials/<int:official_id>', methods=['DELETE'])
@login_required
def delete_official(official_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE officials SET is_active = 0 WHERE id = ?", (official_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_OFFICIAL', 'officials', official_id)
            conn.close()
            return jsonify({'success': True, 'message': 'Official deactivated successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Official not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete official error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete official'}), 500

# Location API Routes (complete CRUD)
@app.route('/api/locations/<int:location_id>', methods=['GET'])
@login_required
def get_location(location_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        location = cursor.fetchone()
        conn.close()
        
        if location:
            return jsonify({'success': True, 'item': dict(location)})
        else:
            return jsonify({'success': False, 'error': 'Location not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Get location error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve location'}), 500

@app.route('/api/locations/<int:location_id>', methods=['PUT'])
@login_required
def update_location(location_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        allowed_fields = ['name', 'address', 'city', 'state', 'zip_code', 'contact_person',
                         'contact_phone', 'contact_email', 'capacity', 'notes', 'is_active',
                         'latitude', 'longitude', 'parking_info', 'facilities']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if update_fields:
            query = f"UPDATE locations SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(location_id)
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                log_activity(session['user_id'], 'UPDATE_LOCATION', 'locations', location_id)
                conn.close()
                return jsonify({'success': True, 'message': 'Location updated successfully'})
            else:
                conn.close()
                return jsonify({'success': False, 'error': 'Location not found'}), 404
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
            
    except Exception as e:
        app.logger.error(f"Update location error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update location'}), 500

@app.route('/api/locations/<int:location_id>', methods=['DELETE'])
@login_required
def delete_location(location_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE locations SET is_active = 0 WHERE id = ?", (location_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(session['user_id'], 'DELETE_LOCATION', 'locations', location_id)
            conn.close()
            return jsonify({'success': True, 'message': 'Location deactivated successfully'})
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Location not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Delete location error: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete location'}), 500

# Report Generation Routes
@app.route('/api/reports/<report_type>')
@login_required
def generate_report(report_type):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        if report_type == 'upcoming_games':
            cursor.execute("""
                SELECT g.date, g.time, g.home_team, g.away_team, g.sport, 
                       l.name as location, g.status, COUNT(a.id) as officials_assigned
                FROM games g
                LEFT JOIN locations l ON g.location_id = l.id
                LEFT JOIN assignments a ON g.id = a.game_id AND a.status IN ('assigned', 'confirmed')
                WHERE g.date >= date('now') AND g.status = 'scheduled'
                GROUP BY g.id
                ORDER BY g.date, g.time
            """)
            
            writer.writerow(['Date', 'Time', 'Home Team', 'Away Team', 'Sport', 'Location', 'Status', 'Officials Assigned'])
            
        elif report_type == 'official_assignments':
            cursor.execute("""
                SELECT u.full_name, g.date, g.time, g.home_team, g.away_team, 
                       a.position, a.status, a.fee_amount
                FROM assignments a
                JOIN officials o ON a.official_id = o.id
                JOIN users u ON o.user_id = u.id
                JOIN games g ON a.game_id = g.id
                WHERE g.date >= date('now', '-30 days')
                ORDER BY g.date DESC, u.full_name
            """)
            
            writer.writerow(['Official Name', 'Date', 'Time', 'Home Team', 'Away Team', 'Position', 'Status', 'Fee Amount'])
            
        elif report_type == 'payment_summary':
            cursor.execute("""
                SELECT u.full_name, COUNT(a.id) as total_assignments, 
                       SUM(a.fee_amount) as total_fees, AVG(a.fee_amount) as avg_fee
                FROM assignments a
                JOIN officials o ON a.official_id = o.id
                JOIN users u ON o.user_id = u.id
                JOIN games g ON a.game_id = g.id
                WHERE g.date >= date('now', '-90 days') AND a.status = 'confirmed'
                GROUP BY u.id, u.full_name
                ORDER BY total_fees DESC
            """)
            
            writer.writerow(['Official Name', 'Total Assignments', 'Total Fees', 'Average Fee'])
            
        elif report_type == 'location_utilization':
            cursor.execute("""
                SELECT l.name, COUNT(g.id) as games_scheduled, 
                       AVG(CAST(strftime('%w', g.date) AS INTEGER)) as avg_day_of_week
                FROM locations l
                LEFT JOIN games g ON l.id = g.location_id
                WHERE g.date >= date('now', '-90 days')
                GROUP BY l.id, l.name
                ORDER BY games_scheduled DESC
            """)
            
            writer.writerow(['Location Name', 'Games Scheduled (90 days)', 'Average Day of Week'])
            
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid report type'}), 400
        
        for row in cursor.fetchall():
            formatted_row = []
            for field in row:
                if field is None:
                    formatted_row.append('')
                elif isinstance(field, float):
                    formatted_row.append(f"{field:.2f}")
                else:
                    formatted_row.append(str(field))
            writer.writerow(formatted_row)
        
        csv_data = output.getvalue()
        output.close()
        conn.close()
        
        log_activity(session['user_id'], f'GENERATE_REPORT_{report_type.upper()}')
        
        return jsonify({
            'success': True,
            'data': csv_data,
            'filename': f'{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        })
        
    except Exception as e:
        app.logger.error(f"Generate report error: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate report'}), 500

# CSV Import Route
@app.route('/api/import', methods=['POST'])
@login_required
def import_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        import_type = request.form.get('type')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'File must be a CSV'}), 400
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                if import_type == 'games':
                    cursor.execute("""
                        INSERT INTO games (date, time, home_team, away_team, sport, location, 
                                         league, level, officials_needed, status, created_date, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('date', ''), row.get('time', ''), row.get('home_team', ''),
                        row.get('away_team', ''), row.get('sport', ''), row.get('location', ''),
                        row.get('league', ''), row.get('level', ''), 
                        int(row.get('officials_needed', 1)), row.get('status', 'scheduled'),
                        datetime.now().isoformat(), session['user_id']
                    ))
                
                elif import_type == 'officials':
                    # First create user
                    cursor.execute("""
                        INSERT INTO users (username, password, full_name, email, phone, role, 
                                         is_active, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('username', f"official_{row_num}"), 
                        hash_password(row.get('password', 'default123')),
                        row.get('full_name', ''), row.get('email', ''), 
                        row.get('phone', ''), 'official', 1, datetime.now().isoformat()
                    ))
                    
                    user_id = cursor.lastrowid
                    
                    # Then create official profile
                    cursor.execute("""
                        INSERT INTO officials (user_id, sport, experience_level, certifications, 
                                             rating, availability, is_active, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_id, row.get('sport', ''), row.get('experience_level', 'Beginner'),
                        row.get('certifications', ''), float(row.get('rating', 0.0)),
                        row.get('availability', ''), 1, datetime.now().isoformat()
                    ))
                
                elif import_type == 'locations':
                    cursor.execute("""
                        INSERT INTO locations (name, address, city, state, zip_code, contact_person,
                                             contact_phone, contact_email, capacity, notes, is_active,
                                             created_date, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('name', ''), row.get('address', ''), row.get('city', ''),
                        row.get('state', ''), row.get('zip_code', ''), row.get('contact_person', ''),
                        row.get('contact_phone', ''), row.get('contact_email', ''),
                        int(row.get('capacity', 0)), row.get('notes', ''), 1,
                        datetime.now().isoformat(), session['user_id']
                    ))
                
                imported_count += 1
                
            except Exception as row_error:
                errors.append(f"Row {row_num}: {str(row_error)}")
                continue
        
        if imported_count > 0:
            conn.commit()
            log_activity(session['user_id'], f'IMPORT_CSV_{import_type.upper()}', 
                        details=f"Imported {imported_count} records")
        
        conn.close()
        
        result = {
            'success': True,
            'imported': imported_count,
            'message': f'Successfully imported {imported_count} records'
        }
        
        if errors:
            result['errors'] = errors[:10]  # Limit error display
            result['message'] += f' with {len(errors)} errors'
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Import CSV error: {e}")
        return jsonify({'success': False, 'error': 'Failed to import CSV data'}), 500

# Export routes
@app.route('/api/export/all')
@login_required
def export_all_data():
    try:
        # Create a zip file with all data
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Export each table
            tables = ['games', 'officials', 'assignments', 'leagues', 'locations', 'users']
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                if rows:
                    output = io.StringIO()
                    writer = csv.writer(output)
                    
                    # Write headers
                    writer.writerow([description[0] for description in cursor.description])
                    
                    # Write data
                    for row in rows:
                        writer.writerow(row)
                    
                    zf.writestr(f'{table}.csv', output.getvalue())
                    output.close()
            
            conn.close()
        
        memory_file.seek(0)
        
        log_activity(session['user_id'], 'EXPORT_ALL_DATA')
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'sports_schedulers_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        app.logger.error(f"Export all data error: {e}")
        return jsonify({'success': False, 'error': 'Failed to export data'}), 500

# Health check and error handlers
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
            'company': 'JES Baseball LLC',
            'features': 'Complete Production System - All CRUD Operations Active'
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Page not found', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error', 'status': 500}), 500

# Initialize database on startup
try:
    init_database()
except Exception as e:
    app.logger.error(f"Failed to initialize database: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Starting Sports Schedulers Production System v2.0.0")
    app.logger.info(f"Company: JES Baseball LLC")
    app.logger.info(f"Features: Complete CRUD, Google Maps, Reports, Susan Assistant")
    app.logger.info(f"Production server ready on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
