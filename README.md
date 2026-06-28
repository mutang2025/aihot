# AIHOT - 每日 AI 热点新闻展示站

## 项目简介

AIHOT 是一个每日 AI 热点新闻聚合与展示网站，参考卡兹克（数字生命卡兹克）的 AIHOT 经验设计，采用 L3 全栈方案。

核心功能：自动抓取全球 AI 领域新闻源 → 智能筛选 AI 相关内容 → 自动评分排序 → 翻译 → 聚类去重 → 精选展示，全程自动化。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + Tailwind CSS + Shadcn/ui |
| 后端 | FastAPI (Python 3.12) + SQLAlchemy + APScheduler |
| 数据库 | PostgreSQL 15 (复用宿主 postgresql 容器) |
| 缓存/队列 | Redis 7 |
| AI 能力 | QwenPaw / LiteLLM / Agnes API |
| 部署 | Docker Compose + 1panel-network |

## 架构概览

```
信源 RSS → Scraper Worker → 原始新闻入库
                                ↓
                         Prefilter Worker (AI 相关判断)
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
              Scorer Worker          Translator Worker
              (评分排序)             (中英翻译)
                    ↓                       ↓
                    └───────────┬───────────┘
                                ↓
                       Clusterer Worker (聚类去重)
                                ↓
                      Digester Worker (精选摘要)
                                ↓
                        API → Next.js Frontend
```

## 目录结构

```
/home/aihot/
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── api/        # REST 路由 (health, news, sources, feedback)
│   │   ├── models/     # SQLAlchemy ORM 模型
│   │   ├── workers/    # 后台任务 (scraper, prefilter, scorer, clusterer, digester, translator)
│   │   └── sources_data/
│   │       └── sources.yaml  # 30 个信源配置
│   ├── alembic/        # 数据库迁移
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/           # Next.js 前端
│   ├── app/            # App Router 页面
│   ├── components/     # UI 组件
│   ├── lib/            # API 客户端、工具函数
│   └── public/         # 静态资源
├── scrapers/           # 自定义爬虫逻辑
├── data/               # 运行时数据 (日志、缓存)
├── docs/               # 文档
├── docker-compose.yml  # 编排配置
├── .env                # 环境变量 (敏感信息，不提交)
└── .env.example        # 环境变量模板
```

## 信源分级

| 等级 | 说明 | 数量 |
|------|------|------|
| T1 | 顶级信源 (Official Blogs, Major News) | 10 |
| T1.5 | 高级信源 (Top Research Labs, Influential Accounts) | 10 |
| T2 | 普通信源 (News Aggregators, Community Feeds) | 10 |

共 30 个信源，涵盖 ArXiv、OpenAI Blog、Google AI Blog、Hacker News、TechCrunch 等。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/news` | 获取新闻列表 (支持分页、筛选) |
| GET | `/api/news/{id}` | 获取单条新闻详情 |
| GET | `/api/sources` | 获取信源列表 |
| POST | `/api/admin/scrape` | 手动触发抓取 |
| POST | `/api/admin/run-prefilter` | 手动运行预筛 |
| POST | `/api/admin/run-scoring` | 手动运行评分 |
| POST | `/api/admin/run-translator` | 手动运行翻译 |
| POST | `/api/admin/run-cluster` | 手动运行聚类 |
| POST | `/api/admin/run-digest` | 手动运行精选 |
| POST | `/api/feedback` | 提交反馈 |

完整 API 文档: `http://<host>:8888/docs`

## 快速开始

### 1. 配置环境变量

```bash
cd /home/aihot
cp .env.example .env
# 编辑 .env 填入实际值
```

### 2. 启动服务

```bash
docker compose up -d --build
```

### 3. 初始化数据

```bash
# 等待数据库就绪后执行
docker compose exec backend python -m app.scripts.seed_sources
```

### 4. 访问

- 前端: `http://<主机IP>:3080`
- API: `http://<主机IP>:8888/docs`

## 数据 Pipeline

每条新闻的处理流程：

1. **抓取 (Scrape)**: 从 RSS/API 拉取原始新闻
2. **预筛 (Prefilter)**: AI 相关性判断，标记 `is_ai_related`
3. **评分 (Score)**: 多维度评分 (信源权重 × 热度因子 × 新鲜度衰减)
4. **翻译 (Translate)**: 非中文新闻自动翻译为中/英双语
5. **聚类 (Cluster)**: 相似新闻合并去重
6. **精选 (Digest)**: 按公式重算排序，取 Top 25 展示

## 部署说明

- 复用宿主机的 `postgresql` 容器 (1panel-network)
- 网络模式: `1panel-network` (外部网络)
- 数据持久化: `aihot-redis-data`, `aihot-data` 卷
- 时区: `Asia/Shanghai`

## 管理员

- 默认账号: `aihot` / `changeme` (通过环境变量修改)
- 管理面板: `/admin` (前端)

## 许可证

内部项目，仅供团队使用。
