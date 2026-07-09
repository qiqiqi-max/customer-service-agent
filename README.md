# Customer Service Agent

面向电商售前、订单、物流和售后的智能客服工作台。项目从车载用品店铺客服场景出发，把大模型回复、知识库检索、订单/物流/退款工具调用、会话沉淀、质检和前端坐席台整合到一个可本地运行、可继续接真实业务系统的应用里。

这个仓库已经不只是原始 Demo：当前版本支持本地 Mock 演示，也支持替换为 DeepSeek、智谱或火山引擎模型；知识库可以从火山引擎切换到 Dify；订单、物流、退款能力可以先用本地模拟数据跑通，再通过 HTTP 适配器接入真实业务接口。

## 项目定位

这个项目适合用来展示一个完整的“AI 客服 + 业务工具 + 知识库 + 工作台”的落地流程：

- 给客服坐席提供一个更像真实业务系统的接待页面，而不是简单聊天框。
- 通过大模型生成客服回复，并在需要时调用订单查询、物流查询、退款处理等工具。
- 通过知识库回答商品介绍、售后规则、常见问题等稳定信息。
- 通过会话记录、质检、总结和处理结果面板，帮助运营复盘客服质量。
- 保留标准 API，方便后续接入 CRM、小程序、企业微信或自建客服系统。

## 主要功能

- **客服工作台前端**：包含接待设置、场景切换、服务权限、商品货架、历史接待、聊天记录、处理结果、执行记录和复盘沉淀。
- **智能客服回复**：支持流式输出和非流式输出，可根据用户问题自动组织客服话术。
- **知识库检索**：商品知识和 FAQ 可走火山引擎知识库，也可切换为 Dify Dataset。
- **工具调用**：支持订单查询、物流查询、退款退货等业务动作，DeepSeek/智谱等 OpenAI 兼容模型也可以使用工具调用。
- **会话持久化**：使用 SQLite 保存会话、账号、用户问题、助手回复和元数据。
- **质检能力**：内置规则质检，同时保留大模型质检接口，用于识别不合规承诺、极限词等风险。
- **对话总结**：将客服与用户的对话整理成简短摘要，方便交接和复盘。
- **FAQ 沉淀**：可将高质量问答保存到本地 Mock、火山引擎 FAQ 知识库或 Dify FAQ 数据集。
- **运行观测**：输出 JSON Lines 日志，记录 HTTP 请求、大模型调用、知识库检索、工具执行和业务接口调用耗时。
- **API 鉴权**：标准 `/api/*` 接口支持可选 `X-API-Key` 或 `Authorization: Bearer` 鉴权。

## 技术栈

- **后端框架**：Python、FastAPI、Arkitect BotServer
- **模型接入**：火山引擎 Ark、DeepSeek、智谱、其他 OpenAI-compatible Chat Completions API
- **知识库接入**：火山引擎知识库、Dify Dataset API
- **业务工具层**：订单查询、物流查询、退款处理，支持 Mock 和 HTTP 业务系统适配
- **数据存储**：SQLite 会话库、本地 Mock FAQ 文件、结构化日志文件
- **前端实现**：原生 HTML/CSS/JavaScript，无复杂前端构建链路，便于演示和二次改造
- **测试**：Python unittest，覆盖模型适配、业务服务、会话存储、RAG、质检规则和 API 逻辑

## 项目结构

```text
backend/
├── main.py                    # 服务入口，注册页面、标准 API 和兼容 API
├── config.py                  # 环境变量配置
├── llm_provider.py            # DeepSeek/智谱/OpenAI-compatible 模型适配
├── business_services.py       # 订单、物流、退款的 Mock/HTTP 业务数据层
├── conversation_store.py      # SQLite 会话持久化
├── agent_tools.py             # 工具调用定义和结果转换
├── mock_agent.py              # 本地 Mock 回复能力
├── quality_rules.py           # 本地质检规则
├── observability.py           # JSON 结构化日志
├── data/
│   ├── product.py             # 商品基础数据
│   ├── orders.py              # Mock 订单数据
│   ├── tracking.py            # Mock 物流数据
│   └── rag.py                 # 火山引擎/Dify 知识库检索与 FAQ 保存
├── tools/
│   ├── order_check.py         # 订单查询工具
│   ├── pack_track.py          # 物流查询工具
│   └── order_refund.py        # 退款处理工具
├── webui/
│   ├── index.html             # 客服工作台页面
│   ├── styles.css             # 工作台视觉样式
│   └── app.js                 # 前端交互、接口调用和状态管理
├── docs/
│   ├── dify_product_service_knowledge.md # Dify 商品知识库导入文件
│   └── dify_faq_knowledge.md             # Dify FAQ 知识库导入文件
├── tests/                     # 单元测试
├── API.md                     # API 和环境变量说明
└── start_demo.ps1             # Windows 本地启动脚本
```

## 快速启动

### 1. 安装依赖

```powershell
cd D:\projects\customer-service-agent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install uv
uv sync
```

也可以使用已有虚拟环境，直接安装 `requirements.txt` 或通过 `uv sync` 同步依赖。

### 2. 配置本地环境

