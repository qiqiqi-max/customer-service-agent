# Customer Service Agent - Local Setup Guide (Windows / PowerShell)

This guide records the local setup and verification flow for running the backend on Windows with PowerShell.

## 1) Prerequisites

- Windows PowerShell
- Python 3.10.x
- MySQL 8.0 running locally
- Navicat or another MySQL client for data inspection

## 2) Install dependencies

Run in:

`<project-root>`

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install --upgrade "arkitect==0.2.1" "langchain==0.3.25" "langchain-core==0.3.58" "langchain-text-splitters==0.3.8"
```

## 3) Environment variables

For local development, use local MySQL:

```powershell
$env:MOCK_MODE="False"
$env:LANGUAGE="zh"
$env:DATABASE_URL="mysql+pymysql://customer_service_agent:change_me@127.0.0.1:3306/customer_service"
$env:KNOWLEDGE_PROVIDER="mysql"
$env:BUSINESS_DATA_PROVIDER="mysql"
```

Products, orders, logistics, conversations, quality reviews, and FAQ records are
stored in MySQL and can be viewed from Navicat through the project-only account.

For real VolcEngine integration, set `MOCK_MODE=False` and configure:

Set in the same PowerShell window where `main.py` will be started:

```powershell
$env:VOLC_ACCESSKEY="your_ak"
$env:VOLC_SECRETKEY="your_sk"
$env:COLLECTION_NAME="your_product_collection"
$env:FAQ_COLLECTION_NAME="your_faq_collection"
$env:LLM_ENDPOINT_ID="doubao-seed-1-6-250615"
$env:BUCKET_NAME="your_beijing_bucket"
$env:USE_SERVER_AUTH="True"
$env:ARK_API_KEY="your_ark_api_key"
$env:LANGUAGE="zh"
```

For DeepSeek/OpenAI-compatible integration, set:

```powershell
$env:MOCK_MODE="False"
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="your_deepseek_api_key"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseekv4pro"
$env:LANGUAGE="zh"
```

If your account exposes the model under a different ID, change only
`DEEPSEEK_MODEL`.

For Zhipu/OpenAI-compatible integration, set:

```powershell
$env:MOCK_MODE="False"
$env:LLM_PROVIDER="zhipu"
$env:ZHIPU_API_KEY="your_zhipu_api_key"
$env:ZHIPU_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
$env:ZHIPU_MODEL="glm-5.2"
$env:LANGUAGE="zh"
```

`ZAI_API_KEY` is also accepted as an alias for `ZHIPU_API_KEY`.

To replace the VolcEngine knowledge base with Dify, set:

```powershell
$env:KNOWLEDGE_PROVIDER="dify"
$env:DIFY_API_KEY="your_dify_api_key"
$env:DIFY_BASE_URL="https://api.dify.ai/v1"
$env:DIFY_DATASET_ID="your_product_dataset_id"
$env:DIFY_FAQ_DATASET_ID="your_faq_dataset_id"
$env:DIFY_TOP_K="5"
```

If you only have one Dify dataset, set `DIFY_DATASET_ID` and
`DIFY_FAQ_DATASET_ID` to the same value.

To replace local MySQL order/logistics/refund data with a real business API, set:

```powershell
$env:BUSINESS_DATA_PROVIDER="http"
$env:BUSINESS_API_BASE_URL="https://your-business-api.example.com"
$env:BUSINESS_API_KEY="your_business_api_key"
$env:BUSINESS_API_TIMEOUT="8"
```

The built-in HTTP adapter calls:

- `GET /orders?account_id=...`
- `GET /orders/{order_id}?account_id=...`
- `GET /tracking?account_id=...&order_id=...&tracking_number=...`
- `POST /refunds`

Structured JSON logs are written to `logs/app.log` by default:

```powershell
$env:LOG_LEVEL="INFO"
$env:LOG_DIR="./logs"
$env:LOG_TO_STDOUT="False"
```

Each HTTP response includes `X-Request-ID`, which can be used to trace the
matching `http.request` event in `logs/app.log`.

## 4) Start backend

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python main.py
```

