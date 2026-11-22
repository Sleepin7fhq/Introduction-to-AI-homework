"""在系统分配的回环端口运行一次完整的 HTTP 协议测试。"""

import base64
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ai_service import SHORT, Config, guide_answer, recognize
from guide_data import load_catalog
from photos import prepare_photo

ROOT = Path(__file__).resolve().parents[1]


class LocalHttpTests(unittest.TestCase):
    def test_real_http_transport_with_local_stand_in(self):
        packets = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                packets.append((self.path, self.headers.get("Authorization"), data))
                if isinstance(data["messages"][-1]["content"], list):
                    answer = {"building_id": "B", "reason": "测试桩固定返回方柱特征。"}
                else:
                    answer = {"coverage": "full", "fact_ids": ["columns"]}
                body = json.dumps({"choices": [{"message": {"content": json.dumps(answer)}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            thread.start()
            try:
                cfg = Config("local-test-only", f"http://127.0.0.1:{server.server_port}/v1", "fixture-vision")
                cards = load_catalog(ROOT / "data/buildings.example.json")
                target = prepare_photo((ROOT / "data/demo-a.png").read_bytes())
                refs = []
                for bid, color in (("A", "blue"), ("B", "tan"), ("C", "green")):
                    raw = BytesIO()
                    Image.new("RGB", (32, 32), color).save(raw, "PNG")
                    refs.append((bid, prepare_photo(raw.getvalue())))
                with patch.dict(os.environ, {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}):
                    prediction = recognize(cfg, cards, target, refs)
                    guide = guide_answer(cards[prediction.building_id], SHORT, cfg)
                    answer = guide_answer(cards["B"], SHORT, cfg, question="这些柱子是什么形状？", guide=guide)
                self.assertEqual(prediction.building_id, "B")
                self.assertEqual(answer.fact_ids, ("columns",))
            finally:
                server.shutdown()
                thread.join()

        self.assertEqual(len(packets), 3)
        for path, auth, body in packets:
            self.assertEqual(path, "/v1/chat/completions")
            self.assertEqual(auth, "Bearer local-test-only")
            self.assertEqual(body["model"], "fixture-vision")
            self.assertFalse(body["stream"])
        parts = packets[0][2]["messages"][-1]["content"]
        self.assertEqual(len(parts), 9)
        self.assertIn("候选资料", parts[0]["text"])
        for i, (bid, expected) in enumerate(refs):
            self.assertIn(f"已知建筑编号 {bid}", parts[1 + 2 * i]["text"])
            encoded = parts[2 + 2 * i]["image_url"]["url"]
            self.assertEqual(encoded, "data:image/jpeg;base64," + base64.b64encode(expected).decode())
        self.assertIn("待识别图", parts[-2]["text"])
        self.assertEqual(base64.b64decode(parts[-1]["image_url"]["url"].split(",")[1]), target)
        self.assertTrue(all(isinstance(m["content"], str) for m in packets[2][2]["messages"]))
