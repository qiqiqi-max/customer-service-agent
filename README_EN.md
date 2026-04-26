# AI Shopping Assistant
## Overview
This is an AI shopping assistant designed with Clothes & Fashion e-commerce as an example scenario. It leverages Function calling capabilities of LLM, along with product knowledge bases and existing e-commerce tools, to support e-commerce operations. In addition, developers can use this demo as a reference to integrate real e-commerce system APIs, enabling intelligent e-commerce optimization, customer service algorithm testing, and more.
### Demo Preview
![alt text](assets/image-1.png)
1. Simulate e-commerce operations: Manage products on store shelves.
2. Configure intelligent customer service capabilities: Support functions such as product introduction, Shipping inquiry, Refund and return, Product recommendation, Order inquiry, and Quality inspection.
3. Experience and testing: Supports switching between fully automated and human-assisted modes to test the fluency of conversations between the intelligent assistant and customers. Advanced features such as conversation summary and real-time quality inspection are also included.
  - Automatic mode: The AI assistant responds to customer inquiries directly.
  - Human-assisted mode: The AI assistant's suggested response appears in the input box, allowing manual edits before sending.

### System Architecture
![alt text](assets/image-9.png)
## Key Features
### Enjoy the intelligent E-commerce operation experience
Leveraging LLMs' function call capabilities to provide comprehensive intelligent customer service for e-commerce. Developers can easily integrate with or replace existing online store interfaces within the current framework, achieving one-stop AI upgrade management.
### Supports both fully automatic and human-assisted modes
The system offers two interaction modes: fully automatic and human-assisted. Merchants can flexibly choose and switch based on actual needs. It also supports one-click summarization of the current conversation, ensuring smooth and efficient communication with potential customers, thus improving order conversion rates.
### Customizable functionality
Based on the product knowledge base and FAQ database, it provides customers with accurate product information and answers to frequently asked questions. It offers capabilities such as product introduction, intelligent shopping guide, order inquiry, logistics information, and return/refund support, all of which can be flexibly configured to be turned on or off.
### Application with rich features
- Quality inspection: Real-time inspection that customer service responses meet standards, avoiding inappropriate language
- Conversation summary: Automatically summarizes key points of customer service conversations, helping to quickly understand conversation content
- FAQ management: Supports adding and updating answers to frequently asked questions, continuously enriching the knowledge base

## Related Models and Cloud Services
### Models
| Type  | Service name | Description                                      | Billing rules                                                                                                                                                                              |
| ----- | ------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Model | Skylark-pro  | Powerful model with function calling capability. | 500K tokens are given as a free quota upon activation. For usage exceeding this amount, payment is based on the token consumption. For detailed pricing, refer to the billing description. |

### Cloud Services
| Type          | Service name               | Description                                                                                                                                                                                                           | Billing rules     |
| ------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| Cloud service | Knowledge base             | - (Coming soon on BytePlus) RAG Cloud is a knowledge management solution that analyzes, segments, and processes business knowledge for enhanced retrieval capabilities.<br>- You can also choose other RAG solutions. | /                 |
| Cloud service | Torch Object Storage (TOS) | Optional, used to update the FAQ knowledge base. Rapidly scalable, low cost cloud storage for diverse and high performance applications.                                                                              | Billing by volume |

## Environment Setup 
- Python version requirement: ≥ 3.9 and < 3.12
- Poetry version 1.6.1, you can install it using the following command: 
```shell
pip install poetry==1.6.1
```
- Create API key on ModelArk Console
- Activate Skylark-pro mode on Console

## Quick Start
This guide explains how to deploy and run the ShopAssist application locally.
1. Create a knowledge base for product information retrieval and note down its name for later use.
2. Create a knowledge base for FAQ retrieval and record the name for later use.
3. Download the code repository.
```shell
git clone https://github.com/volcengine/ai-app-lab.git
cd demohouse/shop_assist/backend
```
4. Set the environment variables. You can refer to the Environment Setup section for details on the required values.
```shell
# Enter the ARK_API_KEY
export ARK_API_KEY="your ARK_API_KEY"
# Enter the Model ID of the LLM to use (recommend: skylark-pro)
export LLM_ENDPOINT_ID="skylark-pro"
export USE_SERVER_AUTH="True" 
```
5. Install dependencies
```shell
python -m venv .venv
source .venv/bin/activate
pip install poetry==1.6.1

poetry install
```

