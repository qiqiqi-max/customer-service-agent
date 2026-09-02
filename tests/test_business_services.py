import unittest
from unittest.mock import patch
from uuid import uuid4

from business_services import (
    LocalDatabaseBusinessDataService,
    get_business_service,
    reset_business_service,
)
from data.refunds import RefundError, RefundStatus


class TestLocalDatabaseBusinessDataService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_business_service()
        self.service = LocalDatabaseBusinessDataService()
        self.account_id = f"svc_{uuid4().hex}"

    async def test_refund_requires_manual_approval_before_execution(self):
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
        self.assertEqual(refund["status"], RefundStatus.PENDING_APPROVAL.value)
        self.assertEqual(refunded_order["status"], shipped_order["status"])
        with self.assertRaises(RefundError):
            await self.service.execute_refund(self.account_id, refund["id"])

        approved = await self.service.approve_refund(self.account_id, refund["id"])
        self.assertEqual(approved["status"], RefundStatus.APPROVED.value)
        executed = await self.service.execute_refund(self.account_id, refund["id"])
        self.assertEqual(executed["status"], RefundStatus.EXECUTED.value)
        refunded_order = await self.service.get_order(
            self.account_id,
            shipped_order["order_id"],
        )
        self.assertEqual(refunded_order["status"], "已退款")
        self.assertEqual(refunded_order["reason"], "customer request")

        self.assertEqual(len(orders), 3)
        self.assertEqual(tracking["tracking_number"], shipped_order["tracking_number"])
        with self.assertRaises(RefundError):
            await self.service.refund_order(
                self.account_id,
                shipped_order["order_id"],
                "second request",
            )

    async def test_rejected_refund_cannot_be_executed(self):
        orders = await self.service.get_all_orders(self.account_id)
        request = await self.service.refund_order(
            self.account_id,
            orders[0]["order_id"],
            "customer changed mind",
        )
        rejected = await self.service.reject_refund(self.account_id, request["id"])
        self.assertEqual(rejected["status"], RefundStatus.REJECTED.value)
        with self.assertRaises(RefundError):
            await self.service.execute_refund(self.account_id, request["id"])

    async def test_refund_requests_are_account_isolated(self):
        orders = await self.service.get_all_orders(self.account_id)
        request = await self.service.refund_order(
            self.account_id,
            orders[0]["order_id"],
            "account isolation",
        )
        with self.assertRaises(RefundError):
            await self.service.approve_refund("another_account", request["id"])

    async def test_pending_order_has_no_tracking(self):
        orders = await self.service.get_all_orders(self.account_id)
        pending_order = next(item for item in orders if not item.get("tracking_number"))

        tracking = await self.service.get_tracking(
            self.account_id,
            order_id=pending_order["order_id"],
        )

        self.assertIn("not been shipped", tracking)


class TestBusinessServiceFactory(unittest.TestCase):
    def tearDown(self):
        reset_business_service()

    def test_mysql_provider_uses_local_database_service(self):
        with patch("business_services.config.business_data_provider", "mysql"):
            service = get_business_service()

        self.assertIsInstance(service, LocalDatabaseBusinessDataService)
        self.assertEqual(service.provider_name, "mysql")


if __name__ == "__main__":
    unittest.main()
