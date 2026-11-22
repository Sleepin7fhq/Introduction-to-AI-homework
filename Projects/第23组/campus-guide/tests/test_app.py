import unittest
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

from ai_service import NO_INFO, Config
from guide_data import GuideError, Source, load_catalog

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def setUp(self):
        cards = load_catalog(ROOT / "data/buildings.example.json")
        self.catalog = self.enterContext(patch("guide_data.load_catalog", return_value=cards))
        self.enterContext(patch("ai_service.requests.post", side_effect=AssertionError("界面测试意外联网")))
        self.settings = self.enterContext(patch("ai_service.read_settings", return_value=None))
        self.config = self.enterContext(patch("ai_service.cloud_config", return_value=Config(
            "test-only", "http://127.0.0.1:1/v1", "fixture-vision")))
        self.app = AppTest.from_file(str(ROOT / "app.py")).run()

    def tearDown(self):
        self.assertFalse(self.app.exception, [e.message for e in self.app.exception])

    def photo_mode(self):
        self.app.radio(key="route").set_value("从照片识别").run()

    def has_generate(self):
        return any(b.key == "generate" for b in self.app.button)

    def test_manual_guide_followups_and_building_switch(self):
        a = self.app
        self.assertEqual(a.radio(key="mode").value, "离线模拟")
        a.button(key="generate").click().run()
        self.assertTrue(a.button(key="generate").disabled)
        a.chat_input[0].set_value("圆窗在哪里？").run()
        a.chat_input[0].set_value("再说一遍").run()
        a.chat_input[0].set_value("建于哪一年？").run()
        self.assertEqual(len(a.session_state.visit.turns), 3)
        self.assertIn(NO_INFO, [x.value for x in a.text])
        a.radio(key="length").set_value("详细").run()
        a.button(key="generate").click().run()
        self.assertEqual(len(a.session_state.visit.guides["详细"].fact_ids), 3)
        self.assertEqual(len(a.session_state.visit.turns), 3)
        a.selectbox(key="manual").set_value("B").run()
        self.assertFalse(a.session_state.visit.guides or a.session_state.visit.turns)
        self.assertFalse(a.chat_input)
        a.selectbox(key="manual").set_value("A").run()
        self.assertFalse(a.session_state.visit.turns)

    def test_photo_confirmation_correction_and_replacement(self):
        a = self.app
        self.photo_mode()
        name = "same-name.png"
        a.file_uploader[0].set_value((name, (ROOT / "data/demo-a.png").read_bytes(), "image/png")).run()
        a.button(key="identify").click().run()
        self.assertEqual(a.session_state.visit.result.building_id, "A")
        self.assertFalse(self.has_generate())
        a.selectbox[0].set_value("C").run()
        a.button(key="confirm").click().run()
        a.button(key="generate").click().run()
        a.chat_input[0].set_value("塔身有什么窗？").run()
        self.assertEqual(a.session_state.visit.building_id, "C")
        a.selectbox[0].set_value("B").run()
        self.assertFalse(self.has_generate())
        self.assertFalse(a.session_state.visit.turns)
        a.button(key="confirm").click().run()
        a.button(key="generate").click().run()
        raw = BytesIO()
        Image.new("RGB", (50, 30), "navy").save(raw, "PNG")
        a.file_uploader[0].set_value((name, raw.getvalue(), "image/png")).run()
        self.assertIsNone(a.session_state.visit.result)
        self.assertIsNone(a.session_state.visit.building_id)
        self.assertFalse(a.session_state.visit.guides or a.session_state.visit.turns)
        a.button(key="identify").click().run()
        self.assertEqual(a.session_state.visit.result.building_id, "无法确定")
        self.assertIsNone(a.selectbox[0].value)
        self.assertTrue(a.button(key="confirm").disabled)
        a.file_uploader[0].set_value((name, b"broken", "image/png")).run()
        self.assertTrue(a.error)
        self.assertIsNone(a.session_state.visit.result)
        a.file_uploader[0].clear().run()
        self.assertIsNone(a.session_state.visit.photo)

    def test_no_requests_on_rerun_or_confirmation(self):
        a = self.app
        with patch("ai_service.chat_json", side_effect=[
            {"building_id": "B", "reason": "能看到平顶长廊。"},
            {"coverage": "full", "fact_ids": ["columns"]},
            {"coverage": "none", "fact_ids": []},
        ]) as api:
            a.radio(key="mode").set_value("真实 API").run()
            self.photo_mode()
            a.file_uploader[0].set_value(("test.png", (ROOT / "data/demo-a.png").read_bytes(), "image/png")).run()
            self.assertEqual(api.call_count, 0)
            a.button(key="identify").click().run()
            a.run()
            a.button(key="confirm").click().run()
            a.radio(key="length").set_value("详细").run()
            self.assertEqual(api.call_count, 1)
            a.button(key="generate").click().run()
            a.run()
            a.chat_input[0].set_value("建于哪年？").run()
            a.run()
            a.radio(key="length").set_value("简短").run()
            self.assertEqual(api.call_count, 3)
            a.radio(key="mode").set_value("离线模拟").run()
            self.assertIsNone(a.session_state.visit.result)
            self.assertFalse(a.session_state.visit.turns)

    def test_missing_config_and_failed_response_never_switch_to_mock(self):
        a = self.app
        self.config.side_effect = GuideError("未找到 config.toml")
        a.radio(key="mode").set_value("真实 API").run()
        self.assertIn("config.toml", a.warning[0].value)
        self.assertTrue(a.button(key="generate").disabled)
        self.config.side_effect = None
        a.run()
        with patch("ai_service.chat_json", side_effect=GuideError("接口等待超时")) as api:
            a.button(key="generate").click().run()
            self.assertIn("超时", a.error[0].value)
            self.assertFalse(a.session_state.visit.guides)
            a.run()
            self.assertEqual(api.call_count, 1)

    def test_only_the_local_source_url_is_offered(self):
        a = self.app
        cards = self.catalog.return_value.copy()
        card = cards["A"]
        facts = card.facts.copy()
        facts["window"] = replace(facts["window"], source_ids=("field", "web"))
        url = "https://example.invalid/fixture"
        sources = {"field": Source("field", "测试记录", ""), "web": Source("web", "测试网页", url)}
        cards["A"] = replace(card, sources=sources, facts=facts, placeholder=False)
        self.catalog.return_value = cards
        a.radio(key="mode").set_value("真实 API").run()
        with patch("ai_service.chat_json", return_value={
            "coverage": "full", "fact_ids": ["window"], "url": "https://invented.invalid",
        }):
            a.button(key="generate").click().run()
            a.chat_input[0].set_value("圆窗在哪里？").run()
        self.assertFalse(a.link_button)
        footers = [x.proto.body for x in a.get("html")]
        self.assertEqual(len(footers), 2)
        self.assertTrue(all(t.count(url) == 1 and "测试记录" in t and "invented.invalid" not in t for t in footers))

    def test_catalog_can_be_corrected_after_file_error(self):
        a = self.app
        a.button(key="generate").click().run()
        self.catalog.side_effect = GuideError("建筑资料 JSON 第 1 行附近格式有误")
        a.run()
        self.assertTrue(a.error)
        self.assertFalse(self.has_generate())
        self.catalog.side_effect = None
        a.run()
        self.assertTrue(self.has_generate())
        self.assertFalse(a.session_state.visit.guides)

    def test_unconfigured_web_search_leaves_local_guide_available(self):
        a = self.app
        self.settings.return_value = {"SEARCH_ENABLED": True}
        a.run()
        self.assertTrue(any("尚未配置搜索服务" in c.value and "暂不可用" in c.value for c in a.caption))
        a.button(key="generate").click().run()
        self.assertTrue(a.session_state.visit.guides)
        self.settings.side_effect = GuideError("无法读取 config.toml")
        a.run()
        self.assertTrue(a.chat_input)
        a.radio(key="mode").set_value("真实 API").run()
        self.assertTrue(a.button(key="generate").disabled)

    def test_failed_question_only_retried_on_click(self):
        a = self.app
        a.radio(key="mode").set_value("真实 API").run()
        with patch("ai_service.chat_json", side_effect=[
            {"coverage": "full", "fact_ids": ["window"]}, GuideError("接口等待超时"),
            {"coverage": "full", "fact_ids": ["window"]},
        ]) as api:
            a.button(key="generate").click().run()
            a.chat_input[0].set_value("圆窗呢？").run()
            self.assertEqual(a.session_state.visit.failed_question, "圆窗呢？")
            self.assertFalse(a.session_state.visit.turns)
            a.run()
            self.assertEqual(api.call_count, 2)
            a.button(key="retry_question").click().run()
            a.run()
            self.assertEqual(api.call_count, 3)
            self.assertEqual(len(a.session_state.visit.turns), 1)
            self.assertFalse(a.session_state.visit.failed_question)

    def test_bad_reference_leaves_manual_correction_available(self):
        a = self.app
        cards = self.catalog.return_value.copy()
        cards["B"] = replace(cards["B"], reference_images=("missing-test-fixture.jpg",))
        self.catalog.return_value = cards
        a.radio(key="mode").set_value("真实 API").run()
        self.photo_mode()
        a.file_uploader[0].set_value(("test.png", (ROOT / "data/demo-a.png").read_bytes(), "image/png")).run()
        a.button(key="identify").click().run()
        self.assertIn("参考图", a.error[0].value)
        a.selectbox[0].set_value("B").run()
        a.button(key="confirm").click().run()
        self.assertTrue(self.has_generate())
