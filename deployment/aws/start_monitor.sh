#!/bin/bash

# Binance Portfolio Monitor - Start Script
# Spouští aplikaci pomocí screen utility

# Nastavení barev pro výstup
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Název screen session
SCREEN_NAME="monitor"

# Pracovní adresář (upravte podle potřeby)
WORK_DIR="/home/ec2-user/binance-monitor"

echo -e "${GREEN}🚀 Binance Portfolio Monitor - Spouštěč${NC}"
echo "======================================="

# Kontrola, jestli už běží screen session
if screen -list | grep -q "\.${SCREEN_NAME}"; then
    echo -e "${YELLOW}⚠️  Monitor již běží v screen session '${SCREEN_NAME}'${NC}"
    echo "Pro připojení použijte: screen -r ${SCREEN_NAME}"
    echo "Pro zastavení: připojte se a stiskněte Ctrl+C"
    exit 1
fi

# Kontrola pracovního adresáře
if [ ! -d "$WORK_DIR" ]; then
    echo -e "${RED}❌ Pracovní adresář neexistuje: $WORK_DIR${NC}"
    echo "Upravte proměnnou WORK_DIR v tomto scriptu"
    exit 1
fi

cd "$WORK_DIR"

# Kontrola Python instalace
if ! command -v python3.9 &> /dev/null; then
    echo -e "${RED}❌ Python 3.9 není nainstalován${NC}"
    echo "Nainstalujte pomocí: sudo yum install python3.9"
    exit 1
fi

# Kontrola virtuálního prostředí
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Nalezeno virtuální prostředí${NC}"
    PYTHON_CMD="venv/bin/python"
else
    echo -e "${YELLOW}⚠️  Virtuální prostředí nenalezeno, používám systémový Python${NC}"
    PYTHON_CMD="python3.9"
fi

# Kontrola requirements
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠️  Soubor requirements.txt nenalezen${NC}"
fi

# Kontrola .env souboru
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Soubor .env nenalezen${NC}"
    echo "Vytvořte jej pomocí: cp deployment/aws/.env.example .env"
    echo "A vyplňte své údaje"
    exit 1
fi

# Vytvoření adresáře pro logy
mkdir -p logs

# Informace o spuštění
echo -e "\n${YELLOW}📋 Konfigurace:${NC}"
echo "   Screen session: ${SCREEN_NAME}"
echo "   Pracovní adresář: ${WORK_DIR}"
echo "   Python: ${PYTHON_CMD}"
echo "   Logy: ${WORK_DIR}/logs/"

# Spuštění v screen session
echo -e "\n${GREEN}🏃 Spouštím monitor...${NC}"

screen -dmS ${SCREEN_NAME} bash -c "
    cd ${WORK_DIR}
    source .env
    export PYTHONPATH=${WORK_DIR}
    echo '🚀 Spouštím Binance Portfolio Monitor...'
    echo 'Pro ukončení stiskněte Ctrl+C'
    echo ''
    ${PYTHON_CMD} deployment/aws/run_forever.py
"

# Čekání na start
sleep 2

# Kontrola, jestli session běží
if screen -list | grep -q "\.${SCREEN_NAME}"; then
    echo -e "\n${GREEN}✅ Monitor úspěšně spuštěn!${NC}"
    echo ""
    echo -e "${YELLOW}📌 Užitečné příkazy:${NC}"
    echo "   Připojení k monitoru:  screen -r ${SCREEN_NAME}"
    echo "   Odpojení (běží dál):   Ctrl+A, pak D"
    echo "   Zobrazení logů:        tail -f logs/continuous_runner.log"
    echo "   Kontrola dashboardu:   curl http://localhost:8000"
    echo ""
    echo -e "${GREEN}🌐 Dashboard běží na: http://localhost:8000${NC}"
else
    echo -e "${RED}❌ Nepodařilo se spustit monitor${NC}"
    echo "Zkontrolujte logy pro více informací"
    exit 1
fi