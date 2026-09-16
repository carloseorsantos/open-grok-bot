#!/usr/bin/env bash
set -e

echo "=================================================="
echo "🚀 Open Grok Bot — Instalador Automático (Lightsail/Ubuntu)"
echo "=================================================="

# 1. Configurar 2GB Swap se não existir (evita OOM no Chromium com 1GB RAM)
if [ ! -f /swapfile ]; then
    echo "📦 Configurando 2GB de Swap..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✅ Swap de 2GB ativado com sucesso!"
else
    echo "✅ Swap já configurado."
fi

# 2. Atualizar pacotes e dependências do sistema
echo "📦 Instalando pacotes do sistema..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl

# 3. Criar ambiente virtual Python
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual Python (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Instalar Chromium e dependências de sistema do Playwright
echo "🌐 Instalando Chromium do Playwright e bibliotecas Linux..."
playwright install chromium
sudo playwright install-deps chromium

# 5. Garantir arquivo .env
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        chmod 600 .env
        echo "⚠️ Arquivo .env criado a partir de .env.example. Não se esqueça de preencher suas chaves!"
    fi
fi

# 6. Criar serviço systemd para rodar 24/7 automaticamente
echo "⚙️ Configurando serviço systemd (24/7)..."
APP_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/open-grok-bot.service"

sudo bash -c "cat << SERVICE_EOF > $SERVICE_FILE
[Unit]
Description=Open Grok Bot Telegram Daemon
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -u run.py --telegram
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF"

sudo systemctl daemon-reload
sudo systemctl enable open-grok-bot
sudo systemctl restart open-grok-bot

echo ""
echo "=================================================="
echo "🎉 Instalação concluída com sucesso!"
echo "🤖 O Open Grok Bot está rodando 24/7 via systemd!"
echo "Comandos úteis:"
echo "• Ver status: sudo systemctl status open-grok-bot"
echo "• Ver logs:   sudo journalctl -u open-grok-bot -f"
echo "• Reiniciar:  sudo systemctl restart open-grok-bot"
echo "=================================================="
