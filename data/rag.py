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

import io
import json
import logging
from pathlib import Path
from typing import List, Tuple
import urllib.error
import urllib.request

import config
import pandas as pd
from observability import elapsed_ms, log_event, monotonic
from tos import TosClientV2
from tos.exceptions import TosServerError
from volcengine.viking_knowledgebase import VikingKnowledgeBaseService

from arkitect.types.llm.model import ActionDetail, ArkMessage, ToolDetail

logger = logging.getLogger(__name__)
MOCK_FAQ_DIR = Path(__file__).resolve().parent / "mock_faq"

try:
    viking_knowledgebase_service = VikingKnowledgeBaseService(
        host="api-knowledgebase.mlp.cn-beijing.volces.com",
        scheme="https",
        connection_timeout=30,
        socket_timeout=30,
    )
    viking_knowledgebase_service.set_ak(config.ak)
    viking_knowledgebase_service.set_sk(config.sk)
except Exception as exc:
    logger.warning("VolcEngine knowledge base client initialization failed: %s", exc)
    viking_knowledgebase_service = None

# Initialize TOS client
tos_client = TosClientV2(
    ak=config.ak,
    sk=config.sk,
    region="cn-beijing",
    endpoint="tos-cn-beijing.volces.com",
)


def _require_env_settings(settings: dict) -> None:
    missing = [env_name for env_name, attr in settings.items() if not getattr(config, attr)]
    if missing:
        raise ValueError(
            "Missing required environment variables: "
            f"{', '.join(missing)}. Please configure them before saving FAQ data."
        )


def save_faq(faq_data: pd.DataFrame, account_id: str) -> None:
    """
    Download existing FAQs from TOS, append new FAQ, upload back to TOS in xlsx format,
    and update the knowledge base.

    Args:
        faq_data: Dictionary containing the new FAQ data to append
    """
    provider = "mock" if config.mock_mode else config.knowledge_provider
    started = monotonic()
    success = False
    try:
        if config.mock_mode:
            _save_mock_faq(faq_data, account_id)
            success = True
            return

        if config.knowledge_provider == "dify":
            _save_dify_faq(faq_data, account_id)
            success = True
            return

        _require_env_settings(
            {
                "BUCKET_NAME": "bucket_name",
                "FAQ_COLLECTION_NAME": "faq_collection_name",
            }
        )
        if viking_knowledgebase_service is None:
            raise RuntimeError(
                "VolcEngine knowledge base client is unavailable. "
                "Set KNOWLEDGE_PROVIDER=dify or check VolcEngine network/configuration."
            )
        bucket_name = config.bucket_name
        if account_id == "":
            account_id = "test"
        object_key = f"custom_support/faq/{account_id}.faq.xlsx"
        try:
            # Download existing FAQs
            object_stream = tos_client.get_object(bucket_name, object_key)
            df = pd.read_excel(io.BytesIO(object_stream.read()))
            df = pd.concat([df, faq_data], ignore_index=True)
        except TosServerError as e:
            if e.status_code != 404:  # NoSuchKey
                raise e
            df = faq_data

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        # Upload updated FAQs back to TOS, meta will be doc meta in knowledgebase
        tos_client.put_object(
            bucket=bucket_name,
            key=object_key,
            content=output,
            # doc_id in knowledgebase must start with a letter
            meta={"doc_id": f"doc_id_{account_id}", "account_id": account_id},
        )
        # Update knowledge base
        collection = viking_knowledgebase_service.get_collection(
            collection_name=config.faq_collection_name,
            project="default",
        )
        collection.add_doc(add_type="tos", tos_path=f"{bucket_name}/{object_key}")
        success = True
    except Exception as exc:
        log_event(
            "faq.save",
            level="error",
            ok=False,
            provider=provider,
            account_id=account_id,
            row_count=len(faq_data),
            duration_ms=elapsed_ms(started),
            error_type=exc.__class__.__name__,
            error=str(exc),
        )
        raise
    finally:
        if provider and success:
            log_event(
                "faq.save",
                ok=True,
                provider=provider,
                account_id=account_id,
                row_count=len(faq_data),
                duration_ms=elapsed_ms(started),
            )


