import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

import config
from data import orders, tracking
from data.orders import OrderStatus
from data.refunds import (
    approve_refund,
    create_refund_request,
    execute_refund,
    reject_refund,
)
from observability import elapsed_ms, log_event, monotonic


class BusinessServiceError(Exception):
    pass


class BusinessDataService(ABC):
    @abstractmethod
    async def get_order(self, account_id: str, order_id: str) -> Any:
        pass

    @abstractmethod
    async def get_orders_by_product(self, account_id: str, product: str) -> Any:
        pass

    @abstractmethod
    async def get_all_orders(self, account_id: str) -> Any:
        pass

    @abstractmethod
    async def get_tracking(
        self,
        account_id: str,
        order_id: str = "",
        tracking_number: str = "",
    ) -> Any:
        pass

    @abstractmethod
    async def refund_order(self, account_id: str, order_id: str, reason: str = "") -> Any:
        pass

    @abstractmethod
    async def approve_refund(self, account_id: str, refund_id: str) -> Any:
        pass

    @abstractmethod
    async def execute_refund(self, account_id: str, refund_id: str) -> Any:
        pass

    @abstractmethod
    async def reject_refund(self, account_id: str, refund_id: str) -> Any:
        pass


class LocalDatabaseBusinessDataService(BusinessDataService):
    def __init__(self, provider_name: str = "mysql"):
        self.provider_name = provider_name

    async def get_order(self, account_id: str, order_id: str) -> Any:
        started = monotonic()
        result = await orders.get_order(account_id, order_id)
        _log_business_call("get_order", self.provider_name, account_id, started, result)
        return result

    async def get_orders_by_product(self, account_id: str, product: str) -> Any:
        started = monotonic()
        result = await orders.get_orders_by_product(account_id, product)
        _log_business_call(
            "get_orders_by_product",
            self.provider_name,
            account_id,
            started,
            result,
        )
        return result

    async def get_all_orders(self, account_id: str) -> Any:
        started = monotonic()
        result = await orders.get_all_orders(account_id)
        _log_business_call("get_all_orders", self.provider_name, account_id, started, result)
        return result

    async def get_tracking(
        self,
        account_id: str,
        order_id: str = "",
        tracking_number: str = "",
    ) -> Any:
        started = monotonic()
        if order_id:
            order = await orders.get_order(account_id, order_id)
            if not order:
                result = "Order information not found"
                _log_business_call("get_tracking", self.provider_name, account_id, started, result)
                return result
            if order["status"] == OrderStatus.REFUNDED.value:
                result = "Order has been refunded, no shipping information available"
                _log_business_call("get_tracking", self.provider_name, account_id, started, result)
                return result
            if order["status"] == OrderStatus.PENDING.value:
                result = "Order has not been shipped yet, no tracking information available"
                _log_business_call("get_tracking", self.provider_name, account_id, started, result)
                return result
            tracking_number = order.get("tracking_number") or ""

        if not tracking_number:
            result = "Order has no tracking number"
            _log_business_call("get_tracking", self.provider_name, account_id, started, result)
            return result

        result = tracking.get_tracking_info(tracking_number)
        _log_business_call("get_tracking", self.provider_name, account_id, started, result)
        return result

    async def refund_order(self, account_id: str, order_id: str, reason: str = "") -> Any:
        started = monotonic()
        result = await create_refund_request(account_id, order_id, reason)
        _log_business_call("refund_order", self.provider_name, account_id, started, result)
        return result

    async def approve_refund(self, account_id: str, refund_id: str) -> Any:
        return await approve_refund(account_id, refund_id)

    async def execute_refund(self, account_id: str, refund_id: str) -> Any:
        return await execute_refund(account_id, refund_id)

    async def reject_refund(self, account_id: str, refund_id: str) -> Any:
        return await reject_refund(account_id, refund_id)


class MockBusinessDataService(LocalDatabaseBusinessDataService):
    def __init__(self):
        super().__init__("mock")


