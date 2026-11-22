"""kernel_client.py —— UI 与 C++ 内核之间的 IPC 客户端。

协议与内核侧 ``kernel/include/dn/ipc_server.h`` 中的说明一一对应：

* 传输层：TCP，127.0.0.1:8765（仅本机回环，不对外暴露）
* 编码：每行一个 UTF-8 JSON 对象，以 ``\\n`` 结尾
* UI → 内核：``{"cmd": ...}``
* 内核 → UI：``{"type": "state" | "alert" | "offline_result" | "ok" | "error", ...}``

隐私说明：本模块只接收「类别 / 置信度 / 累计时长 / 告警」等结构化结果，
**内核不会、也无法通过这条通道发送原始音频数据**。
"""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class KernelState:
    """内核状态的一次快照（已解析成便于 UI 使用的结构）。"""

    kernel_alive: bool = False
    capture_running: bool = False
    device_name: str = ""
    model_path: str = ""
    total_audio_sec: float = 0.0
    segment_total: int = 0
    infer_ms_avg: float = 0.0
    client_count: int = 0

    segment_sec: float = 5.0
    min_confidence: float = 0.05
    auto_alert: bool = True
    normal_volume_dbfs: float = -45.0
    thresholds: list[float] = field(default_factory=lambda: [15.0, 9999.0, 45.0, 9999.0])

    # 各类累计时长与状态
    classes: list[dict[str, Any]] = field(default_factory=list)

    # 最近一次识别结果；内核可在其中返回 rms_dbfs。
    last: dict[str, Any] = field(default_factory=dict)

    # 历史分段（供 UI 画图）
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> "KernelState":
        cfg = obj.get("config") or {}
        return cls(
            kernel_alive=bool(obj.get("kernel_alive")),
            capture_running=bool(obj.get("capture_running")),
            device_name=str(obj.get("device_name") or ""),
            model_path=str(obj.get("model_path") or ""),
            total_audio_sec=float(obj.get("total_audio_sec") or 0.0),
            segment_total=int(obj.get("segment_total") or 0),
            infer_ms_avg=float(obj.get("infer_ms_avg") or 0.0),
            client_count=int(obj.get("client_count") or 0),
            segment_sec=float(cfg.get("segment_sec", 5.0)),
            min_confidence=float(cfg.get("min_confidence", 0.05)),
            auto_alert=bool(cfg.get("auto_alert", True)),
            normal_volume_dbfs=float(cfg.get("normal_volume_dbfs", -45.0)),
            thresholds=[float(x) for x in (cfg.get("thresholds") or [15.0, 9999.0, 45.0, 9999.0])],
            classes=list(obj.get("classes") or []),
            last=dict(obj.get("last") or {}),
            history=list(obj.get("history") or []),
        )


