# -*- coding: utf-8 -*-
"""绕过 pip，直接从 PyPI 下载 imageio-ffmpeg 的 wheel 并取出 ffmpeg.exe。

pip 在本环境因临时目录权限失败，但 urllib 下载正常，
而 imageio-ffmpeg 的 wheel 里就带着一个静态编译的 ffmpeg。
"""
import json
import os
import shutil
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TMP = os.path.join(ROOT, '.render', 'ffmpeg-dl')
DEST = os.path.join(ROOT, '.render', 'ffmpeg.exe')

os.makedirs(TMP, exist_ok=True)


def fetch(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': 'dsh-studio/2.0'})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, 'wb') as f:
        shutil.copyfileobj(r, f)
    return os.path.getsize(path)


def main():
    if os.path.exists(DEST):
        print('ffmpeg already present:', DEST)
        return 0

    meta = json.load(urllib.request.urlopen(
        urllib.request.Request('https://pypi.org/pypi/imageio-ffmpeg/json',
                               headers={'User-Agent': 'dsh-studio/2.0'}), timeout=60))
    urls = [u for u in meta['urls'] if u['filename'].endswith('win_amd64.whl')]
    if not urls:
        print('no win_amd64 wheel found; candidates:',
              [u['filename'] for u in meta['urls']][:8])
        return 1
    url = urls[0]['url']
    whl = os.path.join(TMP, urls[0]['filename'])
    print('downloading', urls[0]['filename'], '...')
    size = fetch(url, whl)
    print('  %.1f MB' % (size / 1e6))

    with zipfile.ZipFile(whl) as z:
        names = [n for n in z.namelist() if 'binaries' in n and n.endswith('.exe')]
        if not names:
            print('no exe in wheel:', z.namelist()[:10])
            return 1
        name = names[0]
        with z.open(name) as src, open(DEST, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    os.chmod(DEST, 0o755)
    print('extracted %s -> %.1f MB' % (name, os.path.getsize(DEST) / 1e6))
    return 0


if __name__ == '__main__':
    sys.exit(main())
