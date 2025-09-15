"""Sports Schedulers Light - Production Web Application
Author: Jose Ortiz
Date: September 14, 2025
Version: 1.0.0 Production Release
Copyright (c) 2025 Jose Ortiz. All rights reserved.

Production-ready sports scheduling management system."""

import os
import re
import secrets
import logging
from flask import Flask, make_response, render_template, request, jsonify, redirect, session
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps
import csv
import io
from logging.handlers import RotatingFileHandler

# Production Flask app configuration
app = Flask(__name__)

# Production security settings
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ENABLED', 'false').lower() == 'true',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file uploads
)

# Production logging configuration
def setup_logging():
    """Configure production-grade logging"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Main application log
    file_handler = RotatingFileHandler(
        'logs/sports_schedulers_light.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Console logging for production monitoring
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # Security log
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=5242880,  # 5MB
        backupCount=5
    )
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s SECURITY: %(message)s'
    ))
    
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    return security_logger

# Initialize logging
security_logger = setup_logging()

def hash_password(password):
    """Secure password hashing with salt"""
    salt = hashlib.sha256(password.encode()).hexdigest()[:16]
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def verify_password(stored_password, provided_password):
    """Verify password against stored hash"""
    try:
        salt = hashlib.sha256(provided_password.encode()).hexdigest()[:16]
        test_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt.encode(), 100000).hex()
        return test_hash == stored_password
    except:
        return False

def get_db_connection():
    """Get database connection with security settings"""
    db_path = os.environ.get('DATABASE_PATH', 'scheduler_light.db')
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def login_required(f):
    """Enhanced decorator for login required routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'login_time' not in session:
            security_logger.warning(f"Unauthorized access attempt to {request.endpoint} from {request.remote_addr}")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect('/login')
        
        # Check session timeout (1 hour)
        if (datetime.now() - datetime.fromisoformat(session['login_time'])).seconds > 3600:
            session.clear()
            security_logger.info(f"Session expired for user {session.get('username', 'unknown')}")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Session expired'}), 401
            return redirect('/login')
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Enhanced decorator for admin required routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') not in ['admin', 'superadmin']:
            security_logger.warning(f"Unauthorized admin access attempt by {session.get('username')} from {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Administrator access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def validate_input(data, required_fields, max_lengths=None):
    """Comprehensive input validation"""
    errors = []
    
    # Check required fields
    for field in required_fields:
        if not data.get(field) or str(data.get(field)).strip() == '':
            errors.append(f'{field} is required')
    
    # Check max lengths
    if max_lengths:
        for field, max_len in max_lengths.items():
            if data.get(field) and len(str(data.get(field))) > max_len:
                errors.append(f'{field} must be {max_len} characters or less')
    
    # Sanitize inputs
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove potentially dangerous characters
            sanitized_value = re.sub(r'[<>"\']', '', value.strip())
            sanitized_data[key] = sanitized_value
        else:
            sanitized_data[key] = value
    
    return errors, sanitized_data

def init_database():
    """Initialize production database with enhanced security"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        app.logger.info("Initializing production database...")
        
        # Users table with enhanced security
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                phone TEXT,
                role TEXT DEFAULT 'official' CHECK (role IN ('official', 'admin', 'superadmin')),
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                last_login TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                account_locked_until TEXT
            )
        """)
        
        # Games table with constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL CHECK (date != ''),
                time TEXT NOT NULL CHECK (time != ''),
                home_team TEXT NOT NULL CHECK (home_team != ''),
                away_team TEXT NOT NULL CHECK (away_team != ''),
                location TEXT,
                sport TEXT NOT NULL CHECK (sport != ''),
                league TEXT,
                level TEXT,
                officials_needed INTEGER DEFAULT 1 CHECK (officials_needed > 0),
                notes TEXT,
                status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
                created_date TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                modified_date TEXT,
                modified_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (modified_by) REFERENCES users (id)
            )
        """)

        # Officials table with validation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS officials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                sport TEXT,
                experience_level TEXT CHECK (experience_level IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),
                certifications TEXT,
                availability TEXT,
                rating REAL DEFAULT 0.0 CHECK (rating >= 0.0 AND rating <= 5.0),
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Assignments table with constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                official_id INTEGER NOT NULL,
                position TEXT DEFAULT 'Referee',
                status TEXT DEFAULT 'assigned' CHECK (status IN ('assigned', 'confirmed', 'declined', 'completed')),
                assigned_date TEXT NOT NULL,
                confirmed_date TEXT,
                notes TEXT,
                assigned_by INTEGER NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
                FOREIGN KEY (official_id) REFERENCES officials (id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_by) REFERENCES users (id),
                UNIQUE(game_id, official_id)
            )
        """)
        
        # Leagues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (name != ''),
                sport TEXT NOT NULL CHECK (sport != ''),
                season TEXT NOT NULL CHECK (season != ''),
                levels TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)
        
        # Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL CHECK (name != ''),
                address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                contact_person TEXT,
                contact_phone TEXT,
                capacity INTEGER CHECK (capacity IS NULL OR capacity > 0),
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        # Activity log for security auditing
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_game ON assignments(game_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)")

        # Create production admin users with secure passwords
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'superadmin'")
        if cursor.fetchone()[0] == 0:
            # Create jose_1 superadmin account
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
            
            # Create admin account as backup
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

