import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import AsyncIterator, Iterable
from uuid import uuid4

import config
from agent_tools import tool_detail_from_call, tool_result_message
from arkitect.types.llm.model import (
    ActionDetail,
    ArkChatCompletionChunk,
    ArkChatResponse,
    ArkMessage,
    BotUsage,
)
from observability import elapsed_ms, log_event, monotonic
from volcenginesdkarkruntime.types.chat.chat_completion import Choice
from volcenginesdkarkruntime.types.chat.chat_completion_chunk import Choice as ChunkChoice


OPENAI_COMPATIBLE_PROVIDERS = {"deepseek", "zhipu", "openai_compatible"}


def is_openai_compatible_provider() -> bool:
    return config.llm_provider in OPENAI_COMPATIBLE_PROVIDERS


async def run_openai_compatible_chat(
    messages: Iterable[ArkMessage | dict],
    model: str | None = None,
    temperature: float = 0.3,
    tools: list[dict] | None = None,
    tool_executor=None,
    max_tool_rounds: int = 3,
) -> ArkChatResponse:
    settings = _provider_settings()
    provider_messages = list(messages)
    tool_details = []
    selected_model = model or settings["model"]
    total_started = monotonic()

    for round_index in range(max_tool_rounds + 1):
        round_started = monotonic()
        try:
            payload = await asyncio.to_thread(
                _post_chat_completion,
                provider_messages,
                selected_model,
                temperature,
                settings,
                tools,
            )
        except Exception as exc:
            log_event(
                "llm.openai_compatible_round",
                level="error",
                ok=False,
                provider=config.llm_provider,
                model=selected_model,
                round=round_index,
                duration_ms=elapsed_ms(round_started),
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise
        tool_calls = _extract_tool_calls(payload)
        log_event(
            "llm.openai_compatible_round",
            ok=True,
            provider=config.llm_provider,
            model=selected_model,
            round=round_index,
            duration_ms=elapsed_ms(round_started),
            tool_call_count=len(tool_calls),
        )
        if not tool_calls or not tools or not tool_executor:
            break

        provider_messages.append(_assistant_tool_call_message(payload))
        for tool_call in tool_calls:
            output = await tool_executor(tool_call)
            tool_details.append(tool_detail_from_call(tool_call, output))
            provider_messages.append(tool_result_message(tool_call, output))

    content = _extract_content(payload)
    response = _make_response(content, payload)
    response.bot_usage = _tool_usage(tool_details)
    log_event(
        "llm.openai_compatible_complete",
        provider=config.llm_provider,
        model=selected_model,
        duration_ms=elapsed_ms(total_started),
        tool_call_count=len(tool_details),
        output_chars=len(content),
    )
    return response


async def stream_openai_compatible_chat(
    messages: Iterable[ArkMessage | dict],
    model: str | None = None,
    temperature: float = 0.3,
    tools: list[dict] | None = None,
    tool_executor=None,
    max_tool_rounds: int = 3,
) -> AsyncIterator[ArkChatCompletionChunk | ArkChatResponse]:
    """Stream content chunks as the provider produces them.

    Tool-call rounds are resolved between streamed rounds. The last item is a full
    ArkChatResponse whose content is everything streamed, with tool usage attached.
    """
    settings = _provider_settings()
    provider_messages = list(messages)
    tool_details = []
    selected_model = model or settings["model"]
    total_started = monotonic()
    stream_id = ""
    created = int(time.time())
    streamed = []
    finish_reason = "stop"

    for round_index in range(max_tool_rounds + 1):
        round_started = monotonic()
        round_content = []
        pending_calls: dict[int, dict] = {}
        response = await asyncio.to_thread(
            _open_chat_stream,
            provider_messages,
            selected_model,
            temperature,
            settings,
            tools,
        )
        try:
            async for event in _iter_stream_events(response):
                stream_id = stream_id or event.get("id") or f"{config.llm_provider}-{uuid4().hex}"
                created = event.get("created") or created
                selected_model = event.get("model") or selected_model
                choices = event.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                _merge_tool_call_deltas(pending_calls, delta.get("tool_calls") or [])
                if choice.get("finish_reason"):
                    finish_reason = _normalize_finish_reason(choice["finish_reason"])
                text = delta.get("content") or ""
                if text:
                    round_content.append(text)
                    streamed.append(text)
                    yield _make_chunk(stream_id, created, selected_model, text)
        finally:
            response.close()

        tool_calls = [pending_calls[index] for index in sorted(pending_calls)]
        log_event(
            "llm.openai_compatible_stream_round",
            ok=True,
            provider=config.llm_provider,
            model=selected_model,
            round=round_index,
            duration_ms=elapsed_ms(round_started),
            tool_call_count=len(tool_calls),
        )
        if not tool_calls or not tools or not tool_executor:
            break

        provider_messages.append(
            {"role": "assistant", "content": "".join(round_content), "tool_calls": tool_calls}
        )
        for tool_call in tool_calls:
            output = await tool_executor(tool_call)
            tool_details.append(tool_detail_from_call(tool_call, output))
            provider_messages.append(tool_result_message(tool_call, output))

    content = "".join(streamed)
    response = _make_response(
        content,
        {
            "id": stream_id or f"{config.llm_provider}-{uuid4().hex}",
            "created": created,
            "model": selected_model,
            "choices": [{"finish_reason": finish_reason}],
        },
    )
    response.bot_usage = _tool_usage(tool_details)
    log_event(
        "llm.openai_compatible_stream_complete",
        provider=config.llm_provider,
        model=selected_model,
        duration_ms=elapsed_ms(total_started),
        tool_call_count=len(tool_details),
        output_chars=len(content),
    )
    yield response


def _make_chunk(
    chunk_id: str,
    created: int,
    model: str,
    content: str,
    finish_reason: str | None = None,
) -> ArkChatCompletionChunk:
    return ArkChatCompletionChunk(
        id=chunk_id,
        created=created,
        model=model,
        object="chat.completion.chunk",
        choices=[
            ChunkChoice(
                index=0,
                delta={"role": "assistant", "content": content},
                finish_reason=finish_reason,
            )
        ],
    )


_FINISH_REASONS = {"stop", "length", "tool_calls", "content_filter", "function_call"}


def _normalize_finish_reason(value: str | None) -> str:
    # Zhipu reports "sensitive" for filtered output; Choice only accepts the OpenAI set.
    if value == "sensitive":
        return "content_filter"
    return value if value in _FINISH_REASONS else "stop"


def _build_chat_request(
    messages: list[ArkMessage | dict],
    model: str,
    temperature: float,
    settings: dict,
    tools: list[dict] | None,
    stream: bool,
) -> urllib.request.Request:
    if not settings["api_key"]:
        raise ValueError(
            f"{settings['api_key_name']} is required when LLM_PROVIDER={config.llm_provider}."
        )

    body = {
        "model": model,
        "messages": [_to_openai_message(message) for message in messages],
        "temperature": temperature,
        "stream": stream,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(
        _chat_completions_url(settings["base_url"]),
        data=data,
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "text/event-stream" if stream else "application/json",
        },
        method="POST",
    )


def _post_chat_completion(
    messages: list[ArkMessage | dict],
    model: str,
    temperature: float,
    settings: dict,
    tools: list[dict] | None = None,
) -> dict:
    request = _build_chat_request(messages, model, temperature, settings, tools, stream=False)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise _http_error(settings, exc) from exc


def _open_chat_stream(
    messages: list[ArkMessage | dict],
    model: str,
    temperature: float,
    settings: dict,
    tools: list[dict] | None = None,
):
    request = _build_chat_request(messages, model, temperature, settings, tools, stream=True)
    try:
        return urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as exc:
        raise _http_error(settings, exc) from exc


def _http_error(settings: dict, exc: urllib.error.HTTPError) -> RuntimeError:
    detail = exc.read().decode("utf-8", errors="replace")
    return RuntimeError(f"{settings['label']} API returned HTTP {exc.code}: {detail}")


async def _iter_stream_events(response) -> AsyncIterator[dict]:
    """Yield parsed SSE `data:` payloads until `[DONE]` or end of body.

    Each line is read in a worker thread so a slow provider does not block the event loop.
    """
    while True:
        raw = await asyncio.to_thread(response.readline)
        if not raw:
            return
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            return
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def _merge_tool_call_deltas(pending: dict[int, dict], deltas: list) -> None:
    for position, delta in enumerate(deltas):
        if not isinstance(delta, dict):
            continue
        index = delta.get("index", position)
        call = pending.setdefault(
            index,
            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
        )
        if delta.get("id"):
            call["id"] = delta["id"]
        if delta.get("type"):
            call["type"] = delta["type"]
        function = delta.get("function") or {}
        if function.get("name"):
            call["function"]["name"] = function["name"]
        arguments = function.get("arguments")
        if isinstance(arguments, dict):
            call["function"]["arguments"] = json.dumps(arguments, ensure_ascii=False)
        elif arguments:
            call["function"]["arguments"] += arguments


def _tool_usage(tool_details: list) -> BotUsage | None:
    if not tool_details:
        return None
    return BotUsage(
        action_details=[
            ActionDetail(
                name="tool_calling",
                count=len(tool_details),
                tool_details=tool_details,
            )
        ]
    )


def _provider_settings() -> dict:
    if config.llm_provider == "zhipu":
        return {
            "label": "Zhipu",
            "api_key": config.zhipu_api_key,
            "api_key_name": "ZHIPU_API_KEY",
            "base_url": config.zhipu_base_url,
            "model": config.zhipu_model,
        }
    return {
        "label": "DeepSeek",
        "api_key": config.deepseek_api_key,
        "api_key_name": "DEEPSEEK_API_KEY",
        "base_url": config.deepseek_base_url,
        "model": config.deepseek_model,
    }


def _to_openai_message(message: ArkMessage | dict) -> dict:
    if isinstance(message, dict):
        return message
    content = message.content
    if isinstance(content, list):
        content = json.dumps(content, ensure_ascii=False)
    return {
        "role": message.role,
        "content": content or "",
    }


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _extract_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


def _extract_tool_calls(payload: dict) -> list[dict]:
    choices = payload.get("choices") or []
    if not choices:
        return []
    message = (choices[0].get("message") or {})
    tool_calls = message.get("tool_calls") or []
    return tool_calls if isinstance(tool_calls, list) else []


def _assistant_tool_call_message(payload: dict) -> dict:
    choices = payload.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    return {
        "role": "assistant",
        "content": message.get("content") or "",
        "tool_calls": message.get("tool_calls") or [],
    }


def _make_response(content: str, raw_payload: dict) -> ArkChatResponse:
    return ArkChatResponse(
        id=raw_payload.get("id") or f"deepseek-{uuid4().hex}",
        created=raw_payload.get("created") or int(time.time()),
        model=raw_payload.get("model") or config.deepseek_model,
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason=_normalize_finish_reason(
                    (raw_payload.get("choices") or [{}])[0].get("finish_reason")
                ),
                message={"role": "assistant", "content": content},
            )
        ],
        metadata={"provider": config.llm_provider},
    )
