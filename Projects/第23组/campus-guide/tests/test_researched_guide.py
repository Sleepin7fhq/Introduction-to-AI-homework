import json
import unittest
import re
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ai_service import DETAIL, NO_INFO, SHORT, UNKNOWN, Config, guide_answer
from guide_data import GuideError, load_catalog

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/buildings.json"


class ResearchedGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = load_catalog(CATALOG)

    def test_research_and_photo_sources(self):
        dossier = json.loads((ROOT / "docs/建筑资料核查_2026-11-20.json").read_text(encoding="utf-8"))
        urls = {item["id"]: item["url"] for item in dossier["sources"]}
        used = set()
        for row in dossier["buildings"]:
            card = self.cards[row["existing_id"]]
            facts = row.get("facts", row.get("facts_for_identified_library"))
            for fact in facts:
                with self.subTest(building=card.id, fact=fact["id"]):
                    ids = card.facts[fact["id"]].source_ids
                    self.assertTrue(set(fact["source_ids"]).issubset(ids))
                    self.assertTrue(all(sid in urls for sid in ids))
            for fact in card.facts.values():
                for sid in fact.source_ids:
                    if card.sources[sid].url:
                        self.assertEqual(card.sources[sid].url, urls[sid])
                        used.add(sid)
            photo_facts = [f for f in card.facts.values() if f.source_ids in (("front_photo",), ("side_photo",))]
            self.assertEqual(len(photo_facts), 4)
        self.assertEqual(used, set(urls))
        lib = self.cards["C"]
        self.assertEqual((lib.name, lib.photo_label), ("四牌楼校区图书馆", ""))
        self.assertEqual(lib.reference_images, ("四牌楼校区图书馆-正面.jpg", "四牌楼校区图书馆-侧墙.jpg"))

    def test_default_introductions_and_expansion_discrepancy(self):
        for bid, year in (("A", "1929"), ("B", "1923"), ("C", "1985")):
            card = self.cards[bid]
            short = guide_answer(card, SHORT, None)
            opening, observation = [card.facts[fid] for fid in short.fact_ids]
            self.assertIn(year, opening.text)
            self.assertTrue(all(card.sources[sid].url for sid in opening.source_ids))
            self.assertEqual(observation.source_ids, ("front_photo",))
        a = self.cards["A"]
        detail = "".join(guide_answer(a, DETAIL, None).paragraphs(a))
        self.assertIn("20世纪50年代后期", detail)
        self.assertNotIn("1957", detail)
        self.assertNotIn("1958", detail)
        answer = guide_answer(a, SHORT, None, question="中大院是哪一年扩建的？")
        dispute = answer.paragraphs(a)[0]
        for term in ("1957", "1958", "校友总会", "建筑学院", "沈国尧"):
            self.assertIn(term, dispute)
        self.assertEqual({source.id for source in answer.sources(a)}, {"S1", "S2", "S3"})

    def test_followups_and_gaps(self):
        cases = [("A", "以前叫什么，是谁设计的？", "李宗侃"),
                 ("B", "泰戈尔和谁一起来演讲？", "徐志摩"),
                 ("C", "外墙的八字是什么意思？", "严谨、求实、团结、奋进"),
                 ("C", "怎么判断拍的是哪座图书馆？", "正面实拍"),
                 ("C", "这里是邵逸夫捐建的吗？", "尚未找到"),
                 ("C", "它和孟芳图书馆有什么区别？", "1985")]
        for bid, question, expected in cases:
            with self.subTest(bid=bid, question=question):
                card = self.cards[bid]
                answer = guide_answer(card, SHORT, None, question=question)
                self.assertIn(expected, "".join(answer.paragraphs(card)))
        for card in self.cards.values():
            answer = guide_answer(card, SHORT, None, question=f"{card.name}2026年周日几点开放？")
            self.assertEqual(answer.paragraphs(card), [NO_INFO])
            self.assertFalse(answer.sources(card))
        b = self.cards["B"]
        task = guide_answer(b, SHORT, None, question="攀岩区有6000平方米吗？")
        self.assertIn("学生要设计", task.paragraphs(b)[0])
        self.assertEqual([source.id for source in task.sources(b)], ["S4"])
        c = self.cards["C"]
        old_library = guide_answer(c, SHORT, None, question="孟芳图书馆哪年建成？")
        for year in ("1923", "1924", "1985"):
            self.assertIn(year, old_library.paragraphs(c)[0])

    @patch("ai_service.chat_json")
    def test_model_only_receives_brief_facts_until_a_question_is_asked(self, chat):
        cfg = Config("fixture", "http://127.0.0.1:1", "fixture")
        a = self.cards["A"]
        chat.return_value = {"coverage": "full", "fact_ids": ["origin", "front"]}
        guide_answer(a, SHORT, cfg)
        prompt = json.loads(chat.call_args.args[1][-1]["content"])
        self.assertEqual(list(prompt["当前建筑卡"]["事实"]), ["origin", "front"])
        chat.return_value = {"coverage": "full", "fact_ids": ["expansion_dates"]}
        with self.assertRaises(GuideError):
            guide_answer(a, SHORT, cfg)
        answer = guide_answer(a, SHORT, cfg, question="扩建年份怎么有两种说法？")
        self.assertEqual(answer.fact_ids, ("expansion_dates",))

    def test_real_cards_in_offline_interface(self):
        with patch("ai_service.read_settings", return_value=None), patch(
                "ai_service.requests.post", side_effect=AssertionError("离线界面意外联网")):
            app = AppTest.from_file(str(ROOT / "app.py")).run()
            for card in self.cards.values():
                app.selectbox(key="manual").set_value(card.id).run()
                self.assertIn(card.name, [h.value for h in app.subheader])
                self.assertFalse(any("馆名待" in c.value or "照片原标注" in c.value for c in app.caption))
                app.button(key="generate").click().run()
                intro, observation = [card.facts[fid] for fid in card.guide_fact_ids[:2]]
                self.assertEqual([url for x in app.get("html") for url in re.findall(r'href="([^"]+)"', x.proto.body)],
                                 [card.sources[sid].url for sid in intro.source_ids])
                self.assertIn(observation.text, [p.value for p in app.text])
                self.assertIn(card.sources["front_photo"].title, app.get("html")[0].proto.body)
                question, fact_id = {
                    "A": ("中大院具体是哪年扩建的？", "expansion_dates"),
                    "B": ("是谁陪同泰戈尔来演讲的？", "tagore"),
                    "C": ("这座馆正式叫逸夫图书馆吗？", "name_check"),
                }[card.id]
                before = len(app.get("html"))
                app.chat_input[0].set_value(question).run()
                fact = card.facts[fact_id]
                self.assertIn(fact.text, [p.value for p in app.text])
                self.assertEqual([url for x in app.get("html")[before:] for url in re.findall(r'href="([^"]+)"', x.proto.body)],
                                 [card.sources[sid].url for sid in fact.source_ids])
                app.chat_input[0].set_value("2026年周日几点开放？").run()
                self.assertEqual(app.session_state.visit.turns[-1].answer.paragraphs(card), [NO_INFO])
                self.assertFalse(app.exception)

    def test_seven_held_out_photos_can_be_confirmed_offline(self):
        with patch("ai_service.read_settings", return_value=None), patch(
                "ai_service.requests.post", side_effect=AssertionError("离线界面意外联网")):
            app = AppTest.from_file(str(ROOT / "app.py")).run()
            app.radio(key="route").set_value("从照片识别").run()
            for i, bid in enumerate("AAABBBC", start=1):
                card = self.cards[bid]
                path = ROOT / "data/test_images" / f"T{i:02d}.jpg"
                app.file_uploader[0].set_value((path.name, path.read_bytes(), "image/jpeg")).run()
                self.assertFalse(app.session_state.visit.guides)
                app.button(key="identify").click().run()
                self.assertEqual(app.session_state.visit.result.building_id, UNKNOWN)
                app.selectbox[0].set_value(bid).run()
                app.button(key="confirm").click().run()
                app.button(key="generate").click().run()
                self.assertEqual(app.session_state.visit.guides[SHORT].fact_ids, card.guide_fact_ids[:2])
                self.assertFalse(app.exception)
