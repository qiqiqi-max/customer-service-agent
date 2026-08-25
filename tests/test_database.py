import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arkitect.types.llm.model import (
    ActionDetail,
    ArkChatRequest,
    ArkMessage,
    BotUsage,
    ToolDetail,
)

import conversation_store
from audit_store import (
    list_faq_candidates,
    list_quality_reviews,
    save_faq_candidate,
    save_quality_review,
)
from database import get_engine
from llm_provider import _make_response


class TestDatabasePersistence(unittest.TestCase):
    def test_tool_calls_are_persisted_separately(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "conversations.sqlite3")
            with patch("conversation_store.config.conversation_db_path", db_path):
                conversation_id = conversation_store.ensure_conversation(None, "100000")
                request = ArkChatRequest(
                    stream=False,
                    model="test",
                    messages=[ArkMessage(role="user", content="查物流")],
                )
                response = _make_response(
                    "正在为您查询。",
                    {
                        "id": "chatcmpl-test",
                        "created": 123,
                        "model": "test-model",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": "正在为您查询。"},
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
                                    name="pack_track",
                                    input={"order_id": "100000_1"},
                                    output={"status": "派送中"},
                                )
                            ],
                        )
                    ]
                )
                conversation_store.record_chat_turn(
                    conversation_id,
                    request,
                    response,
                )
                with get_engine().connect() as conn:
                    row = conn.exec_driver_sql(
                        "select tool_name, input_json, output_json from tool_calls"
                    ).first()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "pack_track")
        self.assertIn("100000_1", row[1])
        self.assertIn("派送中", row[2])

    def test_audit_records_are_scoped_by_account(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "audit.sqlite3")
            with patch("conversation_store.config.conversation_db_path", db_path):
                save_quality_review(
                    account_id="account_a",
                    content="回复 A",
                    keywords="",
                    result="通过",
                    structured_result={"risk_level": "none"},
                )
                save_quality_review(
                    account_id="account_b",
                    content="回复 B",
                    keywords="",
                    result="风险",
                    structured_result={"risk_level": "high"},
                )
                save_faq_candidate(
                    account_id="account_a",
                    question="问题 A",
                    answer="答案 A",
                    score=5,
                )
                save_faq_candidate(
                    account_id="account_b",
                    question="问题 B",
                    answer="答案 B",
                    score=4,
                )

                account_a_reviews = list_quality_reviews("account_a")
                account_b_candidates = list_faq_candidates("account_b")

        self.assertEqual(len(account_a_reviews), 1)
        self.assertEqual(account_a_reviews[0]["content"], "回复 A")
        self.assertEqual(len(account_b_candidates), 1)
        self.assertEqual(account_b_candidates[0]["question"], "问题 B")


if __name__ == "__main__":
    unittest.main()
