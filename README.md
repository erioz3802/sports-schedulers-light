# 🚀 Sports Schedulers Light - Production Deployment Guide

**Version:** 1.0.0 Production Release  
**Author:** Jose Ortiz  
**Date:** September 14, 2025  

## 📋 **Production Package Contents**

```
sports-schedulers-light-production/
├── app.py                    # Production Flask application
├── requirements.txt          # Production dependencies
├── .env.example             # Environment configuration template
├── templates/
│   ├── dashboard.html       # Main application interface
│   ├── login.html          # Login page
│   ├── 404.html            # Error pages
│   └── 500.html
├── static/                  # Static assets (CSS, JS, images)
├── logs/                    # Application logs (auto-created)
├── backups/                 # Database backups (auto-created)
├── deploy/
│   ├── nginx.conf          # Nginx configuration
│   ├── gunicorn.conf.py    # Gunicorn configuration
│   └── systemd.service     # Linux service file
└── docs/
    ├── DEPLOYMENT.md       # This file
    ├── SECURITY.md         # Security guidelines
    └── MAINTENANCE.md      # Maintenance procedures
```

## 🎯 **Production Features**

### **✅ Enhanced Security**
- **Strong password hashing** with PBKDF2 and salt
- **Account lockout** after 5 failed login attempts
- **Session timeout** and secure session management
- **Security headers** (HSTS, CSP, XSS protection)
- **Input validation** and SQL injection prevention
- **Activity logging** for security auditing

### **✅ Production Logging**
- **Rotating log files** with size limits
- **Separate security logs** for audit trails
- **Structured logging** with timestamps and context
- **Performance monitoring** capabilities

### **✅ Database Security**
- **Foreign key constraints** enabled
- **Data validation** at database level
- **Backup automation** with retention policies
- **Connection pooling** and timeout handling

### **✅ Performance Optimization**
- **Database indexing** for fast queries
- **Pagination** for large datasets
- **Connection management** with proper cleanup
- **Static file optimization**

### **✅ Monitoring & Health Checks**
- **Health check endpoint** at `/health`
- **Application metrics** and status monitoring
- **Database connectivity verification**
- **Error tracking** and alerting

## 🛠️ **Installation Methods**

### **Method 1: Simple Production Setup (Recommended)**

#### **Prerequisites:**
- **Python 3.8+** installed
- **2GB RAM minimum** (4GB recommended)
- **10GB disk space** for logs and backups
- **Ubuntu 20.04+** or **CentOS 8+** (or Windows Server)

#### **Quick Setup:**
```bash
# 1. Create application directory
sudo mkdir -p /opt/sports-schedulers-light
cd /opt/sports-schedulers-light

# 2. Copy application files
# (Upload your production package here)

# 3. Set up Python environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 6. Set permissions
sudo chown -R www-data:www-data /opt/sports-schedulers-light
chmod 755 app.py

# 7. Test the application
python app.py
```

#### **Access Application:**
- **URL:** http://your-server-ip:5000
- **Login:** jose_1 / Josu2398-1

### **Method 2: Professional Production Deployment**

#### **Using Gunicorn + Nginx (Linux)**

##### **Step 1: Install System Dependencies**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx

# CentOS/RHEL
sudo yum install python3 python3-pip nginx
```

##### **Step 2: Configure Gunicorn**
```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn config
nano gunicorn.conf.py
```

```python
# gunicorn.conf.py
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
user = "www-data"
group = "www-data"
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
```

##### **Step 3: Configure Nginx**
```nginx
# /etc/nginx/sites-available/sports-schedulers-light
server {
    listen 80;
    server_name your-domain.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Static files
    location /static/ {
        alias /opt/sports-schedulers-light/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
```

##### **Step 4: Create System Service**
```ini
# /etc/systemd/system/sports-schedulers-light.service
[Unit]
Description=Sports Schedulers Light Web Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/sports-schedulers-light
Environment=PATH=/opt/sports-schedulers-light/venv/bin
ExecStart=/opt/sports-schedulers-light/venv/bin/gunicorn -c gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

##### **Step 5: Start Services**
```bash
# Enable and start services
sudo systemctl enable sports-schedulers-light
sudo systemctl start sports-schedulers-light
sudo systemctl enable nginx
sudo systemctl start nginx

# Check status
sudo systemctl status sports-schedulers-light
sudo systemctl status nginx
```

### **Method 3: Docker Deployment**

#### **Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs backups

# Set permissions
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application
CMD ["python", "app.py"]
```

#### **Docker Compose:**
```yaml
version: '3.8'

services:
  sports-schedulers-light:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - sports-schedulers-light
    restart: unless-stopped
```

## 🔒 **Security Configuration**

### **1. Environment Variables**
```bash
# Generate secure secret key
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" >> .env

# Set production environment
echo "FLASK_ENV=production" >> .env
echo "FLASK_DEBUG=false" >> .env

# Configure HTTPS if available
echo "HTTPS_ENABLED=true" >> .env  # Only if you have SSL
```

### **2. File Permissions**
```bash
# Set secure permissions
sudo chown -R www-data:www-data /opt/sports-schedulers-light
sudo chmod 750 /opt/sports-schedulers-light
sudo chmod 640 /opt/sports-schedulers-light/.env
sudo chmod 644 /opt/sports-schedulers-light/app.py
```

### **3. Firewall Configuration**
```bash
# Ubuntu UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL Firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 📊 **Monitoring & Maintenance**

### **1. Log Monitoring**
```bash
# View application logs
tail -f /opt/sports-schedulers-light/logs/sports_schedulers_light.log

# View security logs
tail -f /opt/sports-schedulers-light/logs/security.log

# Monitor Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **2. Health Checks**
```bash
# Application health
curl http://localhost:5000/health

# Database connectivity
curl http://localhost:5000/health | jq '.status'
```

### **3. Backup Procedures**
```bash
# Manual database backup
cp /opt/sports-schedulers-light/scheduler_light.db \
   /opt/sports-schedulers-light/backups/manual_backup_$(date +%Y%m%d_%H%M%S).db

# Automated backup script (add to crontab)
#!/bin/bash
BACKUP_DIR="/opt/sports-schedulers-light/backups"
DB_FILE="/opt/sports-schedulers-light/scheduler_light.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cp "$DB_FILE" "$BACKUP_DIR/auto_backup_$TIMESTAMP.db"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "auto_backup_*.db" -mtime +30 -delete
```

## 🚀 **Performance Optimization**

### **1. Database Optimization**
```bash
# Add to crontab for weekly optimization
0 2 * * 0 sqlite3 /opt/sports-schedulers-light/scheduler_light.db "VACUUM;"
```

### **2. Log Rotation**
```bash
# /etc/logrotate.d/sports-schedulers-light
/opt/sports-schedulers-light/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 www-data www-data
    postrotate
        systemctl reload sports-schedulers-light
    endscript
}
```

## 🔧 **Troubleshooting**

### **Common Issues:**

#### **Application Won't Start**
```bash
# Check logs
sudo journalctl -u sports-schedulers-light -f

# Check Python environment
source /opt/sports-schedulers-light/venv/bin/activate
python -c "import flask; print('Flask OK')"

# Check permissions
ls -la /opt/sports-schedulers-light/
```

#### **Database Errors**
```bash
# Check database file exists
ls -la /opt/sports-schedulers-light/scheduler_light.db

# Check database integrity
sqlite3 scheduler_light.db "PRAGMA integrity_check;"

# Reset database (CAUTION: Will lose data)
rm scheduler_light.db
python app.py  # Will recreate database
```

#### **Performance Issues**
```bash
# Check system resources
htop
df -h
free -m

# Check application metrics
curl http://localhost:5000/health

# Monitor database size
ls -lh scheduler_light.db
```

## 📞 **Support & Updates**

### **Getting Help:**
- **Documentation:** Check all files in `/docs/` directory
- **Logs:** Always check application and system logs first
- **Health Check:** Use `/health` endpoint for diagnostics
- **Contact:** Jose Ortiz (application author)

### **Update Procedures:**
1. **Backup database** before any updates
2. **Test updates** in staging environment first
3. **Use rolling updates** to minimize downtime
4. **Monitor logs** after updates

### **Version Information:**
- **Current Version:** 1.0.0 Production Release
- **Release Date:** September 14, 2025
- **Python Requirements:** 3.8+
- **Database:** SQLite (built-in)

---

**🎉 Sports Schedulers Light - Production Ready!**  
**Built with ❤️ by Jose Ortiz - September 2025**