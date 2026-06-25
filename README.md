# 🚀 AI新闻系统 ( News )
一个基于 FastAPI 和 SQLAlchemy 构建的现代化新闻资讯平台后端服务，提供完整的用户管理、新闻浏览、收藏、历史记录，并集成了 AI 智能问答（多轮对话 + 角色定制）。项目采用全异步架构，结合 Redis 缓存与会话管理，具备生产级可维护性和扩展能力。

## ✨ 核心特性

#### 👤 用户认证：注册、登录、Token 鉴权（7天有效期），密码加密存储。

#### 📰 新闻模块：分类列表、分页新闻列表、新闻详情、自动增加浏览量。


#### ❤️ 收藏功能：添加/取消收藏、收藏列表、清空收藏、收藏状态检查。


#### 🕒 浏览历史：自动记录浏览行为、分页历史列表、单条删除/全部清空。


## 🤖 AI 智能问答：

基于阿里云 DashScope（通义千问）的流式对话。

#### 多轮会话记忆：通过 Redis 存储用户对话上下文，支持连续对话。

#### 角色定制：内置“通用助手”、“新闻助手”、“情感顾问”、“科技专家”，通过 system prompt 实现。

后端统一代理 API Key，前端无需暴露敏感信息。

#### 🗄️ 缓存策略：Redis 缓存新闻列表、分类数据、用户历史记录，提升响应速度。

#### 📜 日志系统：分级日志（DEBUG/INFO/ERROR），输出到控制台和文件（自动轮转），便于调试与监控。

#### ⚡ 高性能异步：全异步 SQLAlchemy + FastAPI，支持高并发。

## 🛠 技术栈

| 类别 | 技术选型 |
|------|----------|
| 框架 | FastAPI |
| 数据库 | MySQL (5.7+) |
| ORM | SQLAlchemy 2.0 (异步) + aiomysql |
| 缓存/会话 | Redis (异步) |
| AI 服务 | 阿里云 DashScope (通义千问) / 兼容 OpenAI 接口 |
| 日志 | Python logging + RotatingFileHandler |
| 密码加密 | passlib[bcrypt] |
| 异步 HTTP | httpx |
| 环境变量 | python-dotenv |

## 📁 项目结构
```bash

├── cache/                     # 缓存操作封装
│   └── news_cache.py
├── config/                    # 配置管理
│   ├── db_config.py           # MySQL 异步连接
│   ├── cache_conf.py          # Redis 连接
│   ├── settings.py            # 全局配置（AI、上下文参数）
│   └── roles.py               # 预定义 AI 角色与 system prompt
├── crud/                      # 数据访问层（CRUD）
│   ├── favorite.py
│   ├── history.py
│   ├── news.py
│   ├── news_cache.py
│   ├── users.py
│   └── ai.py                  # AI 调用 + 上下文管理（Redis）
├── models/                    # SQLAlchemy ORM 模型
│   ├── favorite.py
│   ├── history.py
│   ├── news.py
│   └── users.py
├── routers/                   # API 路由层
│   ├── favorite.py
│   ├── history.py
│   ├── news.py
│   ├── users.py
│   └── ai.py                  # AI 对话流式接口
├── schemas/                   # Pydantic 数据验证模型
│   ├── base.py
│   ├── favorite.py
│   ├── history.py
│   ├── users.py
│   └── ai.py
├── utils/                     # 工具函数
│   ├── auth.py                # 认证依赖
│   ├── exception.py           # 全局异常处理器
│   ├── logger.py              # 日志配置
│   ├── response.py            # 统一响应格式
│   └── security.py            # 密码加密/验证
├── logs/                      # 运行时日志目录（自动创建）
├── .env                       # 环境变量（需自行创建）
├── main.py                    # 应用入口
└── test_main.http             # HTTP 接口测试样例
```

## 🚦 快速开始

### 前置要求

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+
- （可选）阿里云 DashScope API Key（用于 AI 功能）
  
### 1. 克隆项目
```bash
git clone https://github.com/yourusername/toutiao-news-backend.git
cd toutiao-news-backend
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
在项目根目录创建 .env 文件，填写以下内容：

```bash
# 阿里云 DashScope API（如需 AI 功能）
ALI_API_KEY=sk-your-api-key
ALI_MODEL=qwen3-max-preview
ALI_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

# 可选：调整上下文长度（默认10条）
CONTEXT_MAX_LENGTH=10
CONTEXT_EXPIRE_SECONDS=3600
```

### 4. 配置数据库与缓存
编辑 config/db_config.py 和 config/cache_conf.py 中的连接信息（或通过环境变量覆盖）：

```bash
# db_config.py
ASYNC_DATABASE_URL = "mysql+aiomysql://root:password@localhost:3306/news?charset=utf8mb4"

