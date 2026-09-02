# Customer Service Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React%20%2B%20Vite-Workbench-3b82f6?style=flat-square&logo=react&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Persistence-4479A1?style=flat-square&logo=mysql&logoColor=white)

面向电商售后场景的智能客服 Agent 工作台。项目把接待对话、知识库检索、订单/物流工具、退款审批、会话留痕、质检复盘和 FAQ 沉淀放在同一套流程里，解决客服回复依赖人工查询、操作不可追溯以及高风险售后缺少审核的问题。

当前版本已经从早期演示页升级为工作台结构：左侧管理场景、能力开关和最近会话，中间处理客服会话，右侧通过上下文面板切换客户概况、商品货架、工具轨迹和业务结果。业务数据默认走 MySQL，Dify 可作为外部知识库来源，模型层支持 DeepSeek、智谱、火山引擎和 OpenAI Compatible 接口。退款由 Agent 发起申请，人工确认后才允许执行。

## 项目截图

### 桌面端

![客服工作台桌面端](docs/images/workbench-desktop.png)

### 移动端

![客服工作台移动端](docs/images/workbench-mobile.png)

## 项目能力

- 接待工作台：提供客服对话、商品范围选择、流式回复开关和接待上下文展示。
- 知识问答：支持本地 FAQ/MySQL 知识数据，也预留 Dify Dataset 检索入口。
- 业务工具：封装订单查询、物流查询和退款申请等售后能力。
- 退款审批：退款申请先进入 `pending_approval`，经人工批准后才允许执行，避免 Agent 直接改动订单状态。
- 会话持久化：保存会话、消息、工具调用记录，便于追踪一次回复的来源。
- 质检复盘：按会话读取完整的多轮客户与客服消息，结合规则配置检查漏答、风险话术和工具使用情况，并保存质检结果。
- FAQ 沉淀：将高质量问答保存为候选 FAQ，用于后续知识库维护。
- 多模型适配：兼容 DeepSeek、智谱、火山引擎和 OpenAI Compatible API。
- MySQL 数据层：商品、订单、物流、FAQ、会话和质检数据统一落库，方便用 Navicat 查看。

## 技术栈

### 后端

- FastAPI：提供对话、商品、会话、工具轨迹等 HTTP API。
- SQLAlchemy：统一管理 MySQL/SQLite 数据访问。
- Alembic：管理数据库迁移。
- PyMySQL：连接本地或远程 MySQL。
- Python 3.10+：实现 Agent 编排、业务工具和质检规则。

### 前端

- React：构建客服工作台界面。
- Vite：负责本地开发服务和前端打包。
- TypeScript：给前端组件和数据结构提供类型约束。
- Lucide Icons：提供工作台图标。

### 模型与知识库

- DeepSeek / 智谱 / 火山引擎：作为可切换的大模型提供方。
- OpenAI Compatible：兼容同类 Chat Completions 接口。
- Dify Dataset：作为可选的外部知识库检索来源。
- MySQL FAQ：作为本地可控的 FAQ 数据来源。

## 架构说明

项目按照“前端工作台 + 后端 API + Agent 编排 + 业务工具 + 数据存储”的方式拆分。

```text
customer-service-agent/
├── frontend/                 # React + Vite 工作台
├── main.py                   # FastAPI 入口与路由注册
├── llm_provider.py           # 大模型适配层
├── business_services.py      # 业务数据服务，支持 MySQL/HTTP/兼容模式
├── agent_tools.py            # Agent 可调用的订单、物流、退款工具
├── conversation_store.py     # 会话与消息持久化
├── quality_rules.py          # 本地质检规则
├── database.py               # SQLAlchemy 表结构和数据库连接
├── alembic/                  # 数据库迁移脚本
├── tools/                    # 数据初始化、迁移和业务脚本
├── docs/                     # 知识库文档和项目截图
└── tests/                    # 单元测试
```

## 核心流程

1. 客户在工作台发起问题。
2. 后端接收消息，整理会话上下文、商品范围和账户信息。
3. Agent 根据问题检索知识库，必要时调用订单、物流、退款工具。
4. 大模型结合系统提示、知识库内容和工具结果生成客服回复。
5. 后端保存会话、消息、工具结果、质检结果和 FAQ 候选数据。
6. 质检或总结前校验会话是否形成有效问答，避免对空会话或单边消息生成虚假结论。
7. 前端展示回复内容、客户信息、工具轨迹和可复盘记录。

### 退款流程

退款采用独立申请状态机，不把“申请成功”误认为“退款完成”：

```text
客户确认订单
    -> Agent 创建退款申请（pending_approval）
    -> 人工批准（approved）
    -> 执行退款（executed）
    -> 订单状态更新为“已退款”
```

如果人工拒绝，申请进入 `rejected`，订单保持原状态；如果执行前未完成人工批准，接口会拒绝执行。执行过程出现业务错误时，应保留失败原因并进入人工处理流程。

## MySQL 与 Dify 分工

