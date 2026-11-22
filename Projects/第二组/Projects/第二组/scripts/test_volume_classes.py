"""Regression: low-level environmental gate, speech separation, removed music and alerts."""
import json
import math
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ui'))
from kernel_client import KernelClient

exe = ROOT / 'build/bin/dorm_noise_kernel.exe'
model = ROOT / 'models/ast_audioset_int8.onnx'

def infer(path):
    p = subprocess.run([str(exe), '--model', str(model), '--offline', str(path)],
                       capture_output=True, timeout=40)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])['segments']

with tempfile.TemporaryDirectory() as td:
    silence = Path(td) / 'silence.wav'
    with wave.open(str(silence), 'wb') as w:
        w.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        w.writeframes(bytes(16000 * 2 * 2))
    low = Path(td) / 'low_speech.wav'
    import array
    with wave.open(str(ROOT / 'assets/audio_demo/real_speech_0.wav'), 'rb') as r:
        params = r.getparams()
        pcm = array.array('h', r.readframes(r.getnframes()))
    quiet = array.array('h', (int(v * 0.0001) for v in pcm))
    with wave.open(str(low), 'wb') as w:
        w.setparams(params)
        w.writeframes(quiet.tobytes())
    for path in (silence, low):
        segs = infer(path)
        assert segs and all(s['class_key'] == 'normal_volume' and s['rms_dbfs'] <= -45 for s in segs), segs
    speech = infer(ROOT / 'assets/audio_demo/real_speech_0.wav')
    assert speech[0]['class_key'] == 'normal_talk', speech
    music = infer(ROOT / 'assets/audio_demo/piano.wav')
    assert all(s['class_key'] not in ('music', 'normal_talk') for s in music), music
    print('PASS silence / attenuated speech / normal speech / removed music')

    proc = subprocess.Popen([str(exe), '--model', str(model), '--no-capture', '--port', '8786'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = KernelClient(port=8786)
    try:
        deadline = time.monotonic() + 20
        while not client.connect(timeout=0.5):
            assert time.monotonic() < deadline, 'startup timeout'
            time.sleep(0.2)
        st = client.status()
        assert st['config']['thresholds'] == [15, 9999, 45, 9999], st
        assert st['config']['normal_volume_dbfs'] == -45
        assert [c['key'] for c in st['classes']] == ['loud_talk','normal_volume','game_audio','normal_talk']
        # Normal volume is distinct and does not trigger its disabled reminder.
        client.offline_file(str(silence)) if silence.exists() else None
        for i in range(3):
            r = client.offline_file(str(ROOT / 'assets/audio_demo/esc50_clapping_3.wav'))
            assert r['segments'][0]['class_key'] == 'loud_talk', r
        state = client.status()
        assert state['classes'][0]['duration_sec'] == 15
        assert state['classes'][0]['exceeded']
        alerts = []
        while not client.messages.empty():
            msg = client.messages.get_nowait()
            if msg.get('type') == 'alert': alerts.append(msg)
        assert alerts, 'no threshold alert'
        cfg = client.set_config(5, [15,9999,45,9999], 0.05, True, -10)
        assert cfg['type'] == 'ok'
        assert client.status()['config']['normal_volume_dbfs'] == -10
        assert client.send({'cmd':'set_config','normal_volume_dbfs':5})['type'] == 'error'
        print('PASS class protocol / defaults / 15s alert / configurable gate / validation')
    finally:
        client.disconnect()
        proc.terminate()
        proc.wait(timeout=10)
