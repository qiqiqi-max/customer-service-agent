# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates

from typing import Callable

from business_services import get_business_service
from pydantic import Field


def get_order_check_fn(account_id: str) -> Callable:
    async def order_check(
        order_id: str = Field(description="Order ID", default=""),
        product: str = Field(description="Product name", default=""),
    ):
        """
        Use this function to query order details. Returns detailed order information.
        If both order ID and product name are empty, returns all order information.
        """
        service = get_business_service()
        if product:
            return await service.get_orders_by_product(account_id, product)

        if order_id:
            return await service.get_order(account_id, order_id)

        return await service.get_all_orders(account_id)

    return order_check
