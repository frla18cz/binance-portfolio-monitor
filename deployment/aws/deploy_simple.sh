#!/bin/bash

# Binance Portfolio Monitor - Simple Deploy Script
# Nahraje kód na EC2 instanci pomocí rsync

# Nastavení barev
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Kontrola parametrů
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Chyba: Nedostatek parametrů${NC}"
    echo ""
    echo "Použití: $0 <instance-ip> <key-file>"
    echo "Příklad: $0 54.123.45.67 my-key.pem"
    echo ""
    echo "Volitelné parametry:"
    echo "  -u <user>    SSH uživatel (výchozí: ec2-user)"
    echo "  -d <dir>     Cílový adresář (výchozí: /home/ec2-user/binance-monitor)"
    exit 1
fi

# Výchozí hodnoty
INSTANCE_IP=$1
KEY_FILE=$2
SSH_USER="ec2-user"
TARGET_DIR="/home/ec2-user/binance-monitor"

# Zpracování volitelných parametrů
shift 2
while getopts "u:d:" opt; do
    case $opt in
        u) SSH_USER="$OPTARG";;
        d) TARGET_DIR="$OPTARG";;
        \?) echo "Neplatná volba: -$OPTARG" >&2; exit 1;;
    esac
done

echo -e "${GREEN}🚀 Binance Portfolio Monitor - Deploy Script${NC}"
echo "============================================"

# Kontrola SSH klíče
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}❌ SSH klíč nenalezen: $KEY_FILE${NC}"
    exit 1
fi

# Kontrola oprávnění klíče
chmod 400 "$KEY_FILE"

# Test SSH připojení
echo -e "\n${YELLOW}🔌 Testování SSH připojení...${NC}"
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$KEY_FILE" "$SSH_USER@$INSTANCE_IP" "echo 'SSH OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ SSH připojení funguje${NC}"
else
    echo -e "${RED}❌ Nelze se připojit přes SSH${NC}"
    echo "Zkontrolujte:"
    echo "  - IP adresu: $INSTANCE_IP"
    echo "  - SSH klíč: $KEY_FILE"
    echo "  - Uživatele: $SSH_USER"
    echo "  - Security group povoluje SSH (port 22)"
    exit 1
fi

# Informace o nasazení
echo -e "\n${YELLOW}📋 Konfigurace nasazení:${NC}"
echo "   Cílový server: $SSH_USER@$INSTANCE_IP"
echo "   Cílový adresář: $TARGET_DIR"
echo "   SSH klíč: $KEY_FILE"

# Získání cesty k projektu
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "   Zdrojový adresář: $PROJECT_ROOT"

# Vytvoření cílového adresáře
echo -e "\n${YELLOW}📁 Příprava cílového adresáře...${NC}"
ssh -i "$KEY_FILE" "$SSH_USER@$INSTANCE_IP" "mkdir -p $TARGET_DIR"

# Vytvoření seznamu souborů k vyloučení
EXCLUDE_FILE=$(mktemp)
cat > "$EXCLUDE_FILE" << EOF
.git/
.gitignore
__pycache__/
*.pyc
.env
.env.local
logs/
*.log
.idea/
.vscode/
*.swp
*.swo
.DS_Store
venv/
.pytest_cache/
node_modules/
instance-details.json
deploy-to-instance.sh
*.pem
EOF

# Nahrání souborů pomocí rsync
echo -e "\n${YELLOW}📦 Nahrávání souborů...${NC}"
rsync -avz --progress \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    --exclude-from="$EXCLUDE_FILE" \
    "$PROJECT_ROOT/" \
    "$SSH_USER@$INSTANCE_IP:$TARGET_DIR/"

RSYNC_STATUS=$?

# Cleanup
rm -f "$EXCLUDE_FILE"

if [ $RSYNC_STATUS -eq 0 ]; then
    echo -e "\n${GREEN}✅ Soubory úspěšně nahrány${NC}"
else
    echo -e "\n${RED}❌ Chyba při nahrávání souborů${NC}"
    exit 1
fi

# Nastavení oprávnění pro skripty
echo -e "\n${YELLOW}🔧 Nastavení oprávnění...${NC}"
ssh -i "$KEY_FILE" "$SSH_USER@$INSTANCE_IP" << EOF
    cd $TARGET_DIR
    chmod +x deployment/aws/*.sh
    chmod +x deployment/aws/*.py
    chmod +x test_binance_aws.py
EOF

# Kontrola .env souboru
echo -e "\n${YELLOW}🔑 Kontrola konfigurace...${NC}"
if ssh -i "$KEY_FILE" "$SSH_USER@$INSTANCE_IP" "[ -f $TARGET_DIR/.env ]"; then
    echo -e "${GREEN}✅ Soubor .env již existuje${NC}"
else
    echo -e "${YELLOW}⚠️  Soubor .env neexistuje${NC}"
    
    # Pokus o nahrání lokálního .env souboru
    if [ -f "$PROJECT_ROOT/.env" ]; then
        read -p "Nahrát lokální .env soubor? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            scp -i "$KEY_FILE" "$PROJECT_ROOT/.env" "$SSH_USER@$INSTANCE_IP:$TARGET_DIR/"
            echo -e "${GREEN}✅ .env soubor nahrán${NC}"
        fi
    else
        echo "Vytvořte .env soubor na serveru pomocí:"
        echo "ssh -i $KEY_FILE $SSH_USER@$INSTANCE_IP"
        echo "cd $TARGET_DIR"
        echo "cp deployment/aws/.env.example .env"
        echo "nano .env"
    fi
fi

# Vytvoření adresáře pro logy
ssh -i "$KEY_FILE" "$SSH_USER@$INSTANCE_IP" "mkdir -p $TARGET_DIR/logs"

# Souhrn
echo -e "\n${GREEN}🎉 Nasazení dokončeno!${NC}"
echo "======================="
echo ""
echo -e "${YELLOW}📋 Další kroky:${NC}"
echo ""
echo "1. Připojte se k serveru:"
echo "   ssh -i $KEY_FILE $SSH_USER@$INSTANCE_IP"
echo ""
echo "2. Přejděte do adresáře projektu:"
echo "   cd $TARGET_DIR"
echo ""
echo "3. Nainstalujte Python závislosti:"
echo "   python3.9 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "4. Otestujte Binance API:"
echo "   python test_binance_aws.py"
echo ""
echo "5. Spusťte monitoring:"
echo "   chmod +x deployment/aws/start_monitor.sh"
echo "   ./deployment/aws/start_monitor.sh"
echo ""
echo -e "${GREEN}🌐 Dashboard bude dostupný na: http://$INSTANCE_IP:8000${NC}"