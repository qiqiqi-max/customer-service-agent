# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# Licensed under the "火山方舟" 原型应用软件自用许可协议

import os
import time
from pathlib import Path
from typing import AsyncIterable, List, Optional, Union
from uuid import uuid4

import pandas as pd
from volcenginesdkarkruntime import AsyncArk
from agent_tools import build_openai_tools, build_tool_executor
from audit_store import (
    list_faq_candidates,
    list_quality_reviews,
    list_tool_calls,
    save_faq_candidate,
    save_quality_review,
)
from config import api_keys, endpoint_id, language, mock_mode
from database import migrate_database
from conversation_store import (
    attach_conversation_metadata,
    ConversationAccessError,
    ensure_conversation,
    get_conversation,
    init_db,
    list_conversations,
    record_chat_turn,
)
from data import rag
from data.product import get_products
from data.rag import retrieval_knowledge
from data.refunds import RefundError, get_refund_request
from business_services import get_business_service
from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from llm_provider import is_openai_compatible_provider, run_openai_compatible_chat
from mock_agent import make_mock_chat_response, stream_mock_response
from next_question import next_question_chat
from observability import configure_observability, elapsed_ms, log_event, monotonic
from pydantic import BaseModel, Field
from quality_inspection import quality_inspection_chat
from quality_rules import inspect_quality_text
from summary import summary_chat
from tools.tools import FUNCTION_MAP, register_support_functions
from utils import get_auth_header, get_handler

from arkitect.core.component.bot.server import BotServer
from arkitect.core.component.llm import BaseChatLanguageModel
from arkitect.launcher.runner import (
    get_endpoint_config,
    get_runner,
)
from arkitect.telemetry.trace import task
from arkitect.telemetry.trace.setup import setup_tracing
from arkitect.types.llm.model import (
    ActionDetail,
    ArkChatCompletionChunk,
    ArkChatRequest,
    ArkChatResponse,
    ArkMessage,
    BotUsage,
)
from arkitect.utils.context import (
    set_resource_id,
    set_resource_type,
)
from volcenginesdkarkruntime.types.chat.chat_completion import Choice

BACKEND_DIR = Path(__file__).resolve().parent
WEBUI_DIR = BACKEND_DIR / "webui"
FRONTEND_DIST_DIR = BACKEND_DIR / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"


