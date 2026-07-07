# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# Licensed under the 【火山方舟】原型应用软件自用许可协议
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     https://www.volcengine.com/docs/82379/1433703
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import json
import unittest
from unittest.mock import MagicMock, patch

from arkitect.types.llm.model import ArkMessage
import pandas as pd
from data.rag import retrieval_knowledge, save_faq
from tos.exceptions import TosServerError


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class TestSaveFAQ(unittest.TestCase):
    def setUp(self):
        # Mock TOS client
        self.mock_tos = MagicMock()
        self.mock_get_object = MagicMock()
        self.mock_tos.get_object = self.mock_get_object
        self.mock_tos.put_object = MagicMock()

        # Mock Viking service
        self.mock_collection = MagicMock()
        self.mock_collection.add_doc = MagicMock()
        self.mock_viking_service = MagicMock()
        self.mock_viking_service.get_collection.return_value = self.mock_collection

        # Apply patches
        self.tos_patcher = patch("data.rag.tos_client", self.mock_tos)
        self.viking_patcher = patch(
            "data.rag.viking_knowledgebase_service", self.mock_viking_service
        )
        self.bucket_patcher = patch("data.rag.config.bucket_name", "customer-support-faqs")
        self.collection_patcher = patch(
            "data.rag.config.faq_collection_name", "faq_collection"
        )
        self.tos_patcher.start()
        self.viking_patcher.start()
        self.bucket_patcher.start()
        self.collection_patcher.start()

    def tearDown(self):
        self.tos_patcher.stop()
        self.viking_patcher.stop()
        self.bucket_patcher.stop()
        self.collection_patcher.stop()

    def test_save_faq_new_file(self):
        # Setup scenario where no existing file
        self.mock_get_object.side_effect = TosServerError(
            msg="", host_id="", resource="", resp=MagicMock(), code="NoSuchKey"
        )
        self.mock_get_object.side_effect.status_code = 404
        test_data = {"question": "new_q", "answer": "new_a", "score": 1}

        # Execute
        save_faq(pd.DataFrame([test_data]), "100000")

        # Verify TOS operations
        self.mock_tos.put_object.assert_called_once()
        put_args = self.mock_tos.put_object.call_args[1]

        # Check uploaded Excel content
        uploaded_bytes = put_args["content"].read()
        df = pd.read_excel(io.BytesIO(uploaded_bytes))
        self.assertEqual(
            df.to_dict(),
            {"question": {0: "new_q"}, "answer": {0: "new_a"}, "score": {0: 1}},
        )

        # Verify knowledge base update
        self.assertEqual(put_args["bucket"], "customer-support-faqs")
        self.assertEqual(put_args["key"], "custom_support/faq/100000.faq.xlsx")
        self.assertEqual(
            put_args["meta"],
            {"doc_id": "doc_id_100000", "account_id": "100000"},
        )
        self.mock_collection.add_doc.assert_called_once_with(
            add_type="tos",
            tos_path="customer-support-faqs/custom_support/faq/100000.faq.xlsx",
        )

    def test_save_faq_existing_file(self):
        # Setup existing file scenario
        existing_data = pd.DataFrame(
            {"question": ["existing_q"], "answer": ["existing_a"], "score": [1]}
        )
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer) as writer:
            existing_data.to_excel(writer, index=False)
        excel_buffer.seek(0)

        self.mock_get_object.return_value = MagicMock(
            read=lambda: excel_buffer.getvalue()
        )

        test_data = {"question": "new_q", "answer": "new_a", "score": 2}

        # Execute
        save_faq(pd.DataFrame([test_data]), "100000")

        # Verify TOS operations
        self.mock_tos.put_object.assert_called_once()
        put_args = self.mock_tos.put_object.call_args[1]

        # Check merged data
        uploaded_bytes = put_args["content"].read()
        df = pd.read_excel(io.BytesIO(uploaded_bytes))
        self.assertEqual(
            df.to_dict(),
            {
                "answer": {0: "existing_a", 1: "new_a"},
                "question": {0: "existing_q", 1: "new_q"},
                "score": {0: 1, 1: 2},
            },
        )

    def test_save_faq_requires_bucket_config(self):
        with patch("data.rag.config.bucket_name", ""):
            with self.assertRaisesRegex(ValueError, "BUCKET_NAME"):
                save_faq(
                    pd.DataFrame(
                        [{"question": "new_q", "answer": "new_a", "score": 1}]
                    ),
                    "100000",
                )


