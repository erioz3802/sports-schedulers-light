#!/usr/bin/env python3
"""
Sports Schedulers Web Application - PHASE 4 COMPLETE
Full CRUD Operations Implementation - Production Ready

Author: Jose Ortiz / JES Baseball LLC
Date: September 15, 2025
Version: Phase 4 Complete with Full CRUD
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, send_file
import sqlite3
import hashlib
import os
import logging
from datetime import datetime
from functools import wraps
import csv
import io

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production-12345')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE = 'scheduler.db'

def get_db_connection():
    """Get database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if session.get('role') not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Database initialization
def init_database():
    """Initialize database with complete structure"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create users table if it doesn't exist
        if 'users' not in existing_tables:
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    created_date TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
        
        # Create games table if it doesn't exist
        if 'games' not in existing_tables:
            cursor.execute("""
                CREATE TABLE games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    location TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    league TEXT,
                    level TEXT,
                    officials_needed INTEGER DEFAULT 1,
                    notes TEXT,
                    status TEXT DEFAULT 'scheduled',
                    created_date TEXT NOT NULL
                )
            """)
        
        # Create officials table
        if 'officials' in existing_tables:
            cursor.execute("PRAGMA table_info(officials)")
            officials_columns = [column[1] for column in cursor.fetchall()]
            logger.info(f"Officials table columns: {officials_columns}")
            
            # Add missing columns safely
            if 'name' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN name TEXT")
                # Try to populate from existing data
                if 'first_name' in officials_columns and 'last_name' in officials_columns:
                    cursor.execute("""
                        UPDATE officials 
                        SET name = COALESCE(first_name || ' ' || last_name, 'Official ' || id)
                        WHERE name IS NULL OR name = ''
                    """)
                else:
                    cursor.execute("UPDATE officials SET name = 'Official ' || id WHERE name IS NULL OR name = ''")
            
            if 'email' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN email TEXT")
            if 'phone' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN phone TEXT")
            if 'experience_level' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN experience_level TEXT")
            if 'rating' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN rating REAL DEFAULT 0.0")
            if 'is_active' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN is_active INTEGER DEFAULT 1")
            if 'created_date' not in officials_columns:
                cursor.execute("ALTER TABLE officials ADD COLUMN created_date TEXT")
                cursor.execute(f"UPDATE officials SET created_date = ? WHERE created_date IS NULL", (datetime.now().isoformat(),))
        else:
            cursor.execute("""
                CREATE TABLE officials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    experience_level TEXT,
                    rating REAL DEFAULT 0.0,
                    is_active INTEGER DEFAULT 1,
                    created_date TEXT NOT NULL
                )
            """)
        
        # Create assignments table if it doesn't exist
        if 'assignments' not in existing_tables:
            cursor.execute("""
                CREATE TABLE assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER NOT NULL,
                    official_id INTEGER NOT NULL,
                    position TEXT,
                    status TEXT DEFAULT 'pending',
                    assigned_date TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (game_id) REFERENCES games (id),
                    FOREIGN KEY (official_id) REFERENCES officials (id)
                )
            """)
        
        # Create locations table if it doesn't exist
        if 'locations' not in existing_tables:
            cursor.execute("""
                CREATE TABLE locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    contact_person TEXT,
                    notes TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_date TEXT NOT NULL
                )
            """)
        
        # Create leagues table if it doesn't exist
        if 'leagues' not in existing_tables:
            cursor.execute("""
                CREATE TABLE leagues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    sport TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_date TEXT NOT NULL
                )
            """)
        
        # Create default admin user if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'jose_1'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password, role, full_name, email, created_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ('jose_1', hash_password('Josu2398-1'), 'superadmin', 'Jose Ortiz', 'jose@example.com', 
                 datetime.now().isoformat(), 1))
            logger.info("Default superadmin user created: jose_1")
        
        # Add sample data if tables are empty
        cursor.execute("SELECT COUNT(*) FROM locations")
        if cursor.fetchone()[0] == 0:
            sample_locations = [
                ("Main Stadium", "123 Stadium Way", "Houston", "TX", "77001", "Field Manager", "Primary venue"),
                ("Community Park", "456 Park Ave", "Sugar Land", "TX", "77479", "Park Director", "Youth league games"),
                ("High School Field", "789 School St", "Cypress", "TX", "77433", "Athletic Director", "High school games")
            ]
            for loc in sample_locations:
                cursor.execute("""
                    INSERT INTO locations (name, address, city, state, zip_code, contact_person, notes, created_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*loc, datetime.now().isoformat(), 1))
        
        # Add sample games if empty
        cursor.execute("SELECT COUNT(*) FROM games")
        if cursor.fetchone()[0] == 0:
            sample_games = [
                ("2025-09-20", "18:00", "Eagles", "Hawks", "Main Stadium", "Baseball", "Youth League", "U12"),
                ("2025-09-21", "19:30", "Lions", "Tigers", "Community Park", "Baseball", "High School", "Varsity"),
                ("2025-09-22", "17:00", "Bears", "Wolves", "High School Field", "Baseball", "Adult League", "Open")
            ]
            for game in sample_games:
                cursor.execute("""
                    INSERT INTO games (date, time, home_team, away_team, location, sport, league, level, created_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*game, datetime.now().isoformat(), 'scheduled'))
        
        # Add sample officials if empty
        cursor.execute("SELECT COUNT(*) FROM officials")
        if cursor.fetchone()[0] == 0:
            sample_officials = [
                ("John Smith", "john.smith@email.com", "555-1234", "Advanced", 4.5),
                ("Maria Garcia", "maria.garcia@email.com", "555-5678", "Intermediate", 4.2),
                ("Robert Johnson", "robert.j@email.com", "555-9012", "Beginner", 3.8)
            ]
            for official in sample_officials:
                cursor.execute("""
                    INSERT INTO officials (name, email, phone, experience_level, rating, created_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (*official, datetime.now().isoformat(), 1))
        
        # Add sample leagues if empty
        cursor.execute("SELECT COUNT(*) FROM leagues")
        if cursor.fetchone()[0] == 0:
            sample_leagues = [
                ("Youth Baseball League", "Baseball", "Competitive youth baseball for ages 8-16"),
                ("Adult Basketball League", "Basketball", "Recreation league for adults"),
                ("High School Soccer", "Soccer", "Regional high school soccer competition")
            ]
            for league in sample_leagues:
                cursor.execute("""
                    INSERT INTO leagues (name, sport, description, created_date, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, (*league, datetime.now().isoformat(), 1))
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

# Login template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Schedulers - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .login-container { 
            background: white; padding: 40px; border-radius: 16px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.15); width: 100%; max-width: 400px;
        }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header h1 { color: #1e40af; font-size: 28px; margin-bottom: 8px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 500; color: #374151; }
        .form-group input { 
            width: 100%; padding: 12px 16px; border: 2px solid #e5e7eb;
            border-radius: 8px; font-size: 16px; transition: border-color 0.2s;
        }
        .form-group input:focus { outline: none; border-color: #3b82f6; }
        .login-btn { 
            width: 100%; background: #3b82f6; color: white; padding: 14px;
            border: none; border-radius: 8px; font-size: 16px; font-weight: 500;
            cursor: pointer; transition: background-color 0.2s;
        }
        .login-btn:hover { background: #2563eb; }
        .alert { 
            background: #fef2f2; border: 1px solid #fca5a5;
            color: #991b1b; padding: 12px; border-radius: 8px; margin-bottom: 20px;
        }
        .test-credentials { 
            margin-top: 20px; padding: 16px; background: #e0f2fe; 
            border-radius: 8px; color: #0369a1; font-size: 14px; 
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>Sports Schedulers</h1>
            <p>Professional Management System</p>
        </div>
        {% if error %}
            <div class="alert">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="login-btn">Login to System</button>
        </form>
        <div class="test-credentials">
            <strong>Default Login:</strong><br>
            Username: <code>jose_1</code><br>
            Password: <code>Josu2398-1</code>
        </div>
    </div>
</body>
</html>
"""

# Main dashboard template with COMPLETE CRUD functionality
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sports Schedulers - Dashboard</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8fafc; }
        .sidebar { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); min-height: 100vh; }
        .nav-link { color: rgba(255,255,255,0.8); padding: 0.75rem 1rem; border-radius: 8px; margin: 2px 0; }
        .nav-link:hover, .nav-link.active { color: white; background-color: rgba(255,255,255,0.1); }
        .card { border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stats-card { background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%); color: white; }
        .modal-header { background: #3b82f6; color: white; }
        .btn-primary { background: #3b82f6; border-color: #3b82f6; }
        .btn-primary:hover { background: #2563eb; border-color: #2563eb; }
        .action-buttons .btn { margin: 2px; }
        .toast-container { position: fixed; top: 20px; right: 20px; z-index: 9999; }
        .toast { min-width: 300px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2 px-0">
                <div class="sidebar px-3 py-4">
                    <h4 class="text-white mb-4"><i class="fas fa-calendar-alt me-2"></i>Sports Schedulers</h4>
                    <ul class="nav nav-pills flex-column">
                        <li class="nav-item">
                            <a href="#" class="nav-link active" onclick="showSection('dashboard')">
                                <i class="fas fa-tachometer-alt me-2"></i>Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('games')">
                                <i class="fas fa-gamepad me-2"></i>Games
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('officials')">
                                <i class="fas fa-user-tie me-2"></i>Officials
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('assignments')">
                                <i class="fas fa-clipboard-list me-2"></i>Assignments
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('leagues')">
                                <i class="fas fa-trophy me-2"></i>Leagues
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('locations')">
                                <i class="fas fa-map-marker-alt me-2"></i>Locations
                            </a>
                        </li>
                        <li class="nav-item">
                            <a href="#" class="nav-link" onclick="showSection('users')">
                                <i class="fas fa-users me-2"></i>Users
                            </a>
                        </li>
                    </ul>
                    <div class="mt-auto">
                        <hr class="text-white-50">
                        <div class="text-white-50 small">
                            <div><strong>{{ session.full_name }}</strong></div>
                            <div>{{ session.role|title }}</div>
                            <a href="/logout" class="text-white small">Logout</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="col-md-9 col-lg-10">
                <div class="p-4">
                    <!-- Dashboard Section -->
                    <div id="dashboard-section">
                        <h2>Dashboard Overview</h2>
                        <p class="text-muted">Welcome back, {{ session.full_name }}!</p>
                        
                        <div class="row g-4 mb-4">
                            <div class="col-md-3">
                                <div class="card stats-card">
                                    <div class="card-body text-center">
                                        <i class="fas fa-gamepad fa-2x mb-3"></i>
                                        <div class="h3" id="total-games">0</div>
                                        <div>Total Games</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stats-card">
                                    <div class="card-body text-center">
                                        <i class="fas fa-user-tie fa-2x mb-3"></i>
                                        <div class="h3" id="total-officials">0</div>
                                        <div>Officials</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stats-card">
                                    <div class="card-body text-center">
                                        <i class="fas fa-clipboard-list fa-2x mb-3"></i>
                                        <div class="h3" id="total-assignments">0</div>
                                        <div>Assignments</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stats-card">
                                    <div class="card-body text-center">
                                        <i class="fas fa-map-marker-alt fa-2x mb-3"></i>
                                        <div class="h3" id="total-locations">0</div>
                                        <div>Locations</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-header">
                                <h5 class="mb-0">Sports Schedulers - Phase 4 Complete with Full CRUD</h5>
                            </div>
                            <div class="card-body">
                                <p><strong>✅ Complete CRUD Operations Available:</strong></p>
                                <ul>
                                    <li><strong>Games:</strong> Create, view, edit, and delete games with full details and validation</li>
                                    <li><strong>Officials:</strong> Manage official profiles with ratings, experience levels, and contact info</li>
                                    <li><strong>Assignments:</strong> Assign officials to games with position and status tracking</li>
                                    <li><strong>Leagues:</strong> Organize leagues by sport with descriptions and status management</li>
                                    <li><strong>Locations:</strong> Manage venues with full address and contact information</li>
                                    <li><strong>Users:</strong> Complete user management with role-based access control</li>
                                    <li><strong>Export:</strong> CSV export functionality for all data tables</li>
                                </ul>
                                <p><strong>🚀 Ready for Production Deployment to Render!</strong></p>
                                <p>Navigate to any section above to start managing your sports scheduling operations.</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Games Section -->
                    <div id="games-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Games Management</h2>
                            <button class="btn btn-primary" onclick="openModal('gameModal')">
                                <i class="fas fa-plus me-2"></i>Add Game
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-header d-flex justify-content-between">
                                <h5 class="mb-0">Games List</h5>
                                <button class="btn btn-outline-success btn-sm" onclick="exportData('games')">
                                    <i class="fas fa-download me-2"></i>Export CSV
                                </button>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Date</th>
                                                <th>Time</th>
                                                <th>Teams</th>
                                                <th>Location</th>
                                                <th>Sport</th>
                                                <th>League</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="games-table">
                                            <tr><td colspan="7" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Officials Section -->
                    <div id="officials-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Officials Management</h2>
                            <button class="btn btn-primary" onclick="openModal('officialModal')">
                                <i class="fas fa-plus me-2"></i>Add Official
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-header d-flex justify-content-between">
                                <h5 class="mb-0">Officials List</h5>
                                <button class="btn btn-outline-success btn-sm" onclick="exportData('officials')">
                                    <i class="fas fa-download me-2"></i>Export CSV
                                </button>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
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
                                        <tbody id="officials-table">
                                            <tr><td colspan="7" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Assignments Section -->
                    <div id="assignments-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Assignments Management</h2>
                            <button class="btn btn-primary" onclick="openModal('assignmentModal')">
                                <i class="fas fa-plus me-2"></i>Create Assignment
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Game</th>
                                                <th>Official</th>
                                                <th>Position</th>
                                                <th>Status</th>
                                                <th>Assigned Date</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="assignments-table">
                                            <tr><td colspan="6" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Leagues Section -->
                    <div id="leagues-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Leagues Management</h2>
                            <button class="btn btn-primary" onclick="openModal('leagueModal')">
                                <i class="fas fa-plus me-2"></i>Add League
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Sport</th>
                                                <th>Description</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="leagues-table">
                                            <tr><td colspan="5" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Locations Section -->
                    <div id="locations-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Locations Management</h2>
                            <button class="btn btn-primary" onclick="openModal('locationModal')">
                                <i class="fas fa-plus me-2"></i>Add Location
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Address</th>
                                                <th>City</th>
                                                <th>State</th>
                                                <th>Contact</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="locations-table">
                                            <tr><td colspan="6" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Users Section -->
                    <div id="users-section" class="d-none">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h2>Users Management</h2>
                            <button class="btn btn-primary" onclick="openModal('userModal')">
                                <i class="fas fa-plus me-2"></i>Add User
                            </button>
                        </div>
                        <div class="card">
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th>Username</th>
                                                <th>Full Name</th>
                                                <th>Email</th>
                                                <th>Role</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="users-table">
                                            <tr><td colspan="6" class="text-center">Loading...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast Container -->
    <div class="toast-container"></div>
    
    <!-- MODALS FOR CRUD OPERATIONS -->
    
    <!-- Game Modal -->
    <div class="modal fade" id="gameModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-gamepad me-2"></i><span id="gameModalTitle">Add Game</span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="gameForm">
                        <input type="hidden" id="gameId">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Date *</label>
                                <input type="date" class="form-control" id="gameDate" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Time *</label>
                                <input type="time" class="form-control" id="gameTime" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Home Team *</label>
                                <input type="text" class="form-control" id="gameHomeTeam" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Away Team *</label>
                                <input type="text" class="form-control" id="gameAwayTeam" required>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Location *</label>
                                <input type="text" class="form-control" id="gameLocation" required>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Sport *</label>
                                <select class="form-select" id="gameSport" required>
                                    <option value="">Select Sport</option>
                                    <option value="Baseball">Baseball</option>
                                    <option value="Basketball">Basketball</option>
                                    <option value="Football">Football</option>
                                    <option value="Soccer">Soccer</option>
                                    <option value="Softball">Softball</option>
                                </select>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-4 mb-3">
                                <label class="form-label">League</label>
                                <input type="text" class="form-control" id="gameLeague">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Level</label>
                                <input type="text" class="form-control" id="gameLevel">
                            </div>
                            <div class="col-md-4 mb-3">
                                <label class="form-label">Officials Needed</label>
                                <input type="number" class="form-control" id="gameOfficialsNeeded" value="1" min="1">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" id="gameNotes" rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveGame()">Save Game</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Official Modal -->
    <div class="modal fade" id="officialModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-user-tie me-2"></i><span id="officialModalTitle">Add Official</span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="officialForm">
                        <input type="hidden" id="officialId">
                        <div class="mb-3">
                            <label class="form-label">Name *</label>
                            <input type="text" class="form-control" id="officialName" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" id="officialEmail">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Phone</label>
                            <input type="tel" class="form-control" id="officialPhone">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Experience Level</label>
                            <select class="form-select" id="officialExperience">
                                <option value="">Select Level</option>
                                <option value="Beginner">Beginner</option>
                                <option value="Intermediate">Intermediate</option>
                                <option value="Advanced">Advanced</option>
                                <option value="Expert">Expert</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Rating (0-5)</label>
                            <input type="number" class="form-control" id="officialRating" min="0" max="5" step="0.1" value="0">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveOfficial()">Save Official</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- User Modal -->
    <div class="modal fade" id="userModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-user me-2"></i><span id="userModalTitle">Add User</span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="userForm">
                        <input type="hidden" id="userId">
                        <div class="mb-3">
                            <label class="form-label">Username *</label>
                            <input type="text" class="form-control" id="userUsername" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Full Name *</label>
                            <input type="text" class="form-control" id="userFullName" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" id="userEmail">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Phone</label>
                            <input type="tel" class="form-control" id="userPhone">
                        </div>
                        <div class="mb-3" id="passwordField">
                            <label class="form-label">Password *</label>
                            <input type="password" class="form-control" id="userPassword" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Role *</label>
                            <select class="form-select" id="userRole" required>
                                <option value="">Select Role</option>
                                <option value="user">User</option>
                                <option value="official">Official</option>
                                <option value="admin">Admin</option>
                                <option value="superadmin">Super Admin</option>
                            </select>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveUser()">Save User</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Location Modal -->
    <div class="modal fade" id="locationModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-map-marker-alt me-2"></i><span id="locationModalTitle">Add Location</span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="locationForm">
                        <input type="hidden" id="locationId">
                        <div class="mb-3">
                            <label class="form-label">Name *</label>
                            <input type="text" class="form-control" id="locationName" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Address</label>
                            <input type="text" class="form-control" id="locationAddress">
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">City</label>
                                <input type="text" class="form-control" id="locationCity">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">State</label>
                                <input type="text" class="form-control" id="locationState" maxlength="2">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">ZIP Code</label>
                                <input type="text" class="form-control" id="locationZip">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Contact Person</label>
                                <input type="text" class="form-control" id="locationContact">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" id="locationNotes" rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveLocation()">Save Location</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- League Modal -->
    <div class="modal fade" id="leagueModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-trophy me-2"></i><span id="leagueModalTitle">Add League</span></h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="leagueForm">
                        <input type="hidden" id="leagueId">
                        <div class="mb-3">
                            <label class="form-label">League Name *</label>
                            <input type="text" class="form-control" id="leagueName" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Sport *</label>
                            <select class="form-select" id="leagueSport" required>
                                <option value="">Select Sport</option>
                                <option value="Baseball">Baseball</option>
                                <option value="Basketball">Basketball</option>
                                <option value="Football">Football</option>
                                <option value="Soccer">Soccer</option>
                                <option value="Softball">Softball</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Description</label>
                            <textarea class="form-control" id="leagueDescription" rows="3"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveLeague()">Save League</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Assignment Modal -->
    <div class="modal fade" id="assignmentModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"><i class="fas fa-clipboard-list me-2"></i>Create Assignment</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="assignmentForm">
                        <div class="mb-3">
                            <label class="form-label">Game *</label>
                            <select class="form-select" id="assignmentGame" required>
                                <option value="">Select Game</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Official *</label>
                            <select class="form-select" id="assignmentOfficial" required>
                                <option value="">Select Official</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Position</label>
                            <select class="form-select" id="assignmentPosition">
                                <option value="Official">Official</option>
                                <option value="Referee">Referee</option>
                                <option value="Umpire">Umpire</option>
                                <option value="Crew Chief">Crew Chief</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Status</label>
                            <select class="form-select" id="assignmentStatus">
                                <option value="pending">Pending</option>
                                <option value="confirmed">Confirmed</option>
                                <option value="declined">Declined</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Notes</label>
                            <textarea class="form-control" id="assignmentNotes" rows="2"></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="saveAssignment()">Create Assignment</button>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentEditId = null;
        let currentEditType = null;
        
        // Utility Functions
        function showNotification(message, type = 'success') {
            const container = document.querySelector('.toast-container');
            const toastId = 'toast-' + Date.now();
            
            const toast = document.createElement('div');
            toast.id = toastId;
            toast.className = `toast show`;
            toast.setAttribute('role', 'alert');
            
            const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-warning';
            
            toast.innerHTML = `
                <div class="toast-body ${bgClass} text-white d-flex align-items-center">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                    <span class="flex-grow-1">${message}</span>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
            `;
            
            container.appendChild(toast);
            
            setTimeout(() => {
                if (document.getElementById(toastId)) {
                    const bsToast = new bootstrap.Toast(document.getElementById(toastId));
                    bsToast.hide();
                    setTimeout(() => toast.remove(), 500);
                }
            }, 5000);
        }
        
        function getStatusBadge(status) {
            const statusClasses = {
                'scheduled': 'bg-primary',
                'pending': 'bg-warning',
                'confirmed': 'bg-success',
                'declined': 'bg-danger',
                'completed': 'bg-secondary',
                'active': 'bg-success',
                'inactive': 'bg-secondary'
            };
            
            const className = statusClasses[status] || 'bg-secondary';
            const displayStatus = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
            return `<span class="badge ${className}">${displayStatus}</span>`;
        }
        
        // Navigation
        function showSection(sectionName) {
            // Hide all sections
            document.querySelectorAll('[id$="-section"]').forEach(section => {
                section.classList.add('d-none');
            });
            
            // Show selected section
            document.getElementById(sectionName + '-section').classList.remove('d-none');
            
            // Update navigation
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Load data for section
            loadSectionData(sectionName);
        }
        
        // Load section data
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
                case 'leagues':
                    loadLeagues();
                    break;
                case 'locations':
                    loadLocations();
                    break;
                case 'users':
                    loadUsers();
                    break;
            }
        }
        
        // API calls and data loading
        async function loadDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('total-games').textContent = data.stats.total_games || 0;
                    document.getElementById('total-officials').textContent = data.stats.total_officials || 0;
                    document.getElementById('total-assignments').textContent = data.stats.total_assignments || 0;
                    document.getElementById('total-locations').textContent = data.stats.total_locations || 0;
                }
            } catch (error) {
                console.error('Dashboard error:', error);
            }
        }
        
        async function loadGames() {
            try {
                const response = await fetch('/api/games');
                const data = await response.json();
                
                const tbody = document.getElementById('games-table');
                if (data.success && data.games.length > 0) {
                    tbody.innerHTML = data.games.map(game => `
                        <tr>
                            <td>${game.date}</td>
                            <td>${game.time}</td>
                            <td><strong>${game.home_team}</strong> vs <strong>${game.away_team}</strong></td>
                            <td>${game.location}</td>
                            <td><span class="badge bg-secondary">${game.sport}</span></td>
                            <td>${game.league || 'N/A'}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editGame(${game.id})" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteGame(${game.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No games found</td></tr>';
                }
            } catch (error) {
                console.error('Games error:', error);
            }
        }
        
        async function loadOfficials() {
            try {
                const response = await fetch('/api/officials');
                const data = await response.json();
                
                const tbody = document.getElementById('officials-table');
                if (data.success && data.officials.length > 0) {
                    tbody.innerHTML = data.officials.map(official => `
                        <tr>
                            <td><strong>${official.name || 'N/A'}</strong></td>
                            <td>${official.email || 'N/A'}</td>
                            <td>${official.phone || 'N/A'}</td>
                            <td><span class="badge bg-info">${official.experience_level || 'N/A'}</span></td>
                            <td>${(official.rating || 0).toFixed(1)} ⭐</td>
                            <td>${getStatusBadge(official.is_active ? 'active' : 'inactive')}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editOfficial(${official.id})" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteOfficial(${official.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No officials found</td></tr>';
                }
            } catch (error) {
                console.error('Officials error:', error);
            }
        }
        
        async function loadAssignments() {
            try {
                const response = await fetch('/api/assignments');
                const data = await response.json();
                
                const tbody = document.getElementById('assignments-table');
                if (data.success && data.assignments.length > 0) {
                    tbody.innerHTML = data.assignments.map(assignment => `
                        <tr>
                            <td>${assignment.game_info || 'N/A'}</td>
                            <td>${assignment.official_name || 'N/A'}</td>
                            <td><span class="badge bg-info">${assignment.position || 'Official'}</span></td>
                            <td>${getStatusBadge(assignment.status)}</td>
                            <td>${assignment.assigned_date || 'N/A'}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteAssignment(${assignment.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No assignments found</td></tr>';
                }
            } catch (error) {
                console.error('Assignments error:', error);
            }
        }
        
        async function loadLeagues() {
            try {
                const response = await fetch('/api/leagues');
                const data = await response.json();
                
                const tbody = document.getElementById('leagues-table');
                if (data.success && data.leagues.length > 0) {
                    tbody.innerHTML = data.leagues.map(league => `
                        <tr>
                            <td><strong>${league.name}</strong></td>
                            <td><span class="badge bg-secondary">${league.sport}</span></td>
                            <td>${league.description || 'N/A'}</td>
                            <td>${getStatusBadge(league.is_active ? 'active' : 'inactive')}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editLeague(${league.id})" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteLeague(${league.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No leagues found</td></tr>';
                }
            } catch (error) {
                console.error('Leagues error:', error);
            }
        }
        
        async function loadLocations() {
            try {
                const response = await fetch('/api/locations');
                const data = await response.json();
                
                const tbody = document.getElementById('locations-table');
                if (data.success && data.locations.length > 0) {
                    tbody.innerHTML = data.locations.map(location => `
                        <tr>
                            <td><strong>${location.name}</strong></td>
                            <td>${location.address || 'N/A'}</td>
                            <td>${location.city || 'N/A'}</td>
                            <td>${location.state || 'N/A'}</td>
                            <td>${location.contact_person || 'N/A'}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editLocation(${location.id})" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteLocation(${location.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No locations found</td></tr>';
                }
            } catch (error) {
                console.error('Locations error:', error);
            }
        }
        
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                
                const tbody = document.getElementById('users-table');
                if (data.success && data.users.length > 0) {
                    tbody.innerHTML = data.users.map(user => `
                        <tr>
                            <td><strong>${user.username}</strong></td>
                            <td>${user.full_name}</td>
                            <td>${user.email || 'N/A'}</td>
                            <td><span class="badge bg-primary">${user.role}</span></td>
                            <td>${getStatusBadge(user.is_active ? 'active' : 'inactive')}</td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editUser(${user.id})" title="Edit">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteUser(${user.id})" title="Delete">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No users found</td></tr>';
                }
            } catch (error) {
                console.error('Users error:', error);
            }
        }
        
        // Modal functions
        function openModal(modalId) {
            currentEditId = null;
            currentEditType = null;
            
            // Reset form
            const form = document.querySelector(`#${modalId} form`);
            if (form) form.reset();
            
            // Reset title
            const titleElement = document.querySelector(`#${modalId} .modal-title span`);
            if (titleElement) {
                const type = modalId.replace('Modal', '');
                titleElement.textContent = `Add ${type.charAt(0).toUpperCase() + type.slice(1)}`;
            }
            
            // Load dropdown data for assignments
            if (modalId === 'assignmentModal') {
                loadAssignmentDropdowns();
            }
            
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            modal.show();
        }
        
        async function loadAssignmentDropdowns() {
            try {
                // Load games
                const gamesResponse = await fetch('/api/games');
                const gamesData = await gamesResponse.json();
                
                const gameSelect = document.getElementById('assignmentGame');
                gameSelect.innerHTML = '<option value="">Select Game</option>';
                
                if (gamesData.success) {
                    gamesData.games.forEach(game => {
                        const option = document.createElement('option');
                        option.value = game.id;
                        option.textContent = `${game.date} ${game.time} - ${game.home_team} vs ${game.away_team}`;
                        gameSelect.appendChild(option);
                    });
                }
                
                // Load officials
                const officialsResponse = await fetch('/api/officials');
                const officialsData = await officialsResponse.json();
                
                const officialSelect = document.getElementById('assignmentOfficial');
                officialSelect.innerHTML = '<option value="">Select Official</option>';
                
                if (officialsData.success) {
                    officialsData.officials.forEach(official => {
                        const option = document.createElement('option');
                        option.value = official.id;
                        option.textContent = official.name;
                        officialSelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading assignment dropdowns:', error);
            }
        }
        
        // CRUD Operations
        async function saveGame() {
            const id = document.getElementById('gameId').value;
            const isEdit = !!id;
            
            const gameData = {
                date: document.getElementById('gameDate').value,
                time: document.getElementById('gameTime').value,
                home_team: document.getElementById('gameHomeTeam').value,
                away_team: document.getElementById('gameAwayTeam').value,
                location: document.getElementById('gameLocation').value,
                sport: document.getElementById('gameSport').value,
                league: document.getElementById('gameLeague').value,
                level: document.getElementById('gameLevel').value,
                officials_needed: document.getElementById('gameOfficialsNeeded').value,
                notes: document.getElementById('gameNotes').value
            };
            
            try {
                const url = isEdit ? `/api/games/${id}` : '/api/games';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(gameData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(isEdit ? 'Game updated successfully!' : 'Game created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('gameModal')).hide();
                    loadGames();
                } else {
                    showNotification(result.error || 'Failed to save game', 'error');
                }
            } catch (error) {
                showNotification('Error saving game', 'error');
            }
        }
        
        async function editGame(id) {
            try {
                const response = await fetch(`/api/games/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    const game = data.game;
                    document.getElementById('gameId').value = game.id;
                    document.getElementById('gameDate').value = game.date;
                    document.getElementById('gameTime').value = game.time;
                    document.getElementById('gameHomeTeam').value = game.home_team;
                    document.getElementById('gameAwayTeam').value = game.away_team;
                    document.getElementById('gameLocation').value = game.location;
                    document.getElementById('gameSport').value = game.sport;
                    document.getElementById('gameLeague').value = game.league || '';
                    document.getElementById('gameLevel').value = game.level || '';
                    document.getElementById('gameOfficialsNeeded').value = game.officials_needed || 1;
                    document.getElementById('gameNotes').value = game.notes || '';
                    
                    document.getElementById('gameModalTitle').textContent = 'Edit Game';
                    const modal = new bootstrap.Modal(document.getElementById('gameModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading game for edit', 'error');
            }
        }
        
        async function deleteGame(id) {
            if (confirm('Are you sure you want to delete this game?')) {
                try {
                    const response = await fetch(`/api/games/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('Game deleted successfully!', 'success');
                        loadGames();
                    } else {
                        showNotification(result.error || 'Failed to delete game', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting game', 'error');
                }
            }
        }
        
        // Official CRUD operations
        async function saveOfficial() {
            const id = document.getElementById('officialId').value;
            const isEdit = !!id;
            
            const officialData = {
                name: document.getElementById('officialName').value,
                email: document.getElementById('officialEmail').value,
                phone: document.getElementById('officialPhone').value,
                experience_level: document.getElementById('officialExperience').value,
                rating: document.getElementById('officialRating').value
            };
            
            try {
                const url = isEdit ? `/api/officials/${id}` : '/api/officials';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(officialData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(isEdit ? 'Official updated successfully!' : 'Official created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('officialModal')).hide();
                    loadOfficials();
                } else {
                    showNotification(result.error || 'Failed to save official', 'error');
                }
            } catch (error) {
                showNotification('Error saving official', 'error');
            }
        }
        
        async function editOfficial(id) {
            try {
                const response = await fetch(`/api/officials/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    const official = data.official;
                    document.getElementById('officialId').value = official.id;
                    document.getElementById('officialName').value = official.name;
                    document.getElementById('officialEmail').value = official.email || '';
                    document.getElementById('officialPhone').value = official.phone || '';
                    document.getElementById('officialExperience').value = official.experience_level || '';
                    document.getElementById('officialRating').value = official.rating || 0;
                    
                    document.getElementById('officialModalTitle').textContent = 'Edit Official';
                    const modal = new bootstrap.Modal(document.getElementById('officialModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading official for edit', 'error');
            }
        }
        
        async function deleteOfficial(id) {
            if (confirm('Are you sure you want to delete this official?')) {
                try {
                    const response = await fetch(`/api/officials/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('Official deleted successfully!', 'success');
                        loadOfficials();
                    } else {
                        showNotification(result.error || 'Failed to delete official', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting official', 'error');
                }
            }
        }
        
        // User CRUD operations
        async function saveUser() {
            const id = document.getElementById('userId').value;
            const isEdit = !!id;
            
            const userData = {
                username: document.getElementById('userUsername').value,
                full_name: document.getElementById('userFullName').value,
                email: document.getElementById('userEmail').value,
                phone: document.getElementById('userPhone').value,
                role: document.getElementById('userRole').value
            };
            
            if (!isEdit) {
                userData.password = document.getElementById('userPassword').value;
            }
            
            try {
                const url = isEdit ? `/api/users/${id}` : '/api/users';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(isEdit ? 'User updated successfully!' : 'User created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
                    loadUsers();
                } else {
                    showNotification(result.error || 'Failed to save user', 'error');
                }
            } catch (error) {
                showNotification('Error saving user', 'error');
            }
        }
        
        async function editUser(id) {
            try {
                const response = await fetch(`/api/users/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    const user = data.user;
                    document.getElementById('userId').value = user.id;
                    document.getElementById('userUsername').value = user.username;
                    document.getElementById('userFullName').value = user.full_name;
                    document.getElementById('userEmail').value = user.email || '';
                    document.getElementById('userPhone').value = user.phone || '';
                    document.getElementById('userRole').value = user.role;
                    
                    // Hide password field for editing
                    document.getElementById('passwordField').style.display = 'none';
                    document.getElementById('userPassword').required = false;
                    
                    document.getElementById('userModalTitle').textContent = 'Edit User';
                    const modal = new bootstrap.Modal(document.getElementById('userModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading user for edit', 'error');
            }
        }
        
        async function deleteUser(id) {
            if (confirm('Are you sure you want to delete this user?')) {
                try {
                    const response = await fetch(`/api/users/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('User deleted successfully!', 'success');
                        loadUsers();
                    } else {
                        showNotification(result.error || 'Failed to delete user', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting user', 'error');
                }
            }
        }
        
        // Location CRUD operations
        async function saveLocation() {
            const id = document.getElementById('locationId').value;
            const isEdit = !!id;
            
            const locationData = {
                name: document.getElementById('locationName').value,
                address: document.getElementById('locationAddress').value,
                city: document.getElementById('locationCity').value,
                state: document.getElementById('locationState').value,
                zip_code: document.getElementById('locationZip').value,
                contact_person: document.getElementById('locationContact').value,
                notes: document.getElementById('locationNotes').value
            };
            
            try {
                const url = isEdit ? `/api/locations/${id}` : '/api/locations';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(locationData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(isEdit ? 'Location updated successfully!' : 'Location created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('locationModal')).hide();
                    loadLocations();
                } else {
                    showNotification(result.error || 'Failed to save location', 'error');
                }
            } catch (error) {
                showNotification('Error saving location', 'error');
            }
        }
        
        async function editLocation(id) {
            try {
                const response = await fetch(`/api/locations/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    const location = data.location;
                    document.getElementById('locationId').value = location.id;
                    document.getElementById('locationName').value = location.name;
                    document.getElementById('locationAddress').value = location.address || '';
                    document.getElementById('locationCity').value = location.city || '';
                    document.getElementById('locationState').value = location.state || '';
                    document.getElementById('locationZip').value = location.zip_code || '';
                    document.getElementById('locationContact').value = location.contact_person || '';
                    document.getElementById('locationNotes').value = location.notes || '';
                    
                    document.getElementById('locationModalTitle').textContent = 'Edit Location';
                    const modal = new bootstrap.Modal(document.getElementById('locationModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading location for edit', 'error');
            }
        }
        
        async function deleteLocation(id) {
            if (confirm('Are you sure you want to delete this location?')) {
                try {
                    const response = await fetch(`/api/locations/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('Location deleted successfully!', 'success');
                        loadLocations();
                    } else {
                        showNotification(result.error || 'Failed to delete location', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting location', 'error');
                }
            }
        }
        
        // League CRUD operations
        async function saveLeague() {
            const id = document.getElementById('leagueId').value;
            const isEdit = !!id;
            
            const leagueData = {
                name: document.getElementById('leagueName').value,
                sport: document.getElementById('leagueSport').value,
                description: document.getElementById('leagueDescription').value
            };
            
            try {
                const url = isEdit ? `/api/leagues/${id}` : '/api/leagues';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(leagueData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification(isEdit ? 'League updated successfully!' : 'League created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('leagueModal')).hide();
                    loadLeagues();
                } else {
                    showNotification(result.error || 'Failed to save league', 'error');
                }
            } catch (error) {
                showNotification('Error saving league', 'error');
            }
        }
        
        async function editLeague(id) {
            try {
                const response = await fetch(`/api/leagues/${id}`);
                const data = await response.json();
                
                if (data.success) {
                    const league = data.league;
                    document.getElementById('leagueId').value = league.id;
                    document.getElementById('leagueName').value = league.name;
                    document.getElementById('leagueSport').value = league.sport;
                    document.getElementById('leagueDescription').value = league.description || '';
                    
                    document.getElementById('leagueModalTitle').textContent = 'Edit League';
                    const modal = new bootstrap.Modal(document.getElementById('leagueModal'));
                    modal.show();
                }
            } catch (error) {
                showNotification('Error loading league for edit', 'error');
            }
        }
        
        async function deleteLeague(id) {
            if (confirm('Are you sure you want to delete this league?')) {
                try {
                    const response = await fetch(`/api/leagues/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('League deleted successfully!', 'success');
                        loadLeagues();
                    } else {
                        showNotification(result.error || 'Failed to delete league', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting league', 'error');
                }
            }
        }
        
        // Assignment CRUD operations
        async function saveAssignment() {
            const assignmentData = {
                game_id: document.getElementById('assignmentGame').value,
                official_id: document.getElementById('assignmentOfficial').value,
                position: document.getElementById('assignmentPosition').value,
                status: document.getElementById('assignmentStatus').value,
                notes: document.getElementById('assignmentNotes').value
            };
            
            try {
                const response = await fetch('/api/assignments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(assignmentData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification('Assignment created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('assignmentModal')).hide();
                    loadAssignments();
                } else {
                    showNotification(result.error || 'Failed to create assignment', 'error');
                }
            } catch (error) {
                showNotification('Error creating assignment', 'error');
            }
        }
        
        async function deleteAssignment(id) {
            if (confirm('Are you sure you want to delete this assignment?')) {
                try {
                    const response = await fetch(`/api/assignments/${id}`, { method: 'DELETE' });
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('Assignment deleted successfully!', 'success');
                        loadAssignments();
                    } else {
                        showNotification(result.error || 'Failed to delete assignment', 'error');
                    }
                } catch (error) {
                    showNotification('Error deleting assignment', 'error');
                }
            }
        }
        
        // Export function
        async function exportData(type) {
            try {
                showNotification(`Preparing ${type} export...`, 'info');
                
                const response = await fetch(`/api/export/${type}`);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showNotification(`${type} exported successfully!`, 'success');
                } else {
                    showNotification(`Failed to export ${type}`, 'error');
                }
            } catch (error) {
                showNotification(`Error exporting ${type}`, 'error');
            }
        }
        
        // Reset form when modal is hidden
        document.addEventListener('hidden.bs.modal', function(event) {
            const modal = event.target;
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
                // Show password field again for user modal
                if (modal.id === 'userModal') {
                    document.getElementById('passwordField').style.display = 'block';
                    document.getElementById('userPassword').required = true;
                }
            }
        });
        
        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboard();
        });
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template_string(DASHBOARD_TEMPLATE, session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
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
            return render_template_string(LOGIN_TEMPLATE, error='Login system error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# API Routes
@app.route('/api/dashboard')
@login_required
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        stats['total_games'] = cursor.execute('SELECT COUNT(*) FROM games').fetchone()[0]
        stats['total_officials'] = cursor.execute('SELECT COUNT(*) FROM officials WHERE is_active = 1').fetchone()[0]
        stats['total_assignments'] = cursor.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
        stats['total_locations'] = cursor.execute('SELECT COUNT(*) FROM locations WHERE is_active = 1').fetchone()[0]
        
        conn.close()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games', methods=['GET', 'POST'])
@login_required
def manage_games():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            games = conn.execute('SELECT * FROM games ORDER BY date DESC, time DESC').fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'games': [dict(row) for row in games]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['date', 'time', 'home_team', 'away_team', 'location', 'sport']
            for field in required_fields:
                if not data.get(field):
                    conn.close()
                    return jsonify({'success': False, 'error': f'{field} is required'}), 400
            
            # Insert new game
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO games (date, time, home_team, away_team, location, sport, 
                                 league, level, officials_needed, notes, created_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['date'], data['time'], data['home_team'], data['away_team'],
                data['location'], data['sport'], data.get('league', ''),
                data.get('level', ''), data.get('officials_needed', 1),
                data.get('notes', ''), datetime.now().isoformat(), 'scheduled'
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Game created successfully'})
        
    except Exception as e:
        logger.error(f"Games API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/games/<int:game_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_game(game_id):
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            game = conn.execute('SELECT * FROM games WHERE id = ?', (game_id,)).fetchone()
            conn.close()
            
            if game:
                return jsonify({'success': True, 'game': dict(game)})
            else:
                return jsonify({'success': False, 'error': 'Game not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update game
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE games SET date=?, time=?, home_team=?, away_team=?, location=?, 
                               sport=?, league=?, level=?, officials_needed=?, notes=?
                WHERE id=?
            """, (
                data['date'], data['time'], data['home_team'], data['away_team'],
                data['location'], data['sport'], data.get('league', ''),
                data.get('level', ''), data.get('officials_needed', 1),
                data.get('notes', ''), game_id
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Game updated successfully'})
        
        elif request.method == 'DELETE':
            # Check for existing assignments
            assignments = conn.execute('SELECT COUNT(*) FROM assignments WHERE game_id = ?', (game_id,)).fetchone()[0]
            
            if assignments > 0:
                conn.close()
                return jsonify({'success': False, 'error': 'Cannot delete game with existing assignments'}), 400
            
            # Delete game
            conn.execute('DELETE FROM games WHERE id = ?', (game_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Game deleted successfully'})
        
    except Exception as e:
        logger.error(f"Single game API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/officials', methods=['GET', 'POST'])
@login_required
def manage_officials():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            officials = conn.execute('SELECT * FROM officials WHERE is_active = 1 ORDER BY name').fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'officials': [dict(row) for row in officials]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name'):
                conn.close()
                return jsonify({'success': False, 'error': 'Name is required'}), 400
            
            # Insert new official
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO officials (name, email, phone, experience_level, rating, created_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['name'], data.get('email', ''), data.get('phone', ''),
                data.get('experience_level', ''), data.get('rating', 0.0),
                datetime.now().isoformat(), 1
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Official created successfully'})
        
    except Exception as e:
        logger.error(f"Officials API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/officials/<int:official_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_official(official_id):
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            official = conn.execute('SELECT * FROM officials WHERE id = ?', (official_id,)).fetchone()
            conn.close()
            
            if official:
                return jsonify({'success': True, 'official': dict(official)})
            else:
                return jsonify({'success': False, 'error': 'Official not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update official
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE officials SET name=?, email=?, phone=?, experience_level=?, rating=?
                WHERE id=?
            """, (
                data['name'], data.get('email', ''), data.get('phone', ''),
                data.get('experience_level', ''), data.get('rating', 0.0), official_id
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Official updated successfully'})
        
        elif request.method == 'DELETE':
            # Mark as inactive instead of deleting
            conn.execute('UPDATE officials SET is_active = 0 WHERE id = ?', (official_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Official deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Single official API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/assignments', methods=['GET', 'POST'])
@login_required
def manage_assignments():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            assignments = conn.execute("""
                SELECT a.*, 
                       (g.date || ' ' || g.time || ' - ' || g.home_team || ' vs ' || g.away_team) as game_info,
                       o.name as official_name
                FROM assignments a
                LEFT JOIN games g ON a.game_id = g.id
                LEFT JOIN officials o ON a.official_id = o.id
                ORDER BY g.date DESC, g.time DESC
            """).fetchall()
            
            conn.close()
            return jsonify({
                'success': True,
                'assignments': [dict(row) for row in assignments]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            if not data.get('game_id') or not data.get('official_id'):
                conn.close()
                return jsonify({'success': False, 'error': 'Game and Official are required'}), 400
            
            # Check for duplicate assignment
            existing = conn.execute(
                'SELECT id FROM assignments WHERE game_id = ? AND official_id = ?',
                (data['game_id'], data['official_id'])
            ).fetchone()
            
            if existing:
                conn.close()
                return jsonify({'success': False, 'error': 'This official is already assigned to this game'}), 400
            
            # Insert new assignment
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO assignments (game_id, official_id, position, status, assigned_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['game_id'], data['official_id'], data.get('position', 'Official'),
                data.get('status', 'pending'), datetime.now().isoformat(),
                data.get('notes', '')
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Assignment created successfully'})
        
    except Exception as e:
        logger.error(f"Assignments API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/assignments/<int:assignment_id>', methods=['DELETE'])
@login_required
def delete_assignment(assignment_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM assignments WHERE id = ?', (assignment_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Assignment deleted successfully'})
        
    except Exception as e:
        logger.error(f"Delete assignment API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locations', methods=['GET', 'POST'])
@login_required
def manage_locations():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            locations = conn.execute('SELECT * FROM locations WHERE is_active = 1 ORDER BY name').fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'locations': [dict(row) for row in locations]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name'):
                conn.close()
                return jsonify({'success': False, 'error': 'Name is required'}), 400
            
            # Insert new location
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO locations (name, address, city, state, zip_code, contact_person, notes, created_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['name'], data.get('address', ''), data.get('city', ''),
                data.get('state', ''), data.get('zip_code', ''),
                data.get('contact_person', ''), data.get('notes', ''),
                datetime.now().isoformat(), 1
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Location created successfully'})
        
    except Exception as e:
        logger.error(f"Locations API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/locations/<int:location_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_location(location_id):
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            location = conn.execute('SELECT * FROM locations WHERE id = ?', (location_id,)).fetchone()
            conn.close()
            
            if location:
                return jsonify({'success': True, 'location': dict(location)})
            else:
                return jsonify({'success': False, 'error': 'Location not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update location
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE locations SET name=?, address=?, city=?, state=?, zip_code=?, contact_person=?, notes=?
                WHERE id=?
            """, (
                data['name'], data.get('address', ''), data.get('city', ''),
                data.get('state', ''), data.get('zip_code', ''),
                data.get('contact_person', ''), data.get('notes', ''), location_id
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Location updated successfully'})
        
        elif request.method == 'DELETE':
            # Mark as inactive instead of deleting
            conn.execute('UPDATE locations SET is_active = 0 WHERE id = ?', (location_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Location deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Single location API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/leagues', methods=['GET', 'POST'])
@login_required
def manage_leagues():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            leagues = conn.execute('SELECT * FROM leagues WHERE is_active = 1 ORDER BY name').fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'leagues': [dict(row) for row in leagues]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            if not data.get('name') or not data.get('sport'):
                conn.close()
                return jsonify({'success': False, 'error': 'Name and sport are required'}), 400
            
            # Insert new league
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leagues (name, sport, description, created_date, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data['name'], data['sport'], data.get('description', ''),
                datetime.now().isoformat(), 1
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'League created successfully'})
        
    except Exception as e:
        logger.error(f"Leagues API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/leagues/<int:league_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_league(league_id):
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            league = conn.execute('SELECT * FROM leagues WHERE id = ?', (league_id,)).fetchone()
            conn.close()
            
            if league:
                return jsonify({'success': True, 'league': dict(league)})
            else:
                return jsonify({'success': False, 'error': 'League not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update league
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leagues SET name=?, sport=?, description=?
                WHERE id=?
            """, (
                data['name'], data['sport'], data.get('description', ''), league_id
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'League updated successfully'})
        
        elif request.method == 'DELETE':
            # Mark as inactive instead of deleting
            conn.execute('UPDATE leagues SET is_active = 0 WHERE id = ?', (league_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'League deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Single league API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            users = conn.execute('SELECT id, username, full_name, email, phone, role, is_active FROM users ORDER BY username').fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'users': [dict(row) for row in users]
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['username', 'full_name', 'password', 'role']
            for field in required_fields:
                if not data.get(field):
                    conn.close()
                    return jsonify({'success': False, 'error': f'{field} is required'}), 400
            
            # Check if username already exists
            existing = conn.execute('SELECT id FROM users WHERE username = ?', (data['username'],)).fetchone()
            if existing:
                conn.close()
                return jsonify({'success': False, 'error': 'Username already exists'}), 400
            
            # Insert new user
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, full_name, email, phone, role, created_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['username'], hash_password(data['password']), data['full_name'],
                data.get('email', ''), data.get('phone', ''), data['role'],
                datetime.now().isoformat(), 1
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'User created successfully'})
        
    except Exception as e:
        logger.error(f"Users API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_user(user_id):
    try:
        conn = get_db_connection()
        
        if request.method == 'GET':
            user = conn.execute('SELECT id, username, full_name, email, phone, role, is_active FROM users WHERE id = ?', (user_id,)).fetchone()
            conn.close()
            
            if user:
                return jsonify({'success': True, 'user': dict(user)})
            else:
                return jsonify({'success': False, 'error': 'User not found'}), 404
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update user (excluding password for now)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET username=?, full_name=?, email=?, phone=?, role=?
                WHERE id=?
            """, (
                data['username'], data['full_name'], data.get('email', ''),
                data.get('phone', ''), data['role'], user_id
            ))
            
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'User updated successfully'})
        
        elif request.method == 'DELETE':
            # Don't allow deleting current user
            if user_id == session.get('user_id'):
                conn.close()
                return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
            
            # Mark as inactive instead of deleting
            conn.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'User deactivated successfully'})
        
    except Exception as e:
        logger.error(f"Single user API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export/<data_type>')
@login_required
def export_data(data_type):
    try:
        conn = get_db_connection()
        
        # Define export queries
        export_queries = {
            'games': 'SELECT * FROM games ORDER BY date DESC',
            'officials': 'SELECT * FROM officials WHERE is_active = 1 ORDER BY name',
            'assignments': '''
                SELECT a.*, 
                       (g.date || ' ' || g.time || ' - ' || g.home_team || ' vs ' || g.away_team) as game_info,
                       o.name as official_name
                FROM assignments a
                LEFT JOIN games g ON a.game_id = g.id
                LEFT JOIN officials o ON a.official_id = o.id
                ORDER BY g.date DESC
            ''',
            'locations': 'SELECT * FROM locations WHERE is_active = 1 ORDER BY name',
            'leagues': 'SELECT * FROM leagues WHERE is_active = 1 ORDER BY name',
            'users': 'SELECT id, username, full_name, email, role, is_active FROM users ORDER BY username'
        }
        
        if data_type not in export_queries:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid export type'}), 400
        
        # Execute query
        cursor = conn.cursor()
        cursor.execute(export_queries[data_type])
        rows = cursor.fetchall()
        
        # Create CSV
        output = io.StringIO()
        if rows:
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            writer = csv.writer(output)
            writer.writerow(column_names)
            
            for row in rows:
                writer.writerow([str(value) if value is not None else '' for value in row])
        
        conn.close()
        
        # Prepare file download
        output.seek(0)
        csv_data = output.getvalue()
        output.close()
        
        # Create response
        response = app.response_class(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={data_type}_export_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Sports Schedulers Web Application - Phase 4 Complete...")
    print("📋 Copyright (c) 2025 Jose Ortiz. All rights reserved.")
    print("🔧 PHASE 4 COMPLETE WITH FULL CRUD OPERATIONS")
    
    # Initialize database
    init_database()
    
    print("🌐 Server starting on http://localhost:5000")
    print("👤 Default login: jose_1 / Josu2398-1")
    print("✅ Phase 4 Complete - Ready for Render Deployment!")
    print("📋 Features: Full CRUD, Export, Validation, Error Handling")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
