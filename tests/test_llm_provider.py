import json
import unittest
from unittest.mock import patch

from arkitect.types.llm.model import ArkMessage

import llm_provider


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class TestOpenAICompatibleProvider(unittest.IsolatedAsyncioTestCase):
    async def test_run_openai_compatible_chat_maps_request_and_response(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeHTTPResponse(
                {
                    "id": "chatcmpl-test",
                    "created": 123,
                    "model": "deepseekv4pro",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "hello from deepseek",
                            },
                        }
                    ],
                }
            )

        with patch("llm_provider.config.deepseek_api_key", "test-key"):
            with patch("llm_provider.config.deepseek_base_url", "https://api.example.com/v1"):
                with patch("llm_provider.config.deepseek_model", "deepseekv4pro"):
                    with patch("urllib.request.urlopen", fake_urlopen):
                        response = await llm_provider.run_openai_compatible_chat(
                            [ArkMessage(role="user", content="hi")]
                        )

        self.assertEqual(captured["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["body"]["model"], "deepseekv4pro")
        self.assertEqual(captured["body"]["messages"][0]["content"], "hi")
        self.assertEqual(response.choices[0].message.content, "hello from deepseek")
        self.assertEqual(response.model, "deepseekv4pro")

    async def test_run_openai_compatible_chat_requires_api_key(self):
        with patch("llm_provider.config.deepseek_api_key", ""):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                await llm_provider.run_openai_compatible_chat(
                    [ArkMessage(role="user", content="hi")]
                )

    async def test_run_openai_compatible_chat_supports_zhipu(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                {
                    "id": "chatcmpl-zhipu",
                    "created": 456,
                    "model": "glm-5.2",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "hello from zhipu",
                            },
                        }
                    ],
                }
            )

        with patch("llm_provider.config.llm_provider", "zhipu"):
            with patch("llm_provider.config.zhipu_api_key", "zhipu-key"):
                with patch(
                    "llm_provider.config.zhipu_base_url",
                    "https://open.bigmodel.cn/api/paas/v4/",
                ):
                    with patch("llm_provider.config.zhipu_model", "glm-5.2"):
                        with patch("urllib.request.urlopen", fake_urlopen):
                            response = await llm_provider.run_openai_compatible_chat(
                                [ArkMessage(role="user", content="你好")]
                            )

        self.assertEqual(
            captured["url"],
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        )
        self.assertEqual(captured["headers"]["Authorization"], "Bearer zhipu-key")
        self.assertEqual(captured["body"]["model"], "glm-5.2")
        self.assertEqual(response.choices[0].message.content, "hello from zhipu")

    async def test_run_openai_compatible_chat_executes_tool_calls(self):
        requests = []

        def fake_urlopen(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            requests.append(body)
            if len(requests) == 1:
                return FakeHTTPResponse(
                    {
                        "id": "chatcmpl-tool-1",
                        "created": 111,
                        "model": "deepseekv4pro",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "tool_calls",
                                "message": {
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "type": "function",
                                            "function": {
                                                "name": "order_check",
                                                "arguments": "{}",
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                )
            return FakeHTTPResponse(
                {
                    "id": "chatcmpl-tool-2",
                    "created": 112,
                    "model": "deepseekv4pro",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "已查到 3 笔订单。",
                            },
                        }
                    ],
                }
            )

        async def fake_executor(tool_call):
            return [{"order_id": "100000_1"}]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "order_check",
                    "description": "Query order",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        with patch("llm_provider.config.deepseek_api_key", "test-key"):
            with patch("urllib.request.urlopen", fake_urlopen):
                response = await llm_provider.run_openai_compatible_chat(
                    [ArkMessage(role="user", content="查订单")],
                    tools=tools,
                    tool_executor=fake_executor,
                )

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["tools"][0]["function"]["name"], "order_check")
        self.assertEqual(requests[1]["messages"][-1]["role"], "tool")
        self.assertEqual(response.choices[0].message.content, "已查到 3 笔订单。")
        self.assertEqual(
            response.bot_usage.action_details[0].tool_details[0].name,
            "order_check",
        )


if __name__ == "__main__":
    unittest.main()