6. Start the backend server
```shell
poetry run python main.py
```
7. After the backend server is successfully started, you can use curl locally to interact with and try out the capabilities of the following five scenarios.
  - Customer service Q&A
```shell
curl --location 'http://localhost:8080/api/v3/bots/chat/completions' \
--header 'Content-Type: application/json' \
--data '{
    "stream": false,
    "model": "my-bot",
    "messages": [
        {
            "role": "user",
            "content": "Help me look up all my past orders"
        }
    ]
}'
```
  - FAQ update
```shell
curl --location 'http://localhost:8080/api/v3/bots/chat/completions/save_faq' \
--header 'Content-Type: application/json' \
--data '{
    "question": "return policy",
    "answer": "This item can be returned in its original condition for a full refund or replacement within 30 days of receipt",
    "score": 5,
    "account_id": "100000"
}'
```
  - Quality inspection
```shell
curl --location 'http://localhost:8080/api/v3/bots/chat/completions/quality_inspection' \
--header 'Content-Type: application/json' \
--data '{
    "stream": false,
    "model": "my-bot",
    "messages": [
        {
            "role": "user",
            "content": "user: Can you give me a better price on this T-shirt?\n assistant: Dear, this product is absolutely the lowest price online!"
        }
    ]
}'
```
  - Conversation summary
```shell
curl --location 'http://localhost:8080/api/v3/bots/chat/completions/summary' \
--header 'Content-Type: application/json' \
--data '{
    "stream": false,
    "model": "my-bot",
    "messages": [
        {
            "role": "user",
            "content": "user: Can you give me a better price on this T-shirt?\n assistant: Dear, this product is absolutely the lowest price online!"
        }
    ]
}'
```
  - Follow-up question generation
```shell
curl --location 'http://localhost:8080/api/v3/bots/chat/completions/next_question' \
--header 'Content-Type: application/json' \
--data '{
    "stream": false,
    "model": "my-bot",
    "messages": [
        {
            "role": "user",
            "content": "user: Can you give me a better price on this T-shirt?\n assistant: Dear, this product is absolutely the lowest price online!"
        }
    ]
}'
```

## Implementation detail
- `/completions`    Customer Service Q&A
  - Implements tool call via the model's Function Calling capabilities
    - Includes three built-in mock tools: order inquiry, logistics inquiry, return and refund
    - Executes internal multi-turn LLM calls until the LLM determines that no further tool usage is required.
- `/summary`   Summarize the conversation between the AI customer service and the user
  - Implemented with a single LLM call
- `/quality_inspection`   Perform quality inspection on customer service responses based on quality inspection keywords and the built-in system prompt.
  - Implemented with a single LLM call
- `/save_faq`
  - Download the FAQ file from TOS BUCKET_NAME bucket, update it, and re-upload it
  - FAQ_COLLECTION_NAME knowledge base loads the new FAQ data from TOS BUCKET_NAME bucket
- `/next_question`   Generate follow-up questions for customers
  - Implemented with a single LLM call

## Project Structure 
```
├── README.md
├── config.py               # Configuration file
├── main.py               
├── quality_inspection.py # Quality inspection module
├── summary.py           # Conversation summary module
├── utils.py
├── docs/                # Documents used for initializing the knowledge base  
├── data/                # Data directory
    ├── cache.py        # Mock storage
    ├── orders.py       # Generates three mock orders per account
    ├── product.py      # Product catalog and info; modify this file to add products
    ├── rag.py          # Retrieves product details and FAQs
    └── tracking.py      # Mock logistics tracking
├── tests/               # Test cases
└── tools/               # Customer service Q&A module and prompts
```

## License
For non-commercial use only. For commercial use, please contact us.
