# Shop Assist Local Repro Guide (Windows / PowerShell)

This guide records the exact local setup and verification flow that has been validated in this environment.

## 1) Prerequisites

- Windows PowerShell
- Python 3.10.x
- VolcEngine resources ready:
  - AK/SK
  - ARK API Key
  - Product KB collection name
  - FAQ KB collection name
  - TOS bucket name (Beijing region)

## 2) Install dependencies

Run in:

`D:\projects\ai-app-lab\demohouse\shop_assist\backend`

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install --upgrade "arkitect==0.2.1" "langchain==0.3.25" "langchain-core==0.3.58" "langchain-text-splitters==0.3.8"
```

## 3) Environment variables

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

## 4) Start backend

```powershell
.\.venv\Scripts\python main.py
```

Keep this terminal open.

## 5) Health check

Run in another terminal:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/v1/ping
```

Expected: `StatusCode : 200`

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