复制示例配置：

```powershell
Copy-Item .env.local.example .env.local
```

本地演示推荐先使用 Mock 模式：

```env
MOCK_MODE=True
LANGUAGE=zh
BUSINESS_DATA_PROVIDER=mock
API_KEYS=
```

### 3. 启动服务

```powershell
.\start_demo.ps1
```

默认访问：

```text
http://127.0.0.1:8080/demo
```

如果 8080 被占用，可以设置端口：

```powershell
$env:_FAAS_RUNTIME_PORT='8081'
.\.venv\Scripts\python.exe main.py
```

## 模型切换

### 本地 Mock

```env
MOCK_MODE=True
```

适合无密钥、本地演示、前端联调和测试。

### DeepSeek

```env
MOCK_MODE=False
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseekv4pro
```

如果你的 DeepSeek V4 Pro 实际模型 ID 不同，只需要改 `DEEPSEEK_MODEL`。

### 智谱

```env
MOCK_MODE=False
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
ZHIPU_MODEL=glm-5.2
```

### 火山引擎

```env
MOCK_MODE=False
LLM_PROVIDER=volcengine
VOLC_ACCESSKEY=your_ak
VOLC_SECRETKEY=your_sk
LLM_ENDPOINT_ID=doubao-seed-1-6-250615
ARK_API_KEY=your_ark_api_key
USE_SERVER_AUTH=True
```

## Dify 知识库接入

项目已经准备了两份可导入 Dify 的知识库文件：

- `docs/dify_product_service_knowledge.md`：商品介绍、适配场景、卖点和售后说明。
- `docs/dify_faq_knowledge.md`：常见问题、客服话术、售后规则和运营沉淀。

推荐在 Dify 中创建两个 Dataset：

- 商品知识库：用于商品介绍、规格、安装、适配和使用建议。
- FAQ 知识库：用于售后政策、物流、退款、常见问题和可复用客服回答。

配置方式：

```env
MOCK_MODE=False
KNOWLEDGE_PROVIDER=dify
DIFY_API_KEY=your_dify_api_key
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_DATASET_ID=your_product_dataset_id
DIFY_FAQ_DATASET_ID=your_faq_dataset_id
DIFY_TOP_K=5
DIFY_SCORE_THRESHOLD_ENABLED=False
DIFY_SCORE_THRESHOLD=0
```

稳定知识放在 Dify；实时订单、物流、退款进度不要放知识库，应通过 `BUSINESS_DATA_PROVIDER=http` 接真实业务接口。

## 业务系统接入

本地默认使用 Mock 数据：

```env
BUSINESS_DATA_PROVIDER=mock
```

接真实系统时切换为 HTTP：

```env
BUSINESS_DATA_PROVIDER=http
BUSINESS_API_BASE_URL=https://your-business-api.example.com
BUSINESS_API_KEY=your_business_api_key
BUSINESS_API_TIMEOUT=8
```

后端期望业务系统提供：

```http
GET /orders?account_id=100000
GET /orders/{order_id}?account_id=100000
GET /orders?account_id=100000&product=product_name
GET /tracking?account_id=100000&order_id=order_id&tracking_number=tracking_number
POST /refunds
```

## 常用 API

```http
GET /health
GET /ready
GET /api/products
POST /api/chat
POST /api/faqs
POST /api/quality-check
POST /api/summary
GET /api/conversations
GET /api/conversations/{conversation_id}
```

兼容原始 Bot 接口：

```http
POST /api/v3/bots/chat/completions
POST /api/v3/bots/chat/completions/save_faq
POST /api/v3/bots/chat/completions/summary
POST /api/v3/bots/chat/completions/quality_inspection
POST /api/v3/bots/chat/completions/next_question
```

更完整的接口说明见 `API.md`。

## 测试与校验

```powershell
node --check .\webui\app.js
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q main.py config.py agent_tools.py business_services.py conversation_store.py llm_provider.py mock_agent.py observability.py quality_rules.py data tools
```

启动后检查服务状态：

```powershell
Invoke-RestMethod -Method GET http://127.0.0.1:8080/ready
```

## 项目亮点

- 从“聊天 Demo”升级为带业务上下文的客服坐席工作台。
- 模型层、知识库层、业务数据层都做了可替换设计，后续迁移成本低。
- DeepSeek/智谱路径支持 OpenAI-compatible tool calling，可以继续保留订单、物流、退款等工具能力。
- Dify 知识库接入后，运营可以直接维护商品知识和 FAQ，不需要改代码。
- 使用 SQLite 保存会话，便于展示历史接待、质检结果和复盘沉淀。
- 前端不依赖复杂工程化，适合快速部署、演示和二次迭代。

## 后续优化方向

- 接入真实订单、物流、售后系统，替换本地 Mock 数据。
- 在 Dify 中完善商品知识库和 FAQ 知识库，并建立运营更新流程。
- 增加客服接管、满意度评价、工单标签、用户画像和风险升级规则。
- 增加更细的权限控制、租户隔离和接口限流，适配生产环境。
- 将前端进一步拆成组件化工程，支持更复杂的客服运营后台。