# cache_conf.py
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
```

### 5. 初始化数据库表
项目使用 SQLAlchemy，首次运行前需创建表结构。可在 Python 交互环境中执行：

```bash
from models import Base
from config.db_config import async_engine
import asyncio

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())
```

或者编写一个简单的初始化脚本。

### 6. 启动服务
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
访问 http://localhost:8000/docs 查看 Swagger 交互式 API 文档。

## 🤖 AI 智能问答模块说明

### 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | 流式对话（SSE），需登录，自动管理上下文 |
| GET | `/api/ai/history` | 获取当前用户的最近对话历史（存于 Redis） |
| DELETE | `/api/ai/context` | 清空当前用户的上下文 |

### 多轮会话机制

- 每个用户的对话上下文以 JSON 数组形式存储在 Redis，键为 `chat:context:{user_id}`
- 默认保留最近 10 条消息（用户+助手各算一条），超出则自动截断
- 上下文过期时间 1 小时（无活动自动清除）

### 角色定制

系统内置四种角色，通过 system 提示词实现差异化回答：

| 角色 ID | 说明 |
|---------|------|
| default | 通用助手 |
| news | 新闻分析师 |
| emotional | 情感顾问 |
| tech | 科技专家 |

前端在请求时携带 `role` 字段即可切换。

---

## 🗄 缓存设计

| 缓存内容 | Redis Key 模式 | 过期时间 | 说明 |
|----------|----------------|----------|------|
| 新闻分类 | `news:categories` | 2小时 | 全量缓存，减少数据库查询 |
| 新闻列表（分页） | `news:list:{category_id}:{page}:{size}` | 30分钟 | 按分类+分页缓存 |
| 用户上下文 | `chat:context:{user_id}` | 1小时 | AI 对话记忆 |

> **注意**：数据更新时会主动清除相关缓存，保证一致性。

---

## 📦 API 概览

### 用户模块 (`/api/users`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 用户注册 |
| POST | `/login` | 用户登录 |
| GET | `/info` | 获取当前用户信息 |
| PUT | `/update` | 更新用户信息 |
| PUT | `/password` | 修改密码 |

### 新闻模块 (`/api/news`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/categories` | 获取分类列表 |
| GET | `/list` | 分页新闻列表 |
| GET | `/detail` | 新闻详情（自动增加浏览量） |

### 收藏模块 (`/api/favorite`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/check` | 检查是否收藏 |
| POST | `/add` | 添加收藏 |
| DELETE | `/remove` | 取消收藏 |
| GET | `/list` | 分页收藏列表 |
| DELETE | `/clear` | 清空所有收藏 |

### 历史模块 (`/api/history`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/add` | 添加浏览记录 |
| GET | `/list` | 分页历史列表 |
| DELETE | `/remove` | 删除单条历史 |
| DELETE | `/clear_all` | 清空所有历史 |

### AI 模块 (`/api/ai`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 流式对话（SSE） |
| GET | `/history` | 获取对话上下文 |
| DELETE | `/context` | 清空当前会话上下文 |

> **注意**：所有需要登录的接口均需在请求头添加 `Authorization: {token}`

## 📝 日志系统

- 日志同时输出到 **控制台** 和 **文件**（`logs/app.log`、`logs/error.log`）
- 日志格式：`时间 - 模块名 - 级别 - 文件名:行号 - 消息`
- 文件按大小轮转（单个 10MB，保留 5 个备份）
- 可在 `utils/logger.py` 中调整日志级别或格式

---

## 🔧 开发与部署建议

- **开发模式**：使用 `uvicorn main:app --reload`，热重载
- **生产环境**：建议使用 `gunicorn -k uvicorn.workers.UvicornWorker main:app` 或部署到云服务
- **环境变量**：生产环境中务必使用 `.env` 管理敏感信息，不要提交到版本控制
- **数据库迁移**：项目目前未集成 Alembic，若需版本管理可自行添加

---

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request。

1. Fork 本仓库
2. 新建分支 `feature/your-feature`
3. 提交代码并编写测试
4. 发起 PR，描述清楚改动内容


## 🙏 致谢

- FastAPI 官方文档
- SQLAlchemy 异步支持
- 阿里云 DashScope 提供的 AI 能力

更多细节请查看源码注释或通过 Swagger（`/docs`）在线调试。如有问题，欢迎提 Issue。

