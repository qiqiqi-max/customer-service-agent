"""Knowledge base helpers backed by MySQL with optional Dify compatibility."""

from __future__ import annotations

import io
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple

import config
import pandas as pd
from arkitect.types.llm.model import ActionDetail, ArkMessage, ToolDetail
from observability import elapsed_ms, log_event, monotonic
from sqlalchemy import desc, insert, select
from tos import TosClientV2
from tos.exceptions import TosServerError
from volcengine.viking_knowledgebase import VikingKnowledgeBaseService

from database import faq_documents, get_engine, init_db

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

tos_client = TosClientV2(
    ak=config.ak,
    sk=config.sk,
    region="cn-beijing",
    endpoint="tos-cn-beijing.volces.com",
)


def save_faq(faq_data: pd.DataFrame, account_id: str) -> None:
    provider = "mock" if config.mock_mode else (config.knowledge_provider or "mysql")
    started = monotonic()
    success = False
    try:
        if config.mock_mode:
            _save_mock_faq(faq_data, account_id)
        elif provider == "dify":
            _save_dify_faq(faq_data, account_id)
            _save_mysql_faq(faq_data, account_id)
        elif provider == "volcengine":
            _save_volcengine_faq(faq_data, account_id)
            _save_mysql_faq(faq_data, account_id)
        else:
            _save_mysql_faq(faq_data, account_id)
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
        if success:
            log_event(
                "faq.save",
                ok=True,
                provider=provider,
                account_id=account_id,
                row_count=len(faq_data),
                duration_ms=elapsed_ms(started),
            )


def _save_mysql_faq(faq_data: pd.DataFrame, account_id: str) -> None:
    init_db()
    rows = []
    now = int(monotonic() * 1000)
    for _, row in faq_data.iterrows():
        question = str(row.get("question", "")).strip()
        answer = str(row.get("answer", "")).strip()
        if not question or not answer:
            continue
        rows.append(
            {
                "account_id": account_id or "test",
                "question": question,
                "answer": answer,
                "score": int(row.get("score", 0) or 0),
                "status": "approved",
                "source": "runtime",
                "created_at": now,
            }
        )
    with get_engine().begin() as conn:
        if rows:
            conn.execute(insert(faq_documents), rows)


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


def _save_volcengine_faq(faq_data: pd.DataFrame, account_id: str) -> None:
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
        object_stream = tos_client.get_object(bucket_name, object_key)
        df = pd.read_excel(io.BytesIO(object_stream.read()))
        df = pd.concat([df, faq_data], ignore_index=True)
    except TosServerError as e:
        if e.status_code != 404:
            raise e
        df = faq_data

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    tos_client.put_object(
        bucket=bucket_name,
        key=object_key,
        content=output,
        meta={"doc_id": f"doc_id_{account_id}", "account_id": account_id},
    )
    collection = viking_knowledgebase_service.get_collection(
        collection_name=config.faq_collection_name,
        project="default",
    )
    collection.add_doc(add_type="tos", tos_path=f"{bucket_name}/{object_key}")


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
    provider = config.knowledge_provider or "mysql"
    if provider == "dify":
        return _retrieve_dify_knowledge(messages)
    records = _search_mysql_faq(messages[-1].content if messages else "", doc_filter)
    action_detail = ActionDetail(
        name="knowledge",
        tool_details=[
            ToolDetail(
                name="mysql_retrieval",
                input=messages[-1].content if messages else "",
                output=records,
            )
        ],
    )
    return (_format_mysql_prompt(records), action_detail)


def _search_mysql_faq(query: str, doc_filter: dict, limit: int = 5) -> List[dict]:
    init_db()
    account_id = _extract_account_id(doc_filter)
    stmt = select(faq_documents).order_by(
        desc(faq_documents.c.created_at),
        desc(faq_documents.c.id),
    )
    if account_id:
        stmt = stmt.where(faq_documents.c.account_id == account_id)
    if query:
        stmt = stmt.where(
            (faq_documents.c.question.contains(query))
            | (faq_documents.c.answer.contains(query))
        )
    stmt = stmt.limit(limit)
    with get_engine().connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


def _format_mysql_prompt(records: List[dict]) -> str:
    title = "参考资料" if config.language == "zh" else "References"
    rule = (
        "请优先且严格依据 <context> 中的 FAQ/知识库内容回答。"
        "如果资料不足，请明确说明暂未查到可靠信息，不要编造。"
        if config.language == "zh"
        else "Use the FAQ/knowledge base content in <context> first. If the data is insufficient, do not invent an answer."
    )
    return f"""
# {title}
{rule}
<context>
{json.dumps(records, ensure_ascii=False, indent=2)}
</context>
"""


def _require_env_settings(settings: dict) -> None:
    missing = [env_name for env_name, attr in settings.items() if not getattr(config, attr)]
    if missing:
        raise ValueError(
            "Missing required environment variables: "
            f"{', '.join(missing)}. Please configure them before saving FAQ data."
        )


def _extract_account_id(doc_filter: dict) -> str:
    if not isinstance(doc_filter, dict):
        return ""
    conds = doc_filter.get("conds") or []
    for item in conds:
        if isinstance(item, str):
            return item
        if isinstance(item, dict) and item.get("field") == "account_id":
            values = item.get("conds") or []
            return str(values[0]) if values else ""
    return ""


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
    rule = (
        "请优先且严格依据 <context> 中的知识库内容回答。"
        "如果知识库内容不足以回答用户问题，请明确说明没有命中可靠资料，不要编造答案。"
        if config.language == "zh"
        else "Use only the knowledge base content in <context> as the primary source. No reliable Dify knowledge base content was retrieved."
    )
    return f"""
# {title}
{rule}
<context>
{json.dumps(chunks, ensure_ascii=False, indent=2)}
</context>
"""


def _dify_retrieve(dataset_id: str, query: str, top_k: int) -> List[dict]:
    if not dataset_id or not config.dify_api_key:
        return []
    payload = _dify_post_json(
        f"/datasets/{dataset_id}/retrieve",
        {
            "query": query,
            "retrieval_model": {
                "search_method": "hybrid_search",
                "reranking_enable": False,
                "top_k": top_k,
                "score_threshold_enabled": config.dify_score_threshold_enabled,
                "score_threshold": config.dify_score_threshold,
            },
        },
    )
    return _normalize_dify_records(payload, dataset_id)


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
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))