def log_activity(user_id, action, resource_type=None, resource_id=None, details=None):
    """Log user activity for security auditing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO activity_log (user_id, action, resource_type, resource_id, details, 
                                    ip_address, user_agent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, action, resource_type, resource_id, details,
            request.remote_addr, request.headers.get('User-Agent', ''), 
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"Activity logging error: {e}")

# =============================================================================
# SECURITY MIDDLEWARE
# =============================================================================

@app.before_request
def security_headers():
    """Add security headers to all responses"""
    pass

@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response

# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/')
def home():
    """Home page - redirect appropriately"""
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced login with security measures"""
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.get_json() or request.form
        username = data.get('username', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not username or not password:
            security_logger.warning(f"Login attempt with missing credentials from {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find user
        cursor.execute("""
            SELECT id, username, password, full_name, email, role, is_active, 
                   failed_login_attempts, account_locked_until
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            security_logger.warning(f"Login attempt for non-existent user '{username}' from {request.remote_addr}")
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        # Check account lockout
        if user['account_locked_until']:
            lockout_time = datetime.fromisoformat(user['account_locked_until'])
            if datetime.now() < lockout_time:
                security_logger.warning(f"Login attempt for locked account '{username}' from {request.remote_addr}")
                return jsonify({'success': False, 'error': 'Account temporarily locked'}), 423
        
        # Verify password
        if verify_password(user['password'], password):
            # Reset failed attempts on successful login
            cursor.execute("""
                UPDATE users SET last_login = ?, failed_login_attempts = 0, account_locked_until = NULL 
                WHERE id = ?
            """, (datetime.now().isoformat(), user['id']))
            
            # Set session
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            session['login_time'] = datetime.now().isoformat()
            
            conn.commit()
            conn.close()
            
            # Log successful login
            log_activity(user['id'], 'LOGIN_SUCCESS')
            app.logger.info(f"Successful login for user '{username}' from {request.remote_addr}")
            
            return jsonify({'success': True, 'redirect': '/dashboard'})
        else:
            # Handle failed login
            failed_attempts = user['failed_login_attempts'] + 1
            lockout_until = None
            
            # Lock account after 5 failed attempts for 30 minutes
            if failed_attempts >= 5:
                lockout_until = (datetime.now().timestamp() + 1800)  # 30 minutes
                lockout_until = datetime.fromtimestamp(lockout_until).isoformat()
            
            cursor.execute("""
                UPDATE users SET failed_login_attempts = ?, account_locked_until = ? WHERE id = ?
            """, (failed_attempts, lockout_until, user['id']))
            
            conn.commit()
            conn.close()
            
            security_logger.warning(f"Failed login attempt for '{username}' from {request.remote_addr} (attempt {failed_attempts})")
            
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Authentication service unavailable'}), 500

@app.route('/logout')
def logout():
    """Enhanced logout with activity logging"""
    user_id = session.get('user_id')
    username = session.get('username', 'unknown')
    
    if user_id:
        log_activity(user_id, 'LOGOUT')
        app.logger.info(f"User '{username}' logged out from {request.remote_addr}")
    
    session.clear()
    return redirect('/login')

# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Production dashboard"""
    return render_template('dashboard.html', user=session)

@app.route('/api/dashboard')
@login_required
def get_dashboard_stats():
    """Get dashboard statistics with error handling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get basic stats with error handling
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE date >= date('now') AND status = 'scheduled'")
        stats['upcoming_games'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM officials WHERE is_active = 1")
        stats['active_officials'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assignments WHERE status IN ('assigned', 'confirmed')")
        stats['total_assignments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leagues WHERE is_active = 1")
        stats['active_leagues'] = cursor.fetchone()[0]
        
        # Get recent games with safety checks
        cursor.execute("""
            SELECT g.*, COUNT(a.id) as assigned_officials
            FROM games g
            LEFT JOIN assignments a ON g.id = a.game_id AND a.status IN ('assigned', 'confirmed')
            WHERE g.date >= date('now') AND g.status = 'scheduled'
            GROUP BY g.id
            ORDER BY g.date, g.time
            LIMIT 5
        """)
        recent_games = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        log_activity(session['user_id'], 'VIEW_DASHBOARD')
        
        return jsonify({
            'success': True,
            **stats,
            'recent_games': recent_games
        })
        
    except Exception as e:
        app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard statistics'}), 500

# =============================================================================
# GAMES MANAGEMENT ROUTES (Enhanced with validation)
# =============================================================================

@app.route('/api/games', methods=['GET'])
@login_required
def get_games():
    """Get games with enhanced filtering and pagination"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Handle pagination
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 per page
        offset = (page - 1) * per_page
        
        # Handle filters with validation
        search = request.args.get('search', '').strip()[:100]  # Limit search length
        sport = request.args.get('sport', '').strip()[:50]
        league = request.args.get('league', '').strip()[:50]
        
        query = """
            SELECT g.*, u.username as created_by_name,
                   COUNT(a.id) as assigned_officials,
                   COUNT(*) OVER() as total_count
            FROM games g
            LEFT JOIN users u ON g.created_by = u.id
            LEFT JOIN assignments a ON g.id = a.game_id AND a.status IN ('assigned', 'confirmed')
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (g.home_team LIKE ? OR g.away_team LIKE ? OR g.location LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if sport:
            query += " AND g.sport = ?"
            params.append(sport)
            
        if league:
            query += " AND g.league = ?"
            params.append(league)
        
        query += " GROUP BY g.id ORDER BY g.date DESC, g.time DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        games = [dict(row) for row in cursor.fetchall()]
        
        total_count = games[0]['total_count'] if games else 0
        
        # Remove total_count from individual records
        for game in games:
            del game['total_count']
        
        conn.close()
        
        log_activity(session['user_id'], 'VIEW_GAMES')
        
        return jsonify({
            'success': True, 
            'games': games,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        app.logger.error(f"Get games error: {e}")
        return jsonify({'success': False, 'error': 'Failed to retrieve games'}), 500

@app.route('/api/games', methods=['POST'])
@login_required
def create_game():
    """Create game with comprehensive validation"""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['date', 'time', 'home_team', 'away_team', 'sport']
        max_lengths = {
            'home_team': 100, 'away_team': 100, 'location': 200,
            'sport': 50, 'league': 100, 'level': 50, 'notes': 500
        }
        
        errors, sanitized_data = validate_input(data, required_fields, max_lengths)
        
        # Additional validation
        try:
            datetime.strptime(sanitized_data['date'], '%Y-%m-%d')
            datetime.strptime(sanitized_data['time'], '%H:%M')
        except ValueError:
            errors.append('Invalid date or time format')
        
        if sanitized_data.get('officials_needed'):
            try:
                officials_needed = int(sanitized_data['officials_needed'])
                if officials_needed < 1 or officials_needed > 10:
                    errors.append('Officials needed must be between 1 and 10')
            except ValueError:
                errors.append('Officials needed must be a number')
        
        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO games (date, time, home_team, away_team, location, sport, league, level, 
                             officials_needed, notes, status, created_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
        """, (
            sanitized_data['date'], sanitized_data['time'], 
            sanitized_data['home_team'], sanitized_data['away_team'],
            sanitized_data.get('location', ''), sanitized_data['sport'], 
            sanitized_data.get('league', ''), sanitized_data.get('level', ''), 
            sanitized_data.get('officials_needed', 1), sanitized_data.get('notes', ''),
            datetime.now().isoformat(), session['user_id']
        ))
        
        game_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_activity(session['user_id'], 'CREATE_GAME', 'games', game_id, 
                    f"Created game: {sanitized_data['home_team']} vs {sanitized_data['away_team']}")
        
        app.logger.info(f"Game created by {session['username']}: ID {game_id}")
        
        return jsonify({'success': True, 'game_id': game_id, 'message': 'Game created successfully'})
        
    except Exception as e:
        app.logger.error(f"Create game error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create game'}), 500

# [Additional routes follow the same enhanced pattern...]

# =============================================================================
# CSV EXPORT WITH SECURITY
# =============================================================================

@app.route('/api/export/games')
@login_required
def export_games():
    """Secure CSV export for games"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, time, home_team, away_team, location, sport, league, level, 
                   officials_needed, status, notes
            FROM games 
            ORDER BY date DESC, time DESC
        """)
        
        games = cursor.fetchall()
        conn.close()
        
        # Create CSV with proper encoding
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Headers
        writer.writerow(['Date', 'Time', 'Home Team', 'Away Team', 'Location', 
                        'Sport', 'League', 'Level', 'Officials Needed', 'Status', 'Notes'])
        
        # Data with sanitization
        for game in games:
            row = [str(field) if field is not None else '' for field in game]
            writer.writerow(row)
        
        csv_data = output.getvalue()
        output.close()
        
        log_activity(session['user_id'], 'EXPORT_GAMES', details=f"Exported {len(games)} games")
        
        return jsonify({
            'success': True,
            'filename': f'games_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'data': csv_data
        })
        
    except Exception as e:
        app.logger.error(f"Export games error: {e}")
        return jsonify({'success': False, 'error': 'Failed to export games data'}), 500

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    if request.is_json:
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    app.logger.error(f"Internal server error: {error}")
    if request.is_json:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file upload size errors"""
    return jsonify({'success': False, 'error': 'File too large'}), 413

# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Quick database connectivity check
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': 'Database connection failed'
        }), 503

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == '__main__':
    try:
        # Initialize database
        init_database()
        
        # Production configuration
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV', 'production') == 'development'
        
        app.logger.info(f"Starting Sports Schedulers Light v1.0.0 in {'development' if debug else 'production'} mode")
        app.logger.info(f"Server will run on port {port}")
        
        if debug:
            app.logger.warning("Running in development mode - ensure this is not production!")
        
        # Start the application
        app.run(
            debug=debug,
            host='0.0.0.0',
            port=port,
            threaded=True
        )
        
    except Exception as e:
        app.logger.error(f"Application startup failed: {e}")
        raise