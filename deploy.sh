#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=============================================="
echo "  企业知识库问答系统 - Ubuntu 一键部署"
echo "=============================================="

# 1. 系统依赖
echo "[1/6] 安装系统依赖 (需要 sudo 密码)..."
sudo apt update
sudo apt install -y curl python3 python3-venv python3-pip \
    tesseract-ocr tesseract-ocr-chi-sim libreoffice nginx

# 2. Node 20（Vite 6 需要 Node 18+，apt 默认版本太老）
echo "[2/6] 安装 Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. 后端依赖
echo "[3/6] 安装后端依赖..."
cd "$ROOT/backend"
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

if [ ! -f .env ]; then
    echo "    警告: 未找到 backend/.env，请复制 .env.example 并填入 ANTHROPIC_AUTH_TOKEN"
fi

# 4. 前端构建
echo "[4/6] 构建前端..."
cd "$ROOT/frontend"
npm install
npm run build

# 5. nginx 配置
echo "[5/6] 配置 nginx..."
sudo tee /etc/nginx/sites-available/kb > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    root ${ROOT}/frontend/dist;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/kb /etc/nginx/sites-enabled/kb
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# 6. systemd 常驻服务
echo "[6/6] 启动后端 (systemd 开机自启)..."
sudo tee /etc/systemd/system/kb.service > /dev/null <<EOF
[Unit]
Description=Knowledge Base Backend
After=network.target

[Service]
WorkingDirectory=${ROOT}/backend
Environment=HF_ENDPOINT=https://hf-mirror.com
ExecStart=${ROOT}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now kb

echo ""
echo "=============================================="
echo "  部署完成！"
echo "  前端:     http://<服务器IP>"
echo "  后端 API: http://<服务器IP>:8000/docs"
echo "  后端日志: sudo journalctl -u kb -f"
echo "=============================================="
echo ""
echo "  ⚠️  若 backend/.env 尚未配置，请先编辑后重启:"
echo "     sudo systemctl restart kb"
