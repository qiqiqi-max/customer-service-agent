# Customer Service Agent

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React%20%2B%20Vite-Workbench-3b82f6?style=flat-square&logo=react&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-111827?style=flat-square)

一个面向电商客服场景的智能客服工作台。它把大模型对话、知识库检索、订单/物流/退款工具、会话持久化、质检复盘和 FAQ 沉淀放到同一条业务链路里，方便本地演示，也方便后续接真实业务系统。

现在这版前端已经从“演示页”改成了更像实际工作的中控台：左侧是场景和能力开关，中间是接待对话，右侧是客户概况、工具轨迹和货架范围。界面更克制，也更适合拿来做简历展示。

## 项目截图

### 桌面端

![客服工作台桌面端](docs/images/workbench-desktop.png)

### 移动端

![客服工作台移动端](docs/images/workbench-mobile.png)

## 这个项目解决什么问题

- 把客服接待、业务查询、知识问答和质检复盘放到一个界面里
- 让大模型回答不是“纯聊天”，而是结合知识库和工具结果
- 让历史会话、FAQ 和质检记录能落库，方便复盘和迭代
- 让商品知识和业务数据可以替换，后续能接 Dify、MySQL 或真实接口

## 当前功能

- 接待工作台
- 会话历史查看
- 商品货架管理
- 质检和会话总结
- FAQ 沉淀
- 接入配置展示
- MySQL 持久化
- Dify 知识库对接入口

## 技术栈

### 后端

- FastAPI
- Python 3.10+
- SQLAlchemy
- MySQL
- Alembic

### 前端

- React
- Vite
- TypeScript
- Lucide Icons

### 模型与知识

- DeepSeek
- 智谱
- 火山引擎
- OpenAI Compatible
- Dify Dataset

## 架构方式

项目按“前端工作台 + 后端 API + 模型适配 + 业务工具 + 数据存储”拆开。

- 前端只负责展示和交互
- 后端负责对话编排、工具调用和数据读写
- 模型层负责兼容不同厂商
- 业务层负责订单、物流、退款等能力
- 数据层负责会话、FAQ、商品和业务数据落库

## 核心流程

1. 客户发消息
2. 后端先做意图识别
3. 按需查知识库或调用业务工具
4. 组合模型回复
5. 把会话、工具结果和质检记录保存到数据库
6. 高质量问答可沉淀成 FAQ

## 本地启动

### 1. 安装依赖

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install uv
uv sync
```

### 2. 配置环境变量

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

### 3. 启动工作台

```bash
.\start_workbench.ps1
```

前端工作台地址：

```text
http://127.0.0.1:5173
```

后端健康检查：

```text
http://127.0.0.1:8080/ready
```

## 目录说明

```text
customer-service-agent/
├── frontend/          # React + Vite 工作台
├── main.py            # 后端入口
├── llm_provider.py    # 大模型适配
├── business_services.py
├── conversation_store.py
├── agent_tools.py
├── quality_rules.py
├── data/              # 商品、订单、物流、RAG 数据
├── tools/             # 订单、物流、退款工具
├── docs/              # 知识库文档和截图
└── tests/             # 测试
```

## 知识库文件

- `docs/dify_product_service_knowledge.md`
- `docs/dify_faq_knowledge.md`

这两个文件可以直接导入 Dify，分别用于商品知识和 FAQ 知识。

## 说明

这个项目不是单纯的聊天 Demo。它更像一个客服 Agent 的工作台样板，重点在于把模型、知识、工具和数据串成一条完整链路。