Keep this terminal open.

### Easier local startup

Create a local env file once:

```powershell
Copy-Item .env.local.example .env.local
```

Fill in the real values inside `.env.local`, then use:

```powershell
.\start_workbench.ps1
```

Or just double-click:

- `start_workbench.cmd`

This script will:

- load local environment variables from `.env.local`
- apply Alembic database migrations
- ensure starter MySQL data exists without clearing existing records
- start the backend
- wait for `/v1/ping`
- start the React workbench
- open the browser at `http://127.0.0.1:5173`

To intentionally reset starter product/order/tracking/FAQ data, run:

```powershell
.\.venv\Scripts\python.exe -m tools.seed_mysql_data --reset
```

### Stop the local workbench

```powershell
.\stop_demo.ps1
```

Or just double-click:

- `stop_demo.cmd`

This script will stop the running `main.py` process for `customer-service-agent`.

## 5) Health check

Run in another terminal:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/v1/ping
```

Expected: `StatusCode : 200`

## 5.1) Open workbench UI

After the workbench starts, open the browser:

`http://127.0.0.1:5173`

This page provides a lightweight web UI for:

- product shelf browsing
- capability toggle
- live customer-service chat
- conversation summary
- quality inspection
- FAQ saving
- follow-up question generation

## 6) API verification

### 6.1 Products

```powershell
Invoke-RestMethod -Method GET "http://127.0.0.1:8080/api/v3/bots/chat/completions/products"
```

### 6.2 Completions

```powershell
$body = @{
  stream   = $false
  model    = "my-bot"
  metadata = @{
    account_id = "100000"
  }
  messages = @(
    @{ role = "user"; content = "我都买过什么？" }
  )
} | ConvertTo-Json -Depth 8

$resp = Invoke-WebRequest -Method POST `
  -Uri "http://127.0.0.1:8080/api/v3/bots/chat/completions" `
  -ContentType "application/json" `
  -Body $body
```

### 6.3 save_faq

```powershell
$faq = @{
  question   = "安装方法"
  answer     = "可参考商品详情页视频说明进行安装。"
  score      = 5
  account_id = "100000"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8080/api/v3/bots/chat/completions/save_faq" `
  -ContentType "application/json" `
  -Body $faq
```

### 6.4 quality_inspection

```powershell
$qcBody = @{
  stream   = $false
  model    = "my-bot"
  messages = @(@{
    role    = "user"
    content = "user:这个可爱风腰靠垫价格还能更低吗？`nassistant:这款已经是全网最低价了。"
  })
} | ConvertTo-Json -Depth 8

$qcResp = Invoke-WebRequest -Method POST `
  -Uri "http://127.0.0.1:8080/api/v3/bots/chat/completions/quality_inspection" `
  -ContentType "application/json" `
  -Body $qcBody
```

### 6.5 next_question

```powershell
$nqBody = @{
  stream   = $false
  model    = "my-bot"
  messages = @(@{
    role    = "user"
    content = "user:我想买一个车载手机支架`nassistant:推荐折叠旋转电动无线充车载支架，支持自动夹紧和无线充电。"
  })
} | ConvertTo-Json -Depth 8

$nqResp = Invoke-WebRequest -Method POST `
  -Uri "http://127.0.0.1:8080/api/v3/bots/chat/completions/next_question" `
  -ContentType "application/json" `
  -Body $nqBody
```

## 7) Chinese text display fix in PowerShell

If Chinese content is garbled in terminal output:

```powershell
chcp 65001
[Console]::InputEncoding  = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding           = [System.Text.UTF8Encoding]::new($false)
```

For response text that is already garbled:

```powershell
$s = ($resp.Content | ConvertFrom-Json).choices[0].message.content
[System.Text.Encoding]::UTF8.GetString([System.Text.Encoding]::GetEncoding(28591).GetBytes($s))
```

