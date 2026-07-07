import time
from pathlib import Path
from typing import AsyncIterable, List
from uuid import uuid4

from arkitect.types.llm.model import (
    ActionDetail,
    ArkChatCompletionChunk,
    ArkChatRequest,
    ArkChatResponse,
    BotUsage,
    ToolDetail,
)
from business_services import get_business_service
from config import language
from data.product import get_products
from volcenginesdkarkruntime.types.chat.chat_completion import Choice
from volcenginesdkarkruntime.types.chat.chat_completion_chunk import Choice as ChunkChoice


MOCK_FAQ_DIR = Path(__file__).resolve().parent / "data" / "mock_faq"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _last_user_text(request: ArkChatRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user" and message.content:
            return str(message.content)
    return ""


def _make_response(text: str, bot_usage: BotUsage | None = None) -> ArkChatResponse:
    return ArkChatResponse(
        id=f"mock-{uuid4().hex}",
        created=int(time.time()),
        model="mock-customer-service-agent",
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message={"role": "assistant", "content": text},
            )
        ],
        bot_usage=bot_usage,
        metadata={"mock": True},
    )


async def make_mock_chat_response(request: ArkChatRequest) -> ArkChatResponse:
    text = _last_user_text(request)
    metadata = request.metadata or {}
    account_id = metadata.get("account_id") or "100000"
    selected_products = metadata.get("product_list") or list(get_products())
    selected_functions = set(metadata.get("support_functions") or [])
    service = get_business_service()

    tool_details: List[ToolDetail] = []
    lowered = text.lower()

    if _should_mock_order(selected_functions, text, lowered):
        order_result = await service.get_all_orders(account_id)
        tool_details.append(
            ToolDetail(
                name="order_check",
                input={"account_id": account_id},
                output=order_result,
                created_at=_now_ms(),
                completed_at=_now_ms(),
            )
        )
        if language == "zh":
            answer = (
                f"亲，已查到账号 {account_id} 下共有 {len(order_result)} 笔订单。"
                "右侧可以查看订单状态和商品信息。"
            )
        else:
            answer = (
                f"I found {len(order_result)} orders for account {account_id}. "
                "You can review the order details on the right."
            )
    elif _should_mock_logistics(selected_functions, text, lowered):
        order_list = await service.get_all_orders(account_id)
        shipped = next(
            (item for item in order_list if item.get("tracking_number")),
            None,
        )
        tracking_result = (
            await service.get_tracking(
                account_id,
                tracking_number=shipped["tracking_number"],
            )
            if shipped
            else {}
        )
        tool_details.append(
            ToolDetail(
                name="pack_track",
                input={"account_id": account_id, "order": shipped},
                output=tracking_result,
                created_at=_now_ms(),
                completed_at=_now_ms(),
            )
        )
        if language == "zh":
            answer = "亲，已帮您查询物流，最新配送节点已同步到右侧结果面板。"
        else:
            answer = "I checked the shipment. The latest tracking update is shown on the right."
    elif _should_mock_refund(selected_functions, text, lowered):
        order_list = await service.get_all_orders(account_id)
        target = order_list[0] if order_list else None
        if target:
            refund_message = await service.refund_order(
                account_id,
                target["order_id"],
                "mock refund request",
            )
            refund_result = {
                "message": refund_message,
                "order": await service.get_order(account_id, target["order_id"]),
            }
        else:
            refund_result = "Order does not exist"
        tool_details.append(
            ToolDetail(
                name="order_refund",
                input={"account_id": account_id, "reason": text},
                output=refund_result,
                created_at=_now_ms(),
                completed_at=_now_ms(),
            )
        )
        answer = (
            "亲，已为您模拟发起退款处理，退款状态可在右侧查看。"
            if language == "zh"
            else "I simulated a refund request for you. The status is shown on the right."
        )
    else:
        product_names = [str(item) for item in selected_products[:3]]
        product_output = [
            get_products()[name]
            for name in product_names
            if name in get_products()
        ]
        tool_details.append(
            ToolDetail(
                name="retrieval",
                input=text,
                output=product_output,
                created_at=_now_ms(),
                completed_at=_now_ms(),
            )
        )
        if language == "zh":
            names = "、".join(product_names) if product_names else "当前货架商品"
            answer = (
                f"亲，可以优先看看{names}。我会根据您的用途、预算和安装场景，"
                "帮您筛选更合适的商品。"
            )
        else:
            names = ", ".join(product_names) if product_names else "the current shelf"
            answer = (
                f"I recommend starting with {names}. I can narrow it down by budget, "
                "use case, and style preference."
            )

    bot_usage = BotUsage(
        action_details=[
            ActionDetail(
                name="mock_support",
                count=len(tool_details),
                tool_details=tool_details,
            )
        ]
    )
    return _make_response(answer, bot_usage)


