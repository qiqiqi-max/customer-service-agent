# Customer Service Agent API

This backend exposes a customer-service agent API that can be used by a web UI,
CRM, mini program, or third-party customer-service platform.

## Base URL

Local default:

```text
http://127.0.0.1:8080
```

If port 8080 is occupied, set `_FAAS_RUNTIME_PORT` before starting the service.

## Switch LLM Provider

The backend supports three modes:

```env
MOCK_MODE=True
```

Runs fully local mock responses.

```env
MOCK_MODE=False
LLM_PROVIDER=volcengine
```

Uses the original VolcEngine Ark integration.

```env
MOCK_MODE=False
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseekv4pro
```

Uses a DeepSeek/OpenAI-compatible chat completions API. If your provider exposes
`deepseekv4pro` under a different model ID, change only `DEEPSEEK_MODEL`.

The current DeepSeek path uses the model for chat, summary, quality inspection,
and next-question generation.

```env
MOCK_MODE=False
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
ZHIPU_MODEL=glm-5.2
```

Uses Zhipu AI's OpenAI-compatible API. `ZAI_API_KEY` is also accepted as an
alias for `ZHIPU_API_KEY`.

DeepSeek and Zhipu chat responses also support OpenAI-compatible tool calling
for:

- `order_check`
- `pack_track`
- `order_refund`

Tool execution details are returned in `bot_usage.action_details`, so the web UI
can show order, logistics, refund, and knowledge-base results in the right panel.

## Switch Knowledge Base Provider

Legacy compatibility with VolcEngine Knowledge Base:

```env
KNOWLEDGE_PROVIDER=volcengine
COLLECTION_NAME=your_product_collection
FAQ_COLLECTION_NAME=your_faq_collection
```

To use Dify instead:

```env
KNOWLEDGE_PROVIDER=dify
DIFY_API_KEY=your_dify_api_key
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_DATASET_ID=your_product_dataset_id
DIFY_FAQ_DATASET_ID=your_faq_dataset_id
DIFY_TOP_K=5
DIFY_SCORE_THRESHOLD_ENABLED=False
DIFY_SCORE_THRESHOLD=0
```

`DIFY_DATASET_ID` is used for product knowledge retrieval. `DIFY_FAQ_DATASET_ID`
is used for FAQ retrieval and FAQ saving. If you only have one Dify dataset, set
both variables to the same dataset ID.

## Business Data

Order lookup, logistics lookup, and refund handling now read from MySQL by
default. To connect a real business system later, expose an HTTP API and set:

```env
BUSINESS_DATA_PROVIDER=http
BUSINESS_API_BASE_URL=https://your-business-api.example.com
BUSINESS_API_KEY=your_business_api_key
BUSINESS_API_TIMEOUT=8
```

The HTTP adapter expects these endpoints:

```http
GET /orders?account_id=100000
GET /orders/{order_id}?account_id=100000
GET /orders?account_id=100000&product=product_name
GET /tracking?account_id=100000&order_id=order_id&tracking_number=tracking_number
POST /refunds
```

`POST /refunds` receives:

```json
{
  "account_id": "100000",
  "order_id": "order_id",
  "reason": "customer refund reason"
}
```

The adapter sends `Authorization: Bearer BUSINESS_API_KEY` when
`BUSINESS_API_KEY` is configured.

## Observability

The backend writes structured JSON-line logs to:

```text
logs/app.log
```

You can configure logging with:

```env
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_TO_STDOUT=False
```

Every HTTP response includes an `X-Request-ID` header. Use that value to find the
matching `http.request` event in `logs/app.log`.

Important log events:

- `http.request`: request path, status code, and duration
- `chat.request`: account, conversation, provider, stream flag, message count
- `knowledge.retrieval`: knowledge provider, duration, hit count
- `knowledge.dify_retrieve`: Dify dataset retrieval duration and hit count
- `llm.openai_compatible_round`: DeepSeek/Zhipu compatible API round timing
- `llm.openai_compatible_complete`: total compatible provider timing
- `llm.volcengine_chat` / `llm.volcengine_stream`: VolcEngine timing
- `tool.execute`: OpenAI-compatible tool execution timing
- `business_service.call`: mock or HTTP business data call timing
- `faq.save`: FAQ save timing and target provider

Sensitive fields whose names contain `key`, `token`, `secret`, or
`authorization` are filtered from structured logs.

## Health Check

```http
GET /v1/ping
```

Expected response:

```json
{}
```