@task()
async def custom_support_chat(
    request: ArkChatRequest,
) -> AsyncIterable[Union[ArkChatCompletionChunk, ArkChatResponse]]:
    meta_data = request.metadata if request.metadata else {}
    account_id = meta_data.get("account_id", "test")
    try:
        conversation_id = ensure_conversation(
            meta_data.get("conversation_id"),
            account_id,
        )
    except ConversationAccessError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ConversationAccessDenied",
                "message": str(exc),
            },
        ) from exc

    log_event(
        "chat.request",
        account_id=account_id,
        conversation_id=conversation_id,
        provider="mock" if mock_mode else ("openai_compatible" if is_openai_compatible_provider() else "volcengine"),
        stream=request.stream,
        message_count=len(request.messages),
    )

    if mock_mode:
        started = monotonic()
        response = await make_mock_chat_response(request)
        log_event(
            "chat.mock_response",
            account_id=account_id,
            conversation_id=conversation_id,
            duration_ms=elapsed_ms(started),
        )
        attach_conversation_metadata(response, conversation_id)
        record_chat_turn(conversation_id, request, response)
        if request.stream:
            async for chunk in stream_mock_response(response):
                yield chunk
        else:
            yield response
        return

    functions = meta_data.get(
        "support_functions",
        [*FUNCTION_MAP],
    )
    products = meta_data.get("product_list", [*get_products()])

    tools, system_prompt = register_support_functions(functions, products, account_id)
    messages = [ArkMessage(role="system", content=system_prompt)]
    messages.extend(request.messages)

    knowledge_prompt = ""
    action_detail = None
    retrieval_started = monotonic()
    try:
        knowledge_prompt, action_detail = retrieval_knowledge(
            messages,
            {
                "op": "or",
                "conds": [
                    {"op": "must", "field": "account_id", "conds": [account_id]},
                    {
                        "op": "must",
                        "field": "产品名" if language == "zh" else "product_name",
                        "conds": products,
                    },
                ],
            },
        )
        log_event(
            "knowledge.retrieval",
            ok=True,
            provider=rag.config.knowledge_provider,
            account_id=account_id,
            conversation_id=conversation_id,
            duration_ms=elapsed_ms(retrieval_started),
            hit_count=_action_hit_count(action_detail),
        )
    except Exception:
        log_event(
            "knowledge.retrieval",
            level="warning",
            ok=False,
            provider=rag.config.knowledge_provider,
            account_id=account_id,
            conversation_id=conversation_id,
            duration_ms=elapsed_ms(retrieval_started),
        )
        knowledge_prompt = ""

    if is_openai_compatible_provider():
        provider_messages = [*messages]
        if knowledge_prompt:
            provider_messages.append(ArkMessage(role="system", content=knowledge_prompt))
        response = await run_openai_compatible_chat(
            provider_messages,
            tools=build_openai_tools(functions),
            tool_executor=build_tool_executor(account_id),
        )
        if action_detail:
            if not response.bot_usage:
                response.bot_usage = BotUsage(action_details=[action_detail])
            else:
                response.bot_usage.action_details = [
                    *(response.bot_usage.action_details or []),
                    action_detail,
                ]
        attach_conversation_metadata(response, conversation_id)
        record_chat_turn(conversation_id, request, response)
        if request.stream:
            async for chunk in stream_mock_response(response):
                yield chunk
        else:
            yield response
        return

    llm = BaseChatLanguageModel(
        model=endpoint_id,
        messages=messages,
    )

    if request.stream:
        model_started = monotonic()
        streamed_text = []
        last_bot_usage = None
        last_response_id = None
        last_model = endpoint_id
        async for resp in llm.astream(
            functions=tools,
            additional_system_prompts=[knowledge_prompt],
            extra_headers=get_auth_header(),
            extra_body={"thinking": {"type": "disabled"}},
        ):
            if action_detail:
                if resp.bot_usage:
                    resp.merge_bot_usages(BotUsage(action_details=[action_detail]))
                else:
                    resp.bot_usage = BotUsage(action_details=[action_detail])
            _attach_metadata(resp, conversation_id)
            if getattr(resp, "bot_usage", None):
                last_bot_usage = resp.bot_usage
            if getattr(resp, "id", None):
                last_response_id = resp.id
            if getattr(resp, "model", None):
                last_model = resp.model
            content_delta = _chunk_content(resp)
            if content_delta:
                streamed_text.append(content_delta)
            yield resp
        record_chat_turn(
            conversation_id,
            request,
            ArkChatResponse(
                id=last_response_id or f"stream-{int(time.time() * 1000)}",
                created=int(time.time()),
                model=last_model,
                object="chat.completion",
                choices=[
                    Choice(
                        index=0,
                        finish_reason="stop",
                        message={
                            "role": "assistant",
                            "content": "".join(streamed_text),
                        },
                    )
                ],
                bot_usage=last_bot_usage,
                metadata={"conversation_id": conversation_id},
            ),
        )
        log_event(
            "llm.volcengine_stream",
            account_id=account_id,
            conversation_id=conversation_id,
            model=last_model,
            duration_ms=elapsed_ms(model_started),
            output_chars=len("".join(streamed_text)),
        )
    else:
        model_started = monotonic()
        resp = await llm.arun(
            functions=tools,
            additional_system_prompts=[knowledge_prompt],
            extra_headers=get_auth_header(),
            extra_body={"thinking": {"type": "disabled"}},
        )
        log_event(
            "llm.volcengine_chat",
            account_id=account_id,
            conversation_id=conversation_id,
            model=getattr(resp, "model", endpoint_id),
            duration_ms=elapsed_ms(model_started),
            output_chars=len(_assistant_content(resp)),
        )
        if action_detail:
            if resp.bot_usage:
                resp.merge_bot_usages(BotUsage(action_details=[action_detail]))
            else:
                resp.bot_usage = BotUsage(action_details=[action_detail])
        attach_conversation_metadata(resp, conversation_id)
        record_chat_turn(conversation_id, request, resp)
        yield resp


class Product(BaseModel):
    name: str
    description: str
    cover_image: str


class ProductListResponse(BaseModel):
    products: List[Product]
    total: int


class FAQRequest(BaseModel):
    question: str = Field(..., max_length=100)
    answer: str = Field(..., max_length=500)
    score: int = Field(..., ge=1, le=5)
    account_id: str = Field(..., max_length=100)
    conversation_id: Optional[str] = Field(None, max_length=100)


class BusinessChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str = Field(..., max_length=4000)


class BusinessChatRequest(BaseModel):
    message: str = Field(..., max_length=4000)
    account_id: str = Field("100000", max_length=100)
    conversation_id: Optional[str] = Field(None, max_length=100)
    support_functions: List[str] = Field(default_factory=lambda: [*FUNCTION_MAP])
    product_list: Optional[List[str]] = None
    history: List[BusinessChatMessage] = Field(default_factory=list)
    model: str = "customer-service-agent"


