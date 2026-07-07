import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from arkitect.types.llm.model import ArkChatRequest, ArkMessage

import mock_agent
from data import rag
from mock_agent import (
    make_mock_chat_response,
    make_mock_quality_response,
    make_mock_summary_response,
)


class TestMockAgent(unittest.IsolatedAsyncioTestCase):
    async def test_mock_chat_returns_order_result(self):
        request = ArkChatRequest(
            stream=False,
            model="test",
            metadata={
                "account_id": "100000",
                "support_functions": ["order_check"],
            },
            messages=[ArkMessage(role="user", content="帮我查一下所有订单")],
        )

        response = await make_mock_chat_response(request)

        self.assertEqual(response.object, "chat.completion")
        self.assertIn("3", response.choices[0].message.content)
        tool = response.bot_usage.action_details[0].tool_details[0]
        self.assertEqual(tool.name, "order_check")
        self.assertEqual(len(tool.output), 3)

    def test_mock_quality_flags_absolute_words(self):
        request = ArkChatRequest(
            stream=False,
            model="test",
            messages=[
                ArkMessage(
                    role="user",
                    content="assistant: 这款已经是全网最低价，绝对划算。",
                )
            ],
        )

        response = make_mock_quality_response(request)

        self.assertIn("存在风险", response.choices[0].message.content)

    def test_mock_summary_returns_structured_text(self):
        request = ArkChatRequest(
            stream=False,
            model="test",
            messages=[ArkMessage(role="user", content="我想退货")],
        )

        response = make_mock_summary_response(request)

        self.assertIn("主要诉求", response.choices[0].message.content)


class TestMockFAQSave(unittest.TestCase):
    def test_mock_faq_save_writes_local_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(rag, "MOCK_FAQ_DIR", Path(tmp_dir)):
                with patch("data.rag.config.mock_mode", True):
                    rag.save_faq(
                        pd.DataFrame(
                            [{"question": "q1", "answer": "a1", "score": 5}]
                        ),
                        "100000",
                    )

            file_path = Path(tmp_dir) / "100000.faq.xlsx"
            self.assertTrue(file_path.exists())
            saved = pd.read_excel(file_path)
            self.assertEqual(saved.to_dict("records")[0]["question"], "q1")


if __name__ == "__main__":
    unittest.main()
