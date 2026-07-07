import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Iterable
from uuid import uuid4

import config
from agent_tools import tool_detail_from_call, tool_result_message
from arkitect.types.llm.model import ActionDetail, ArkChatResponse, ArkMessage, BotUsage
from observability import elapsed_ms, log_event, monotonic
from volcenginesdkarkruntime.types.chat.chat_completion import Choice


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
    if tool_details:
        response.bot_usage = BotUsage(
            action_details=[
                ActionDetail(
                    name="tool_calling",
                    count=len(tool_details),
                    tool_details=tool_details,
                )
            ]
        )
    log_event(
        "llm.openai_compatible_complete",
        provider=config.llm_provider,
        model=selected_model,
        duration_ms=elapsed_ms(total_started),
        tool_call_count=len(tool_details),
        output_chars=len(content),
    )
    return response


def _post_chat_completion(
    messages: list[ArkMessage | dict],
    model: str,
    temperature: float,
    settings: dict,
    tools: list[dict] | None = None,
) -> dict:
    if not settings["api_key"]:
        raise ValueError(
            f"{settings['api_key_name']} is required when LLM_PROVIDER={config.llm_provider}."
        )

    body = {
        "model": model,
        "messages": [_to_openai_message(message) for message in messages],
        "temperature": temperature,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        _chat_completions_url(settings["base_url"]),
        data=data,
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{settings['label']} API returned HTTP {exc.code}: {detail}"
        ) from exc


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
                finish_reason=(
                    (raw_payload.get("choices") or [{}])[0].get("finish_reason")
                    or "stop"
                ),
                message={"role": "assistant", "content": content},
            )
        ],
        metadata={"provider": config.llm_provider},
    )
