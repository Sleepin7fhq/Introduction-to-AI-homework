#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「梦见月瑞习」Demo 服务端 —— 纯标准库，零依赖。

    python3 server.py            # 默认 http://127.0.0.1:8770
    DSH_DEMO_PORT=8080 python3 server.py

可选环境变量（接真模型时用）：
    DSH_DEMO_API_KEY   你的 API Key
    DSH_DEMO_API_BASE  默认 https://api.deepseek.com
    DSH_DEMO_MODEL     默认 deepseek-chat
"""

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "vendor"))   # 内置的二维码库，免 pip install

import engine  # noqa: E402
import knowledge  # noqa: E402
import practice  # noqa: E402


STATIC = os.path.join(HERE, "static")
CONFIG_PATH = os.path.join(HERE, "config.json")
DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}

LOCK = threading.Lock()

# 课堂模式：谁在线
ONLINE = {}
ONLINE_TTL = 25


def touch(sid):
    import time as _t
    ONLINE[sid] = _t.time()
    if len(ONLINE) > 500:
        now = _t.time()
        for k in [k for k, v in ONLINE.items() if now - v > ONLINE_TTL]:
            ONLINE.pop(k, None)


def online_count():
    import time as _t
    now = _t.time()
    return sum(1 for v in ONLINE.values() if now - v <= ONLINE_TTL)


def qr_svg(text):
    import io
    try:
        import qrcode
        import qrcode.image.svg
        img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, border=2)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">'
                '<rect width="300" height="300" fill="#fff"/>'
                '<text x="150" y="150" text-anchor="middle" font-size="14" fill="#B4552F">'
                '二维码生成失败</text></svg>')


def load_config():
    """优先级：环境变量 > config.json > 默认值。"""
    cfg = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f) or {}
    except Exception:  # noqa: BLE001
        cfg = {}
    try:
        engine.configure_visitor(enabled=bool(cfg.get("visitor_ai", True)),
                                 limit=int(cfg.get("visitor_ai_limit", 300)))
    except Exception:  # noqa: BLE001
        pass
    key = os.environ.get("DSH_DEMO_API_KEY") or cfg.get("api_key", "")
    base = os.environ.get("DSH_DEMO_API_BASE") or cfg.get("api_base", "") or DEFAULT_BASE
    model = os.environ.get("DSH_DEMO_MODEL") or cfg.get("model", "") or DEFAULT_MODEL
    engine.configure(key=key, base=base, model=model)
    return {"source": "env" if os.environ.get("DSH_DEMO_API_KEY") else ("file" if cfg.get("api_key") else "none")}


def save_config(key, base, model):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"api_key": key, "api_base": base, "model": model},
                  f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:  # noqa: BLE001
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = "MengJianYue/1.0"

    def log_message(self, fmt, *args):  # 静音
        pass

    # ---------------------------------------------------------- helpers
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json_body(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _static(self, path):
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
        else:
            rel = path.lstrip("/")
        if rel in ("", "index.html"):
            rel = "index.html"
        full = os.path.normpath(os.path.join(STATIC, rel))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---------------------------------------------------------- routes
    def do_GET(self):
        engine.set_client(self.client_address[0] in ("127.0.0.1", "::1"))
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/api/health":
            return self._send(200, {
                "ok": True,
                "engine": engine.engine_name(),
                "llm": engine.llm_enabled(),
                "concepts": len(knowledge.CONCEPTS),
                "key": engine.mask_key(),
                "base": engine.API_BASE,
                "model": engine.API_MODEL,
            })
        if path == "/api/concepts":
            return self._send(200, {"groups": knowledge.list_concepts()})
        if path == "/classroom":
            return self._static("/classroom.html")
        if path == "/api/qr.svg":
            txt = (qs.get("text") or ["http://127.0.0.1:8770/"])[0][:300]
            svg = qr_svg(txt)
            return self._send(200, svg, "image/svg+xml; charset=utf-8")
        if path == "/api/classroom":
            port = int(os.environ.get("DSH_DEMO_PORT", "8770"))
            host = os.environ.get("DSH_DEMO_HOST", "127.0.0.1")
            ips = lan_ips() if host in ("0.0.0.0", "") else []
            return self._send(200, {
                "lan": bool(ips),
                "urls": ["http://%s:%d/" % (ip, port) for ip in ips],
                "local": "http://127.0.0.1:%d/" % port,
                "online": online_count(),
            })
        if path == "/api/usage":
            u = engine.usage()
            u["is_local"] = engine.is_local()
            u["llm_now"] = engine.llm_enabled()
            return self._send(200, u)
        if path == "/api/online":
            return self._send(200, {"online": online_count()})
        return self._static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        engine.set_client(self.client_address[0] in ("127.0.0.1", "::1"))
        body = self._json_body()

        try:
            if path == "/api/start":
                sid = body.get("sid") or uuid.uuid4().hex[:12]
                with LOCK:
                    res = engine.api_start(sid, body.get("concept_id", ""), body.get("custom_name", ""))
                res["sid"] = sid
                return self._send(200, res)

            if path == "/api/explain":
                with LOCK:
                    res = engine.api_explain(body.get("sid", ""), body.get("text", ""))
                code = 400 if "error" in res else 200
                return self._send(code, res)

            if path == "/api/answer":
                with LOCK:
                    res = engine.api_answer(body.get("sid", ""), body.get("text", ""))
                code = 400 if "error" in res else 200
                return self._send(code, res)

            if path == "/api/visitor-ai":
                if self.client_address[0] not in ("127.0.0.1", "::1"):
                    return self._send(403, {"error": "只允许在本机修改"})
                engine.configure_visitor(enabled=bool(body.get("enabled")))
                if body.get("limit") is not None:
                    engine.configure_visitor(limit=body.get("limit"))
                u = engine.usage()
                u["is_local"] = True
                return self._send(200, u)

            if path == "/api/ping":
                sid = str(body.get("sid", ""))[:40]
                if sid:
                    touch(sid)
                return self._send(200, {"online": online_count()})

            if path == "/api/practice/generate":
                return self._send(200, practice.generate(
                    body.get("subject", "linear"), body.get("difficulty", 3),
                    body.get("count", 1)))

            if path == "/api/practice/grade":
                return self._send(200, {"grade": practice.grade(
                    body.get("qid", ""), body.get("answer", ""), body.get("image", ""))})

            if path == "/api/practice/upload":
                return self._send(200, practice.from_file(
                    body.get("name", ""), body.get("data", ""),
                    body.get("subject", "linear"), body.get("difficulty", 3),
                    body.get("count", 5)))

            if path == "/api/config":
                if self.client_address[0] not in ("127.0.0.1", "::1"):
                    return self._send(403, {"error": "只允许在本机修改配置"})
                key = (body.get("api_key") or "").strip()
                base = (body.get("api_base") or DEFAULT_BASE).strip().rstrip("/")
                model = (body.get("model") or DEFAULT_MODEL).strip()
                if not key:
                    engine.configure(key="", base=base, model=model)
                    save_config("", base, model)
                    return self._send(200, {"ok": True, "llm": False,
                                            "engine": engine.engine_name()})
                save_config(key, base, model)
                engine.configure(key=key, base=base, model=model)
                return self._send(200, {"ok": True, "llm": True,
                                        "engine": engine.engine_name(),
                                        "key": engine.mask_key()})

            if path == "/api/test-llm":
                if not engine.llm_enabled():
                    return self._send(200, {"ok": False, "hint": "还没有填入 API Key"})
                return self._send(200, engine.test_connection())

            if path == "/api/diagnose":
                with LOCK:
                    res = engine.api_diagnose(body.get("sid", ""))
                code = 400 if "error" in res else 200
                return self._send(code, res)

            return self._send(404, {"error": "no route"})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"error": "服务器内部错误: %s" % exc})


def keep_awake():
    """阻止 Windows 睡眠，避免演示到一半屏幕黑了、全班断线。"""
    if os.name != "nt":
        return False
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        return True
    except Exception:  # noqa: BLE001
        return False


def lan_ips():
    """列出本机可能的局域网地址，按「像不像真的 Wi-Fi」排序。

    注意：不能简单把 .255 当成广播地址——/16 的网段里 .255 是合法主机
    （我们这台机器的 Wi-Fi 地址就是 10.198.96.255）。
    """
    import re
    import socket

    found = []
    try:
        s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_.connect(("8.8.8.8", 80))
        found.append(s_.getsockname()[0])
        s_.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        found.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except Exception:  # noqa: BLE001
        pass

    out, seen = [], set()
    for ip in found:
        if ip in seen or ip.startswith(("127.", "169.254.")):
            continue
        seen.add(ip)
        out.append(ip)

    def score(ip):
        v = 0
        if ip.startswith("192.168."):
            v += 30                     # 家庭/宿舍路由器最常见
        elif ip.startswith("10."):
            v += 25                     # 校园网、公司网常见
        elif re.match(r"172\.(1[6-9]|2\d|3[01])\.", ip):
            v += 3                      # 这个段常被 WSL / Hyper-V / Docker 占用
        else:
            v += 15
        if ip.endswith(".255"):
            v -= 6                      # 有可能是广播地址，但不确定，只降权不排除
        return v

    out.sort(key=score, reverse=True)
    return out[:4]


def apply_args():
    """支持 python server.py --lan --open --port=8770，方便做成快捷方式。"""
    args = sys.argv[1:]
    if "--lan" in args:
        os.environ["DSH_DEMO_HOST"] = "0.0.0.0"
    if "--open" in args:
        os.environ["DSH_DEMO_OPEN"] = "1"
    for a in args:
        if a.startswith("--port="):
            os.environ["DSH_DEMO_PORT"] = a.split("=", 1)[1]


def main():
    apply_args()
    info = load_config()
    port = int(os.environ.get("DSH_DEMO_PORT", "8770"))
    host = os.environ.get("DSH_DEMO_HOST", "127.0.0.1")
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    print("=" * 58, flush=True)
    print("  梦见月瑞习 Demo 已启动", flush=True)
    print("  本机: http://127.0.0.1:%d" % port, flush=True)
    if host in ("0.0.0.0", ""):
        if keep_awake():
            print("  已阻止系统睡眠（演示期间不会黑屏断线）", flush=True)
        ips = lan_ips()
        if ips:
            for ip in ips:
                print("  局域网: http://%s:%d   （同一 Wi-Fi 下都能打开，逐个试）" % (ip, port), flush=True)
        else:
            print("  局域网: 没拿到本机 IP，用 ipconfig 查一下再拼 :%d" % port, flush=True)
    print("  引擎: %s" % engine.engine_name(), flush=True)
    if engine.llm_enabled():
        print("  Key : %s   (来源: %s)" % (engine.mask_key(), info["source"]), flush=True)
    print("  概念包: %d 个" % len(knowledge.CONCEPTS), flush=True)
    print("=" * 58, flush=True)
    if os.environ.get("DSH_DEMO_OPEN"):
        import threading as _th
        import webbrowser

        def _open():
            import time as _t
            _t.sleep(0.8)
            try:
                webbrowser.open("http://127.0.0.1:%d/classroom" % port)
            except Exception:  # noqa: BLE001
                pass

        _th.Thread(target=_open, daemon=True).start()

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
