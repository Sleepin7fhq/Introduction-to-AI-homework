/**
 * 预生成演示素材。
 *
 * 这两条是本机 ACE-Step 1.5（DiT-only turbo / INT8 / CPU offload）真实生成的，
 * 已经过 `scripts/verify_audio.py` 验证：float32 / 48kHz / 立体声 / peak −1 dBFS /
 * 非静音占比 93% 与 98%。放在这里是为了「服务没起来」时仍能演示真实 AI 音频，
 * 而不是拿符号引擎的结果冒充。
 */
export interface BackupTake {
  id: string;
  label: string;
  hint: string;
  url: string;
  durationSec: number;
}

export const BACKUP_TAKES: BackupTake[] = [
  {
    id: 'techno128',
    label: 'Techno 128 BPM',
    hint: 'dark warehouse · acid bass · 11.9s',
    url: './demo/acestep-techno-128bpm.wav',
    durationSec: 11.87,
  },
  {
    id: 'zaoba138',
    label: '早八 Rave 138 BPM',
    hint: 'chiptune rave · 闹钟琶音 · 10.6s',
    url: './demo/acestep-early8-rave-138bpm.wav',
    durationSec: 10.62,
  },
];
