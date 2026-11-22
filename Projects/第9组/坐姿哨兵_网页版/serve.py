# -*- coding: utf-8 -*-
"""网页版本地服务器。

- 自动挑一个没被占用的端口（8765 起）
- 自动打开浏览器
- 只监听 127.0.0.1，局域网里别人访问不到

    python serve.py
"""
import functools
import http.server
import os
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 安静一点，别刷屏

    def end_headers(self):
        # 防止浏览器缓存旧页面
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    httpd = None
    port = None
    for p in range(8765, 8785):
        try:
            httpd = socketserver.ThreadingTCPServer(
                ("127.0.0.1", p),
                functools.partial(Handler, directory=ROOT))
            port = p
            break
        except OSError:
            continue

    if httpd is None:
        print("8765-8784 端口都被占用了。请关掉一些程序再试。")
        try:
            input("按回车退出…")
        except EOFError:
            pass
        return 1

    url = f"http://localhost:{port}/index.html"
    print("=" * 52)
    print("  坐姿哨兵 网页版")
    print("=" * 52)
    print(f"  地址：{url}")
    print("  浏览器没自动打开的话，手动复制上面这行。")
    print("  关掉这个窗口，服务就停了。")
    print("=" * 52)

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
