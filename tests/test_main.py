import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from arkitect.types.llm.model import (
    ActionDetail,
    ArkChatRequest,
    ArkMessage,
    ToolDetail,
)

import main
from llm_provider import _make_response


class TestRouteRegistration(unittest.TestCase):
    def test_create_server_registers_standard_and_legacy_routes(self):
        server = main.create_server()
        route_paths = {getattr(route, "path", None) for route in server.app.routes}

        self.assertIn("/api/products", route_paths)
        self.assertIn("/api/chat", route_paths)
        self.assertIn("/api/conversations", route_paths)
        self.assertIn("/api/conversations/{conversation_id}/tool-calls", route_paths)
        self.assertIn("/api/quality-reviews", route_paths)
        self.assertIn("/api/faq-candidates", route_paths)
        self.assertIn("/api/refunds/{refund_id}", route_paths)
        self.assertIn("/api/refunds/{refund_id}/approve", route_paths)
        self.assertIn("/api/refunds/{refund_id}/reject", route_paths)
        self.assertIn("/api/refunds/{refund_id}/execute", route_paths)
        self.assertIn("/health", route_paths)
        self.assertIn("/ready", route_paths)
        self.assertIn("/workbench", route_paths)
        self.assertIn("/api/v3/bots/chat/completions/products", route_paths)
        self.assertIn("/api/v3/bots/chat/completions/save_faq", route_paths)

    def test_registered_routes_enforce_api_key(self):
        with patch("main.api_keys", ["secret-key"]):
            client = TestClient(main.create_server().app)

            standard_denied = client.get("/api/products")
            legacy_denied = client.get("/api/v3/bots/chat/completions/products")
            standard_allowed = client.get(
                "/api/products",
                headers={"X-API-Key": "secret-key"},
            )
            legacy_allowed = client.get(
                "/api/v3/bots/chat/completions/products",
                headers={"Authorization": "Bearer secret-key"},
            )

        self.assertEqual(standard_denied.status_code, 401)
        self.assertEqual(legacy_denied.status_code, 401)
        self.assertEqual(standard_allowed.status_code, 200)
        self.assertEqual(legacy_allowed.status_code, 200)

    def test_refund_actions_require_approver_key(self):
        service = MagicMock()
        service.approve_refund = AsyncMock(return_value={"status": "approved"})
        with patch("main.api_keys", ["secret-key"]):
            with patch("main.refund_approver_keys", ["approver-key"]):
                with patch("main.get_business_service", return_value=service):
                    client = TestClient(main.create_server().app)
                    body = {"account_id": "100000"}

                    missing = client.post("/api/refunds/r1/approve", json=body)
                    general = client.post(
                        "/api/refunds/r1/approve",
                        json=body,
                        headers={"X-API-Key": "secret-key"},
                    )
                    approver = client.post(
                        "/api/refunds/r1/approve",
                        json=body,
                        headers={"Authorization": "Bearer approver-key"},
                    )
                    approver_on_business_api = client.get(
                        "/api/products",
                        headers={"X-API-Key": "approver-key"},
                    )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(general.status_code, 403)
        self.assertEqual(approver.status_code, 200)
        self.assertEqual(approver_on_business_api.status_code, 200)
        service.approve_refund.assert_awaited_once_with("100000", "r1")

    def test_refund_actions_denied_without_configured_approver_keys(self):
        with patch("main.api_keys", ["secret-key"]):
            with patch("main.refund_approver_keys", []):
                client = TestClient(main.create_server().app)
                response = client.post(
                    "/api/refunds/r1/execute",
                    json={"account_id": "100000"},
                    headers={"X-API-Key": "secret-key"},
                )

        self.assertEqual(response.status_code, 403)

    def test_scoped_endpoints_require_account_id(self):
        with patch("main.api_keys", []):
            with patch("main.refund_approver_keys", []):
                client = TestClient(main.create_server().app)

                responses = [
                    client.get("/api/conversations"),
                    client.get("/api/conversations?account_id="),
                    client.get("/api/conversations/conv_1"),
                    client.get("/api/faq-candidates"),
                    client.get("/api/quality-reviews"),
                    client.get("/api/refunds/r1"),
                    client.post("/api/refunds/r1/approve", json={}),
                ]

        self.assertEqual([item.status_code for item in responses], [422] * len(responses))

    def test_health_and_ready_are_public(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "ready.sqlite3"
            with patch("config.conversation_db_path", str(db_path)):
                with patch("main.api_keys", ["secret-key"]):
                    client = TestClient(main.create_server().app)

                    health = client.get("/health")
                    ready = client.get("/ready")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertTrue(health.headers.get("X-Request-ID", "").startswith("req_"))
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")


class TestChatKnowledgeUsage(unittest.IsolatedAsyncioTestCase):
    async def test_openai_compatible_response_includes_knowledge_action(self):
        action_detail = ActionDetail(
            name="knowledge",
            tool_details=[
                ToolDetail(
                    name="dify_retrieval",
                    input="安装方法",
                    output=[
                        {
                            "document_name": "install-faq",
                            "score": 0.91,
                            "content": "安装前请先固定底座。",
                        }
                    ],
                )
            ],
        )

        async def fake_run_openai_compatible_chat(messages, **kwargs):
            return _make_response(
                "请先固定底座再安装。",
                {
                    "id": "chatcmpl-test",
                    "created": 123,
                    "model": "test-model",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "请先固定底座再安装。"},
                        }
                    ],
                },
            )

        request = ArkChatRequest(
            stream=False,
            model="test",
            messages=[ArkMessage(role="user", content="安装方法是什么？")],
        )

        with patch("main.mock_mode", False):
            with patch("main.is_openai_compatible_provider", return_value=True):
                with patch(
                    "main.retrieval_knowledge",
                    return_value=("knowledge prompt", action_detail),
                ):
                    with patch(
                        "main.run_openai_compatible_chat",
                        fake_run_openai_compatible_chat,
                    ):
                        responses = [
                            item async for item in main.custom_support_chat.__wrapped__(request)
                        ]

        self.assertEqual(len(responses), 1)
        self.assertEqual(
            responses[0].bot_usage.action_details[0].tool_details[0].name,
            "dify_retrieval",
        )

    async def test_interrupted_stream_still_records_partial_turn(self):
        def chunk(text):
            return SimpleNamespace(
                id="chunk-1",
                model="test-model",
                bot_usage=None,
                metadata=None,
                choices=[SimpleNamespace(delta=SimpleNamespace(content=text))],
            )

        class FakeLLM:
            def __init__(self, **kwargs):
                pass

            async def astream(self, **kwargs):
                yield chunk("您好，")
                yield chunk("订单已发货。")

        request = ArkChatRequest(
            stream=True,
            model="test",
            messages=[ArkMessage(role="user", content="订单到哪了？")],
        )
        record_chat_turn = MagicMock()

        with patch("main.mock_mode", False), \
                patch("main.is_openai_compatible_provider", return_value=False), \
                patch("main.ensure_conversation", return_value="conv_stream"), \
                patch("main.register_support_functions", return_value=([], "system")), \
                patch("main.get_products", return_value={}), \
                patch("main.retrieval_knowledge", return_value=("", None)), \
                patch("main.get_auth_header", return_value={}), \
                patch("main.BaseChatLanguageModel", FakeLLM), \
                patch("main.record_chat_turn", record_chat_turn):
            stream = main.custom_support_chat.__wrapped__(request)
            await stream.__anext__()
            await stream.aclose()

        record_chat_turn.assert_called_once()
        recorded_response = record_chat_turn.call_args.args[2]
        self.assertEqual(recorded_response.choices[0].message.content, "您好，")


