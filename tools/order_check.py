# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates

from typing import Callable

from data import orders
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
        if product:
            return await orders.get_orders_by_product(account_id, product)

        if order_id:
            return await orders.get_order(account_id, order_id)

        return await orders.get_all_orders(account_id)

    return order_check
