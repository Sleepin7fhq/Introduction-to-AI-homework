"""等待 DSH Studio 的两个服务就绪。

用法: python scripts/wait_ready.py [超时秒数]
退出码 0 = 两个服务都就绪；1 = 超时或有服务没起来。

输出一律用 ASCII：这个脚本常被 .bat / PowerShell 以子进程方式调用，
Windows 控制台默认代码页是 936，中文 UTF-8 会显示成乱码。
"""
import json
import sys
import time
import urllib.request

FRONT = 'http://127.0.0.1:5173/'
ACE = 'http://127.0.0.1:8000/health'


def probe(url, timeout=2.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read(600)
    except Exception:
        return None, b''


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    deadline = time.time() + limit
    front_ok = False
    ace_ok = False
    ace_state = 'no-response'
    last_print = 0.0

    while time.time() < deadline:
        if not front_ok:
            status, _ = probe(FRONT)
            front_ok = status == 200

        if not ace_ok:
            status, body = probe(ACE)
            if status == 200:
                try:
                    data = json.loads(body)
                    ace_state = data.get('status', 'unknown')
                    ace_ok = ace_state == 'ready'
                except Exception:
                    ace_state = 'bad-json'
            else:
                ace_state = 'no-response'

        now = time.time()
        if now - last_print > 3:
            print('   frontend: %-6s | ace-step: %s'
                  % ('ready' if front_ok else 'waiting', ace_state), flush=True)
            last_print = now

        if front_ok and ace_ok:
            break
        time.sleep(1.5)

    print('')
    if front_ok and ace_ok:
        print('   [OK] frontend ready : http://127.0.0.1:5173/')
        print('   [OK] ace-step ready : http://127.0.0.1:8000/health')
        return 0

    if not front_ok:
        print('   [FAIL] frontend 5173 not responding')
    if not ace_ok:
        print('   [FAIL] ace-step not ready (state: %s)' % ace_state)
        print('          first load takes 15-20s; check the ACE window for errors')
    return 1


if __name__ == '__main__':
    sys.exit(main())
