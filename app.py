#!/usr/bin/env python3
"""
Sports Schedulers - Web Application
Author: Jose Ortiz
Date: September 14, 2025
Copyright (c) 2025 Jose Ortiz. All rights reserved.

Professional sports scheduling management system.
"""

import os
import sqlite3
import hashlib
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, session, make_response
import csv
import io

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sports-schedulers-secret-key-2025-jose-ortiz')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# Database Functions
# ===============================

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect('scheduler.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(64) NOT NULL,
            full_name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(20),
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            time TIME NOT NULL,
            home_team VARCHAR(100) NOT NULL,
            away_team VARCHAR(100) NOT NULL,
            location VARCHAR(200),
            sport VARCHAR(50),
            league VARCHAR(100),
            level VARCHAR(50),
            officials_needed INTEGER DEFAULT 1,
            notes TEXT,
            status VARCHAR(20) DEFAULT 'scheduled',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Officials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS officials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,
            sports TEXT,
            experience_level VARCHAR(20),
            rating DECIMAL(3,2),
            is_active BOOLEAN DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Assignments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            official_id INTEGER NOT NULL,
            position VARCHAR(50),
            status VARCHAR(20) DEFAULT 'assigned',
            fee DECIMAL(8,2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id),
            FOREIGN KEY (official_id) REFERENCES officials (id)
        )
    ''')
    
    # Activity log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(50),
            resource_type VARCHAR(50),
            resource_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR(45),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create default superadmin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('jose_1',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, full_name, role, email)
            VALUES (?, ?, ?, ?, ?)
        ''', ('jose_1', hash_password('Josu2398-1'), 'Jose Ortiz', 'superadmin', 'jose@jesbaseball.com'))
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ===============================
# Decorators
# ===============================

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Login required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Login required'}), 401
        if session.get('role') not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ===============================
# Helper Functions
# ===============================

