import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arkitect.types.llm.model import ArkChatRequest, ArkMessage, BotUsage, ActionDetail, ToolDetail

import conversation_store
from llm_provider import _make_response


class TestConversationStore(unittest.TestCase):
    def test_record_and_read_conversation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "conversations.sqlite3")
            with patch("conversation_store.config.conversation_db_path", db_path):
                conversation_id = conversation_store.ensure_conversation(
                    None,
                    "100000",
                )
                request = ArkChatRequest(
                    stream=False,
                    model="test",
                    messages=[ArkMessage(role="user", content="帮我查订单")],
                )
                response = _make_response(
                    "已查到 3 笔订单。",
                    {
                        "id": "chatcmpl-test",
                        "created": 123,
                        "model": "test-model",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": "已查到 3 笔订单。"},
                            }
                        ],
                    },
                )
                response.bot_usage = BotUsage(
                    action_details=[
                        ActionDetail(
                            name="tool_calling",
                            tool_details=[
                                ToolDetail(
                                    name="order_check",
                                    input={},
                                    output=[{"order_id": "100000_1"}],
                                )
                            ],
                        )
                    ]
                )

                conversation_store.record_chat_turn(conversation_id, request, response)
                listing = conversation_store.list_conversations()
                detail = conversation_store.get_conversation(conversation_id)

        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["conversations"][0]["id"], conversation_id)
        self.assertEqual(detail["account_id"], "100000")
        self.assertEqual(len(detail["messages"]), 2)
        self.assertEqual(detail["messages"][0]["role"], "user")
        self.assertEqual(detail["messages"][1]["role"], "assistant")
        self.assertEqual(
            detail["messages"][1]["metadata"]["bot_usage"]["action_details"][0][
                "tool_details"
            ][0]["name"],
            "order_check",
        )

    def test_attach_conversation_metadata(self):
        response = _make_response(
            "hello",
            {
                "id": "chatcmpl-test",
                "created": 123,
                "model": "test-model",
                "choices": [
                    {"finish_reason": "stop", "message": {"content": "hello"}}
                ],
            },
        )
        conversation_store.attach_conversation_metadata(response, "conv_123")
        self.assertEqual(response.metadata["conversation_id"], "conv_123")

    def test_conversation_access_is_scoped_to_account(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "conversations.sqlite3")
            with patch("conversation_store.config.conversation_db_path", db_path):
                conversation_id = conversation_store.ensure_conversation(
                    "conv_shared",
                    "account_a",
                )
                conversation_store.ensure_conversation("conv_other", "account_b")

                with self.assertRaises(conversation_store.ConversationAccessError):
                    conversation_store.ensure_conversation(
                        conversation_id,
                        "account_b",
                    )

                account_a_list = conversation_store.list_conversations(
                    account_id="account_a"
                )
                account_b_detail = conversation_store.get_conversation(
                    conversation_id,
                    account_id="account_b",
                )

        self.assertEqual(account_a_list["total"], 1)
        self.assertEqual(account_a_list["conversations"][0]["id"], conversation_id)
        self.assertIsNone(account_b_detail)


if __name__ == "__main__":
    unittest.main()
