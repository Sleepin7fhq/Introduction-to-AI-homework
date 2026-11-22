"""app.py —— 宿舍噪音智能识别系统 · UI 外壳（Gradio）。

设计原则（严格遵守题目约束）：
1. UI **不接触任何原始音频**：只通过本地 socket 接收内核下发的结构化结果
   （类别 / 置信度 / 各类累计时长 / 超标告警）。
2. UI **不做推理**：所有分类都发生在 C++ 内核里。
3. UI 只负责四件事：
   - 参数配置（分段长度、四类阈值、最小置信度、是否自动告警）
   - 实时结果展示（当前类别、置信度、细分标签、推理耗时）
   - 时长图表（四类累计时长柱状图 + 分段历史时间轴）
   - 超标提醒弹窗 + 本地音频文件离线推理按钮

启动：
    python ui/app.py                 # 默认连 127.0.0.1:8765
    python ui/app.py --port 9000     # 指定内核端口
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kernel_client import KernelClient, KernelState  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "build" / "bin"
KERNEL_EXE = BIN_DIR / "dorm_noise_kernel.exe"
if os.name != "nt":
    KERNEL_EXE = BIN_DIR / "dorm_noise_kernel"

CLASS_KEYS = ["loud_talk", "normal_volume", "game_audio", "normal_talk"]
CLASS_ZH = ["大声喧哗", "正常音量", "游戏外放", "正常交谈"]
CLASS_EMOJI = ["🗣️", "🔉", "🎮", "💬"]
CLASS_COLOR = ["#e4572e", "#17bebf", "#33658a", "#59a14f"]

# 共享状态
CLIENT = KernelClient()
ALERT_BOX: list[dict[str, Any]] = []
LAST_OFFLINE: list[Any] = [None, ""]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _fmt_hms(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _class_by_key(key: str) -> int:
    try:
        return CLASS_KEYS.index(key)
    except ValueError:
        return -1


def _state_table(state: KernelState) -> list[list[Any]]:
    rows = []
    for c in state.classes:
        idx = int(c.get("index", 0))
        dur = float(c.get("duration_sec", 0.0))
        thr = float(c.get("threshold_sec", 0.0))
        exceeded = bool(c.get("exceeded", False))
        rows.append([
            f"{CLASS_EMOJI[idx % 4]} {CLASS_ZH[idx % 4]}",
            _fmt_hms(dur),
            f"{dur:.1f} 秒",
            f"{thr:.1f} 秒" if thr < 9000 else "不限制",
            "⚠️ 已超标" if exceeded else "✅ 正常",
            int(c.get("segment_count", 0)),
        ])
    if not rows:
        for i, zh in enumerate(CLASS_ZH):
            rows.append([f"{CLASS_EMOJI[i]} {zh}", "00:00", "0.0 秒", "-", "-", 0])
    return rows


def _duration_chart(state: KernelState):
    """四类累计时长柱状图（含阈值参考线）。"""
    import plotly.graph_objects as go

    names = []
    values = []
    thresholds = []
    colors = []
    for c in state.classes:
        idx = int(c.get("index", 0))
        names.append(CLASS_ZH[idx % 4])
        values.append(float(c.get("duration_sec", 0.0)))
        thresholds.append(float(c.get("threshold_sec", 0.0)))
        colors.append(CLASS_COLOR[idx % 4])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=values, marker_color=colors,
        text=[f"{v:.1f}s" for v in values], textposition="auto",
        name="累计时长",
    ))
    for name, thr, color in zip(names, thresholds, colors):
        if 0 < thr < 9000:
            fig.add_hline(y=thr, line_dash="dash", line_color=color,
                          annotation_text=f"{name} 阈值 {thr:.0f}s",
                          annotation_position="top left")
    fig.update_layout(
        title="各类噪音累计时长",
        yaxis_title="累计时长（秒）",
        xaxis_title="类别",
        height=340,
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white",
    )
    return fig


def _history_chart(state: KernelState):
    """分段历史时间轴（堆叠柱状图，颜色代表类别）。"""
    import plotly.graph_objects as go

    hist = state.history
    fig = go.Figure()
    if hist:
        xs = [h.get("audio_time_sec", 0.0) for h in hist]
        ys = [h.get("segment_sec", 0.0) for h in hist]
        colors = []
        for h in hist:
            idx = int(h.get("class_index", 0))
            colors.append(CLASS_COLOR[idx % 4] if idx >= 0 else "#999999")
        fig.add_trace(go.Bar(
            x=xs, y=ys, marker_color=colors, width=None,
            text=[h.get("class_zh", "") for h in hist], textposition="outside",
            hovertemplate="%{text}<br>时间 %{x:.1f}s<br>时长 %{y:.1f}s<extra></extra>",
            name="分段",
        ))
    fig.update_layout(
        title="分段识别历史（横轴=音频时间，纵轴=该段时长）",
        xaxis_title="音频时间（秒）",
        yaxis_title="分段时长（秒）",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white",
        bargap=0.15,
    )
    return fig


def _last_badge(state: KernelState) -> str:
    last = state.last
    if not last or int(last.get("class_index", -1)) < 0:
        return "### ⏳ 等待第一段识别结果…"
    idx = int(last.get("class_index", 0))
    conf = float(last.get("confidence", 0.0))
    rms_dbfs = last.get("rms_dbfs")
    rms_text = f" ｜ RMS {float(rms_dbfs):.1f} dBFS" if rms_dbfs is not None else ""
    top = str(last.get("top_label_name", "") or "-")
    top_p = float(last.get("top_label_prob", 0.0))
    return (
        f"### {CLASS_EMOJI[idx % 4]} 当前判定：{CLASS_ZH[idx % 4]}\n"
        f"<div style='font-size:15px'>"
        f"四类概率质量 <b>{conf * 100:.1f}%</b> ｜ 细分标签 <b>{top}</b> ({top_p * 100:.1f}%)"
        f" ｜ 段长 {float(last.get('segment_sec', 0)):.1f}s{rms_text}"
        f"</div>"
    )


def _status_line(state: KernelState) -> str:
    if not state.kernel_alive:
        return "🔴 内核未连接"
    cap = "🎤 采集中" if state.capture_running else "⏸️ 采集已停止"
    dev = state.device_name or "未知设备"
    return (f"🟢 内核在线 ｜ {cap} ｜ 设备: {dev} ｜ "
            f"累计音频 {_fmt_hms(state.total_audio_sec)} ｜ "
            f"已处理 {state.segment_total} 段 ｜ 推理均值 {state.infer_ms_avg:.1f} ms")


# ---------------------------------------------------------------------------
# 回调
# ---------------------------------------------------------------------------
def _drain_alerts() -> list[dict[str, Any]]:
    """把内核推送的 alert 消息搬进告警列表（供弹窗显示）。

    注意：消息队列同时承载着命令响应（ok / error / state / offline_result），
    这里只取走 alert，其余消息必须放回去，否则会吞掉正在等待的响应。
    """
    pending: list[dict[str, Any]] = []
    while True:
        try:
            obj = CLIENT.messages.get_nowait()
        except Exception:
            break
        if obj.get("type") == "alert":
            ALERT_BOX.insert(0, obj)
            del ALERT_BOX[20:]
        else:
            pending.append(obj)
    for obj in pending:
        CLIENT.messages.put(obj)
    return ALERT_BOX


def on_connect(port: int):
    """连接内核。"""
    global CLIENT
    if not CLIENT.connected:
        CLIENT.port = int(port)
        if not CLIENT.connect():
            return (_status_line(CLIENT.state),
                    _last_badge(CLIENT.state),
                    gr.DataFrame(value=_state_table(CLIENT.state), headers=[
                        "类别", "累计时长", "秒数", "阈值", "状态", "段数"],
                        datatype=["str", "str", "str", "str", "str", "number"], wrap=True),
                    _duration_chart(CLIENT.state),
                    _history_chart(CLIENT.state),
                    "⚠️ " + (CLIENT.last_error or "连接失败"))
    # 立刻拉一次 status：内核每 500ms 才广播一次 state，首屏不等广播也能有数据。
    resp = CLIENT.status()
    if resp is not None and resp.get("type") == "state":
        CLIENT.state = KernelState.from_json(resp)
    st = CLIENT.state
    return (
        _status_line(st),
        _last_badge(st),
        gr.DataFrame(value=_state_table(st), headers=[
            "类别", "累计时长", "秒数", "阈值", "状态", "段数"],
            datatype=["str", "str", "str", "str", "str", "number"], wrap=True),
        _duration_chart(st),
        _history_chart(st),
        "✅ 已连接内核" if CLIENT.connected else "⚠️ " + (CLIENT.last_error or "连接失败"),
    )


def on_apply_config(segment_sec: float, t_loud: float, t_normal: float,
                    t_game: float, t_talk: float, normal_volume_dbfs: float,
                    min_conf: float, auto_alert: bool):
    """把 UI 上的参数推给内核。"""
    if not CLIENT.connected:
        return "⚠️ 内核未连接，请先点击「连接内核」。"
    resp = CLIENT.set_config(
        segment_sec=float(segment_sec),
        thresholds=[float(t_loud), float(t_normal), float(t_game), float(t_talk)],
        normal_volume_dbfs=float(normal_volume_dbfs),
        min_confidence=float(min_conf),
        auto_alert=bool(auto_alert),
    )
    if resp is None or resp.get("type") == "error":
        return f"❌ 参数下发失败：{CLIENT.last_error or (resp or {}).get('message', '')}"
    return (f"✅ 参数已下发到内核 —— 分段 {float(segment_sec):.1f}s，"
            f"阈值 [{float(t_loud):.0f}, {float(t_normal):.0f}, {float(t_game):.0f}, "
            f"{float(t_talk):.0f}] 秒，正常音量参考电平 {float(normal_volume_dbfs):.1f} dBFS，"
            f"最小置信度 {float(min_conf):.2f}")


def on_start():
    if not CLIENT.connected:
        return "⚠️ 内核未连接。"
    resp = CLIENT.start_capture()
    if resp is None or resp.get("type") == "error":
        return f"❌ 启动采集失败：{(resp or {}).get('message', CLIENT.last_error)}"
    return "🎤 麦克风已开启，正在实时采集…"


def on_stop():
    if not CLIENT.connected:
        return "⚠️ 内核未连接。"
    resp = CLIENT.stop_capture()
    if resp is None or resp.get("type") == "error":
        return f"❌ 停止采集失败：{(resp or {}).get('message', CLIENT.last_error)}"
    return "⏸️ 麦克风已关闭"


def on_reset():
    if not CLIENT.connected:
        return "⚠️ 内核未连接。"
    resp = CLIENT.reset_stats()
    if resp is None or resp.get("type") == "error":
        return f"❌ 重置失败：{(resp or {}).get('message', CLIENT.last_error)}"
    ALERT_BOX.clear()
    return "🧹 统计已清零"


def on_offline(path: str):
    """把本地 wav 交给内核做离线推理（UI 不解析音频）。"""
    if not CLIENT.connected:
        return "⚠️ 内核未连接，请先点击「连接内核」。", None
    if not path:
        return "⚠️ 请先选择一个本地音频文件。", None
    resp = CLIENT.offline_file(str(path))
    if resp is None:
        return f"❌ 离线推理失败：{CLIENT.last_error}", None
    if resp.get("type") == "error":
        return f"❌ {resp.get('message', '离线推理失败')}", None
    segs = resp.get("segments", [])
    rows = []
    for s in segs:
        idx = int(s.get("class_index", 0))
        rms_dbfs = s.get("rms_dbfs")
        rows.append([
            (f"{CLASS_EMOJI[idx]} {s.get('class_zh', '')}" if 0 <= idx < 4 else "❔ 未分类"),
            f"{float(s.get('confidence', 0)) * 100:.1f}%",
            str(s.get("top_label_name", "")),
            f"{float(s.get('top_label_prob', 0)) * 100:.1f}%",
            f"{float(s.get('segment_sec', 0)):.1f}s",
            f"{float(rms_dbfs):.1f} dBFS" if rms_dbfs is not None else "-",
        ])
    LAST_OFFLINE[0] = resp
    summary = (f"✅ 离线推理完成：{resp.get('file', '')} "
               f"（{float(resp.get('duration_sec', 0)):.1f} 秒，共 {len(segs)} 段）")
    return summary, rows


def on_refresh():
    """定时刷新（gr.Timer 触发）。"""
    if not CLIENT.connected:
        return (_status_line(CLIENT.state), _last_badge(CLIENT.state),
                gr.DataFrame(value=_state_table(CLIENT.state), headers=[
                    "类别", "累计时长", "秒数", "阈值", "状态", "段数"],
                    datatype=["str", "str", "str", "str", "str", "number"], wrap=True),
                _duration_chart(CLIENT.state), _history_chart(CLIENT.state),
                _alerts_markdown())
    st = CLIENT.state
    return (_status_line(st), _last_badge(st),
            gr.DataFrame(value=_state_table(st), headers=[
                "类别", "累计时长", "秒数", "阈值", "状态", "段数"],
                datatype=["str", "str", "str", "str", "str", "number"], wrap=True),
            _duration_chart(st), _history_chart(st), _alerts_markdown())


def _alerts_markdown() -> str:
    items = _drain_alerts()
    if not items:
        return "#### 🔔 提醒中心\n\n暂无超标提醒。"
    lines = ["#### 🔔 提醒中心"]
    for a in items[:8]:
        lines.append(
            f"- **{a.get('class_key', '')}**：累计 {float(a.get('duration_sec', 0)):.1f}s "
            f"已超过阈值 {float(a.get('threshold_sec', 0)):.1f}s —— {a.get('message', '')}"
        )
    return "\n".join(lines)


def _launch_kernel(port: int) -> bool:
    """若内核未运行，尝试本地拉起它（方便答辩一键演示）。

    优先使用便携版单文件 exe（自带模型与运行时，双击即用）；依次尝试
    dist/宿舍噪音识别.exe、build/portable/宿舍噪音识别.exe、
    build/portable/dorm_noise_standalone.exe；都没有则回落到普通内核 exe + 外部模型文件。
    """
    portable_candidates = [
        REPO_ROOT / "dist" / "宿舍噪音识别.exe",
        REPO_ROOT / "dist" / "dorm_noise_standalone.exe",
        REPO_ROOT / "build" / "portable" / "宿舍噪音识别.exe",
        REPO_ROOT / "build" / "portable" / "dorm_noise_standalone.exe",
    ]
    for standalone in portable_candidates:
        if standalone.exists():
            subprocess.Popen(
                [str(standalone), "--port", str(port)],
                cwd=str(standalone.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

    if not KERNEL_EXE.exists():
        return False
    model = REPO_ROOT / "models" / "ast_audioset.onnx"
    if not model.exists():
        return False
    subprocess.Popen(
        [str(KERNEL_EXE), "--model", str(model), "--port", str(port)],
        cwd=str(BIN_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def on_launch(port: int) -> str:
    """一键启动内核（后台），再自动连一次。"""
    port = int(port)
    if _launch_kernel(port):
        # 等内核把监听 socket 建起来
        for _ in range(30):
            time.sleep(0.5)
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                continue
        on_connect(port)
        return "🚀 内核已启动并连接（如未成功请检查 build/bin/onnxruntime.dll 是否存在）"
    return "❌ 找不到内核可执行文件或模型文件，请先按《编译运行与部署教程》构建一次。"


def main() -> None:
    parser = argparse.ArgumentParser(description="宿舍噪音智能识别系统 UI")
    parser.add_argument("--port", type=int, default=8765, help="内核 IPC 端口")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--ui-port", type=int, default=7860,
                        help="Gradio 界面端口（被占用时换一个）")
    args = parser.parse_args()

    CLIENT.host = args.host
    CLIENT.port = args.port

    with gr.Blocks(title="宿舍噪音智能识别与分类提醒系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
# 🐋 宿舍噪音智能识别与分类提醒系统

**核心推理运行在 C++ 内核**（本地 ONNX Runtime + AST 音频分类模型），
本页面只是展示外壳：参数配置 / 实时结果 / 时长图表 / 超标提醒 / 离线文件推理。

🔒 **隐私**：内核不保存原始音频、不做语音识别转文字；音频片段提取完特征、
推理完成后立刻从内存擦除，磁盘上不会产生任何录音文件。
"""
        )

        with gr.Row():
            port_box = gr.Number(value=args.port, label="内核端口", precision=0)
            connect_btn = gr.Button("🔌 连接内核", variant="primary")
            launch_btn = gr.Button("🚀 一键启动内核")
        status_line = gr.Markdown("🔴 内核未连接")
        action_msg = gr.Markdown("")

        with gr.Tabs():
            # ---------------- 实时监控 ----------------
            with gr.Tab("📊 实时监控"):
                last_badge = gr.Markdown("### ⏳ 等待第一段识别结果…")
                with gr.Row():
                    start_btn = gr.Button("🎤 开始采集", variant="primary")
                    stop_btn = gr.Button("⏸️ 停止采集")
                    reset_btn = gr.Button("🧹 清零统计")
                with gr.Row():
                    with gr.Column(scale=3):
                        dur_chart = gr.Plot(label="时长图表")
                    with gr.Column(scale=2):
                        stat_table = gr.DataFrame(
                            headers=["类别", "累计时长", "秒数", "阈值", "状态", "段数"],
                            datatype=["str", "str", "str", "str", "str", "number"],
                            wrap=True, interactive=False)
                hist_chart = gr.Plot(label="分段历史")

            # ---------------- 参数配置 ----------------
            with gr.Tab("⚙️ 参数配置"):
                with gr.Row():
                    seg_sec = gr.Slider(1.0, 10.0, value=5.0, step=0.5,
                                        label="分段长度（秒）")
                    min_conf = gr.Slider(0.0, 0.5, value=0.05, step=0.01,
                                         label="最小置信度")
                with gr.Row():
                    t_loud = gr.Number(value=15.0, label="大声喧哗 阈值（秒）")
                    t_normal = gr.Number(value=9999.0, label="正常音量 阈值（秒）")
                    t_game = gr.Number(value=45.0, label="游戏外放 阈值（秒）")
                    t_talk = gr.Number(value=9999.0, label="正常交谈 阈值（秒）")
                normal_volume_dbfs = gr.Number(value=-45.0, label="正常音量参考电平（dBFS）")
                auto_alert = gr.Checkbox(value=True, label="自动弹出超标提醒")
                apply_btn = gr.Button("📤 下发参数到内核", variant="primary")

            # ---------------- 离线推理 ----------------
            with gr.Tab("🎧 离线文件推理（答辩演示）"):
                gr.Markdown(
                    "选择一个本地音频文件（WAV），内核会读取它做离线推理并返回分段结果。\n"
                    "UI 只负责传路径与显示结果，**音频始终没有进入 UI 进程**。")
                wav_path = gr.Textbox(label="音频文件路径",
                                      value=str(REPO_ROOT / "assets" / "audio_demo" / "demo_loud_talk.wav"))
                # 说明：Gradio 5.5 的 gr.File 组件在「作为事件输入」时，
                # 它生成的 api_info schema 里有 gradio_client 无法解析的片段，
                # 会让整个页面在 /info 请求时抛
                #   TypeError: argument of type 'bool' is not iterable
                # 这里用 type="filepath"（值直接是路径字符串）+ api_name=False
                # 绕开该 schema 生成，功能不受影响。
                browse = gr.File(label="或点此选择文件", type="filepath",
                                 file_types=[".wav", ".mp3", ".flac", ".m4a"])

                # 额外加固：gradio_client 1.4.2 在构造 Endpoint 时会遍历
                # config["dependencies"]（含 api_name=False 的依赖），对每个输入组件
                # 调用 value_is_file(component["api_info"])。gr.File 的 api_info 里
                # meta 字段是 {"additionalProperties": true, ...}，客户端把 True 当 dict
                # 传进 get_type()，于是 `"const" in True` 抛 TypeError。
                # 解决办法：把这个组件实例的 api_info 覆盖成简单的字符串 schema。
                #   · 浏览器端的上传/选择交互完全不受影响（postprocess 仍返回 FileData）
                #   · API 客户端不再把该组件当成文件上传参数
                #   · 本组件只服务于 .change 事件（api_name=False），不暴露为 API
                def _file_api_info() -> dict[str, Any]:
                    return {"type": "string", "description": "本地音频文件路径"}

                browse.api_info = _file_api_info  # type: ignore[method-assign]
                offline_btn = gr.Button("🔍 开始离线推理", variant="primary")
                offline_summary = gr.Markdown("")
                offline_table = gr.DataFrame(
                    headers=["判定类别", "置信度", "细分标签", "标签概率", "段长", "RMS 电平"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    wrap=True, interactive=False)

            # ---------------- 提醒中心 ----------------
            with gr.Tab("🔔 提醒中心"):
                alerts_md = gr.Markdown("#### 🔔 提醒中心\n\n暂无超标提醒。")
                gr.Markdown(
                    "> 提醒逻辑：某一类噪音的**累计时长**超过设定阈值即触发一次提醒；"
                    "再次累计到阈值的 1.5 倍时补充提醒一次。")

        timer = gr.Timer(1.0).tick(
            on_refresh, outputs=[status_line, last_badge, stat_table, dur_chart, hist_chart, alerts_md]
        )

        connect_btn.click(on_connect, inputs=[port_box],
                          outputs=[status_line, last_badge, stat_table, dur_chart, hist_chart, action_msg])
        launch_btn.click(on_launch, inputs=[port_box], outputs=[action_msg])
        start_btn.click(on_start, outputs=[action_msg])
        stop_btn.click(on_stop, outputs=[action_msg])
        reset_btn.click(on_reset, outputs=[action_msg])
        apply_btn.click(on_apply_config,
                        inputs=[seg_sec, t_loud, t_normal, t_game, t_talk,
                                normal_volume_dbfs, min_conf, auto_alert],
                        outputs=[action_msg])
        offline_btn.click(on_offline, inputs=[wav_path], outputs=[offline_summary, offline_table])
        browse.change(lambda f: (f or ""), inputs=[browse], outputs=[wav_path], api_name=False)

    demo.queue().launch(server_name="127.0.0.1", server_port=args.ui_port, share=args.share)


if __name__ == "__main__":
    main()
