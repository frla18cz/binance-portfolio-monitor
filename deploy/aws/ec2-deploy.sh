#!/bin/bash
# AWS EC2 Deployment Script for Binance Portfolio Monitor

set -e

# Configuration
INSTANCE_TYPE="t3.micro"
KEY_NAME="binance-monitor-key"
SECURITY_GROUP_NAME="binance-monitor-sg"
INSTANCE_NAME="binance-portfolio-monitor"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Binance Portfolio Monitor - AWS EC2 Deployment${NC}"
echo "================================================"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    echo "   Visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured.${NC}"
    echo "   Run: aws configure"
    exit 1
fi

# Get current AWS region
REGION=$(aws configure get region)
echo -e "${YELLOW}📍 Using AWS Region: ${REGION}${NC}"

# Region recommendation
if [[ ! "$REGION" =~ ^eu- ]]; then
    echo -e "${YELLOW}⚠️  Warning: Non-EU region detected.${NC}"
    echo "   Binance API access might be blocked."
    echo "   Recommended regions: eu-central-1 (Frankfurt), eu-west-1 (Ireland)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create key pair if it doesn't exist
echo -e "\n${YELLOW}🔑 Checking SSH key pair...${NC}"
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME &> /dev/null; then
    echo "Creating new key pair..."
    aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text > ${KEY_NAME}.pem
    chmod 400 ${KEY_NAME}.pem
    echo -e "${GREEN}✅ Key pair created: ${KEY_NAME}.pem${NC}"
else
    echo -e "${GREEN}✅ Key pair already exists${NC}"
fi

# Get default VPC
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
if [ "$DEFAULT_VPC" == "None" ]; then
    echo -e "${RED}❌ No default VPC found${NC}"
    exit 1
fi

# Create security group
echo -e "\n${YELLOW}🔒 Setting up security group...${NC}"
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")

if [ "$SG_ID" == "None" ]; then
    echo "Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for Binance Portfolio Monitor" \
        --vpc-id $DEFAULT_VPC \
        --query 'GroupId' \
        --output text)
    
    # Add SSH access
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0
    
    # Add dashboard access
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0
    
    echo -e "${GREEN}✅ Security group created: $SG_ID${NC}"
else
    echo -e "${GREEN}✅ Security group already exists: $SG_ID${NC}"
fi

# Get latest Amazon Linux 2 AMI
echo -e "\n${YELLOW}💿 Finding latest Amazon Linux 2 AMI...${NC}"
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text)
echo -e "${GREEN}✅ Using AMI: $AMI_ID${NC}"

# Launch instance
echo -e "\n${YELLOW}🚀 Launching EC2 instance...${NC}"
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --user-data file://$(dirname $0)/ec2-userdata.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✅ Instance launched: $INSTANCE_ID${NC}"

# Wait for instance to be running
echo -e "\n${YELLOW}⏳ Waiting for instance to start...${NC}"
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get instance details
INSTANCE_INFO=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0]')
PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress')
PRIVATE_IP=$(echo $INSTANCE_INFO | jq -r '.PrivateIpAddress')

echo -e "${GREEN}✅ Instance is running!${NC}"
echo -e "   Public IP: ${PUBLIC_IP}"
echo -e "   Private IP: ${PRIVATE_IP}"

# Create deployment script
cat > deploy-to-instance.sh << EOF
#!/bin/bash
# Deploy code to EC2 instance

INSTANCE_IP=${PUBLIC_IP}
KEY_FILE=${KEY_NAME}.pem

echo "📦 Deploying to EC2 instance..."

# Wait for instance to be ready for SSH
echo "Waiting for SSH to be ready..."
while ! ssh -o StrictHostKeyChecking=no -i \$KEY_FILE ec2-user@\$INSTANCE_IP echo "SSH ready" 2>/dev/null; do
    sleep 5
done

# Copy project files
echo "Copying project files..."
rsync -avz -e "ssh -i \$KEY_FILE" \\
    --exclude='.git' \\
    --exclude='__pycache__' \\
    --exclude='.env' \\
    --exclude='logs' \\
    --exclude='*.log' \\
    --exclude='deploy' \\
    ../ ec2-user@\$INSTANCE_IP:/opt/binance-monitor/

# Copy environment file if it exists
if [ -f ../.env ]; then
    echo "Copying environment file..."
    scp -i \$KEY_FILE ../.env ec2-user@\$INSTANCE_IP:/opt/binance-monitor/
fi

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. SSH to instance: ssh -i \$KEY_FILE ec2-user@\$INSTANCE_IP"
echo "2. Test API access: cd /opt/binance-monitor && python3.9 test_binance_aws.py"
echo "3. Configure environment: nano /opt/binance-monitor/.env"
echo "4. Run monitoring: python3.9 -m api.index"
echo "5. Access dashboard: http://\$INSTANCE_IP:8000"
EOF

chmod +x deploy-to-instance.sh

# Summary
echo -e "\n${GREEN}🎉 EC2 instance deployment complete!${NC}"
echo "====================================="
echo -e "Instance ID: ${INSTANCE_ID}"
echo -e "Public IP: ${PUBLIC_IP}"
echo -e "SSH Key: ${KEY_NAME}.pem"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Deploy your code:"
echo "   ./deploy-to-instance.sh"
echo ""
echo "2. SSH to instance:"
echo "   ssh -i ${KEY_NAME}.pem ec2-user@${PUBLIC_IP}"
echo ""
echo "3. Test Binance API access:"
echo "   cd /opt/binance-monitor"
echo "   python3.9 test_binance_aws.py"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "- Check /opt/binance-monitor/DEPLOY_INSTRUCTIONS.txt on the instance"
echo "- Monitor logs: tail -f /var/log/binance-monitor.log"
echo "- If API access is blocked, try a different AWS region"

# Save instance details
cat > instance-details.json << EOF
{
  "instance_id": "${INSTANCE_ID}",
  "public_ip": "${PUBLIC_IP}",
  "private_ip": "${PRIVATE_IP}",
  "region": "${REGION}",
  "key_name": "${KEY_NAME}",
  "security_group": "${SG_ID}",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo -e "\n${GREEN}✅ Instance details saved to: instance-details.json${NC}"