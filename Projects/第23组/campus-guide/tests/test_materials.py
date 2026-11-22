import json
import tempfile
import unittest
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ai_service import Answer
from guide_data import GuideError, load_catalog
from photos import MAX_BYTES, prepare_photo, read_photo, reference_photos

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data/buildings.example.json"


class MaterialsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.cards = self.directory / "cards.json"
        self.rows = json.loads(CARDS.read_text(encoding="utf-8"))

    def save(self):
        self.cards.write_text(json.dumps(self.rows, ensure_ascii=False), encoding="utf-8")
        return load_catalog(self.cards)

    def test_three_placeholders_have_no_invented_sources(self):
        cards = load_catalog(CARDS)
        self.assertEqual(list(cards), ["A", "B", "C"])
        self.assertTrue(all(b.placeholder and not b.sources and not b.reference_images for b in cards.values()))

    def test_sources_resolve_only_for_the_selected_facts(self):
        row = self.rows[0]
        row["sources"] = [
            {"id": "note", "title": "测试用现场记录", "url": ""},
            {"id": "page", "title": "测试用网页", "url": "https://example.invalid/test"},
        ]
        row["facts"][0]["source_ids"] = ["note", "page"]
        row["facts"][1]["source_ids"] = ["note"]
        building = self.save()["A"]
        sources = Answer(("window", "entrance")).sources(building)
        self.assertEqual([(s.id, s.url) for s in sources], [("note", ""), ("page", "https://example.invalid/test")])
        self.assertEqual(Answer(("sides",)).sources(building), [])

    def test_broken_source_reference_is_explained(self):
        self.rows[0]["facts"][0]["source_ids"] = ["unlisted"]
        with self.assertRaisesRegex(GuideError, "不存在的编号"):
            self.save()

    def test_bad_file_or_schema(self):
        with self.assertRaisesRegex(GuideError, "无法读取"):
            load_catalog(self.cards)
        self.cards.write_text("[{", encoding="utf-8")
        with self.assertRaisesRegex(GuideError, "第 1 行"):
            load_catalog(self.cards)
        self.rows[1]["id"] = "A"
        with self.assertRaisesRegex(GuideError, "编号须唯一"):
            self.save()

    def test_invalid_source_and_reference_path(self):
        self.rows[0]["sources"] = [{"id": "x", "title": "测试", "url": "javascript:void(0)"}]
        with self.assertRaisesRegex(GuideError, "网页地址"):
            self.save()
        self.rows[0]["sources"] = []
        self.rows[0]["reference_images"] = ["../outside.jpg"]
        with self.assertRaisesRegex(GuideError, "文件名"):
            self.save()

    def test_rotate_resize_and_remove_camera_metadata(self):
        raw = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = "test camera note"
        Image.new("RGB", (1600, 800), "tan").save(raw, "JPEG", exif=exif)
        processed = prepare_photo(raw.getvalue())
        with Image.open(BytesIO(processed)) as result:
            self.assertEqual((result.format, result.mode, result.size), ("JPEG", "RGB", (640, 1280)))
            self.assertFalse(result.getexif())

    def test_png_transparency_and_reference_resize(self):
        path = self.directory / "ref.png"
        Image.new("RGBA", (90, 900), (0, 0, 0, 0)).save(path)
        cards = load_catalog(CARDS)
        cards["C"] = replace(cards["C"], reference_images=("ref.png",))
        [(bid, photo)] = reference_photos(self.directory, cards)
        with Image.open(BytesIO(photo)) as im:
            self.assertEqual((bid, im.height, im.getpixel((0, 0))), ("C", 768, (255, 255, 255)))

    def test_invalid_truncated_and_oversized_photos(self):
        raw = (ROOT / "data/demo-a.png").read_bytes()
        for data in (b"", b"fake jpeg", raw[:100], raw[:len(raw) // 2]):
            with self.subTest(size=len(data)), self.assertRaises(GuideError):
                prepare_photo(data)
        with self.assertRaisesRegex(GuideError, "12 MB"):
            prepare_photo(bytes(MAX_BYTES + 1))
        with patch("photos.MAX_PIXELS", 300), self.assertRaisesRegex(GuideError, "像素"):
            prepare_photo(raw)

    def test_missing_or_unreadable_reference_keeps_building_name(self):
        cards = load_catalog(CARDS)
        cards["B"] = replace(cards["B"], reference_images=("missing.png",))
        with self.assertRaisesRegex(GuideError, "示例建筑 B.*missing.png"):
            reference_photos(self.directory, cards)
        with self.assertRaisesRegex(GuideError, "缺失"):
            read_photo(self.directory / "missing.png")