class TestBusinessAPI(unittest.IsolatedAsyncioTestCase):
    async def test_api_key_auth_allows_requests_when_disabled(self):
        with patch("main.api_keys", []):
            result = await main.require_api_key()

        self.assertIsNone(result)

    async def test_api_key_auth_accepts_x_api_key(self):
        with patch("main.api_keys", ["secret-key"]):
            result = await main.require_api_key(x_api_key="secret-key")

        self.assertIsNone(result)

    async def test_api_key_auth_accepts_bearer_token(self):
        with patch("main.api_keys", ["secret-key"]):
            result = await main.require_api_key(
                authorization="Bearer secret-key",
            )

        self.assertIsNone(result)

    async def test_api_key_auth_rejects_invalid_key(self):
        with patch("main.api_keys", ["secret-key"]):
            with self.assertRaises(HTTPException) as context:
                await main.require_api_key(x_api_key="wrong-key")

        self.assertEqual(context.exception.status_code, 401)

    async def test_api_products_returns_product_list(self):
        result = await main.api_products()

        self.assertGreater(result.total, 0)
        self.assertEqual(result.total, len(result.products))
        self.assertTrue(result.products[0].name)

    async def test_api_chat_returns_answer_and_conversation_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "conversations.sqlite3"
            with patch("config.conversation_db_path", str(db_path)):
                with patch("main.mock_mode", True):
                    result = await main.api_chat(
                        main.BusinessChatRequest(
                            message="please check my orders",
                            account_id="100000",
                            support_functions=["order_check"],
                            model="test",
                        )
                    )
                    conversation = main.get_conversation(result["conversation_id"])

        self.assertTrue(result["conversation_id"].startswith("conv_"))
        self.assertTrue(result["answer"])
        self.assertEqual(result["metadata"]["conversation_id"], result["conversation_id"])
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation["messages"]), 2)

    async def test_api_chat_rejects_cross_account_conversation_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "conversations.sqlite3"
            with patch("config.conversation_db_path", str(db_path)):
                conversation_id = main.ensure_conversation(
                    "conv_account_a",
                    "account_a",
                )
                with patch("main.mock_mode", True):
                    with self.assertRaises(HTTPException) as context:
                        await main.api_chat(
                            main.BusinessChatRequest(
                                message="continue this conversation",
                                account_id="account_b",
                                conversation_id=conversation_id,
                                support_functions=["order_check"],
                                model="test",
                            )
                        )

        self.assertEqual(context.exception.status_code, 403)

    async def test_api_save_faq_uses_existing_save_handler(self):
        faq = main.FAQRequest(
            question="install",
            answer="follow the guide",
            score=5,
            account_id="100000",
        )
        with patch("main.save_faq", AsyncMock(return_value={"message": "success"})):
            result = await main.api_save_faq(faq)

        self.assertEqual(result, {"message": "success"})

    async def test_api_quality_check_returns_result(self):
        with patch("quality_inspection.mock_mode", True):
            result = await main.api_quality_check(
                main.QualityCheckRequest(
                    content="assistant: 这款商品绝对是全网最低价",
                    keywords="全网最低",
                    model="test",
                )
            )

        self.assertTrue(result["result"])
        self.assertEqual(result["structured_result"]["risk_level"], "high")
        self.assertGreaterEqual(result["structured_result"]["hit_count"], 1)
        self.assertIsNotNone(result["bot_usage"])

    async def test_api_summary_returns_summary(self):
        with patch("summary.mock_mode", True):
            result = await main.api_summary(
                main.SummaryRequest(
                    messages=[
                        main.BusinessChatMessage(
                            role="user",
                            content="I want to return this order.",
                        )
                        ,main.BusinessChatMessage(
                            role="assistant",
                            content="I can help check the return policy.",
                        )
                    ],
                    model="test",
                )
            )

        self.assertTrue(result["summary"])
        self.assertIsNotNone(result["bot_usage"])


if __name__ == "__main__":
    unittest.main()