class HttpBusinessDataService(BusinessDataService):
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 8,
    ):
        if not base_url:
            raise BusinessServiceError(
                "BUSINESS_API_BASE_URL is required when BUSINESS_DATA_PROVIDER=http."
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def get_order(self, account_id: str, order_id: str) -> Any:
        return await self._request(
            "GET",
            f"/orders/{urllib.parse.quote(order_id)}",
            query={"account_id": account_id},
        )

    async def get_orders_by_product(self, account_id: str, product: str) -> Any:
        return await self._request(
            "GET",
            "/orders",
            query={"account_id": account_id, "product": product},
        )

    async def get_all_orders(self, account_id: str) -> Any:
        return await self._request(
            "GET",
            "/orders",
            query={"account_id": account_id},
        )

    async def get_tracking(
        self,
        account_id: str,
        order_id: str = "",
        tracking_number: str = "",
    ) -> Any:
        return await self._request(
            "GET",
            "/tracking",
            query={
                "account_id": account_id,
                "order_id": order_id,
                "tracking_number": tracking_number,
            },
        )

    async def refund_order(self, account_id: str, order_id: str, reason: str = "") -> Any:
        return await self._request(
            "POST",
            "/refunds",
            payload={
                "account_id": account_id,
                "order_id": order_id,
                "reason": reason,
            },
        )

    async def approve_refund(self, account_id: str, refund_id: str) -> Any:
        return await self._request(
            "POST",
            f"/refunds/{refund_id}/approve",
            query={"account_id": account_id},
        )

    async def execute_refund(self, account_id: str, refund_id: str) -> Any:
        return await self._request(
            "POST",
            f"/refunds/{refund_id}/execute",
            query={"account_id": account_id},
        )

    async def reject_refund(self, account_id: str, refund_id: str) -> Any:
        return await self._request(
            "POST",
            f"/refunds/{refund_id}/reject",
            query={"account_id": account_id},
        )

    async def _request(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        started = monotonic()
        try:
            result = await asyncio.to_thread(
                self._sync_request,
                method,
                path,
                query,
                payload,
            )
        except Exception as exc:
            log_event(
                "business_service.call",
                level="error",
                ok=False,
                provider="http",
                operation=f"{method} {path}",
                duration_ms=elapsed_ms(started),
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
            raise
        _log_business_call(f"{method} {path}", "http", "", started, result)
        return result

    def _sync_request(
        self,
        method: str,
        path: str,
        query: dict[str, str] | None,
        payload: dict[str, Any] | None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        clean_query = {
            key: value
            for key, value in (query or {}).items()
            if value is not None and str(value) != ""
        }
        if clean_query:
            url = f"{url}?{urllib.parse.urlencode(clean_query)}"

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BusinessServiceError(
                f"Business API request failed with {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise BusinessServiceError(f"Business API request failed: {exc}") from exc

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BusinessServiceError("Business API returned non-JSON response.") from exc


_service: BusinessDataService | None = None
_service_key: tuple[str, str, str, float] | None = None


def get_business_service() -> BusinessDataService:
    global _service, _service_key

    provider = getattr(config, "business_data_provider", "mock")
    base_url = getattr(config, "business_api_base_url", "")
    api_key = getattr(config, "business_api_key", "")
    timeout = getattr(config, "business_api_timeout", 8)
    service_key = (provider, base_url, api_key, timeout)
    if _service and _service_key == service_key:
        return _service

    if provider == "http":
        _service = HttpBusinessDataService(base_url, api_key, timeout)
    elif provider in {"mysql", "local", "database"}:
        _service = LocalDatabaseBusinessDataService(provider_name=provider)
    elif provider == "mock":
        _service = MockBusinessDataService()
    else:
        raise BusinessServiceError(
            f"Unsupported BUSINESS_DATA_PROVIDER={provider!r}. "
            "Use mysql, local, mock, or http."
        )
    _service_key = service_key
    return _service


def reset_business_service() -> None:
    global _service, _service_key
    _service = None
    _service_key = None


def _log_business_call(
    operation: str,
    provider: str,
    account_id: str,
    started: float,
    result: Any,
) -> None:
    log_event(
        "business_service.call",
        ok=True,
        provider=provider,
        operation=operation,
        account_id=account_id,
        duration_ms=elapsed_ms(started),
        result_type=type(result).__name__,
        result_count=_result_count(result),
    )


def _result_count(result: Any) -> int:
    if isinstance(result, list):
        return len(result)
    if isinstance(result, dict):
        if isinstance(result.get("items"), list):
            return len(result["items"])
        if isinstance(result.get("orders"), list):
            return len(result["orders"])
        if isinstance(result.get("events"), list):
            return len(result["events"])
        return 1
    if result:
        return 1
    return 0
