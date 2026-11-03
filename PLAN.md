# 企业知识库 RAG 系统 — 实施计划

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| **前端** | React 18 + Vite + TypeScript + TailwindCSS | 明亮自然风主题 |
| **后端** | Python FastAPI + SQLite | 异步 + 轻量数据库 |
| **文档解析** | PyMuPDF + python-docx + openpyxl + python-pptx + Tesseract OCR | 支持 20+ 格式 |
| **向量库** | ChromaDB（嵌入式） | 零部署，collection 级别隔离 |
| **Embedding** | sentence-transformers (bge-large-zh-v1.5) | RTX 4070 GPU 加速 |
| **LLM** | Anthropic 兼容 API | 用户提供的网关 |
| **OCR** | Tesseract 5.x | 图片文字识别（中英） |
| **存储** | 本地文件系统 | 文档文件存储 |

## 支持的文档格式

| 格式 | 扩展名 | 处理方式 |
|------|--------|---------|
| **PDF** | .pdf | PyMuPDF 逐页提取 |
| **Word** | .docx, .doc | python-docx 段落提取 |
| **Excel** | .xlsx, .xls | openpyxl → Markdown 表格 |
| **PPT** | .pptx, .ppt | python-pptx 逐页提取 |
| **Markdown/文本** | .md, .txt, .rst | 直接读取 |
| **HTML** | .html, .htm | BeautifulSoup 正文提取 |
| **图片** | .png, .jpg, .jpeg, .bmp, .gif, .webp, .tiff | Tesseract OCR + 元数据 |

## 多租户架构

```
Tenant A                    Tenant B
  ├── 用户1 (admin)           ├── 用户3 (admin)
  ├── 用户2 (member)          ├── 用户4 (member)
  ├── 知识库: 技术文档         ├── 知识库: 人事制度
  │   ├── doc1.pdf            │   ├── doc3.pdf
  │   └── doc2.pdf            │   └── doc4.pdf
  └── ChromaDB:              └── ChromaDB:
      collection: kb_{hash}     collection: kb_{hash}
```

- **隔离方式**：JWT 携带 tenant_id，API 层强制注入过滤
- **注册方式**：首次注册自动创建租户，自动创建默认知识库
- **Collection 命名**：MD5 哈希短名（19字符），规避 ChromaDB 63字符限制

## 项目结构

```
mcp2/
├── start.bat                     # 一键启动（后端+前端）
├── START.md                      # 启动说明
├── PLAN.md                       # 本文件
├── backend/
│   ├── start.bat
│   ├── .env                      # API Key / 配置
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI 入口 + CORS
│       ├── config.py             # 环境变量配置
│       ├── database.py           # SQLite ORM (SQLAlchemy)
│       ├── api/
│       │   ├── auth.py           # 注册/登录 JWT
│       │   ├── kb.py             # 知识库 CRUD + 权限管理
│       │   ├── upload.py         # 文件上传 + 异步处理
│       │   ├── chat.py           # RAG 问答 SSE 流式
│       │   └── agent.py          # 跨知识库 Agent 路由
│       ├── core/
│       │   ├── file_processor.py # 通用文件处理器（20+格式）
│       │   ├── embeddings.py     # bge-large-zh GPU 嵌入
│       │   ├── vector_store.py   # ChromaDB 封装 + 短名生成
│       │   ├── reranker.py       # 关键词+向量混合排序
│       │   └── llm_client.py     # LLM (Anthropic/OpenAI 兼容)
│       ├── models/               # Tenant / User / KnowledgeBase / Document / KBMember
│       └── middleware/auth.py    # JWT 中间件
├── frontend/
│   ├── start.bat
│   └── src/
│       ├── pages/
│       │   ├── Login.tsx         # 登录注册（自然风景背景）
│       │   ├── Dashboard.tsx     # 知识库仪表盘 + 统计
│       │   ├── KnowledgeBase.tsx # 文档管理 + 拖拽上传（多格式）
│       │   └── Chat.tsx          # AI 对话界面（流式 + 引用）
│       ├── components/           # Layout / ChatBubble / SourceCard
│       ├── hooks/useChat.ts      # SSE 流式对话 Hook
│       ├── api/client.ts         # API 封装（含 Agent 模式）
│       └── stores/authStore.ts   # Zustand 状态管理
```

## 核心数据流

### 上传流程
```
用户拖拽文件 → 前端上传 /api/upload
  → 后端识别格式 → 保存文件 → 返回 doc_id
  → 异步任务: 对应提取器提取文本
    → 语义分块(800 chars, overlap 100)
    → bge-large-zh GPU 生成 embedding
    → ChromaDB collection.insert(chunks)
  → 更新文档状态: uploaded → processing → done/error
  → 前端轮询刷新状态
```

