# 🚀 Deployment Guide - Binance Portfolio Monitor

**Complete guide for deploying your portfolio monitoring system to production.**

## 🎯 Deployment Options

### Option 1: Vercel (Recommended)
- ✅ **Serverless** - Pay only for usage
- ✅ **Auto-scaling** - Handles traffic spikes
- ✅ **Built-in cron** - Scheduled monitoring
- ✅ **GitHub integration** - Auto-deploy on push
- ✅ **Free tier** - Generous limits for monitoring

### Option 2: Railway
- ✅ **Simple deployment** - One-click from GitHub
- ✅ **Environment variables** - Easy configuration
- ✅ **PostgreSQL** - Built-in database option
- ✅ **Cron jobs** - Built-in scheduling

### Option 3: Digital Ocean App Platform
- ✅ **Managed platform** - No server management
- ✅ **Database integration** - Managed PostgreSQL
- ✅ **Custom domains** - Professional setup
- ✅ **Monitoring** - Built-in observability

## 🔄 Pre-Deployment Checklist

- [ ] **Code tested locally** and working correctly
- [ ] **Supabase database** set up with all tables
- [ ] **Environment variables** documented
- [ ] **API keys** have correct permissions
- [ ] **Dependencies** listed in requirements.txt
- [ ] **Git repository** ready for deployment

## 🚀 Vercel Deployment (Detailed)

### Step 1: Prepare Your Repository

#### Update `.gitignore`
```bash
# Environment variables
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
.venv/

# Vercel
.vercel/

# Logs
*.log
```

#### Create `vercel.json` Configuration
```json
{
  "functions": {
    "api/index.py": {},
    "api/dashboard.py": {}
  },
  "routes": [
    {
      "src": "/dashboard",
      "dest": "/api/dashboard"
    },
    {
      "src": "/api/dashboard/(.*)",
      "dest": "/api/dashboard"
    }
  ],
  "crons": [
    {
      "path": "/api/index",
      "schedule": "0 * * * *"
    }
  ]
}
```

**Important Notes:**
- **Python Runtime**: Vercel uses Python 3.12 by default (no runtime specification needed)
- **Legacy Runtime**: Avoid specifying `"runtime": "python3.9"` as it causes deployment errors
- **Cron Schedule**: Hourly execution requires Vercel Pro plan ($20/month)

#### Verify `requirements.txt`
```txt
python-binance==1.0.29
supabase==2.16.0
python-dotenv==1.1.1
requests==2.32.4
aiohttp==3.12.13
python-dateutil==2.9.0.post0
```

### Step 2: Deploy to Vercel

#### Via Vercel Dashboard
1. Go to [vercel.com](https://vercel.com)
2. Click **"New Project"**
3. Import your GitHub repository
4. **Framework Preset**: Other
5. **Root Directory**: `./` (leave default)
6. Click **"Deploy"**

#### Via CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### Step 3: Configure Environment Variables

In Vercel Dashboard → Project → Settings → Environment Variables:

```bash
# Production Environment Variables
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Optional: Enhanced security
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
ENVIRONMENT=production
```

### Step 4: Test Deployment

```bash
# Test your endpoint
curl https://your-project.vercel.app/api

# Expected response
"Monitoring process completed successfully."
```

### Step 5: Configure Cron Monitoring

Vercel automatically runs your cron job based on `vercel.json`. Monitor executions:

1. **Vercel Dashboard** → **Functions** → **View logs**
2. Check for successful runs every hour
3. Monitor for any error patterns

## 🛤️ Railway Deployment

### Step 1: Connect Repository

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. **"Deploy from GitHub repo"**
4. Select your repository

### Step 2: Configure Build

Railway auto-detects Python projects. Create `railway.toml`:

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python api/index.py"
healthcheckPath = "/api"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"

[env]
PYTHONPATH = "/app"
```

### Step 3: Set Environment Variables

In Railway Dashboard → Variables:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
PORT=8000
```

### Step 4: Add Cron Service

Create `cron.py` for Railway:
```python
import schedule
import time
import requests
import os

def run_monitor():
    try:
        response = requests.get(f"http://localhost:{os.getenv('PORT', 8000)}/api")
        print(f"Monitor run: {response.status_code}")
    except Exception as e:
        print(f"Cron error: {e}")

# Run every hour
schedule.every().hour.do(run_monitor)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)
```

Update `requirements.txt`:
```txt
# ... existing dependencies
schedule==1.2.0
```

## 🌊 Digital Ocean App Platform

### Step 1: Create App Spec

Create `.do/app.yaml`:
```yaml
name: binance-monitor
services:
- name: api
  source_dir: /
  github:
    repo: your-username/binance_monitor_playground
    branch: main
  run_command: python api/index.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  
- name: worker
  source_dir: /
  github:
    repo: your-username/binance_monitor_playground
    branch: main
  run_command: python -c "import schedule, time, requests; schedule.every().hour.do(lambda: requests.get('https://your-app.ondigitalocean.app/api')); [schedule.run_pending() or time.sleep(60) for _ in iter(int, 1)]"
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  
envs:
- key: SUPABASE_URL
  value: https://your-project.supabase.co
- key: SUPABASE_ANON_KEY
  value: your-anon-key
```

### Step 2: Deploy

1. Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
2. **Apps** → **Create App**
3. **GitHub** → Select repository
4. Review app spec and deploy

## 🏠 Self-Hosted Options

### Docker Deployment

#### Create `Dockerfile`
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "api/index.py"]
```

#### Create `docker-compose.yml`
```yaml
version: '3.8'