def log_activity(user_id, action, resource_type=None, resource_id=None, details=None):
    """Log user activity"""
    try:
        conn = get_db_connection()
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        conn.execute('''
            INSERT INTO activity_log (user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, action, resource_type, resource_id, details, ip_address))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Activity logging error: {e}")

# ===============================
# Main Routes
# ===============================

@app.route('/')
def home():
    """Home route - redirect to dashboard if logged in, otherwise login"""
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])  
def login():
    """Login route"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('login.html', error='Please enter username and password')
        
        try:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT * FROM users WHERE username = ? AND is_active = 1', 
                (username,)
            ).fetchone()
            
            if user and user['password'] == hash_password(password):
                # Set session
                session['user_id'] = user['id']
                session['username'] = user['username'] 
                session['role'] = user['role']
                session['full_name'] = user['full_name']
                
                # Update last login
                conn.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                           (datetime.now().isoformat(), user['id']))
                conn.commit()
                conn.close()
                
                # Log activity
                log_activity(user['id'], 'LOGIN')
                
                return redirect('/')
            else:
                conn.close()
                return render_template('login.html', error='Invalid username or password')
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template('login.html', error='Login service unavailable')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout route"""
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'LOGOUT')
    session.clear()
    return redirect('/login')

# ===============================
# API Routes
# ===============================

@app.route('/api/dashboard')
@login_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get upcoming games count
        cursor.execute("SELECT COUNT(*) FROM games WHERE date >= date('now') AND status = 'scheduled'")
        upcoming_games = cursor.fetchone()[0]
        
        # Get active officials count
        cursor.execute("SELECT COUNT(*) FROM officials WHERE is_active = 1")
        active_officials = cursor.fetchone()[0]
        
        # Get total assignments count
        cursor.execute("SELECT COUNT(*) FROM assignments WHERE status IN ('assigned', 'confirmed')")
        total_assignments = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'upcoming_games': upcoming_games,
            'active_officials': active_officials,
            'total_assignments': total_assignments
        })
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

@app.route('/api/games', methods=['GET'])
@login_required
def get_games():
    """Get all games"""
    try:
        conn = get_db_connection()
        games = conn.execute('''
            SELECT g.*, u.username as created_by_name
            FROM games g
            LEFT JOIN users u ON g.created_by = u.id
            ORDER BY g.date DESC, g.time DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'games': [dict(game) for game in games]
        })
        
    except Exception as e:
        logger.error(f"Get games error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load games'}), 500

@app.route('/api/games', methods=['POST'])
@login_required
def create_game():
    """Create new game"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO games (date, time, home_team, away_team, location, sport, league, level, officials_needed, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['date'], data['time'], data['home_team'], data['away_team'],
            data.get('location', ''), data.get('sport', ''), data.get('league', ''),
            data.get('level', ''), data.get('officials_needed', 1),
            data.get('notes', ''), session['user_id']
        ))
        
        game_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE', 'game', game_id)
        
        return jsonify({'success': True, 'message': 'Game created successfully', 'id': game_id})
        
    except Exception as e:
        logger.error(f"Create game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create game'}), 500

@app.route('/api/officials', methods=['GET'])
@login_required
def get_officials():
    """Get all officials"""
    try:
        conn = get_db_connection()
        officials = conn.execute('''
            SELECT * FROM officials WHERE is_active = 1 ORDER BY last_name, first_name
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'officials': [dict(official) for official in officials]
        })
        
    except Exception as e:
        logger.error(f"Get officials error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load officials'}), 500

@app.route('/api/assignments', methods=['GET'])
@login_required
def get_assignments():
    """Get all assignments"""
    try:
        conn = get_db_connection()
        assignments = conn.execute('''
            SELECT a.*, g.date, g.time, g.home_team, g.away_team,
                   o.first_name, o.last_name
            FROM assignments a
            LEFT JOIN games g ON a.game_id = g.id
            LEFT JOIN officials o ON a.official_id = o.id
            ORDER BY g.date DESC, g.time DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'assignments': [dict(assignment) for assignment in assignments]
        })
        
    except Exception as e:
        logger.error(f"Get assignments error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load assignments'}), 500

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)"""
    try:
        conn = get_db_connection()
        users = conn.execute('''
            SELECT id, username, full_name, email, phone, role, is_active, last_login
            FROM users ORDER BY created_at DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'users': [dict(user) for user in users]
        })
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load users'}), 500

# ===============================
# Export Routes
# ===============================

@app.route('/api/export/games')
@login_required
def export_games():
    """Export games to CSV"""
    try:
        conn = get_db_connection()
        games = conn.execute('''
            SELECT g.*, u.username as created_by_name
            FROM games g
            LEFT JOIN users u ON g.created_by = u.id
            ORDER BY g.date DESC
        ''').fetchall()
        conn.close()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Date', 'Time', 'Home Team', 'Away Team', 'Location',
            'Sport', 'League', 'Level', 'Officials Needed', 'Status',
            'Notes', 'Created By', 'Created At'
        ])
        
        # Write data
        for game in games:
            writer.writerow([
                game['id'], game['date'], game['time'], game['home_team'],
                game['away_team'], game['location'], game['sport'],
                game['league'], game['level'], game['officials_needed'],
                game['status'], game['notes'], game['created_by_name'],
                game['created_at']
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=games_export.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        log_activity(session['user_id'], 'EXPORT', 'games')
        
        return response
        
    except Exception as e:
        logger.error(f"Export games error: {e}")
        return jsonify({'success': False, 'error': 'Export failed'}), 500

@app.route('/api/export/officials')
@login_required
def export_officials():
    """Export officials to CSV"""
    try:
        conn = get_db_connection()
        officials = conn.execute('''
            SELECT * FROM officials ORDER BY last_name, first_name
        ''').fetchall()
        conn.close()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Address',
            'Sports', 'Experience Level', 'Rating', 'Active', 'Notes', 'Created At'
        ])
        
        # Write data
        for official in officials:
            writer.writerow([
                official['id'], official['first_name'], official['last_name'],
                official['email'], official['phone'], official['address'],
                official['sports'], official['experience_level'], official['rating'],
                official['is_active'], official['notes'], official['created_at']
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=officials_export.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        log_activity(session['user_id'], 'EXPORT', 'officials')
        
        return response
        
    except Exception as e:
        logger.error(f"Export officials error: {e}")
        return jsonify({'success': False, 'error': 'Export failed'}), 500

# ===============================
# Security Headers
# ===============================

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ===============================
# Application Initialization
# ===============================

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run application
    logger.info("Starting Sports Schedulers Web Application...")
    app.run(host='0.0.0.0', port=port, debug=False)
                