class TestDifyKnowledge(unittest.TestCase):
    def test_retrieval_knowledge_uses_dify_datasets(self):
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(
                {
                    "url": request.full_url,
                    "headers": dict(request.header_items()),
                    "body": json.loads(request.data.decode("utf-8")),
                }
            )
            return FakeHTTPResponse(
                {
                    "records": [
                        {
                            "score": 0.91,
                            "segment": {
                                "id": "segment-1",
                                "document_id": "doc-1",
                                "content": "这是一段 Dify 知识库内容。",
                                "document": {"id": "doc-1", "name": "faq"},
                            },
                        }
                    ]
                }
            )

        with patch("data.rag.config.knowledge_provider", "dify"):
            with patch("data.rag.config.dify_api_key", "dify-key"):
                with patch("data.rag.config.dify_base_url", "https://api.dify.ai/v1"):
                    with patch("data.rag.config.dify_dataset_id", "product-ds"):
                        with patch("data.rag.config.dify_faq_dataset_id", "faq-ds"):
                            with patch("urllib.request.urlopen", fake_urlopen):
                                prompt, action = retrieval_knowledge(
                                    [ArkMessage(role="user", content="怎么安装？")],
                                    {},
                                )

        self.assertEqual(len(requests), 2)
        self.assertEqual(
            requests[0]["url"], "https://api.dify.ai/v1/datasets/product-ds/retrieve"
        )
        self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer dify-key")
        self.assertEqual(requests[0]["body"]["query"], "怎么安装？")
        self.assertIn("这是一段 Dify 知识库内容。", prompt)
        self.assertEqual(action.tool_details[0].name, "dify_retrieval")

    def test_save_faq_uses_dify_create_by_text(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse({"document": {"id": "doc-1"}})

        with patch("data.rag.config.knowledge_provider", "dify"):
            with patch("data.rag.config.dify_api_key", "dify-key"):
                with patch("data.rag.config.dify_faq_dataset_id", "faq-ds"):
                    with patch("data.rag.config.dify_base_url", "https://api.dify.ai/v1"):
                        with patch("urllib.request.urlopen", fake_urlopen):
                            save_faq(
                                pd.DataFrame(
                                    [{"question": "q1", "answer": "a1", "score": 5}]
                                ),
                                "100000",
                            )

        self.assertEqual(
            captured["url"],
            "https://api.dify.ai/v1/datasets/faq-ds/document/create_by_text",
        )
        self.assertEqual(captured["headers"]["Authorization"], "Bearer dify-key")
        self.assertIn("question: q1", captured["body"]["text"])
        self.assertEqual(captured["body"]["indexing_technique"], "high_quality")

    def test_dify_no_hit_prompt_prevents_hallucination(self):
        def fake_urlopen(request, timeout):
            return FakeHTTPResponse({"records": []})

        with patch("data.rag.config.knowledge_provider", "dify"):
            with patch("data.rag.config.dify_api_key", "dify-key"):
                with patch("data.rag.config.dify_dataset_id", "product-ds"):
                    with patch("data.rag.config.dify_faq_dataset_id", "faq-ds"):
                        with patch("urllib.request.urlopen", fake_urlopen):
                            prompt, action = retrieval_knowledge(
                                [ArkMessage(role="user", content="有没有保修？")],
                                {},
                            )

        self.assertIn("没有命中可靠资料", prompt)
        self.assertIn("不要编造答案", prompt)
        self.assertEqual(action.tool_details[0].output, [])


if __name__ == "__main__":
    unittest.main()