services:
  monitor:
    build: .
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    restart: unless-stopped
    
  cron:
    image: alpine:latest
    command: >
      sh -c "
        apk add --no-cache curl &&
        echo '0 * * * * curl http://monitor:8000/api' | crontab - &&
        crond -f
      "
    depends_on:
      - monitor
    restart: unless-stopped
```

#### Deploy
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

### VPS Deployment

#### Ubuntu/Debian Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.13
sudo apt install python3.13 python3.13-venv python3-pip -y

# Clone repository
git clone https://github.com/your-username/binance_monitor_playground.git
cd binance_monitor_playground

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
nano .env  # Add your configuration
```

#### Create Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/binance-monitor.service
```

```ini
[Unit]
Description=Binance Portfolio Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/binance_monitor_playground
Environment=PATH=/home/ubuntu/binance_monitor_playground/.venv/bin
ExecStart=/home/ubuntu/binance_monitor_playground/.venv/bin/python api/index.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add hourly execution
0 * * * * curl http://localhost:8000/api
```

#### Start Services
```bash
# Enable and start service
sudo systemctl enable binance-monitor
sudo systemctl start binance-monitor

# Check status
sudo systemctl status binance-monitor
```

## 📊 Monitoring and Observability

### Health Check Endpoint

Add to `api/index.py`:
```python
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now(UTC).isoformat(),
                'version': '1.0.0'
            }
            self.wfile.write(json.dumps(health_data).encode())
            return
        
        # ... existing code
```

### Log Management

#### Structured Logging
```python
import logging
import json
from datetime import datetime, UTC

# Configure JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        return json.dumps(log_entry)

# Setup logger
logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Application Monitoring

#### Uptime Monitoring
```bash
# Simple uptime check with curl
*/5 * * * * curl -f https://your-app.vercel.app/health || echo "Health check failed" | mail -s "Monitor Down" your-email@domain.com
```

#### Performance Monitoring
Add to your monitoring code:
```python
import time

def process_single_account(account):
    start_time = time.time()
    try:
        # ... existing code
        processing_time = time.time() - start_time
        logger.info(f"Account {account['account_name']} processed in {processing_time:.2f}s")
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Account {account['account_name']} failed after {processing_time:.2f}s: {e}")
```

## 🔒 Production Security

### Environment Security
```bash
# Use service role key for production
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Set environment identifier
ENVIRONMENT=production

# Optional: Add monitoring tokens
MONITORING_TOKEN=secure-random-token
```

### API Key Rotation
```python
def rotate_api_keys():
    """Implement API key rotation strategy"""
    # 1. Generate new API keys in Binance
    # 2. Update database with new keys
    # 3. Test new keys work
    # 4. Disable old keys
    pass
```

### Database Security
```sql
-- Enable RLS if needed
ALTER TABLE binance_accounts ENABLE ROW LEVEL SECURITY;

-- Create service role policy
CREATE POLICY "Service access" ON binance_accounts
    FOR ALL USING (true) WITH CHECK (true);
```

## 📈 Scaling Considerations

### Performance Optimization
- **Connection Pooling**: Reuse database connections
- **Caching**: Cache market prices for short periods
- **Batch Processing**: Process multiple accounts efficiently
- **Rate Limiting**: Respect API limits

### High Availability
- **Multiple Regions**: Deploy to multiple regions
- **Database Replication**: Use read replicas for queries
- **Circuit Breakers**: Handle API failures gracefully
- **Backup Strategy**: Regular database backups

## 🚨 Troubleshooting Production Issues

### Common Deployment Issues

**"Module not found"**
```bash
# Check requirements.txt is complete
pip freeze > requirements.txt
```

**"Environment variable not found"**
```bash
# Verify all required env vars are set
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY
```

**"Database connection failed"**
```bash
# Test database connection
python -c "
from supabase import create_client
client = create_client('$SUPABASE_URL', '$SUPABASE_ANON_KEY')
print(client.table('binance_accounts').select('count').execute())
"
```

### Performance Issues

**"Function timeout"**
- Increase function timeout in platform settings
- Optimize database queries
- Add connection pooling
- Reduce API calls

**"Rate limiting"**
- Implement exponential backoff
- Add delays between API calls
- Cache frequently accessed data
- Use batch requests

### Monitoring Failures

**"Cron job not running"**
```bash
# Check cron configuration
cat /etc/crontab

# Check system logs
tail -f /var/log/cron

# Test manual execution
curl https://your-app.domain.com/api
```

## ✅ Production Readiness Checklist

- [ ] **Code tested** in production-like environment
- [ ] **Environment variables** securely configured
- [ ] **Database backups** configured
- [ ] **Monitoring** and alerting set up
- [ ] **Error handling** covers edge cases
- [ ] **API rate limits** respected
- [ ] **Security measures** implemented
- [ ] **Documentation** updated
- [ ] **Rollback plan** prepared
- [ ] **Performance benchmarks** established

## 🎯 Post-Deployment Tasks

### Week 1: Monitoring
- Check logs daily for errors
- Verify cron jobs run successfully
- Monitor API usage and limits
- Validate data accuracy

### Week 2-4: Optimization
- Analyze performance metrics
- Optimize slow database queries
- Implement caching where beneficial
- Add additional monitoring

### Monthly: Maintenance
- Update dependencies
- Rotate API keys
- Review security settings
- Backup verification
- Performance analysis

---

**Your Binance Portfolio Monitor is now ready for production! 🚀**

Remember to monitor regularly and keep dependencies updated for security and performance.