- MySQL：保存结构化业务数据，包括商品、订单、物流、会话、消息、工具调用、质检记录和 FAQ 候选。
- Dify：保存可检索的知识库文档，适合放商品说明、售后政策、活动规则和客服问答资料。
- 当前项目默认可以使用 MySQL 本地数据运行；切到 Dify 时，需要在 `.env.local` 中配置 `KNOWLEDGE_PROVIDER=dify`、`DIFY_API_KEY` 和 Dataset ID。

## 数据库设计

当前 MySQL 侧包含这些核心表：

- `products`：商品名称、描述和图片地址。
- `orders`：订单状态、客户账号、商品和物流单号。
- `refund_requests`：退款申请、审批状态、执行时间和失败原因。
- `tracking_events`：物流轨迹节点。
- `faq_documents`：已沉淀的 FAQ 知识。
- `conversations`：会话主表。
- `messages`：会话消息，外键关联 `conversations`。
- `tool_calls`：工具调用记录，外键关联 `conversations`。
- `quality_reviews`：质检记录，可关联会话。
- `faq_candidates`：客服接待中沉淀出的 FAQ 候选，可关联会话。

Alembic 负责维护表结构迁移。当前迁移已经覆盖会话表外键和退款申请表，启动脚本会先执行迁移，再补齐缺失的基础数据。默认 seed 不会清空已有业务数据。

## 本地启动

### 1. 安装后端依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install uv
uv sync
```

### 2. 安装前端依赖

```powershell
cd frontend
npm install
cd ..
```

### 3. 准备 MySQL

本地创建项目数据库和项目专属用户。密码请按自己的环境调整：

```sql
CREATE DATABASE customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'customer_service_agent'@'127.0.0.1' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON customer_service.* TO 'customer_service_agent'@'127.0.0.1';
FLUSH PRIVILEGES;
```

这个用户只需要访问 `customer_service` 这个库。日常运行项目时建议使用项目专属账号，`root` 保留给数据库管理。

### 4. 配置环境变量

复制模板：

```powershell
Copy-Item .env.local.example .env.local
```

本地 MySQL 推荐配置：

```env
MOCK_MODE=False
LANGUAGE=zh
DATABASE_URL=mysql+pymysql://customer_service_agent:change_me@127.0.0.1:3306/customer_service
KNOWLEDGE_PROVIDER=mysql
BUSINESS_DATA_PROVIDER=mysql
```

如果要接真实大模型，需要把 `.env.local` 中对应厂商的 API Key 和模型名改成有效值。仓库里的示例值只是占位符。

### 5. 启动工作台

```powershell
.\start_workbench.ps1
```

启动脚本会执行数据库迁移，并在商品、订单、物流或 FAQ 初始表为空时补齐基础数据。默认不会清空已有业务数据。

需要重置基础数据时，可以手动执行：

```powershell
.\.venv\Scripts\python.exe -m tools.seed_mysql_data --reset
```

前端工作台：

```text
http://127.0.0.1:5173
```

后端健康检查：

```text
http://127.0.0.1:8090/ready
```

## API 文档

常用接口：

- `GET /ready`：服务就绪检查。
- `GET /api/products`：商品列表。
- `POST /api/chat`：工作台对话。
- `GET /api/conversations`：会话列表。
- `GET /api/conversations/{conversation_id}`：会话详情。
- `GET /api/conversations/{conversation_id}/tool-calls`：工具调用轨迹。
- `GET /api/refunds/{refund_id}`：退款申请详情。
- `POST /api/refunds/{refund_id}/approve`：人工批准退款申请。
- `POST /api/refunds/{refund_id}/reject`：人工拒绝退款申请。
- `POST /api/refunds/{refund_id}/execute`：执行已批准的退款。

更多接口说明见 [API.md](API.md)。

## 知识库文件

项目提供两份可导入 Dify 的知识库文档：

- [docs/dify_product_service_knowledge.md](docs/dify_product_service_knowledge.md)
- [docs/dify_faq_knowledge.md](docs/dify_faq_knowledge.md)

## 验证状态

当前已验证：

- 前端 `npm run build` 可以完成生产构建。
- 后端测试覆盖路由鉴权、会话持久化、知识库调用和质检基础逻辑。
- 多轮会话质检会拒绝未形成完整客户提问和客服回复的会话。
- 后端健康检查接口可用。
- 商品列表和会话列表接口可用。
- MySQL 迁移已到 `0004_refund_requests`。
- MySQL 启动数据脚本支持非破坏式补齐和手动重置。

需要注意：真实 AI 对话依赖有效的模型 API Key、模型名和知识库配置。使用占位环境变量时，`/api/chat` 可能返回模型配置错误，这是预期的配置问题，不是前端或数据库启动问题。

## 部署说明

项目以本地 MySQL + 本地前后端启动为默认方式。仓库中保留了 Dockerfile 和 docker-compose 配置，方便后续容器化部署；当前日常开发和演示不依赖 Docker。
