# 企业知识库问答系统 — 部署说明

> 面向全员的企业知识库 + 问答智能体：把散落文档整理成 AI 可用的结构化知识，实现引用可追溯的精准问答与数据统计。

---

## 一、技术栈概览

| 层 | 选型 |
|---|---|
| 前端 | React 18 + Vite + TypeScript + TailwindCSS |
| 后端 | Python FastAPI + SQLAlchemy(SQLite) + JWT |
| 向量库 | ChromaDB（嵌入式，零部署） |
| 向量化 | sentence-transformers（bge-large-zh-v1.5） |
| 精排 | FlagEmbedding（bge-reranker-v2-m3） |
| LLM | Anthropic 兼容 API（`deepseek-v4-pro`） |
| 文档解析 | PyMuPDF / python-docx / openpyxl / xlrd / python-pptx / Tesseract OCR |
| 旧格式转换 | `.doc`/`.ppt` → `.docx`/`.pptx`（LibreOffice 优先，MS Office 回退） |

---

## 二、环境要求

### 本地开发（Windows）

- Python 3.10+
- Node.js 18+
- NVIDIA GPU（可选）：RTX 4070 已测试；无 GPU 也能跑（慢）
- MS Office（用于 `.doc`/`.ppt` 自动转换，可选）
- Tesseract OCR（图片/扫描件识别，可选）

### 服务器（Linux / Ubuntu）

- Ubuntu 22.04 LTS（推荐）或 Debian
- 内存 ≥ 8GB，磁盘 ≥ 50GB（模型 + 数据）
- NVIDIA GPU（可选）：T4 / A10 / RTX 系列，8GB+ 显存
- Python 3.10+、Node.js 18+、Tesseract、LibreOffice

---

## 一键部署（推荐）

拿项目到新机器，跑一个命令即可自动装依赖并启动：

**Windows**（需已装 Python 3.10+ 和 Node 18+）：
```cmd
deploy.bat
```

**Linux / Ubuntu**（自动装系统依赖、Node、LibreOffice、Tesseract、nginx）：
```bash
bash deploy.sh
```

> 首次部署前，先配置 `backend/.env`（复制 `backend/.env.example` 改名 `.env`，填入 `ANTHROPIC_AUTH_TOKEN`）。

> 打包纯净版本（排除本地生成文件）用 `package.bat`，产出 `kb-deploy.zip`。

---

## 三、本地部署（Windows）

### 1. 后端

> 以下命令在项目根目录执行。

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

> 有 NVIDIA GPU 时，把 torch 换成 CUDA 版：
> ```cmd
> pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121 --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple/
> ```

启动：

```cmd
set HF_ENDPOINT=https://hf-mirror.com
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端

```cmd
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`（开发态通过 Vite 代理把 `/api` 转发到后端 8000）。

### 3. 配置文件 `backend/.env`

```
ANTHROPIC_AUTH_TOKEN=sk-xxxx
ANTHROPIC_BASE_URL=https://ai-api-gateway.app.baizhi.cloud/api/anthropic
ANTHROPIC_MODEL=deepseek-v4-pro
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
JWT_SECRET=改成随机字符串
DATABASE_URL=sqlite:///./data/app.db
CHROMA_PERSIST_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
TESSERACT_CMD=
```

---

## 四、服务器部署（Ubuntu 22.04）

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm \
     tesseract-ocr tesseract-ocr-chi-sim libreoffice nginx
```

> `libreoffice` 用于 `.doc`/`.ppt` 转换（Linux 下替代 MS Office）。
> 若 GPU 服务器：另装 NVIDIA 驱动 + CUDA 12.1。

### 2. 后端

```bash
cd /opt/app/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

> GPU 服务器装 CUDA torch；纯 CPU 服务器直接用 requirements 里的 torch（CPU 版）。

启动（生产，去掉 --reload）：

```bash
export HF_ENDPOINT=https://hf-mirror.com
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 前端构建 + nginx

```bash
cd /opt/app/frontend
npm install
npm run build        # 产出 dist/ 静态文件
```

nginx 配置（`/etc/nginx/sites-available/app`）：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /opt/app/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用：

```bash
sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 4. 后端常驻（systemd 开机自启）

创建 `/etc/systemd/system/kb.service`：

```ini
[Unit]
Description=Knowledge Base Backend
After=network.target

[Service]
WorkingDirectory=/opt/app/backend
Environment=HF_ENDPOINT=https://hf-mirror.com
ExecStart=/opt/app/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kb
sudo systemctl status kb
```

---

## 五、服务器选型建议

| 方案 | 配置 | 说明 |
|---|---|---|
| **省成本（CPU）** | 4C8G + 50GB SSD | 能跑，embedding 慢、reranker 退回关键词，适合低频使用 |
| **推荐（GPU）** | 4C8G + 50GB SSD + T4(16GB) | embedding+reranker 走 GPU（约 3.5GB 显存），问答快 |
| 操作系统 | **Ubuntu 22.04 LTS** | Python 生态最顺，依赖安装简单 |

> CPU 模式修改：`backend/app/core/embeddings.py` 里 `device="cuda"` 改成 `device="cpu"`；reranker 会自动走 CPU fallback。

---

## 六、上线前注意

1. **`.doc`/`.ppt` 转换**：已兼容——优先用 LibreOffice（Linux 装 `libreoffice`），没有则回退 MS Office（Windows）。
2. **Tesseract 路径**：已自动探测——优先读 `.env` 的 `TESSERACT_CMD`，否则自动找系统 `tesseract`，再退回 Windows 默认路径。
3. **密钥安全**：`.env` 里的 `ANTHROPIC_AUTH_TOKEN`、`JWT_SECRET` 要改，且不要把 `.env` 提交到 git。
4. **CORS**：前端走 nginx 同域后，CORS 配置可保留（同域请求不触发 CORS）。

---

## 七、支持的文档格式

| 格式 | 扩展名 |
|---|---|
| PDF（含扫描件 OCR） | .pdf |
| Word（`.doc` 自动转 `.docx`） | .docx, .doc |
| Excel | .xlsx, .xls |
| CSV | .csv |
| PowerPoint（`.ppt` 自动转 `.pptx`） | .pptx, .ppt |
| Markdown | .md, .markdown |
| 纯文本（自动识别 GBK/UTF-8） | .txt, .rst |
| HTML | .html, .htm |
| 图片（OCR） | .png, .jpg, .jpeg, .bmp, .gif, .webp, .tiff, .tif |

---

## 八、功能清单

- ✅ 20+ 文档格式解析（含表格、扫描件 OCR、GBK 编码识别）
- ✅ 混合检索：向量 + BM25 + RRF 融合 + Cross-Encoder 精排
- ✅ 统计类问答自适应扩大召回（金额合计、笔数等不漏检）
- ✅ 引用可追溯（`[来源N]` + 来源卡片）
- ✅ 多租户隔离 + 工作空间 + 知识库三级权限（admin/write/read）+ 成员管理
- ✅ 对话历史持久化 + 刷新停留当前对话（URL 持久化）
- ✅ Markdown 排版（表格/代码块/列表）
- ✅ LLM 流式回答（Anthropic 兼容 API）

---

## 九、数据存储位置

| 数据 | 路径 |
|---|---|
| SQLite 数据库 | `backend/data/app.db` |
| ChromaDB 向量库 | `backend/data/chroma/` |
| 上传文件 | `backend/data/uploads/{tenant_id}/{kb_id}/` |
| 模型缓存 | `~/.cache/huggingface/hub/`（约 3.3GB） |
