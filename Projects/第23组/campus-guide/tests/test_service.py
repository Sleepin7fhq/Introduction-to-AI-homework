import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from ai_service import (
    DETAIL, NO_INFO, SHORT, UNKNOWN, Answer, Config, Turn, chat_json, cloud_config,
    guide_answer, offline_recognition, read_settings, recognize, select_facts,
)
from guide_data import GuideError, load_catalog

ROOT = Path(__file__).resolve().parents[1]
# 只用于断言字段传播和脱敏，从未签发的测试文字。
TEST_CONFIG = Config("not-a-real-credential", "http://127.0.0.1:1/v1", "test-vision")


def envelope(content):
    return {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}


def http_response(data, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(data).encode()
    response._content_consumed = True
    return response


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.buildings = load_catalog(ROOT / "data/buildings.example.json")
        self.a = self.buildings["A"]

    def test_local_configuration_and_safe_errors(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "config.toml"
            with self.assertRaisesRegex(GuideError, "未找到"):
                cloud_config(read_settings(path))
            path.write_bytes((ROOT / "config.example.toml").read_bytes())
            with self.assertRaisesRegex(GuideError, "API_KEY"):
                cloud_config(read_settings(path))
            path.write_text("API_KEY = [", encoding="utf-8")
            with self.assertRaisesRegex(GuideError, "TOML"):
                read_settings(path)
            for url in ("https://{WorkspaceId}.invalid/v1", "http://example.invalid",
                        "https://user:pass@api.invalid/v1", "https://a.invalid:bad/v1",
                        "https://a.invalid/v1?key=test", "https://a.invalid/v1/chat/completions"):
                path.write_text(f'API_KEY="not-a-real-credential"\nBASE_URL="{url}"\nMODEL_NAME="test"', encoding="utf-8")
                with self.subTest(url=url), self.assertRaisesRegex(GuideError, "BASE_URL"):
                    cloud_config(read_settings(path))
            path.write_text('API_KEY="not-a-real-credential"\nBASE_URL="https://api.invalid/v1/"\nMODEL_NAME="m"', encoding="utf-8")
            cfg = cloud_config(read_settings(path))
            self.assertEqual(cfg.base_url, "https://api.invalid/v1")
            self.assertNotIn(cfg.api_key, repr(cfg))

    @patch("ai_service.requests.post", side_effect=AssertionError("离线路径意外联网"))
    def test_offline_tour_lengths_and_followup(self, post):
        short = guide_answer(self.a, SHORT, None)
        detail = guide_answer(self.a, DETAIL, None)
        self.assertEqual((len(short.fact_ids), len(detail.fact_ids)), (2, 3))
        reply = guide_answer(self.a, SHORT, None, question="圆窗在哪里？", guide=short)
        self.assertEqual(reply.fact_ids, ("window",))
        repeated = guide_answer(self.a, SHORT, None, question="再说一遍", history=[Turn("圆窗在哪里？", reply)])
        self.assertEqual(repeated, reply)
        missing = guide_answer(self.a, SHORT, None, question="建于哪一年？")
        self.assertEqual(missing.paragraphs(self.a), [NO_INFO])
        self.assertEqual(offline_recognition(b"same", b"same", self.buildings).building_id, "A")
        self.assertEqual(offline_recognition(b"other", b"same", self.buildings).building_id, UNKNOWN)
        post.assert_not_called()

    def test_unknown_facts_and_inconsistent_coverage_rejected(self):
        for payload in ({"coverage": "full", "fact_ids": ["not-in-card"]},
                        {"coverage": "none", "fact_ids": ["entrance"]},
                        {"coverage": "full", "fact_ids": []},
                        {"coverage": "full", "fact_ids": [{}]}):
            with self.subTest(payload=payload), self.assertRaisesRegex(GuideError, "格式异常"):
                select_facts(payload, self.a, 2)
        self.assertEqual(select_facts({"coverage": "none", "fact_ids": []}, self.a, 2), Answer((), "none"))

    @patch("ai_service.chat_json")
    def test_invalid_fact_numbers_corrected_once_without_guessing(self, chat):
        chat.side_effect = [
            {"coverage": "full", "fact_ids": [1, 2]},
            {"coverage": "full", "fact_ids": ["window"]},
        ]
        answer = guide_answer(self.a, SHORT, TEST_CONFIG, question="圆窗在哪？")
        self.assertEqual(answer.fact_ids, ("window",))
        self.assertEqual(chat.call_count, 2)
        self.assertIn('"window"', chat.call_args.args[1][-1]['content'])
        chat.reset_mock()
        chat.side_effect = None
        chat.return_value = {"coverage": "full", "fact_ids": [1]}
        with self.assertRaises(GuideError):
            guide_answer(self.a, SHORT, TEST_CONFIG)
        self.assertEqual(chat.call_count, 2)
        chat.reset_mock()
        chat.side_effect = GuideError("接口等待超时")
        with self.assertRaises(GuideError):
            guide_answer(self.a, SHORT, TEST_CONFIG)
        self.assertEqual(chat.call_count, 1)

    @patch("ai_service.chat_json")
    def test_conversation_uses_current_card_and_last_six_turns(self, chat):
        chat.return_value = {"coverage": "full", "fact_ids": ["window"], "url": "https://invented.invalid"}
        previous = [Turn(f"测试追问 {i}", Answer(("entrance",))) for i in range(9)]
        answer = guide_answer(self.a, SHORT, TEST_CONFIG, question="它在哪儿？", history=previous, guide=Answer(("window",)))
        messages = chat.call_args.args[1]
        transcript = json.dumps(messages, ensure_ascii=False)
        self.assertIn(self.a.name, transcript)
        self.assertNotIn(self.buildings["B"].name, transcript)
        self.assertNotIn("测试追问 2", transcript)
        self.assertIn("测试追问 3", transcript)
        self.assertIn("它在哪儿", messages[-1]["content"])
        self.assertEqual(answer.sources(self.a), [])
        self.assertNotIn("invented", str(answer.paragraphs(self.a)))

    @patch("ai_service.chat_json")
    def test_candidate_and_reason_validation(self, chat):
        for bid, reason in [(UNKNOWN, "遮挡了入口，缺少可比对特征。"), ("A", "圆窗位于拱门上方。")]:
            chat.return_value = {"building_id": bid, "reason": reason}
            self.assertEqual(recognize(TEST_CONFIG, self.buildings, b"x", []).building_id, bid)
        for bid, reason in [("D", "测试"), (None, "测试"), ("A", ""), ("A", "有 95％ 的可能"),
                            ("B", "置信度 0.8"), ("C", "见 https://invented.invalid")]:
            chat.return_value = {"building_id": bid, "reason": reason}
            with self.subTest(bid=bid, reason=reason), self.assertRaisesRegex(GuideError, "格式异常"):
                recognize(TEST_CONFIG, self.buildings, b"x", [])

    @patch("ai_service.requests.post")
    def test_http_errors_timeouts_and_no_header_or_body_in_errors(self, post):
        for status, expected in [(400, "未接受"), (401, "拒绝"), (403, "拒绝"), (429, "受限"), (503, "503"), (302, "302")]:
            post.return_value = http_response({"debug": TEST_CONFIG.api_key}, status)
            with self.subTest(status=status), self.assertRaisesRegex(GuideError, expected) as caught:
                chat_json(TEST_CONFIG, [])
            self.assertNotIn(TEST_CONFIG.api_key, str(caught.exception))
        for error, expected in [(requests.Timeout, "超时"), (requests.ConnectionError, "无法连接")]:
            post.reset_mock()
            post.side_effect = error(TEST_CONFIG.api_key)
            with self.assertRaisesRegex(GuideError, expected) as caught:
                chat_json(TEST_CONFIG, [])
            self.assertNotIn(TEST_CONFIG.api_key, str(caught.exception))
            self.assertEqual(post.call_count, 1)
            self.assertFalse(post.call_args.kwargs["allow_redirects"])

    @patch("ai_service.requests.post")
    def test_malformed_and_truncated_model_responses(self, post):
        for data in ({}, {"choices": []}, envelope(None), envelope("普通文本"),
                     envelope("[]"), {"choices": [{"finish_reason": "length"}]}):
            post.return_value = http_response(data)
            with self.subTest(data=data), self.assertRaisesRegex(GuideError, "格式异常"):
                chat_json(TEST_CONFIG, [])
        post.return_value = http_response(envelope('```json\n{"ok":true}\n```'))
        self.assertEqual(chat_json(TEST_CONFIG, []), {"ok": True})