def _save_mock_faq(faq_data: pd.DataFrame, account_id: str) -> None:
    if account_id == "":
        account_id = "test"
    MOCK_FAQ_DIR.mkdir(parents=True, exist_ok=True)
    file_path = MOCK_FAQ_DIR / f"{account_id}.faq.xlsx"
    if file_path.exists():
        df = pd.read_excel(file_path)
        df = pd.concat([df, faq_data], ignore_index=True)
    else:
        df = faq_data
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)


def _save_dify_faq(faq_data: pd.DataFrame, account_id: str) -> None:
    _require_env_settings(
        {
            "DIFY_API_KEY": "dify_api_key",
            "DIFY_FAQ_DATASET_ID": "dify_faq_dataset_id",
        }
    )
    if account_id == "":
        account_id = "test"
    for index, row in faq_data.iterrows():
        question = str(row.get("question", "")).strip()
        answer = str(row.get("answer", "")).strip()
        score = row.get("score", "")
        if not question or not answer:
            continue
        _dify_post_json(
            f"/datasets/{config.dify_faq_dataset_id}/document/create_by_text",
            {
                "name": f"faq_{account_id}_{index}_{question[:24]}",
                "text": (
                    f"account_id: {account_id}\n"
                    f"score: {score}\n"
                    f"question: {question}\n"
                    f"answer: {answer}"
                ),
                "indexing_technique": config.dify_indexing_technique,
                "doc_form": config.dify_doc_form,
                "doc_language": config.dify_doc_language,
            },
        )


def retrieval_knowledge(
    messages: List[ArkMessage], doc_filter: dict
) -> Tuple[str, ActionDetail]:
    if config.knowledge_provider == "dify":
        return _retrieve_dify_knowledge(messages)

    # Rewriting queries in RAG incorporates historical context, ensuring the user’s key
    #  concerns from prior conversations are reflected, improving retrieval relevance.
    pre_processing = {
        "need_instruction": True,
        "rewrite": True,
        "messages": [m.model_dump() for m in messages],
        "return_token_usage": True,
    }

    query = messages[-1].content if messages else ""

    def search_with_fallback(collection_name: str, limit: int) -> dict:
        if viking_knowledgebase_service is None:
            return {"result_list": [], "rewrite_query": query}
        if not collection_name:
            return {"result_list": [], "rewrite_query": query}

        base_params = {
            "collection_name": collection_name,
            "query": query,
            "pre_processing": pre_processing,
            "limit": limit,
            "dense_weight": 0.5,
            "post_processing": {},
            "project": "default",
        }

        # First try strict metadata filter; if metadata schema/labels are not ready,
        # fallback to unfiltered retrieval instead of failing the whole chat.
        try:
            return viking_knowledgebase_service.search_knowledge(
                **base_params,
                query_param={"doc_filter": doc_filter},
            )
        except Exception as exc:
            logger.warning(
                "Knowledge search with metadata filter failed for collection %s: %s",
                collection_name,
                exc,
            )
            try:
                return viking_knowledgebase_service.search_knowledge(**base_params)
            except Exception as fallback_exc:
                logger.warning(
                    "Knowledge search fallback failed for collection %s: %s",
                    collection_name,
                    fallback_exc,
                )
                return {"result_list": [], "rewrite_query": query}

    # seperate retrieval for different doc types
    res = search_with_fallback(config.collection_name, 3)
    faq_res = search_with_fallback(config.faq_collection_name, 5)

    refs = (res.get("result_list") or []) + (faq_res.get("result_list") or [])
    ref = [item.get("doc_info") for item in refs if isinstance(item, dict)]

    action_detail = ActionDetail(
        name="knowledge",
        tool_details=[
            ToolDetail(
                name="retrieval",
                input=faq_res.get("rewrite_query") or res.get("rewrite_query") or query,
                output=ref,
            )
        ],
    )
    return (
        f"""
# {"参考资料" if config.language == "zh" else "References"}
<context>
{res["result_list"]}
{faq_res["result_list"]}
</context>
""",
        action_detail,
    )