class QualityCheckRequest(BaseModel):
    content: str = Field(..., max_length=8000)
    keywords: Optional[str] = Field(None, max_length=1000)
    account_id: str = Field("100000", max_length=100)
    conversation_id: Optional[str] = Field(None, max_length=100)
    model: str = "customer-service-agent"


class SummaryRequest(BaseModel):
    messages: List[BusinessChatMessage]
    model: str = "customer-service-agent"


class RefundActionRequest(BaseModel):
    account_id: str = Field("100000", max_length=100)


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
):
    if not api_keys:
        return

    if not isinstance(x_api_key, str):
        x_api_key = None
    if not isinstance(authorization, str):
        authorization = None

    token = x_api_key or _bearer_token(authorization)
    if token in api_keys:
        return

    raise HTTPException(
        status_code=401,
        detail={
            "code": "Unauthorized",
            "message": "A valid API key is required.",
        },
    )


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


async def list_products():
    products_dict = get_products()
    return ProductListResponse(
        products=[Product(**v) for v in products_dict.values()],
        total=len(products_dict),
    )


async def demo_page():
    return FileResponse(WEBUI_DIR / "index.html")


async def workbench_page():
    frontend_index = FRONTEND_DIST_DIR / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)
    return FileResponse(WEBUI_DIR / "index.html")


async def conversations(limit: int = 20, offset: int = 0, account_id: Optional[str] = None):
    return list_conversations(limit=limit, offset=offset, account_id=account_id)


async def conversation_detail(
    conversation_id: str,
    account_id: Optional[str] = None,
):
    conversation = get_conversation(conversation_id, account_id=account_id)
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ConversationNotFound",
                "message": f"Conversation not found: {conversation_id}",
            },
        )
    return conversation


async def conversation_tool_calls(
    conversation_id: str,
    account_id: str,
    limit: int = 100,
):
    return {
        "conversation_id": conversation_id,
        "tool_calls": list_tool_calls(
            conversation_id,
            account_id=account_id,
            limit=limit,
        ),
    }


async def quality_reviews(
    account_id: str,
    conversation_id: Optional[str] = None,
    limit: int = 50,
):
    return {
        "reviews": list_quality_reviews(
            account_id=account_id,
            conversation_id=conversation_id,
            limit=limit,
        )
    }


async def faq_candidates(account_id: Optional[str] = None, limit: int = 50):
    return {
        "candidates": list_faq_candidates(account_id=account_id, limit=limit),
    }


async def refund_detail(refund_id: str, account_id: str):
    result = await get_refund_request(account_id, refund_id)
    if not result:
        raise HTTPException(status_code=404, detail="Refund request not found")
    return result


async def approve_refund_request(refund_id: str, payload: RefundActionRequest):
    try:
        return await get_business_service().approve_refund(payload.account_id, refund_id)
    except RefundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def reject_refund_request(refund_id: str, payload: RefundActionRequest):
    try:
        return await get_business_service().reject_refund(payload.account_id, refund_id)
    except RefundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def execute_refund_request(refund_id: str, payload: RefundActionRequest):
    try:
        return await get_business_service().execute_refund(payload.account_id, refund_id)
    except RefundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def health_check():
    return {
        "status": "ok",
        "service": "customer-service-agent",
    }


async def readiness_check():
    checks = {
        "webui": WEBUI_DIR.exists(),
        "conversation_store": True,
    }
    errors = {}

    try:
        init_db()
    except Exception as exc:
        checks["conversation_store"] = False
        errors["conversation_store"] = str(exc)

    if not all(checks.values()):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "errors": errors,
            },
        )

    return {
        "status": "ready",
        "checks": checks,
    }


async def api_products():
    return await list_products()


async def api_chat(chat: BusinessChatRequest):
    metadata = {
        "account_id": chat.account_id,
        "support_functions": chat.support_functions,
        "product_list": chat.product_list or [*get_products()],
    }
    if chat.conversation_id:
        metadata["conversation_id"] = chat.conversation_id

    messages = [
        ArkMessage(role=message.role, content=message.content)
        for message in chat.history
    ]
    messages.append(ArkMessage(role="user", content=chat.message))

    request = ArkChatRequest(
        stream=False,
        model=chat.model,
        metadata=metadata,
        messages=messages,
    )
    response = await _run_non_stream_chat(request)
    return _business_chat_response(response)


