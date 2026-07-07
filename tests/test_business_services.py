import unittest
from uuid import uuid4

from business_services import MockBusinessDataService, reset_business_service


class TestMockBusinessDataService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_business_service()
        self.service = MockBusinessDataService()
        self.account_id = f"svc_{uuid4().hex}"

    async def test_order_tracking_and_refund_flow(self):
        orders = await self.service.get_all_orders(self.account_id)
        shipped_order = next(item for item in orders if item.get("tracking_number"))

        tracking = await self.service.get_tracking(
            self.account_id,
            order_id=shipped_order["order_id"],
        )
        refund = await self.service.refund_order(
            self.account_id,
            shipped_order["order_id"],
            "customer request",
        )
        refunded_order = await self.service.get_order(
            self.account_id,
            shipped_order["order_id"],
        )
        duplicate_refund = await self.service.refund_order(
            self.account_id,
            shipped_order["order_id"],
            "second request",
        )

        self.assertEqual(len(orders), 3)
        self.assertEqual(tracking["tracking_number"], shipped_order["tracking_number"])
        self.assertEqual(refund, "Refund successful")
        self.assertEqual(refunded_order["reason"], "customer request")
        self.assertIn("already been refunded", duplicate_refund)

    async def test_pending_order_has_no_tracking(self):
        orders = await self.service.get_all_orders(self.account_id)
        pending_order = next(item for item in orders if not item.get("tracking_number"))

        tracking = await self.service.get_tracking(
            self.account_id,
            order_id=pending_order["order_id"],
        )

        self.assertIn("not been shipped", tracking)


if __name__ == "__main__":
    unittest.main()
