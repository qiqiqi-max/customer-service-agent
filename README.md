# Customer Service Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React%20%2B%20Vite-Workbench-3b82f6?style=flat-square&logo=react&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Persistence-4479A1?style=flat-square&logo=mysql&logoColor=white)

Customer Service Agent 是一个面向电商客服场景的智能客服工作台。项目把大模型对话、商品知识、订单查询、物流跟踪、退款处理、会话归档、质检复盘和 FAQ 沉淀放在同一套业务流程里，适合用来演示客服 Agent 在真实业务中的基本工作方式。

这版项目已经从单页演示整理成了前后端分离的工作台：前端负责接待操作和过程展示，后端负责模型编排、工具调用、接口鉴权和数据落库，MySQL 保存商品、订单、物流、会话和质检数据。启动脚本会自动执行迁移，并补齐缺失的基础数据，不会在每次启动时清空已有记录。

## 项目截图

### 桌面端工作台

![客服工作台桌面端](docs/images/workbench-desktop.png)

### 移动端适配

![客服工作台移动端](docs/images/workbench-mobile.png)

## 功能范围

- **接待工作台**：支持售前导购、订单查询、物流咨询、售后退款等常见客服场景。
- **能力开关**：可以按场景选择商品介绍、导购推荐、订单查询、物流跟踪和退款退货工具。
- **工具轨迹**：展示模型调用业务工具后的输入、输出和结果卡片，方便复盘。
- **会话归档**：客户消息、助手回复和工具调用会保存到数据库，可按账号查看历史会话。
- **商品货架**：商品信息由 MySQL 读取，前端可以控制本轮参与回答的商品范围。
- **质检复盘**：支持会话总结、关键词质检和结构化风险结果保存。
- **FAQ 沉淀**：可以把高质量问答保存为 FAQ，后续作为知识检索内容使用。
- **多模型适配**：预留 DeepSeek、智谱、火山引擎和 OpenAI-compatible 接入方式。
- **知识库扩展**：默认支持 MySQL FAQ 检索，也保留 Dify Dataset 接入入口。

## 技术栈

后端：

- Python 3.10+
- FastAPI
- SQLAlchemy
- Alembic
- MySQL
- Pytest

前端：

- React
- Vite
- TypeScript
- Lucide React

模型与知识：

- DeepSeek / 智谱 / 火山引擎
- OpenAI-compatible Chat Completions
- MySQL FAQ
- Dify Dataset

## 项目结构

```text
customer-service-agent/
├── frontend/          # React + Vite 工作台
├── main.py            # 后端入口和 API 路由
├── llm_provider.py    # 大模型适配
├── business_services.py
├── conversation_store.py
├── audit_store.py
├── agent_tools.py
├── quality_rules.py
├── database.py        # SQLAlchemy 表结构和数据库初始化
├── alembic/           # 数据库迁移
├── data/              # 商品、订单、物流、RAG 数据访问
├── tools/             # 数据初始化和业务辅助脚本
├── docs/              # 知识库文档和项目截图
└── tests/             # 后端测试
```

## 数据库设计

项目当前使用 MySQL 作为主要数据存储，核心表包括：

- `products`：商品名称、描述和图片地址
- `orders`：订单状态、客户账号、商品和物流单号
- `tracking_events`：物流轨迹节点
- `faq_documents`：已沉淀的 FAQ 知识
- `conversations`：会话主表
- `messages`：会话消息，外键关联 `conversations`
- `tool_calls`：工具调用记录，外键关联 `conversations`
- `quality_reviews`：质检记录，可关联会话
- `faq_candidates`：从接待中沉淀的 FAQ 候选，可关联会话

启动时会先执行 Alembic 迁移，再检查基础数据。默认 seed 是幂等的：如果表里已有数据，不会清空重建。需要重置基础商品、订单、物流和 FAQ 时，可以手动执行：

```bash
.\.venv\Scripts\python.exe -m tools.seed_mysql_data --reset
```

## 核心流程

1. 客户在工作台输入问题。
2. 前端把账号、会话、商品范围和能力开关传给后端。
3. 后端构建客服 Agent 的上下文。
4. Agent 按需检索 FAQ 或调用订单、物流、退款工具。
5. 后端保存会话、工具轨迹和模型回复。
6. 运营侧可以继续做总结、质检和 FAQ 沉淀。

## 本地启动

### 1. 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install uv
uv sync
```

### 2. 准备 MySQL

本地创建数据库和项目专属用户，例如：

```sql
CREATE DATABASE customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'customer_service_agent'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON customer_service.* TO 'customer_service_agent'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 3. 配置环境变量

复制模板：

```bash
cp .env.local.example .env.local
```

本地运行常用配置：

```env
MOCK_MODE=False
LANGUAGE=zh
DATABASE_URL=mysql+pymysql://customer_service_agent:change_me@127.0.0.1:3306/customer_service
KNOWLEDGE_PROVIDER=mysql
BUSINESS_DATA_PROVIDER=mysql
```

### 4. 启动工作台

```bash
.\start_workbench.ps1
```

前端工作台：

```text
http://127.0.0.1:5173
```

后端健康检查：

```text
http://127.0.0.1:8080/ready
```

## 常用验证

后端测试：

```bash
.\.venv\Scripts\python.exe -m pytest
```

前端构建：

```bash
cd frontend
npm run build
```

数据库迁移：

```bash
.\.venv\Scripts\alembic.exe upgrade head
```

## 接口说明

常用业务接口：

- `GET /ready`：检查服务和数据库是否可用
- `GET /api/products`：获取商品货架
- `POST /api/chat`：发送客服消息
- `GET /api/conversations`：查看历史会话
- `GET /api/conversations/{conversation_id}`：查看会话详情
- `POST /api/quality-check`：执行质检
- `POST /api/summary`：生成会话总结
- `POST /api/faqs`：保存 FAQ

更完整的请求示例见 [API.md](API.md)。

## 当前状态

- MySQL 已接入为默认业务数据源
- Alembic 迁移已覆盖会话表和外键关系
- seed 脚本默认不覆盖已有数据
- 前端工作台已完成桌面端和移动端适配
- 后端测试覆盖核心接口、会话存储、业务工具、RAG、质检和模型适配
- 本地验证通过：`44 passed`，前端 `npm run build` 通过

## 知识库文件

- `docs/dify_product_service_knowledge.md`
- `docs/dify_faq_knowledge.md`

这两个文件可以导入 Dify，分别用于商品知识和 FAQ 知识。
