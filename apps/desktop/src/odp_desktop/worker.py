"""InferWorker — 在 QThread 中运行 infer_yolo，通过信号桥接 GUI."""

import logging
import time
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

from odp_platform.inference import infer_yolo, InferHooks, CancelToken

from .user_dir_sink import UserDirSink

_ALERT_INTERVAL = 10.0  # 持续检测到 person 多少秒后报警


class InferWorker(QObject):
    """在后台线程中运行推理，通过 Qt 信号将帧/进度/结果传回 GUI 主线程."""

    frame_ready = Signal(object)       # np.ndarray (BGR 标注帧)
    progress_updated = Signal(dict)    # 进度信息
    finished = Signal(object)          # InferResult
    error_occurred = Signal(str)       # 错误信息
    helmet_alert = Signal()            # 安全帽报警

    def __init__(
        self,
        source: str,
        model: str,
        conf: float = 0.25,
        iou: float = 0.70,
        *,
        output_dir: str = "",
        alert_enabled: bool = False,
        throttle: int = 2,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._source = source
        self._model = model
        self._conf = conf
        self._iou = iou
        self._output_dir = output_dir
        self._alert_enabled = alert_enabled
        self._throttle = throttle
        self._cancel_token = CancelToken()
        self._frame_count = 0

        # 报警状态追踪
        self._person_start: float | None = None   # 第一次检测到 person 的时间
        self._last_alert: float = 0.0             # 上次报警时间

    @property
    def cancel_token(self) -> CancelToken:
        return self._cancel_token

    def cancel(self) -> None:
        self._cancel_token.cancel()

    def set_alert_enabled(self, enabled: bool) -> None:
        self._alert_enabled = enabled
        logger.info(f"报警开关: {'开启' if enabled else '关闭'}")
        if not enabled:
            self._person_start = None

    def run_inference(self) -> None:
        try:
            cli_args: dict[str, Any] = {
                "source": self._source,
                "model": self._model,
                "conf": self._conf,
                "iou": self._iou,
                "show": False,
            }

            # 用户指定了输出目录 → 用 UserDirSink, 关掉引擎默认保存避免双写
            output_sink = None
            if self._output_dir:
                output_sink = UserDirSink(self._output_dir)
                cli_args["save"] = False

            hooks = InferHooks(
                on_frame=self._on_frame,
                on_progress=self._on_progress,
                on_complete=self._on_complete,
                on_error=self._on_error,
            )

            result = infer_yolo(
                cli_args=cli_args,
                hooks=hooks,
                cancel_token=self._cancel_token,
                show_info=False,
                output_sink=output_sink,
            )
            self.finished.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))

    # ------------------------------------------------------------------
    def _on_frame(self, evt) -> None:
        self._frame_count += 1
        if self._frame_count % self._throttle == 0:
            self.frame_ready.emit(evt.annotated.copy())

        # 安全帽报警检测 (仅当开启时)
        if not self._alert_enabled:
            return
        has_person = any(
            d.get("label") == "person"
            for d in (evt.detections or [])
        )
        now = time.monotonic()
        if has_person:
            if self._person_start is None:
                self._person_start = now
                logger.info(f"[报警] 首次检测到 person, 开始计时 (阈值={_ALERT_INTERVAL}s)")
            else:
                elapsed = now - self._person_start
                if elapsed >= _ALERT_INTERVAL and now - self._last_alert >= _ALERT_INTERVAL:
                    self._last_alert = now
                    logger.info(f"[报警] 触发! person 已持续 {elapsed:.1f}s, 发射 helmet_alert 信号")
                    self.helmet_alert.emit()
        else:
            if self._person_start is not None:
                logger.info(f"[报警] person 消失, 计时重置 (之前持续 {now - self._person_start:.1f}s)")
            self._person_start = None  # 无人时重置计时

    def _on_progress(self, evt) -> None:
        self.progress_updated.emit({
            "frame_idx": evt.frame_idx,
            "total_frames": evt.total_frames,
            "elapsed_sec": evt.elapsed_sec,
            "fps_loop": evt.fps_loop,
            "fps_infer": evt.fps_infer,
            "detections_total": evt.detections_total,
        })

    def _on_complete(self, result) -> None:
        pass  # finished 信号在 run_inference 中 emit

    def _on_error(self, exc: Exception) -> None:
        self.error_occurred.emit(str(exc))