async def api_save_faq(faq: FAQRequest):
    if faq.conversation_id:
        conversation = get_conversation(faq.conversation_id, account_id=faq.account_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        history = [
            message for message in conversation.get("messages", [])
            if message.get("role") in {"user", "assistant"}
        ]
        if len(history) >= 2:
            faq.question = next(
                (item["content"] for item in reversed(history[:-1]) if item["role"] == "user"),
                faq.question,
            )
            faq.answer = next(
                (item["content"] for item in reversed(history) if item["role"] == "assistant"),
                faq.answer,
            )
    result = await save_faq(faq)
    save_faq_candidate(
        account_id=faq.account_id,
        conversation_id=faq.conversation_id,
        question=faq.question,
        answer=faq.answer,
        score=faq.score,
    )
    return result


async def api_quality_check(payload: QualityCheckRequest):
    review_content = payload.content
    if payload.conversation_id:
        conversation = get_conversation(payload.conversation_id, account_id=payload.account_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_lines = [
            f"{message['role']}: {message['content']}"
            for message in conversation.get("messages", [])
            if message.get("role") in {"user", "assistant"}
        ]
        if conversation_lines:
            review_content = "\n".join(conversation_lines)

    if payload.conversation_id:
        valid_messages = [
            message for message in review_content.splitlines()
            if message.strip()
        ]
        if not any(line.lower().startswith("user:") for line in valid_messages) or not any(
            line.lower().startswith("assistant:") for line in valid_messages
        ):
            raise HTTPException(
                status_code=400,
                detail="当前会话尚未形成完整的客户提问和客服回复，暂不支持质检。",
            )

    structured_result = inspect_quality_text(review_content, payload.keywords)
    content = (
        f"【客服会话】\n{review_content}\n\n【质检关键词】\n{payload.keywords}"
        if payload.keywords
        else f"【客服会话】\n{review_content}"
    )
    request = ArkChatRequest(
        stream=False,
        model=payload.model,
        messages=[ArkMessage(role="user", content=content)],
    )
    response = await _collect_first_response(quality_inspection_chat, request)
    result_text = _assistant_content(response)
    save_quality_review(
        account_id=payload.account_id,
        conversation_id=payload.conversation_id,
        content=review_content,
        keywords=payload.keywords,
        result=result_text,
        structured_result=structured_result,
    )
    return {
        "result": result_text,
        "structured_result": structured_result,
        "metadata": response.metadata or {},
        "bot_usage": _bot_usage(response),
    }


async def api_summary(payload: SummaryRequest):
    valid_messages = [
        message for message in payload.messages if message.role in {"user", "assistant"}
    ]
    user_count = sum(message.role == "user" for message in valid_messages)
    assistant_count = sum(message.role == "assistant" for message in valid_messages)
    if user_count == 0 or assistant_count == 0 or min(user_count, assistant_count) == 0:
        raise HTTPException(
            status_code=400,
            detail="至少完成一轮客户提问和客服回复后才能生成会话总结。",
        )
    request = ArkChatRequest(
        stream=False,
        model=payload.model,
        messages=[
            ArkMessage(role=message.role, content=message.content)
            for message in valid_messages
        ],
    )
    response = await _collect_first_response(summary_chat, request)
    return {
        "summary": _assistant_content(response),
        "metadata": response.metadata or {},
        "bot_usage": _bot_usage(response),
    }


async def _run_non_stream_chat(request: ArkChatRequest) -> ArkChatResponse:
    return await _collect_first_response(custom_support_chat, request)


async def _collect_first_response(runnable, request: ArkChatRequest) -> ArkChatResponse:
    target = getattr(runnable, "__wrapped__", runnable)
    async for item in target(request):
        if isinstance(item, ArkChatResponse):
            return item
    raise HTTPException(
        status_code=502,
        detail={
            "code": "NoChatResponse",
            "message": "The agent did not return a non-stream chat response.",
        },
    )


def _business_chat_response(response: ArkChatResponse) -> dict:
    metadata = response.metadata or {}
    return {
        "conversation_id": metadata.get("conversation_id"),
        "answer": _assistant_content(response),
        "metadata": metadata,
        "bot_usage": _bot_usage(response),
    }


def _assistant_content(response: ArkChatResponse) -> str:
    if not response.choices:
        return ""
    return response.choices[0].message.content or ""


def _bot_usage(response: ArkChatResponse):
    return response.bot_usage.model_dump(mode="json") if response.bot_usage else None


def _attach_metadata(response, conversation_id: str):
    metadata = getattr(response, "metadata", None) or {}
    metadata["conversation_id"] = conversation_id
    response.metadata = metadata


def _chunk_content(chunk: ArkChatCompletionChunk) -> str:
    if not chunk.choices:
        return ""
    choice = chunk.choices[0]
    delta = getattr(choice, "delta", None)
    if isinstance(delta, dict):
        return delta.get("content") or ""
    return getattr(delta, "content", "") or ""


def _action_hit_count(action_detail: ActionDetail | None) -> int:
    if not action_detail or not action_detail.tool_details:
        return 0
    total = 0
    for detail in action_detail.tool_details:
        output = getattr(detail, "output", None)
        if isinstance(output, list):
            total += len(output)
        elif output:
            total += 1
    return total


async def save_faq(faq: FAQRequest):
    columns_order = ["question", "answer", "score"]
    try:
        rag.save_faq(
            pd.DataFrame(
                [{"question": faq.question, "answer": faq.answer, "score": faq.score}],
                columns=columns_order,
            ),
            faq.account_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SaveFaqError",
                "message": str(exc),
            },
        )
    return {"message": "success"}


def configure_runtime() -> None:
    configure_observability()
    set_resource_type(os.getenv("RESOURCE_TYPE") or "")
    set_resource_id(os.getenv("RESOURCE_ID") or "")
    setup_tracing(endpoint=os.getenv("TRACE_ENDPOINT"), trace_on=False)


def create_server() -> BotServer:
    server: BotServer = BotServer(
        runner=get_runner(custom_support_chat),
        health_check_path="/v1/ping",
        endpoint_config=get_endpoint_config(
            "/api/v3/bots/chat/completions", custom_support_chat
        ),
        clients={
            "ark": (
                AsyncArk,
                {
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3"
                    if language == "zh"
                    else "https://ark.ap-southeast.volces.com/api/v3",
                    "region": "cn-beijing" if language == "zh" else "ap-southeast-1",
                },
            ),
        },
    )
    register_routes(server)
    return server


def register_routes(server: BotServer) -> BotServer:
    @server.app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        started = monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                "http.request",
                level="error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                ok=False,
                duration_ms=elapsed_ms(started),
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise
        response.headers["X-Request-ID"] = request_id
        log_event(
            "http.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            ok=response.status_code < 500,
            duration_ms=elapsed_ms(started),
        )
        return response

    business_api_dependencies = [Depends(require_api_key)]
    server.app.add_api_route(
        "/api/v3/bots/chat/completions",
        get_handler(custom_support_chat),
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route("/", demo_page, methods=["GET"])
    server.app.add_api_route("/demo", demo_page, methods=["GET"])
    server.app.add_api_route("/workbench", workbench_page, methods=["GET"])
    server.app.add_api_route("/health", health_check, methods=["GET"])
    server.app.add_api_route("/ready", readiness_check, methods=["GET"])
    server.app.mount("/static", StaticFiles(directory=WEBUI_DIR), name="webui")
    if FRONTEND_ASSETS_DIR.exists():
        server.app.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_ASSETS_DIR),
            name="frontend-assets",
        )
    server.app.add_api_route(
        "/api/v3/bots/chat/completions/products",
        list_products,
        methods=["GET"],
        response_model=ProductListResponse,
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/products",
        api_products,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/chat",
        api_chat,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/faqs",
        api_save_faq,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/quality-check",
        api_quality_check,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/summary",
        api_summary,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/conversations",
        conversations,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/conversations/{conversation_id}",
        conversation_detail,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/conversations/{conversation_id}/tool-calls",
        conversation_tool_calls,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/quality-reviews",
        quality_reviews,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/faq-candidates",
        faq_candidates,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/refunds/{refund_id}",
        refund_detail,
        methods=["GET"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/refunds/{refund_id}/approve",
        approve_refund_request,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/refunds/{refund_id}/reject",
        reject_refund_request,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/refunds/{refund_id}/execute",
        execute_refund_request,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/v3/bots/chat/completions/save_faq",
        save_faq,
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/v3/bots/chat/completions/summary",
        get_handler(summary_chat),
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/v3/bots/chat/completions/quality_inspection",
        get_handler(quality_inspection_chat),
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    server.app.add_api_route(
        "/api/v3/bots/chat/completions/next_question",
        get_handler(next_question_chat),
        methods=["POST"],
        dependencies=business_api_dependencies,
    )
    return server


def run_server() -> None:
    configure_runtime()
    migrate_database()
    server = create_server()
    port = os.getenv("_FAAS_RUNTIME_PORT")
    server.run(app=server.app, port=int(port) if port else 8080, host="0.0.0.0")


if __name__ == "__main__":
    run_server()
