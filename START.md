# 企业知识库问答系统 — 部署说明（Windows）

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
| 旧格式转换 | `.doc`/`.ppt` → `.docx`/`.pptx`（MS Office COM，Windows） |

---

## 二、环境要求

- **Python 3.10+**（安装时勾选 "Add to PATH"）
- **Node.js 18+**
- **Microsoft VC++ Redistributable**（PyTorch 依赖，`deploy.bat` 会自动检测并安装）
- NVIDIA GPU（可选）：有则向量化/精排更快，无则 CPU 慢跑
- MS Office（可选）：用于 `.doc`/`.ppt` 自动转换
- Tesseract OCR（可选）：图片/扫描件文字识别

---

## 一键部署（推荐）

在项目根目录**双击 `deploy.bat`**，会自动完成：

1. 检测并安装 VC++ 运行库（如缺失）
2. 创建虚拟环境 + 安装后端依赖
3. 安装前端依赖
4. 同时启动后端（8000）和前端（5173）

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

## 四、云服务器部署（Windows）

### 1. 上传项目到服务器

- 本机跑 `package.bat` 生成 `kb-deploy.zip`（纯净版本，不含 venv/node_modules/data）
- 上传 zip 到服务器并解压

### 2. 配置密钥

把 `backend\.env.example` 复制成 `backend\.env`，填入 `ANTHROPIC_AUTH_TOKEN`。

### 3. 双击 `deploy.bat`

自动装 VC++ 运行库 + 依赖 + 启动前后端。首次会下载模型（约 3.3GB），需几分钟。

### 4. 放行端口（两层防火墙都要放）

**阿里云安全组**（控制台）：入方向放行 `5173` 和 `8000`。

**Windows 防火墙**（服务器上，管理员 cmd）：

```cmd
netsh advfirewall firewall add rule name="KB-Frontend" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="KB-Backend" dir=in action=allow protocol=TCP localport=8000
```

### 5. 验证

本机浏览器访问：

- 后端：`http://服务器IP:8000/api/health` → 返回 `{"status":"ok"}`
- 前端：`http://服务器IP:5173`

---

## 五、上线前注意

1. **VC++ 运行库**：`deploy.bat` 已自动检测安装；手动部署时若报 `c10.dll` / `vcruntime140.dll` 加载失败，装 `https://aka.ms/vs/16/release/vc_redist.x64.exe`。
2. **`.doc`/`.ppt` 转换**：Windows 上依赖 MS Office，没装 Office 则旧版 Word/PPT 无法转换（其余格式不受影响）。
3. **Tesseract 路径**：自动探测——优先读 `.env` 的 `TESSERACT_CMD`，否则找系统 `tesseract`，再退回 `D:\tools\TesseractOCR\tesseract.exe`。
4. **密钥安全**：`.env` 里的 `ANTHROPIC_AUTH_TOKEN`、`JWT_SECRET` 要改，且不要把 `.env` 提交到 git。
5. **首次启动慢**：首次会下载 bge 模型（约 3.3GB），走 `hf-mirror.com` 加速。

---

## 六、支持的文档格式

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

## 七、功能清单

- ✅ 20+ 文档格式解析（含表格、扫描件 OCR、GBK 编码识别）
- ✅ 混合检索：向量 + BM25 + RRF 融合 + Cross-Encoder 精排
- ✅ 统计类问答自适应扩大召回（金额合计、笔数等不漏检）
- ✅ 引用可追溯（`[来源N]` + 来源卡片）
- ✅ 多租户隔离 + 工作空间 + 知识库三级权限（admin/write/read）+ 成员管理
- ✅ 对话历史持久化 + 刷新停留当前对话（URL 持久化）
- ✅ Markdown 排版（表格/代码块/列表）
- ✅ LLM 流式回答（Anthropic 兼容 API）

---

## 八、数据存储位置

| 数据 | 路径 |
|---|---|
| SQLite 数据库 | `backend/data/app.db` |
| ChromaDB 向量库 | `backend/data/chroma/` |
| 上传文件 | `backend/data/uploads/{tenant_id}/{kb_id}/` |
| 模型缓存 | `C:\Users\{用户}\.cache\huggingface\hub\`（约 3.3GB） |