async def stream_mock_response(
    response: ArkChatResponse,
) -> AsyncIterable[ArkChatCompletionChunk]:
    content = response.choices[0].message.content or ""
    chunk_id = response.id
    for piece in _split_for_stream(content):
        yield ArkChatCompletionChunk(
            id=chunk_id,
            created=response.created,
            model=response.model,
            object="chat.completion.chunk",
            choices=[
                ChunkChoice(
                    index=0,
                    delta={"role": "assistant", "content": piece},
                    finish_reason=None,
                )
            ],
        )
    yield ArkChatCompletionChunk(
        id=chunk_id,
        created=response.created,
        model=response.model,
        object="chat.completion.chunk",
        choices=[
            ChunkChoice(
                index=0,
                delta={"role": "assistant", "content": ""},
                finish_reason="stop",
            )
        ],
        bot_usage=response.bot_usage,
        metadata=response.metadata,
    )


def make_mock_summary_response(request: ArkChatRequest) -> ArkChatResponse:
    transcript = _merge_request_text(request)
    if language == "zh":
        text = (
            "- 主要诉求：用户正在咨询商品、订单或售后相关问题。\n"
            "- 解决方案：客服已基于当前上下文给出处理建议，质检风险 0。\n"
            "- 结果：本地 mock 模式已生成会话总结，可用于接口联调。"
        )
    else:
        text = (
            "- Main request: The customer is asking about product, order, or support issues.\n"
            "- Solution: The agent provided a context-aware response. Quality risk: 0.\n"
            "- Result: Mock mode generated a summary for integration testing."
        )
    return _make_response(text, _mock_utility_usage("summary", transcript, text))


def make_mock_next_question_response(request: ArkChatRequest) -> ArkChatResponse:
    if language == "zh":
        text = "这款商品适合哪些车型？\n现在下单多久可以发货？\n如果不合适支持退货吗？"
    else:
        text = "What occasions is this item suitable for?\nHow long does shipping take?\nCan I return it if it does not fit?"
    return _make_response(text, _mock_utility_usage("next_question", _merge_request_text(request), text))


def make_mock_quality_response(request: ArkChatRequest) -> ArkChatResponse:
    transcript = _merge_request_text(request)
    risky = any(word in transcript for word in ["绝对", "最低价", "保证", "全网"])
    if language == "zh":
        text = (
            "话术判断：存在风险\n问题定位：绝对化或承诺类表达\n改进建议：改为更克制、可验证的表述。"
            if risky
            else "话术判断：未发现明显风险\n问题定位：无\n改进建议：保持礼貌、准确和可验证表达。"
        )
    else:
        text = (
            "Script judgment: Risk found\nIssue: Absolute or guarantee-style wording\nSuggestion: Use verifiable and restrained wording."
            if risky
            else "Script judgment: No obvious risk found\nIssue: None\nSuggestion: Keep replies polite, accurate, and verifiable."
        )
    return _make_response(text, _mock_utility_usage("quality_inspection", transcript, text))


def _mock_utility_usage(name: str, input_text: str, output: str) -> BotUsage:
    return BotUsage(
        action_details=[
            ActionDetail(
                name="mock_utility",
                count=1,
                tool_details=[
                    ToolDetail(
                        name=name,
                        input=input_text,
                        output=output,
                        created_at=_now_ms(),
                        completed_at=_now_ms(),
                    )
                ],
            )
        ]
    )


def _merge_request_text(request: ArkChatRequest) -> str:
    return "\n".join(
        f"{message.role}: {message.content}"
        for message in request.messages
        if message.content
    )


def _split_for_stream(text: str) -> List[str]:
    if not text:
        return [""]
    size = max(1, len(text) // 3)
    return [text[index : index + size] for index in range(0, len(text), size)]


def _mentions_order(text: str, lowered: str) -> bool:
    return "订单" in text or "买过" in text or "order" in lowered or "purchased" in lowered


def _mentions_logistics(text: str, lowered: str) -> bool:
    return "物流" in text or "快递" in text or "送到" in text or "shipping" in lowered or "delivery" in lowered


def _mentions_refund(text: str, lowered: str) -> bool:
    return "退款" in text or "退货" in text or "refund" in lowered or "return" in lowered


def _should_mock_order(functions: set, text: str, lowered: str) -> bool:
    return _only_enabled(functions, "order_check") or (
        _mentions_order(text, lowered) and (not functions or "order_check" in functions)
    )


def _should_mock_logistics(functions: set, text: str, lowered: str) -> bool:
    return _only_enabled(functions, "package_track") or (
        _mentions_logistics(text, lowered)
        and (not functions or "package_track" in functions)
    )


def _should_mock_refund(functions: set, text: str, lowered: str) -> bool:
    return _only_enabled(functions, "order_refund") or (
        _mentions_refund(text, lowered) and (not functions or "order_refund" in functions)
    )


def _only_enabled(functions: set, function_name: str) -> bool:
    return bool(functions) and functions <= {function_name, "order_check"}
