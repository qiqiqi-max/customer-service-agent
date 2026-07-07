import json
from typing import Any, Awaitable, Callable

from arkitect.types.llm.model import ToolDetail
from business_services import get_business_service
from observability import elapsed_ms, log_event, monotonic

ToolExecutor = Callable[[dict], Awaitable[Any]]


def build_openai_tools(functions: list[str] | None) -> list[dict]:
    enabled = set(functions or [])
    if not enabled:
        enabled = {"order_check", "package_track", "order_refund"}

    tools = []
    if "order_check" in enabled or "package_track" in enabled:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "order_check",
                    "description": (
                        "Query customer order details. Use this when the customer asks "
                        "about previous purchases, order IDs, order status, or a product order."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID. Leave empty when unknown.",
                            },
                            "product": {
                                "type": "string",
                                "description": "Product name. Leave empty to query all orders.",
                            },
                        },
                    },
                },
            }
        )

    if "package_track" in enabled:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "pack_track",
                    "description": (
                        "Query shipping or delivery tracking information. Use this when "
                        "the customer asks where a package is or when it will arrive."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID. Leave empty when unknown.",
                            },
                            "tracking_number": {
                                "type": "string",
                                "description": "Tracking number. Leave empty when unknown.",
                            },
                        },
                    },
                },
            }
        )

    if "order_refund" in enabled:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "order_refund",
                    "description": (
                        "Process a refund request. Use only after the customer clearly "
                        "requests a refund or return and an order can be identified."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Order ID. Required for real refund processing.",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Refund reason summarized from the conversation.",
                            },
                        },
                    },
                    "required": ["order_id"],
                },
            }
        )

    return tools


def build_tool_executor(account_id: str) -> ToolExecutor:
    async def execute(tool_call: dict) -> Any:
        name = _tool_name(tool_call)
        arguments = _tool_arguments(tool_call)
        started = monotonic()
        try:
            if name == "order_check":
                output = await _order_check(account_id, arguments)
            elif name == "pack_track":
                output = await _pack_track(account_id, arguments)
            elif name == "order_refund":
                output = await _order_refund(account_id, arguments)
            else:
                output = {"error": f"Unsupported tool: {name}"}
        except Exception as exc:
            log_event(
                "tool.execute",
                level="error",
                ok=False,
                tool=name,
                account_id=account_id,
                duration_ms=elapsed_ms(started),
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise
        log_event(
            "tool.execute",
            ok=True,
            tool=name,
            account_id=account_id,
            duration_ms=elapsed_ms(started),
            output_type=type(output).__name__,
        )
        return output

    return execute


def tool_detail_from_call(tool_call: dict, output: Any) -> ToolDetail:
    return ToolDetail(
        name=_tool_name(tool_call),
        input=_tool_arguments(tool_call),
        output=output,
    )


def tool_result_message(tool_call: dict, output: Any) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call.get("id", ""),
        "name": _tool_name(tool_call),
        "content": json.dumps(output, ensure_ascii=False),
    }


def _tool_name(tool_call: dict) -> str:
    return ((tool_call.get("function") or {}).get("name") or "").strip()


def _tool_arguments(tool_call: dict) -> dict:
    raw = (tool_call.get("function") or {}).get("arguments") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def _order_check(account_id: str, arguments: dict) -> Any:
    service = get_business_service()
    order_id = str(arguments.get("order_id") or "")
    product = str(arguments.get("product") or "")
    if product:
        return await service.get_orders_by_product(account_id, product)
    if order_id:
        return await service.get_order(account_id, order_id)
    return await service.get_all_orders(account_id)


async def _pack_track(account_id: str, arguments: dict) -> Any:
    service = get_business_service()
    order_id = str(arguments.get("order_id") or "")
    tracking_number = str(arguments.get("tracking_number") or "")
    return await service.get_tracking(account_id, order_id, tracking_number)


async def _order_refund(account_id: str, arguments: dict) -> Any:
    service = get_business_service()
    order_id = str(arguments.get("order_id") or "")
    reason = str(arguments.get("reason") or "")
    return await service.refund_order(account_id, order_id, reason)