def _retrieve_dify_knowledge(messages: List[ArkMessage]) -> Tuple[str, ActionDetail]:
    query = messages[-1].content if messages else ""
    product_res = _dify_retrieve(config.dify_dataset_id, query, min(config.dify_top_k, 5))
    faq_res = _dify_retrieve(config.dify_faq_dataset_id, query, config.dify_top_k)
    chunks = product_res + faq_res

    action_detail = ActionDetail(
        name="knowledge",
        tool_details=[
            ToolDetail(
                name="dify_retrieval",
                input=query,
                output=chunks,
            )
        ],
    )

    return (_format_dify_prompt(chunks), action_detail)


def _format_dify_prompt(chunks: List[dict]) -> str:
    title = "参考资料" if config.language == "zh" else "References"
    if chunks:
        rule = (
            "请优先且严格依据 <context> 中的知识库内容回答。"
            "如果知识库内容不足以回答用户问题，请明确说明暂未查到可靠资料，"
            "不要编造商品参数、价格、售后承诺或物流时效。"
            if config.language == "zh"
            else "Use only the knowledge base content in <context> as the primary source. "
            "If the context is insufficient, say that reliable information was not found; "
            "do not invent product specs, prices, support promises, or delivery times."
        )
    else:
        rule = (
            "本轮 Dify 知识库没有命中可靠资料。请不要编造答案；"
            "如果用户问题需要商品、售后或规则依据，请说明暂未查到相关资料，"
            "并引导用户补充信息或转人工处理。"
            if config.language == "zh"
            else "No reliable Dify knowledge base content was retrieved. Do not invent an answer; "
            "ask for more information or suggest human support when the question requires a verified source."
        )

    return f"""
# {title}
{rule}
<context>
{json.dumps(chunks, ensure_ascii=False, indent=2)}
</context>
"""


def _dify_retrieve(dataset_id: str, query: str, top_k: int) -> List[dict]:
    if not dataset_id:
        return []
    if not config.dify_api_key:
        logger.warning("DIFY_API_KEY is missing; skip Dify retrieval.")
        log_event(
            "knowledge.dify_retrieve",
            level="warning",
            ok=False,
            dataset_id=dataset_id,
            top_k=top_k,
            error="DIFY_API_KEY is missing.",
        )
        return []

    started = monotonic()
    retrieval_model = {
        "search_method": "hybrid_search",
        "reranking_enable": False,
        "top_k": top_k,
        "score_threshold_enabled": config.dify_score_threshold_enabled,
        "score_threshold": config.dify_score_threshold,
    }
    try:
        payload = _dify_post_json(
            f"/datasets/{dataset_id}/retrieve",
            {
                "query": query,
                "retrieval_model": retrieval_model,
            },
        )
    except Exception as exc:
        logger.warning("Dify retrieval failed for dataset %s: %s", dataset_id, exc)
        log_event(
            "knowledge.dify_retrieve",
            level="warning",
            ok=False,
            dataset_id=dataset_id,
            top_k=top_k,
            duration_ms=elapsed_ms(started),
            error_type=exc.__class__.__name__,
            error=str(exc),
        )
        return []

    records = _normalize_dify_records(payload, dataset_id)
    log_event(
        "knowledge.dify_retrieve",
        ok=True,
        dataset_id=dataset_id,
        top_k=top_k,
        duration_ms=elapsed_ms(started),
        hit_count=len(records),
    )
    return records


def _normalize_dify_records(payload: dict, dataset_id: str) -> List[dict]:
    records = payload.get("records") or []
    normalized = []
    for record in records:
        segment = record.get("segment") or {}
        document = segment.get("document") or record.get("document") or {}
        normalized.append(
            {
                "dataset_id": dataset_id,
                "document_id": document.get("id") or segment.get("document_id"),
                "document_name": document.get("name"),
                "segment_id": segment.get("id") or record.get("segment_id"),
                "score": record.get("score"),
                "content": segment.get("content") or record.get("content") or "",
            }
        )
    return normalized


def _dify_post_json(path: str, body: dict) -> dict:
    url = f"{config.dify_base_url.rstrip('/')}{path}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.dify_api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Dify API returned HTTP {exc.code}: {detail}") from exc
