# AWS Deployment Guide for Binance Portfolio Monitor

## Overview
This directory contains configurations and scripts for deploying the Binance Portfolio Monitor to AWS.

## Deployment Options

### 1. EC2 Instance (Recommended for testing)
- Full control over the environment
- Can test different regions easily
- Persistent storage for logs

### 2. AWS Lambda (Serverless)
- Cost-effective for scheduled runs
- Auto-scaling
- Requires VPC configuration for static IP

### 3. ECS/Fargate (Container-based)
- Good for production workloads
- Easy to manage and scale
- Built-in monitoring

## Pre-deployment Testing

Before deploying, test Binance API access from your target AWS region:

1. Launch a small EC2 instance in your target region
2. Copy and run the test script:
   ```bash
   scp test_binance_aws.py ec2-user@your-instance:~/
   ssh ec2-user@your-instance
   python3 test_binance_aws.py
   ```

## Recommended AWS Regions

Based on Binance access patterns:
- **Primary**: eu-central-1 (Frankfurt)
- **Secondary**: eu-west-1 (Ireland)
- **Avoid**: us-east-1, us-west-2 (often blocked)

## Environment Variables Required

```bash
# Binance API (only needed for private endpoints)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# Optional
WEBHOOK_URL=your_webhook_url
NOTIFICATION_ENABLED=false
```

## Quick Start

1. Test API access:
   ```bash
   cd ../..
   python test_binance_aws.py
   ```

2. Choose deployment method:
   - EC2: Use `ec2-deploy.sh`
   - Lambda: Use `lambda-deploy.sh`
   - ECS: Use `ecs-deploy.sh`

3. Deploy:
   ```bash
   ./deploy/aws/[method]-deploy.sh
   ```

## Troubleshooting

### API Access Blocked
If private API access is blocked:
1. Try different AWS region
2. Use NAT Gateway with Elastic IP
3. Set up VPN gateway
4. Consider residential proxy service

### Data API Already Configured
The application already uses `data-api.binance.vision` for public endpoints (prices), so these should work from any AWS region.

## Monitoring

Set up CloudWatch alarms for:
- Failed API calls
- Missing data points
- High error rates
- Function timeouts

## Cost Estimation

- EC2 t3.micro: ~$8/month
- Lambda: ~$1/month (hourly execution)
- ECS Fargate: ~$10/month
- Data transfer: Minimal (<$1/month)