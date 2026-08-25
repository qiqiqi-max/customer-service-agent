# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# Licensed under the 【火山方舟】原型应用软件自用许可协议
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     https://www.volcengine.com/docs/82379/1433703
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ak = os.getenv("VOLC_ACCESSKEY", "")
sk = os.getenv("VOLC_SECRETKEY", "")
collection_name = os.getenv("COLLECTION_NAME", "")
faq_collection_name = os.getenv("FAQ_COLLECTION_NAME", "")
endpoint_id = os.getenv("LLM_ENDPOINT_ID", "doubao-seed-1-6-250615")
bucket_name = os.getenv("BUCKET_NAME", "")
use_server_auth = os.getenv("USE_SERVER_AUTH", "False").lower() in ("true", "1", "t")
mock_mode = os.getenv("MOCK_MODE", "False").lower() in ("true", "1", "t", "yes")
knowledge_provider = os.getenv("KNOWLEDGE_PROVIDER", "volcengine").lower()
dify_api_key = os.getenv("DIFY_API_KEY", "")
dify_base_url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
dify_dataset_id = os.getenv("DIFY_DATASET_ID", "")
dify_faq_dataset_id = os.getenv("DIFY_FAQ_DATASET_ID", "")
dify_top_k = int(os.getenv("DIFY_TOP_K", "5"))
dify_score_threshold = float(os.getenv("DIFY_SCORE_THRESHOLD", "0"))
dify_score_threshold_enabled = os.getenv(
    "DIFY_SCORE_THRESHOLD_ENABLED", "False"
).lower() in ("true", "1", "t", "yes")
dify_indexing_technique = os.getenv("DIFY_INDEXING_TECHNIQUE", "high_quality")
dify_doc_form = os.getenv("DIFY_DOC_FORM", "text_model")
dify_doc_language = os.getenv("DIFY_DOC_LANGUAGE", "Chinese")
conversation_db_path = os.getenv(
    "CONVERSATION_DB_PATH",
    str(BASE_DIR / "data" / "conversations.sqlite3"),
)
database_url = os.getenv("DATABASE_URL", "")
api_keys = [
    key.strip()
    for key in os.getenv("API_KEYS", os.getenv("API_KEY", "")).split(",")
    if key.strip()
]
business_data_provider = os.getenv("BUSINESS_DATA_PROVIDER", "mock").lower()
business_api_base_url = os.getenv("BUSINESS_API_BASE_URL", "")
business_api_key = os.getenv("BUSINESS_API_KEY", "")
business_api_timeout = float(os.getenv("BUSINESS_API_TIMEOUT", "8"))
log_level = os.getenv("LOG_LEVEL", "INFO")
log_dir = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
log_to_stdout = os.getenv("LOG_TO_STDOUT", "False").lower() in (
    "true",
    "1",
    "t",
    "yes",
)
llm_provider = os.getenv("LLM_PROVIDER", "volcengine").lower()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseekv4pro")
zhipu_api_key = os.getenv("ZHIPU_API_KEY") or os.getenv("ZAI_API_KEY", "")
zhipu_base_url = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
zhipu_model = os.getenv("ZHIPU_MODEL", "glm-5.2")
language = os.getenv("LANGUAGE", "zh").lower()
if language not in ("zh", "en"):
    language = "zh"