class KernelClient:
    """内核 IPC 客户端。

    后台线程持续读取内核推送的消息（state / alert / offline_result），
    放入 :attr:`messages` 队列；UI 定时轮询这个队列即可。
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        # 广播消息（state / alert）队列，UI 轮询这里
        self.messages: "queue.Queue[dict[str, Any]]" = queue.Queue()
        # 命令响应按 rid 分发：rid -> queue
        self._pending: dict[str, "queue.Queue[dict[str, Any]]"] = {}
        self._pending_lock = threading.Lock()
        self.state = KernelState()
        self.connected = False
        self.last_error = ""
        self.on_alert: Callable[[dict[str, Any]], None] | None = None
        self.on_offline: Callable[[dict[str, Any]], None] | None = None

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def connect(self, timeout: float = 5.0) -> bool:
        """连接内核。失败时返回 False 并把原因写入 :attr:`last_error`。"""
        self.disconnect()
        try:
            sock = socket.create_connection((self.host, self.port), timeout=timeout)
            sock.settimeout(1.0)
        except OSError as exc:
            self.connected = False
            self.last_error = f"无法连接内核 {self.host}:{self.port} —— {exc}"
            return False

        with self._lock:
            self._sock = sock
        self._stop.clear()
        self.connected = True
        self.last_error = ""
        self._reader = threading.Thread(target=self._read_loop, name="kernel-reader", daemon=True)
        self._reader.start()
        return True

    def disconnect(self) -> None:
        self._stop.set()
        with self._lock:
            sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._reader is not None:
            self._reader.join(timeout=2.0)
            self._reader = None
        self.connected = False

    def _read_loop(self) -> None:
        buf = b""
        while not self._stop.is_set():
            with self._lock:
                sock = self._sock
            if sock is None:
                break
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.strip()
                if not text:
                    continue
                try:
                    obj = json.loads(text.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                self._handle(obj)

        self.connected = False

    def _handle(self, obj: dict[str, Any]) -> None:
        kind = obj.get("type")
        rid = obj.get("rid")

        # 带 rid 的是命令响应 —— 直接交给等待它的调用方，不进广播队列。
        if rid is not None:
            with self._pending_lock:
                q = self._pending.get(rid)
            if q is not None:
                q.put(obj)
                return

        if kind == "state":
            self.state = KernelState.from_json(obj)
        elif kind == "alert":
            if self.on_alert is not None:
                self.on_alert(obj)
        elif kind == "offline_result":
            if self.on_offline is not None:
                self.on_offline(obj)
        self.messages.put(obj)

    # ------------------------------------------------------------------
    # 命令发送
    # ------------------------------------------------------------------
    def send(self, payload: dict[str, Any], timeout: float = 15.0) -> dict[str, Any] | None:
        """发送一条命令，并等待**属于这条命令**的响应。

        内核每 500ms 广播一次 state，如果只按消息类型等待，广播会把真正的
        ok / offline_result 挤掉。因此每次请求都带一个短 rid，内核在响应里
        原样回显；响应按 rid 分发给等待者，广播走 :attr:`messages` 队列。
        """
        with self._lock:
            sock = self._sock
        if sock is None:
            self.last_error = "内核未连接"
            return None

        rid = f"{int(time.time() * 1000) % 100000000:08x}"
        body = dict(payload)
        body["rid"] = rid
        resp_q: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[rid] = resp_q
        try:
            sock.sendall(json.dumps(body, ensure_ascii=False).encode("utf-8") + b"\n")
        except OSError as exc:
            self.last_error = f"发送失败: {exc}"
            with self._pending_lock:
                self._pending.pop(rid, None)
            return None

        try:
            try:
                obj = resp_q.get(timeout=timeout)
            except queue.Empty:
                self.last_error = "等待内核响应超时"
                return None
            # 兼容不返回 rid 的旧版内核：没匹配上就去广播队列里找一条命令响应。
            if obj is None:
                return None
            return obj
        finally:
            with self._pending_lock:
                self._pending.pop(rid, None)

    # ---- 便捷方法 ----
    def status(self) -> dict[str, Any] | None:
        return self.send({"cmd": "status"})

    def set_config(
        self,
        segment_sec: float,
        thresholds: list[float],
        min_confidence: float,
        auto_alert: bool,
        normal_volume_dbfs: float = -45.0,
    ) -> dict[str, Any] | None:
        return self.send(
            {
                "cmd": "set_config",
                "segment_sec": float(segment_sec),
                "thresholds": [float(t) for t in thresholds],
                "min_confidence": float(min_confidence),
                "auto_alert": bool(auto_alert),
                "normal_volume_dbfs": float(normal_volume_dbfs),
            }
        )

    def start_capture(self) -> dict[str, Any] | None:
        return self.send({"cmd": "start_capture"})

    def stop_capture(self) -> dict[str, Any] | None:
        return self.send({"cmd": "stop_capture"})

    def reset_stats(self) -> dict[str, Any] | None:
        return self.send({"cmd": "reset"})

    def offline_file(self, path: str) -> dict[str, Any] | None:
        return self.send({"cmd": "offline_file", "path": path})
