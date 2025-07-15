#!/bin/bash
# EC2 User Data script for Binance Portfolio Monitor
# This script runs automatically when the EC2 instance starts

# Update system
yum update -y

# Install Python 3.9 and dependencies
yum install -y python39 python39-pip git

# Create app directory
mkdir -p /opt/binance-monitor
cd /opt/binance-monitor

# Clone repository (replace with your repo URL)
# git clone https://github.com/yourusername/binance_monitor_playground.git .

# For now, we'll prepare for manual deployment
# The actual code will be deployed separately

# Install Python dependencies
pip3.9 install python-binance==1.0.21 \
                supabase==2.8.1 \
                httpx==0.27.0 \
                python-dateutil==2.9.0 \
                python-dotenv==1.0.1

# Create systemd service
cat > /etc/systemd/system/binance-monitor.service << 'EOF'
[Unit]
Description=Binance Portfolio Monitor
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/binance-monitor
ExecStart=/usr/bin/python3.9 -m api.index
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Create cron job for hourly execution
cat > /etc/cron.d/binance-monitor << 'EOF'
# Run Binance Portfolio Monitor every hour
0 * * * * ec2-user cd /opt/binance-monitor && /usr/bin/python3.9 -m api.index >> /var/log/binance-monitor.log 2>&1
EOF

# Create log directory
mkdir -p /var/log
touch /var/log/binance-monitor.log
chown ec2-user:ec2-user /var/log/binance-monitor.log

# Set permissions
chown -R ec2-user:ec2-user /opt/binance-monitor

# Create environment file template
cat > /opt/binance-monitor/.env.template << 'EOF'
# Binance API credentials (optional - only for private endpoints)
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Supabase credentials (required)
SUPABASE_URL=
SUPABASE_ANON_KEY=

# Optional features
WEBHOOK_URL=
NOTIFICATION_ENABLED=false
EOF

# Create deployment instructions
cat > /opt/binance-monitor/DEPLOY_INSTRUCTIONS.txt << 'EOF'
Binance Portfolio Monitor - EC2 Deployment Instructions

1. Connect to this instance:
   ssh -i your-key.pem ec2-user@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

2. Upload your code:
   scp -r -i your-key.pem /path/to/binance_monitor_playground/* ec2-user@INSTANCE_IP:/opt/binance-monitor/

3. Configure environment:
   cd /opt/binance-monitor
   cp .env.template .env
   nano .env  # Add your credentials

4. Test the application:
   python3.9 test_binance_aws.py

5. Run monitoring manually:
   python3.9 -m api.index

6. Enable automatic monitoring:
   sudo systemctl enable binance-monitor
   sudo systemctl start binance-monitor

7. Check logs:
   tail -f /var/log/binance-monitor.log
   sudo journalctl -u binance-monitor -f

8. Dashboard access:
   python3.9 -m api.dashboard
   # Access at http://INSTANCE_IP:8000
EOF

echo "EC2 instance setup complete! Check /opt/binance-monitor/DEPLOY_INSTRUCTIONS.txt"