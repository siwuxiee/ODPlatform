"""主窗口 — 组装所有面板，管理 QThread + InferWorker 生命周期."""

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QMessageBox, QSplitter, QStatusBar,
    QWidget, QVBoxLayout,
)
from PySide6.QtCore import QThread, Qt

from .widgets import (
    SourcePanel, ModelPanel, DisplayWidget, ControlPanel, ResultsPanel,
)
from .worker import InferWorker
from .alert_player import AlertPlayer


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ODPlatform 推理客户端")
        self.resize(1280, 800)

        self._worker: InferWorker | None = None
        self._thread: QThread | None = None
        self._paused = False
        self._user_output_dir = ""
        self._alert_player = AlertPlayer()

        # -- 中央控件 --
        self._display = DisplayWidget()
        self._source_panel = SourcePanel()
        self._model_panel = ModelPanel()
        self._control_panel = ControlPanel()
        self._results_panel = ResultsPanel()

        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._source_panel)
        left_layout.addWidget(self._model_panel)
        left_layout.addWidget(self._control_panel)
        left_layout.addWidget(self._results_panel, 1)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._display)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 960])
        self.setCentralWidget(splitter)

        # -- 状态栏 --
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("就绪")
        self.setStatusBar(self._status_bar)

        # -- 信号连接 --
        self._control_panel.start_requested.connect(self._on_start)
        self._control_panel.stop_requested.connect(self._on_stop)
        self._control_panel.pause_toggled.connect(self._on_pause)
        self._source_panel.alert_enabled_changed.connect(self._on_alert_toggled)

        # -- 默认模型路径 --
        self._set_default_model()

    def closeEvent(self, event) -> None:
        """窗口关闭时确保推理线程被取消和清理."""
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        event.accept()

    # ------------------------------------------------------------------
    def _on_start(self) -> None:
        source = self._source_panel.get_source()
        model = self._model_panel.get_model_path()

        if not source:
            QMessageBox.warning(self, "输入错误", "请先选择输入源.")
            return
        if not model:
            QMessageBox.warning(self, "输入错误", "请先选择模型文件.")
            return

        output_dir = self._model_panel.get_output_dir()
        self._user_output_dir = output_dir

        self._results_panel.clear()
        self._display.clear()
        self._results_panel.append_log(f"[开始] source={source}, model={model}")
        if output_dir:
            self._results_panel.append_log(f"[输出] {output_dir}")

        self._worker = InferWorker(
            source=source,
            model=model,
            conf=self._model_panel.get_conf(),
            iou=self._model_panel.get_iou(),
            output_dir=output_dir,
            alert_enabled=self._source_panel.is_alert_enabled(),
        )

        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        # 连接信号
        self._thread.started.connect(self._worker.run_inference)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.helmet_alert.connect(self._alert_player.play, Qt.DirectConnection)
        self._thread.finished.connect(self._on_thread_finished)

        self._paused = False
        self._control_panel.set_running(True)
        self._status_bar.showMessage("运行中...")
        self._thread.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._status_bar.showMessage("正在停止...")
            self._results_panel.append_log("[停止] 正在取消推理...")

    def _on_pause(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._status_bar.showMessage("已暂停")
        else:
            self._status_bar.showMessage("运行中...")

    def _on_alert_toggled(self, enabled: bool) -> None:
        if self._worker is not None:
            self._worker.set_alert_enabled(enabled)

    # -- worker 回调 --
    def _on_frame(self, frame) -> None:
        if not self._paused:
            self._display.set_frame(frame)

    def _on_progress(self, data: dict) -> None:
        self._results_panel.update_progress(data)
        total = data.get("total_frames")
        if total:
            self._control_panel.set_progress(data["frame_idx"], total)
        else:
            self._control_panel.set_progress(0, 0)

    def _on_finished(self, result) -> None:
        # 用户自选输出目录时替换 result 中的 output_dir
        if result.success and self._user_output_dir:
            from pathlib import Path
            object.__setattr__(result, 'output_dir', Path(self._user_output_dir))
        self._results_panel.show_result(result)
        self._status_bar.showMessage(
            "推理完成" if result.success else f"推理失败: {result.error}"
        )
        self._cleanup_thread()

    def _on_error(self, msg: str) -> None:
        self._results_panel.append_log(f"[错误] {msg}")
        self._status_bar.showMessage(f"错误: {msg}")

    def _on_thread_finished(self) -> None:
        self._cleanup_thread()

    def _cleanup_thread(self) -> None:
        self._control_panel.set_running(False)
        self._paused = False
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
            self._thread = None
        self._worker = None

    def _set_default_model(self) -> None:
        """自动查找默认模型: train-6 > 其他训练结果 > checkpoints > pretrained."""
        root = Path(__file__).resolve().parents[4]
        train_runs = root / "runs" / "detect_train"

        if train_runs.exists():
            # 1) train-6 优先 (轻量模型)
            t6 = train_runs / "train-6" / "weights" / "best.pt"
            if t6.exists():
                self._model_panel.set_model_path(str(t6))
                return

            # 2) 其他训练结果 (按时间倒序)
            best_pts = sorted(
                train_runs.glob("*/weights/best.pt"),
                key=lambda p: p.stat().st_mtime, reverse=True,
            )
            if best_pts:
                self._model_panel.set_model_path(str(best_pts[0]))
                return

        # 3) models/checkpoints/
        d = root / "models" / "checkpoints"
        if d.exists():
            pts = list(d.glob("*.pt"))
            if pts:
                self._model_panel.set_model_path(str(pts[0]))
                return

        # 4) models/pretrained/ (最后兜底)
        d = root / "models" / "pretrained"
        if d.exists():
            pts = list(d.glob("*.pt"))
            if pts:
                self._model_panel.set_model_path(str(pts[0]))
                return
