# AI插画生成器

输入描述 + 选风格，AI 绘制插画。前后端分离、异步任务编排的全栈项目。

## 项目来源

本项目基于开源教程项目 [yuyuanweb/ai-ppt](https://github.com/yuyuanweb/ai-ppt)（编程导航系列）进行二次开发。在其 AI PPT 生成能力基础上，主要做了以下改动：

- **新增独立的 AI 插画生成模块**：完整的后端 API + ARQ 异步任务 + 火山方舟 Seedream 对接 + 前端三页面（列表 / 创建 / 进度）
- **LLM 提示词优化管线**：用户中文需求 → LLM 按风格模板改写为英文生图提示词，支持重新生成与手动编辑
- **奶油甜品风 UI**：为插画模块设计独立的设计系统（`.images-module` scoped CSS 变量），不污染原有 PPT 模块样式
- **交互完善**：项目列表删除确认弹窗、错误友好提示、进度可视化等

---

## 功能特性

### 🎨 AI 插画生成（本仓库新增）

完整流程：**输入中文描述 → LLM 优化为生图提示词 → 火山方舟 Seedream 生图 → 下载校验 → 持久化存储**

- 三种风格模板：吉伊卡哇科普 / 简约手绘涂鸦 / 蜡笔小新教育
- 三种比例：1:1 / 16:9 / 9:16
- 提示词可预览、可编辑、可重新生成后再提交
- ARQ 异步任务 + 前端轮询进度，失败可重试
- 图片下载后做格式/尺寸校验，再写入本地 Storage
- 插画集列表页：卡片网格、大图预览、一键下载、带确认弹窗的删除
<img width="1269" height="757" alt="image" src="https://github.com/user-attachments/assets/cab561f5-d4c6-411f-a631-d8f1025cf3d6" />

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 19 · TypeScript · Vite · Tailwind CSS v4 · TanStack Query · Zustand · react-router |
| 后端 | FastAPI · SQLAlchemy (async) · Alembic · Pydantic Settings |
| 异步任务 | ARQ (Redis) · SSE 实时推送 |
| AI | LangChain（DeepSeek 等 OpenAI 兼容 LLM）· 火山方舟 Seedream 文生图 |
| 文档渲染 | python-pptx · FontTools |
| 基础设施 | PostgreSQL 16 · Redis 7 · Docker Compose |

---

## 本地开发

### 前置要求

- Docker Desktop（用于 Postgres / Redis）
- Node.js ≥ 20
- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)（Python 包管理）

### 启动步骤

```bash
# 1. 克隆仓库
git clone https://github.com/<your-name>/ai-ppt-generator.git
cd ai-ppt-generator

# 2. 启动数据库与缓存（postgres :39432, redis :39379）
make up

# 3. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少填写：
#   LLM_API_KEY      — DeepSeek 或其他 OpenAI 兼容 LLM 密钥（PPT 必需）
#   SEEDREAM_API_KEY — 火山方舟密钥（插画模块必需）

# 4. 安装依赖 + 数据库迁移
cd backend && uv sync && cd ..
make migrate

# 5. 启动三个进程（建议分三个终端窗口）
make dev-api     # 后端 API    http://localhost:39800
make dev-worker  # ARQ Worker（处理大纲/PPT/插画生成任务）
make dev-web     # 前端 dev    http://localhost:39173
```

访问 <http://localhost:39173> 注册账号即可使用。

### 端口约定

为避免与本机已有服务冲突，所有端口统一使用 `39xxx` 段：

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| 前端 dev server | 39173 | Vite strictPort |
| 后端 API | 39800 | uvicorn，前端 `/api` 代理到此 |
| PostgreSQL | 39432 | docker-compose 映射到容器内 5432 |
| Redis | 39379 | docker-compose 映射到容器内 6379 |

---

## 项目结构

```
backend/app/
├── api/          REST 接口（auth / projects / image_projects / media ...）
├── worker/       ARQ 异步任务（generate_outline / generate_deck / generate_image）
├── images/       Seedream 客户端 + 图片格式校验
├── services/     业务逻辑（含 LLM 提示词优化）
├── models/       SQLAlchemy ORM
├── schemas/      Pydantic 请求/响应模型
└── storage/      文件存储驱动（local / cos）

frontend/src/
├── features/images/   插画模块组件（ImageCard / StyleSelector / PromptEditor ...）
├── pages/             路由页面（ImagesPage / ImageCreatePage / ProjectsPage ...）
└── components/        通用 UI（AppShell / Button / Dialog ...）

shared/                前后端共享的布局 / 主题 JSON
docker-compose.yml     本地开发用的 postgres + redis
docker-compose.prod.yml 生产部署编排（nginx + caddy + api + worker）
```

---

## License

MIT