### 问答流程
```
用户提问 → POST /api/chat (SSE)
  → ChromaDB 向量检索 top_k=10
  → 关键词+向量 Reranker 精排 → top_k=5
  → 构建 Prompt + 上下文 + 来源标注
  → LLM 流式生成
  → SSE 推送: chunk → sources → done
```

## API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册（自动创建租户+默认知识库） |
| POST | /api/auth/login | 登录，返回 JWT |
| GET  | /api/auth/me | 当前用户信息 |
| GET  | /api/knowledge-bases | 列出当前租户的知识库 |
| POST | /api/knowledge-bases | 创建知识库 |
| DELETE | /api/knowledge-bases/{id} | 删除知识库 |
| PUT  | /api/knowledge-bases/{id}/members | 管理成员 |
| POST | /api/knowledge-bases/{id}/upload | 上传文档（20+格式） |
| GET  | /api/knowledge-bases/{id}/documents | 文档列表 |
| DELETE | /api/documents/{id} | 删除文档（含向量清理） |
| POST | /api/knowledge-bases/{id}/chat | SSE 流式问答 |
| POST | /api/agent/chat | Agent 跨知识库问答 |

## 启动方式

```cmd
cd D:\cy\AI\agent\mcp2
start.bat
```

或分别启动：
```cmd
# 后端
cd backend
venv\Scripts\activate
set HF_ENDPOINT=https://hf-mirror.com
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm run dev
```

- 后端: `http://localhost:8000/docs`
- 前端: `http://localhost:5173`

## 数据存储位置

| 数据 | 路径 |
|------|------|
| SQLite 数据库 | `backend/data/app.db` |
| ChromaDB 向量库 | `backend/data/chroma/` |
| 上传文件 | `backend/data/uploads/{tenant_id}/{kb_id}/` |
| Embedding 模型 | `C:\Users\{用户}\.cache\huggingface\hub\models--BAAI--bge-large-zh-v1.5\` |
| Reranker 模型 | `C:\Users\{用户}\.cache\huggingface\hub\models--BAAI--bge-reranker-v2-m3\` |

## 检索架构

```
用户问题
  → 向量检索 (ChromaDB, bge-large-zh, top_k=20)
  → BM25 关键词检索 (内存倒排索引, top_k=20)
  → RRF 融合 (Reciprocal Rank Fusion, 向量权重 0.55)
  → Cross-Encoder Reranker (bge-reranker-v2-m3, GPU, top_k=5)
  → LLM 生成回答 (流式 SSE)
```

## GPU 使用

| 组件 | 显存 | 说明 |
|------|------|------|
| Embedding (bge-large-zh-v1.5) | ~1.3GB | 文本转向量 |
| Reranker (bge-reranker-v2-m3) | ~2.0GB | 搜索结果精排 |
| **合计** | **~3.5GB** | RTX 4070 (8GB) 绰绰有余 |

## 已实现功能

- ✅ 20+ 文档格式上传解析（PDF/Word/Excel/PPT/Markdown/HTML/图片OCR）
- ✅ 混合检索：向量 + BM25 with RRF 融合
- ✅ GPU Cross-Encoder Reranker 精排
- ✅ LLM 流式回答 (Anthropic Messages API)
- ✅ 多租户隔离 + 知识库权限 (admin/write/read)
- ✅ Agent 跨知识库路由
- ✅ 对话历史持久化 (SQLite, 刷新不丢)
- ✅ 明亮自然风 Web UI (React + TailwindCSS)
- ✅ 一键启动脚本

## 已知决策

1. **Embedding**：`BAAI/bge-large-zh-v1.5` 本地 GPU 运行（RTX 4070，~1.3GB）
2. **Reranker**：`BAAI/bge-reranker-v2-m3` 本地 GPU 运行（~2.0GB）
3. **模型下载镜像**：`hf-mirror.com`（国内加速）
4. **Pip 镜像**：`pypi.tuna.tsinghua.edu.cn`
5. **Tesseract**：`D:\tools\TesseractOCR\`
6. **租户注册**：开放注册，首次注册自动创建租户和默认知识库
7. **ChromaDB 命名**：采用 `kb_{md5_hash[:16]}` 短名（19字符）
8. **LLM**：Anthropic 兼容 API，支持 system prompt 和流式
9. **对话持久化**：SQLite `conversations` + `conversation_messages` 表
