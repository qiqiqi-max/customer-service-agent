import unittest
from uuid import uuid4

from business_services import reset_business_service
from agent_tools import build_openai_tools, build_tool_executor


class TestAgentTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_business_service()

    def test_build_openai_tools_filters_enabled_functions(self):
        tools = build_openai_tools(["order_check"])
        names = [item["function"]["name"] for item in tools]
        self.assertEqual(names, ["order_check"])

    async def test_order_check_executor_returns_orders(self):
        executor = build_tool_executor(f"agent_{uuid4().hex}")
        output = await executor(
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "order_check", "arguments": "{}"},
            }
        )
        self.assertEqual(len(output), 3)
        self.assertIn("order_id", output[0])

    async def test_pack_track_executor_returns_tracking(self):
        account_id = f"agent_{uuid4().hex}"
        executor = build_tool_executor(account_id)
        orders = await executor(
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "order_check", "arguments": "{}"},
            }
        )
        shipped_order = next(item for item in orders if item.get("tracking_number"))

        output = await executor(
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "pack_track",
                    "arguments": {"order_id": shipped_order["order_id"]},
                },
            }
        )

        self.assertEqual(output["tracking_number"], shipped_order["tracking_number"])
        self.assertGreaterEqual(len(output["events"]), 1)

    async def test_order_refund_executor_only_creates_pending_request(self):
        account_id = f"agent_{uuid4().hex}"
        executor = build_tool_executor(account_id)
        orders = await executor(
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "order_check", "arguments": "{}"},
            }
        )

        refund = await executor(
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "order_refund",
                    "arguments": {
                        "order_id": orders[0]["order_id"],
                        "reason": "changed mind",
                    },
                },
            }
        )
        current_order = await executor(
            {
                "id": "call_3",
                "type": "function",
                "function": {
                    "name": "order_check",
                    "arguments": {"order_id": orders[0]["order_id"]},
                },
            }
        )

        self.assertEqual(refund["status"], "pending_approval")
        self.assertIn("id", refund)
        self.assertNotEqual(current_order["status"], "已退款")


if __name__ == "__main__":
    unittest.main()