The service also exposes deployment-friendly health endpoints. These endpoints
are public even when `API_KEYS` is enabled.

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "customer-service-agent"
}
```

```http
GET /ready
```

Response:

```json
{
  "status": "ready",
  "checks": {
    "webui": true,
    "conversation_store": true
  }
}
```

## Standard Business APIs

These endpoints provide a simpler business-facing shape. The legacy
`/api/v3/bots/chat/completions/*` paths remain available for compatibility.

Optional API key auth can be enabled for standard `/api/*` business endpoints:

```env
API_KEYS=key_for_crm,key_for_mini_program
```

When `API_KEYS` is set, pass either header:

```http
X-API-Key: key_for_crm
```

or:

```http
Authorization: Bearer key_for_crm
```

### Product List

```http
GET /api/products
```

Response:

```json
{
  "products": [
    {
      "name": "product name",
      "description": "product description",
      "cover_image": "tos://..."
    }
  ],
  "total": 10
}
```

### Chat

```http
POST /api/chat
```

Request:

```json
{
  "message": "Please recommend a product for my car.",
  "account_id": "100000",
  "conversation_id": "conv_xxx",
  "support_functions": ["order_check", "package_track", "order_refund"],
  "product_list": ["product name"],
  "history": [
    {
      "role": "user",
      "content": "Previous question"
    }
  ],
  "model": "customer-service-agent"
}
```

Only `message` is required. If `conversation_id` is omitted, the backend creates
a new stored conversation.

Response:

```json
{
  "conversation_id": "conv_xxx",
  "answer": "Assistant reply",
  "metadata": {
    "conversation_id": "conv_xxx"
  },
  "bot_usage": {
    "action_details": []
  }
}
```

### Save FAQ

```http
POST /api/faqs
```

Request:

```json
{
  "question": "How do I install it?",
  "answer": "Follow the installation guide.",
  "score": 5,
  "account_id": "100000"
}
```

Response:

```json
{
  "message": "success"
}
```

### Quality Check

```http
POST /api/quality-check
```

Request:

```json
{
  "content": "user: ...\nassistant: ...",
  "keywords": "absolute, guarantee",
  "model": "customer-service-agent"
}
```

Response:

```json
{
  "result": "Quality inspection result",
  "structured_result": {
    "risk_level": "high",
    "risk_score": 93,
    "hit_count": 2,
    "hits": [
      {
        "rule_id": "absolute_language",
        "category": "Absolute wording",
        "severity": "high",
        "keyword": "absolute",
        "start": 18,
        "end": 26,
        "evidence": "absolute",
        "description": "Risk description",
        "suggestion": "Rewrite the reply with verifiable wording."
      }
    ],
    "suggestions": ["Rewrite the reply with verifiable wording."]
  },
  "metadata": {},
  "bot_usage": {}
}
```

`structured_result` is generated by local deterministic rules and is returned
even when mock mode or a remote model is used. It is intended for frontend
highlighting, dashboards, and automated quality gates.

### Summary

```http
POST /api/summary
```

Request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "I want to return this order."
    },
    {
      "role": "assistant",
      "content": "Please provide the order number."
    }
  ],
  "model": "customer-service-agent"
}
```

Response:

```json
{
  "summary": "Conversation summary",
  "metadata": {},
  "bot_usage": {}
}
```

## Products

```http
GET /api/v3/bots/chat/completions/products
```

Response:

```json
{
  "products": [
    {
      "name": "车载收纳盒",
      "description": "车载收纳盒是一款为汽车提供收纳功能的产品。",
      "cover_image": "tos://..."
    }
  ],
  "total": 10
}
```

## Conversations

The backend now stores chat turns in MySQL.

Set `DATABASE_URL` to your project-only MySQL account:

```env
DATABASE_URL=mysql+pymysql://customer_service_agent:change_me@127.0.0.1:3306/customer_service
```

Additional persistence endpoints:

- `GET /api/conversations/{conversation_id}/tool-calls?account_id=...`
- `GET /api/quality-reviews?account_id=...`
- `GET /api/faq-candidates?account_id=...`

List recent conversations:

```http
GET /api/conversations?limit=50
```

Get one conversation:

```http
GET /api/conversations/{conversation_id}
```

Chat responses include:

```json
{
  "metadata": {
    "conversation_id": "conv_xxx"
  }
}
```

Pass the same ID in the next chat request to continue the same stored
conversation:

```json
{
  "metadata": {
    "account_id": "100000",
    "conversation_id": "conv_xxx"
  }
}
```

## Chat Completion

```http
POST /api/v3/bots/chat/completions
```

Request:

```json
{
  "stream": false,
  "model": "customer-service-agent",
  "metadata": {
    "account_id": "100000",
    "support_functions": [
      "product_description",
      "product_recommend",
      "order_check",
      "package_track",
      "order_refund"
    ],
    "product_list": ["车载收纳盒", "车载手机超级快充"]
  },
  "messages": [
    {
      "role": "user",
      "content": "帮我查一下这个账号之前买过哪些商品。"
    }
  ]
}
```

Response follows the OpenAI-compatible chat completion shape:

```json
{
  "id": "mock-...",
  "object": "chat.completion",
  "model": "mock-customer-service-agent",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "亲，已查到账号 100000 下共有 3 笔订单。右侧可以查看订单状态和商品信息。"
      }
    }
  ],
  "bot_usage": {
    "action_details": [
      {
        "name": "mock_support",
        "tool_details": [
          {
            "name": "order_check",
            "input": {"account_id": "100000"},
            "output": []
          }
        ]
      }
    ]
  }
}
```

## Conversation Summary

```http
POST /api/v3/bots/chat/completions/summary
```

Request body uses the same `stream`, `model`, and `messages` fields as chat
completion.

## Quality Inspection

```http
POST /api/v3/bots/chat/completions/quality_inspection
```

Example message:

```json
{
  "stream": false,
  "model": "customer-service-agent",
  "messages": [
    {
      "role": "user",
      "content": "user: 这个还能便宜吗？\nassistant: 这款已经是全网最低价。"
    }
  ]
}
```

## Next Questions

```http
POST /api/v3/bots/chat/completions/next_question
```

Returns three suggested follow-up questions separated by line breaks.

## Save FAQ

```http
POST /api/v3/bots/chat/completions/save_faq
```

Request:

```json
{
  "question": "安装方法",
  "answer": "可参考商品详情页视频说明进行安装。",
  "score": 5,
  "account_id": "100000"
}
```

FAQ data is saved to MySQL by default.
If `KNOWLEDGE_PROVIDER=dify`, FAQ data can also be synchronized to Dify.
