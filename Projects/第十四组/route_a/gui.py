"""可视化界面：选文件、拨开关、生成伴奏、试听。

不引入任何新依赖，只用标准库 tkinter + winsound。
启动：python -m route_a.gui（或双击 run_gui.cmd）
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
import winsound
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from music21 import key as m21key

from .analysis import KeyInfo, detect_key
from .auto import suggest as auto_suggest
from .cli import arrange, make_layer_tracks, parse_key
from .config import (BUNDLED_IRS, ENSEMBLES, IR_DIR, SOUNDFONT,
                     SOUNDFONT_ALIASES)
from .counter import make_counter
from .drums import PATTERNS, make_drums
from .dynamics import apply as apply_humanize
from .expression import build as build_expression
from .io import load_melody
from .instruments import INSTRUMENTS
from .mixer import volumes_for
from .render import ExtraTrack, export_midi, export_stems, render_wav, write_chart
from .texture import STYLE_DESC, STYLES
from .variation import add_phrase_fills, avoid_melody

KEY_CHOICES = ["自动", "C major", "G major", "D major", "F major", "A minor", "E minor", "D minor"]
LAYER_CHOICES = ["无"] + list(STYLES)
LAYER_INST_CHOICES = ["auto"] + list(INSTRUMENTS)

COLORS = {
    "melody": "#3b82f6",
    "chords": "#10b981",
    "bass": "#f59e0b",
    "counter": "#8b5cf6",
    "drums": "#6b7280",
}


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("旋律自动配伴奏 · route A")
        self.geometry("1180x990")
        self.minsize(980, 700)
        self.configure(bg="#f4f5f7")

        self.var_input = tk.StringVar()
        self.var_outdir = tk.StringVar()
        self.var_style = tk.StringVar(value=f"{STYLES[0]} · {STYLE_DESC[STYLES[0]]}")
        self.var_cpb = tk.IntVar(value=1)
        self.var_phrase = tk.IntVar(value=4)
        self.var_key = tk.StringVar(value="自动")
        self.var_counter = tk.BooleanVar(value=False)
        self.var_drums = tk.BooleanVar(value=False)
        self.var_drum = tk.StringVar(value="auto")
        self.var_reverb = tk.StringVar(value="无")
        self.var_reverb_engine = tk.StringVar(value="ir")
        self.var_ir = tk.StringVar(value="无")
        self.var_soundfont = tk.StringVar(value="fluid")
        self.var_harmony = tk.StringVar(value="rich")
        self.var_ensemble = tk.StringVar(value="piano")
        self.var_humanize = tk.StringVar(value="off")
        self.var_balance = tk.StringVar(value="orchestral")
        self.var_variation = tk.BooleanVar(value=True)
        self.var_stems = tk.BooleanVar(value=False)
        self.var_expression = tk.BooleanVar(value=True)
        self.var_layer1 = tk.StringVar(value="无")
        self.var_layer2 = tk.StringVar(value="无")
        self.var_layer_inst1 = tk.StringVar(value="auto")
        self.var_layer_inst2 = tk.StringVar(value="auto")
        self.var_layer_oct = tk.StringVar(value="0")
        self.var_modulate = tk.BooleanVar(value=True)
        self.var_status = tk.StringVar(value="选择一首旋律，然后点“生成伴奏”")

        self.result: dict | None = None
        self.roll_notes: list[tuple[float, float, int, str]] = []
        self.drum_notes: list = []
        self.bpb = 4.0
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Hint.TLabel", foreground="#6b7280")

        header = ttk.Frame(self, padding=(18, 14, 18, 6))
        header.pack(fill="x")
        ttk.Label(header, text="旋律自动配伴奏", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="music21 + 规则/DP + FluidSynth", style="Hint.TLabel").pack(
            side="left", padx=12, pady=(8, 0))

        file_row = ttk.Frame(self, padding=(18, 4))
        file_row.pack(fill="x")
        ttk.Label(file_row, text="旋律文件").pack(side="left")
        ttk.Entry(file_row, textvariable=self.var_input).pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(file_row, text="浏览…", command=self._browse).pack(side="left")
        self.btn_auto = ttk.Button(file_row, text="自动配置", command=self.auto_config)
        self.btn_auto.pack(side="left", padx=(8, 0))
        self.btn_gen = ttk.Button(file_row, text="生成伴奏", command=self.generate)
        self.btn_gen.pack(side="left", padx=8)

        body = ttk.Frame(self, padding=(18, 8))
        body.pack(fill="both", expand=True)

        left = ttk.LabelFrame(body, text="参数", padding=12)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(left, text="织体").grid(row=row, column=0, sticky="w", pady=4)
        style_box = ttk.Combobox(left, textvariable=self.var_style, state="readonly",
                                 values=[f"{s} · {STYLE_DESC[s]}" for s in STYLES], width=26)
        style_box.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ttk.Label(left, text="和声节奏").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(left, textvariable=self.var_cpb, state="readonly",
                     values=[1, 2], width=6).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(left, text="乐句长度").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Spinbox(left, from_=2, to=8, textvariable=self.var_phrase, width=6).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(left, text="调性").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(left, textvariable=self.var_key, state="readonly",
                     values=KEY_CHOICES, width=12).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        mode_row = ttk.Frame(left)
        mode_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Label(mode_row, text="和声").pack(side="left")
        ttk.Combobox(mode_row, textvariable=self.var_harmony, state="readonly",
                     values=["rich", "simple"], width=6).pack(side="left", padx=(2, 4))
        ttk.Label(mode_row, text="音色").pack(side="left")
        ttk.Combobox(mode_row, textvariable=self.var_ensemble, state="readonly",
                     values=["piano", "strings", "band"], width=7).pack(side="left", padx=(2, 4))
        ttk.Label(mode_row, text="人性").pack(side="left")
        ttk.Combobox(mode_row, textvariable=self.var_humanize, state="readonly",
                     values=["off", "light", "strong"], width=6).pack(side="left", padx=2)
        row += 1

        balance_row = ttk.Frame(left)
        balance_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Label(balance_row, text="平衡").pack(side="left")
        ttk.Combobox(balance_row, textvariable=self.var_balance, state="readonly",
                     values=["orchestral", "pop", "flat"], width=10).pack(side="left", padx=(2, 4))
        ttk.Label(balance_row, text="旋律优先", style="Hint.TLabel").pack(side="left")
        row += 1

        ttk.Separator(left).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        ttk.Checkbutton(left, text="加副旋律（通道 4）", variable=self.var_counter).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=3)
        row += 1

        ttk.Checkbutton(left, text="加鼓轨（通道 10）", variable=self.var_drums).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=3)
        row += 1

        ttk.Label(left, text="鼓型").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Combobox(left, textvariable=self.var_drum, state="readonly",
                     values=list(PATTERNS), width=10).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        rev_row = ttk.Frame(left)
        rev_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(rev_row, text="混响").pack(side="left")
        ttk.Combobox(rev_row, textvariable=self.var_reverb, state="readonly",
                     values=["无", "轻", "中", "大厅"], width=8).pack(side="left", padx=(2, 6))
        ttk.Label(rev_row, text="算法").pack(side="left")
        ttk.Combobox(rev_row, textvariable=self.var_reverb_engine, state="readonly",
                     values=["ir", "freeverb"], width=8).pack(side="left", padx=2)
        row += 1

        ir_row = ttk.Frame(left)
        ir_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Label(ir_row, text="厅堂").pack(side="left")
        ttk.Combobox(ir_row, textvariable=self.var_ir, state="readonly",
                     values=["无", "hall", "opera", "church"], width=7).pack(
            side="left", padx=(2, 6))
        ttk.Label(ir_row, text="音源").pack(side="left")
        ttk.Combobox(ir_row, textvariable=self.var_soundfont, state="readonly",
                     values=["fluid", "musescore", "generaluser"], width=10).pack(
            side="left", padx=2)
        row += 1

        layer_row = ttk.Frame(left)
        layer_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Label(layer_row, text="叠层1").pack(side="left")
        ttk.Combobox(layer_row, textvariable=self.var_layer1, state="readonly",
                     values=LAYER_CHOICES, width=8).pack(side="left", padx=(2, 6))
        ttk.Label(layer_row, text="叠层2").pack(side="left")
        ttk.Combobox(layer_row, textvariable=self.var_layer2, state="readonly",
                     values=LAYER_CHOICES, width=8).pack(side="left", padx=2)
        row += 1

        inst_row = ttk.Frame(left)
        inst_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Label(inst_row, text="乐器1").pack(side="left")
        ttk.Combobox(inst_row, textvariable=self.var_layer_inst1, state="readonly",
                     values=LAYER_INST_CHOICES, width=7).pack(side="left", padx=(2, 6))
        ttk.Label(inst_row, text="乐器2").pack(side="left")
        ttk.Combobox(inst_row, textvariable=self.var_layer_inst2, state="readonly",
                     values=LAYER_INST_CHOICES, width=7).pack(side="left", padx=2)
        row += 1

        oct_row = ttk.Frame(left)
        oct_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 3))
        ttk.Label(oct_row, text="叠层八度").pack(side="left")
        ttk.Combobox(oct_row, textvariable=self.var_layer_oct, state="readonly",
                     values=["-12", "0", "12"], width=5).pack(side="left", padx=4)
        ttk.Label(oct_row, text="0 最稳", style="Hint.TLabel").pack(side="left")
        row += 1

        ttk.Checkbutton(left, text="允许尾部自动转调", variable=self.var_modulate).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=3)
        row += 1

        opt_row = ttk.Frame(left)
        opt_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(opt_row, text="乐句加花", variable=self.var_variation).pack(side="left")
        ttk.Checkbutton(opt_row, text="表情", variable=self.var_expression).pack(
            side="left", padx=(10, 0))
        ttk.Checkbutton(opt_row, text="分轨", variable=self.var_stems).pack(
            side="left", padx=(10, 0))
        row += 1

        ttk.Separator(left).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        ttk.Label(left, text="输出目录").grid(row=row, column=0, sticky="w", pady=4)
        row += 1
        out_row = ttk.Frame(left)
        out_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self.var_outdir).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_row, text="…", width=3, command=self._browse_outdir).grid(row=0, column=1)
        row += 1

        ttk.Label(left, text="留空则输出到旋律同目录", style="Hint.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w")
        row += 1

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(right, bg="#fbfbf9", height=180,
                                highlightthickness=1, highlightbackground="#d1d5db")
        self.canvas.pack(fill="x")
        self.canvas.bind("<Configure>", lambda _e: self._draw_roll())

        bar = ttk.Frame(right, padding=(0, 8))
        bar.pack(fill="x")
        self.btn_play = ttk.Button(bar, text="▶ 播放", command=self._play, state="disabled")
        self.btn_play.pack(side="left")
        self.btn_stop = ttk.Button(bar, text="■ 停止", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        self.btn_open = ttk.Button(bar, text="打开 WAV", command=self._open_wav, state="disabled")
        self.btn_open.pack(side="left", padx=6)
        self.btn_folder = ttk.Button(bar, text="打开输出目录", command=self._open_folder,
                                     state="disabled")
        self.btn_folder.pack(side="left", padx=6)

        self.log = tk.Text(right, height=8, wrap="word", font=("Microsoft YaHei UI", 9),
                           bg="#ffffff", relief="flat", highlightthickness=1,
                           highlightbackground="#d1d5db")
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled")

        status = ttk.Frame(self, padding=(18, 6, 18, 12))
        status.pack(fill="x")
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=160)
        self.progress.pack(side="right")
        ttk.Label(status, textvariable=self.var_status).pack(side="left")

    # ------------------------------------------------------------ actions
    def auto_config(self) -> None:
        raw = self.var_input.get().strip()
        if not raw:
            messagebox.showwarning("没有输入", "先选一首旋律，再点“自动配置”。")
            return
        source = Path(raw)
        if not source.exists():
            messagebox.showwarning("找不到文件", "请先选择一个存在的 MIDI 或 MusicXML 文件。")
            return
        if source.suffix.lower() not in (".mid", ".midi", ".xml", ".musicxml"):
            messagebox.showwarning("格式不支持", "输入需要是 .mid / .midi / .xml / .musicxml。")
            return
        self.btn_auto.configure(state="disabled")
        self.btn_gen.configure(state="disabled")
        self.var_status.set("正在分析旋律…")
        self.progress.start(12)
        threading.Thread(target=self._auto_work, args=(source,), daemon=True).start()

    def _auto_work(self, source: Path) -> None:
        try:
            melody = load_melody(source)
            key_info = detect_key(melody)
            plan = auto_suggest(melody, key_info)
            self.after(0, lambda: self._apply_plan(plan))
        except Exception:  # noqa: BLE001
            detail = traceback.format_exc()
            self.after(0, lambda: self._auto_fail(detail))

    def _apply_plan(self, plan) -> None:
        self.progress.stop()
        self.btn_auto.configure(state="normal")
        self.btn_gen.configure(state="normal")
        self.var_style.set(f"{plan.style} · {STYLE_DESC[plan.style]}")
        self.var_cpb.set(plan.chords_per_bar)
        self.var_phrase.set(plan.phrase_bars)
        self.var_harmony.set(plan.harmony)
        self.var_ensemble.set(plan.ensemble)
        self.var_humanize.set(plan.humanize)
        self.var_balance.set(plan.balance)
        reverb_label = {"off": "无", "light": "轻", "medium": "中", "hall": "大厅"}
        self.var_reverb.set(reverb_label[plan.reverb])
        self.var_reverb_engine.set(plan.reverb_engine)
        self.var_ir.set(plan.ir if plan.reverb != "off" else "无")
        self.var_soundfont.set(plan.soundfont)
        self.var_counter.set(plan.counter)
        self.var_drums.set(plan.drums)
        self.var_drum.set(plan.drum_pattern)
        self.var_layer_oct.set("0")
        layer_vars = [self.var_layer1, self.var_layer2]
        inst_vars = [self.var_layer_inst1, self.var_layer_inst2]
        for index in range(2):
            if index < len(plan.layers):
                style, instrument = plan.layers[index]
                layer_vars[index].set(style)
                inst_vars[index].set(instrument or "auto")
            else:
                layer_vars[index].set("无")
                inst_vars[index].set("auto")
        lines = ["自动配置:"] + [f"- {reason}" for reason in plan.reasons]
        lines += ["", f"织体 {plan.style} / 和声 {plan.harmony} / 音色 {plan.ensemble}",
                  f"混响 {plan.reverb} / 平衡 {plan.balance} / 叠层 {plan.layers}"]
        self._set_log("\n".join(lines))
        self.var_status.set(f"自动配置完成：{plan.style} / {plan.ensemble}")

    def _auto_fail(self, detail: str) -> None:
        self.progress.stop()
        self.btn_auto.configure(state="normal")
        self.btn_gen.configure(state="normal")
        self.var_status.set("自动配置失败")
        self._set_log(detail)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="选择旋律",
            filetypes=[("MIDI / MusicXML", "*.mid *.midi *.xml *.musicxml"),
                       ("所有文件", "*.*")])
        if not path:
            return
        self.var_input.set(path)
        if not self.var_outdir.get().strip():
            self.var_outdir.set(str(Path(path).parent))

    def _browse_outdir(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.var_outdir.set(path)

    def generate(self) -> None:
        source = Path(self.var_input.get().strip())
        if not source.exists():
            messagebox.showwarning("找不到文件", "请先选择一个存在的 MIDI 或 MusicXML 文件。")
            return
        if source.suffix.lower() not in (".mid", ".midi", ".xml", ".musicxml"):
            messagebox.showwarning("格式不支持", "输入需要是 .mid / .midi / .xml / .musicxml。")
            return

        layer_styles = []
        layer_instruments = []
        for style, instrument in ((self.var_layer1.get(), self.var_layer_inst1.get()),
                                  (self.var_layer2.get(), self.var_layer_inst2.get())):
            if style == "无":
                continue
            layer_styles.append(style)
            layer_instruments.append(None if instrument == "auto" else instrument)

        params = {
            "style": self.var_style.get().split(" · ")[0],            "cpb": int(self.var_cpb.get()),
            "phrase": int(self.var_phrase.get()),
            "key": self.var_key.get(),
            "counter": self.var_counter.get(),
            "drums": self.var_drums.get(),
            "drum_pattern": self.var_drum.get(),
            "reverb": {"无": "off", "轻": "light", "中": "medium", "大厅": "hall"}[
                self.var_reverb.get()],
            "reverb_engine": self.var_reverb_engine.get(),
            "ir": self.var_ir.get(),
            "soundfont": self.var_soundfont.get(),
            "harmony": self.var_harmony.get(),
            "ensemble": self.var_ensemble.get(),
            "humanize": self.var_humanize.get(),
            "balance": self.var_balance.get(),
            "variation": self.var_variation.get(),
            "stems": self.var_stems.get(),
            "expression": "light" if self.var_expression.get() else "off",
            "layers": layer_styles,
            "layer_instruments": layer_instruments,
            "layer_octave": int(self.var_layer_oct.get()),
            "modulate": self.var_modulate.get(),
            "outdir": self.var_outdir.get().strip(),
        }
        self.btn_gen.configure(state="disabled")
        self.btn_play.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        self.btn_open.configure(state="disabled")
        self.progress.start(12)
        self.var_status.set("正在分析、配和声、渲染…")
        threading.Thread(target=self._work, args=(source, params), daemon=True).start()

    def _work(self, source: Path, params: dict) -> None:
        try:
            melody = load_melody(source)
            if params["key"] == "自动":
                key_info = detect_key(melody)
            else:
                key_info = KeyInfo(m21=parse_key(params["key"]), confidence=1.0,
                                   alternatives=[])

            harmony, chord_notes, bass_notes, voicings, parallels = arrange(
                melody, key_info, style=params["style"],
                chords_per_bar=params["cpb"], phrase_bars=params["phrase"],
                modulate=params["modulate"],
                simple=params["harmony"] == "simple")

            extras = []
            counter_notes = []
            drum_notes = []
            layer_names = []
            if params["counter"]:
                counter_notes = make_counter(melody, harmony, phrase_bars=params["phrase"])
                extras.append(ExtraTrack("Counter", counter_notes, channel=3))
            if params["drums"]:
                drum_notes = make_drums(melody, harmony, pattern=params["drum_pattern"],
                                        style=params["style"])
                extras.append(ExtraTrack("Drums", drum_notes, channel=9, is_drum=True))
            ensemble = ENSEMBLES[params["ensemble"]]
            if params["layers"]:
                layer_tracks = make_layer_tracks(melody, harmony, voicings,
                                                 params["layers"],
                                                 octave=params["layer_octave"],
                                                 primary_style=params["style"],
                                                 instruments=params["layer_instruments"],
                                                 fallback_program=ensemble["layer"])
                extras.extend(layer_tracks)
                layer_names = [track.name.replace("Layer ", "") for track in layer_tracks]

            for extra in extras:
                if extra.name == "Counter":
                    extra.program = ensemble["counter"]

            chord_notes = avoid_melody(chord_notes, melody)
            bass_notes = avoid_melody(bass_notes, melody)
            for extra in extras:
                if not extra.is_drum:
                    extra.notes = avoid_melody(extra.notes, melody)
            if params["variation"]:
                chord_notes = add_phrase_fills(chord_notes, melody, harmony,
                                               phrase_bars=params["phrase"],
                                               style=params["style"])

            if params["humanize"] != "off":
                chord_notes = apply_humanize(chord_notes, melody, melody.bpm,
                                             phrase_bars=params["phrase"],
                                             level=params["humanize"])
                bass_notes = apply_humanize(bass_notes, melody, melody.bpm,
                                            phrase_bars=params["phrase"],
                                            level=params["humanize"])
                for extra in extras:
                    extra.notes = apply_humanize(extra.notes, melody, melody.bpm,
                                                 phrase_bars=params["phrase"],
                                                 level=params["humanize"])

            outdir = Path(params["outdir"]) if params["outdir"] else source.parent
            outdir.mkdir(parents=True, exist_ok=True)
            midi_path = outdir / f"{source.stem}_accomp.mid"
            wav_path = outdir / f"{source.stem}_accomp.wav"
            chart_path = outdir / f"{source.stem}_accomp_chords.txt"

            volumes = volumes_for(params["balance"], counter=params["counter"],
                                  layers=len(params["layers"]), drums=params["drums"])
            for extra in extras:
                if extra.name.startswith("Layer"):
                    volumes[extra.channel] = min(
                        1.0, volumes.get(extra.channel, 1.0) * extra.gain)
            expressions = build_expression(melody, extras, params["phrase"],
                                           params["expression"])
            export_midi(melody, harmony, chord_notes, bass_notes, midi_path,
                        extras=extras, programs=ensemble["primary"], volumes=volumes,
                        expressions=expressions)
            write_chart(chart_path, harmony)
            ir_name = params["ir"]
            ir_path = IR_DIR / BUNDLED_IRS[ir_name] if ir_name in BUNDLED_IRS else None
            soundfont = SOUNDFONT_ALIASES.get(params["soundfont"], SOUNDFONT)
            render_wav(midi_path, wav_path, soundfont=soundfont,
                       reverb=params["reverb"],
                       reverb_engine=params["reverb_engine"], ir_path=ir_path)
            stem_dir = None
            if params["stems"]:
                stem_dir = midi_path.parent / f"{midi_path.stem}_stems"
                export_stems(midi_path, stem_dir, soundfont=soundfont)

            self.after(0, lambda: self._done(source, melody, key_info, harmony,
                                             chord_notes, bass_notes, counter_notes,
                                             drum_notes, midi_path, wav_path, chart_path,
                                             parallels, layer_names, stem_dir))
        except Exception:  # noqa: BLE001
            detail = traceback.format_exc()
            self.after(0, lambda: self._fail(detail))

    def _done(self, source, melody, key_info, harmony, chord_notes, bass_notes,
              counter_notes, drum_notes, midi_path, wav_path, chart_path, parallels,
              layer_names, stem_dir=None) -> None:
        self.progress.stop()
        self.btn_gen.configure(state="normal")
        self.btn_play.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.btn_open.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.result = {"wav": wav_path, "midi": midi_path, "chart": chart_path,
                       "outdir": wav_path.parent}
        self.bpb = melody.beats_per_bar
        self.drum_notes = drum_notes
        self.roll_notes = []
        for n in melody.notes:
            self.roll_notes.append((n.start, n.end, n.pitch, "melody"))
        for n in chord_notes:
            self.roll_notes.append((n.start, n.end, n.pitch, "chords"))
        for n in bass_notes:
            self.roll_notes.append((n.start, n.end, n.pitch, "bass"))
        for n in counter_notes:
            self.roll_notes.append((n.start, n.end, n.pitch, "counter"))
        self._draw_roll(drums=drum_notes)
        tracks = ["旋律", "和弦", "低音"]
        if counter_notes:
            tracks.append("副旋律")
        for name in layer_names:
            tracks.append(f"叠层:{name}")
        if drum_notes:
            tracks.append("鼓")
        lines = [
            f"输入    : {source}",
            f"调性    : {key_info.name}  (相关度 {key_info.confidence:.3f})",
            f"拍号/速度: {melody.time_sig[0]}/{melody.time_sig[1]}, {melody.bpm:g} BPM, "
            f"{melody.bars} 小节",
            f"和弦    : {harmony.chart_text()}",
        ]
        if harmony.modulation:
            lines.append(f"转调    : {harmony.modulation.text}")
        lines += [
            f"和声    : V7 {int(harmony.stats.get('v7', 0))} 处，"
            f"副属 {int(harmony.stats.get('secondary', 0))} 处",
            f"低音    : 转位 {int(harmony.stats.get('inversions', 0))} 处，"
            f"经过音 {int(harmony.stats.get('passing_tones', 0))} 个",
            f"表情    : {'开' if self.var_expression.get() else '关'}（CC11 随旋律起伏）",
            f"模式    : 和声 {self.var_harmony.get()} / 音色 {self.var_ensemble.get()} / "
            f"人性 {self.var_humanize.get()} / 平衡 {self.var_balance.get()}",
            f"织体    : {self.var_style.get()}",
            f"质量    : 强拍冲突 {harmony.stats['conflict_rate'] * 100:.1f}%，"
            f"平行五/八度 {parallels} 处",
            f"轨道    : {' / '.join(tracks)}",
            f"叠层    : {' / '.join(layer_names) if layer_names else '无'}",
            f"混响    : {self.var_reverb.get()} / {self.var_reverb_engine.get()} / "
            f"{self.var_ir.get()}",
            f"音源    : {self.var_soundfont.get()}",
            "",
            f"MIDI    : {midi_path}",
            f"WAV     : {wav_path}",
            f"和弦谱  : {chart_path}",
        ]
        if stem_dir is not None:
            lines.append(f"分轨    : {stem_dir}")
        skeleton = getattr(melody, "skeleton", None)
        if skeleton is not None and getattr(skeleton, "chords", None):
            if getattr(skeleton, "polyphonic", False):
                total = matched = 0
                for slot in harmony.slots:
                    if slot.chord is None:
                        continue
                    root = skeleton.root_at(slot.start)
                    if root is None:
                        continue
                    total += 1
                    matched += int(root == slot.chord.root_pc)
                lines.append(f"骨架    : {len(skeleton.chords)} 段，"
                             f"根音吻合 {matched / max(1, total):.0%}")
            else:
                lines.append("骨架    : 单声部输入，跳过和声骨架")
        self._set_log("\n".join(lines))
        self.var_status.set("生成完成，可以播放或打开输出目录")

    def _fail(self, detail: str) -> None:
        self.progress.stop()
        self.btn_gen.configure(state="normal")
        self.var_status.set("生成失败")
        self._set_log("生成失败：\n\n" + detail)
        messagebox.showerror("生成失败", detail.strip().splitlines()[-1])

    # ------------------------------------------------------------ drawing
    def _draw_roll(self, drums: list | None = None) -> None:
        c = self.canvas
        c.delete("all")
        drums = self.drum_notes if drums is None else drums
        width = max(c.winfo_width(), 400)
        height = max(c.winfo_height(), 260)
        if not self.roll_notes:
            c.create_text(width // 2, height // 2, text="生成后在这里显示钢琴卷帘",
                          fill="#9ca3af", font=("Microsoft YaHei UI", 11))
            return

        left, right, top, drum_h = 42, 12, 16, 34
        plot_w = width - left - right
        plot_h = height - top - drum_h - 18
        max_beat = max(n[1] for n in self.roll_notes) + 1
        pitches = [n[2] for n in self.roll_notes]
        lo, hi = min(pitches) - 1, max(pitches) + 1

        def x(beat: float) -> float:
            return left + beat / max_beat * plot_w

        def y(pitch: int) -> float:
            return top + (hi - pitch) / (hi - lo) * plot_h

        # 小节线
        bpb = self.bpb or 4.0
        bar = 0
        while bar * bpb <= max_beat:
            bx = x(bar * bpb)
            c.create_line(bx, top, bx, top + plot_h, fill="#eceff3")
            bar += 1

        for start, end, pitch, kind in self.roll_notes:
            color = COLORS.get(kind, "#9ca3af")
            yy = y(pitch)
            c.create_rectangle(x(start), yy - 3, max(x(end) - 1, x(start) + 2), yy + 3,
                               fill=color, outline="")

        # 鼓：底部单独一条
        c.create_line(left, top + plot_h + 8, left + plot_w, top + plot_h + 8, fill="#d1d5db")
        c.create_text(left - 6, top + plot_h + drum_h / 2, text="鼓", anchor="e",
                      fill="#6b7280", font=("Microsoft YaHei UI", 8))
        for n in drums or []:
            dx = x(n.start)
            c.create_rectangle(dx, top + plot_h + 12, dx + 2,
                               top + plot_h + 12 + drum_h - 8, fill=COLORS["drums"],
                               outline="")

        # 图例
        lx = left
        for kind, label in (("melody", "旋律"), ("chords", "和弦"), ("bass", "低音"),
                            ("counter", "副旋律"), ("drums", "鼓")):
            c.create_rectangle(lx, height - 12, lx + 10, height - 6,
                               fill=COLORS[kind], outline="")
            c.create_text(lx + 14, height - 9, text=label, anchor="w",
                          fill="#374151", font=("Microsoft YaHei UI", 8))
            lx += 64

    # ------------------------------------------------------------ misc
    def _set_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("1.0", text)
        self.log.configure(state="disabled")

    def _play(self) -> None:
        if self.result:
            winsound.PlaySound(str(self.result["wav"]),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)

    def _stop(self) -> None:
        winsound.PlaySound(None, winsound.SND_PURGE)

    def _open_wav(self) -> None:
        if self.result:
            os.startfile(str(self.result["wav"]))

    def _open_folder(self) -> None:
        if self.result:
            os.startfile(str(self.result["outdir"]))

    def _on_close(self) -> None:
        self._stop()
        self.destroy()


def main() -> None:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    app = App()
    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
        if source.exists():
            app.var_input.set(str(source))
            app.var_outdir.set(str(source.parent))
    app.mainloop()


if __name__ == "__main__":
    main()
