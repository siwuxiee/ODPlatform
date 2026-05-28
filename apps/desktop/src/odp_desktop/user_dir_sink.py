"""UserDirSink — 将推理结果输出到用户指定目录的 OutputSink."""

import logging
from pathlib import Path

import numpy as np

from odp_platform.frame_source import SourceType
from odp_platform.inference.sinks import OutputSink

logger = logging.getLogger(__name__)


class UserDirSink(OutputSink):
    """与 LocalFileSink 行为一致, 但输出到用户指定目录下的子文件夹中.

    用户选 /home/me/Downloads → 实际输出 /home/me/Downloads/predict/

    视频/摄像头 → output.mp4
    图片       → <原文件名>.jpg
    """

    def __init__(self, user_dir: str | Path) -> None:
        self._parent_dir = Path(user_dir)
        self._work_dir: Path | None = None
        self._is_stream: bool = False
        self._video = None       # cv2.VideoWriter, lazy init
        self._count: int = 0

    @property
    def output_dir(self) -> Path:
        return self._work_dir or self._parent_dir

    def open(self, output_dir: Path, source_type: SourceType) -> None:
        # 在用户选的目录下创建子文件夹, 避免文件散落一地
        self._parent_dir.mkdir(parents=True, exist_ok=True)
        self._work_dir = _resolve_subdir(self._parent_dir, "predict")
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._is_stream = source_type in (SourceType.VIDEO, SourceType.CAMERA)

    def write(self, frame, annotated: np.ndarray) -> None:
        import cv2
        try:
            if self._is_stream:
                if self._video is None:
                    h, w = annotated.shape[:2]
                    fps = float(
                        getattr(frame.info, "fps", None) or 30.0
                    )
                    out = self._work_dir / "output.mp4"
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    self._video = cv2.VideoWriter(
                        str(out), fourcc, fps, (w, h),
                    )
                self._video.write(annotated)
            else:
                fname = (
                    frame.info.filename
                    or f"frame_{frame.info.frame_index:06d}"
                )
                cv2.imwrite(
                    str(self._work_dir / f"{Path(fname).stem}.jpg"),
                    annotated,
                )
            self._count += 1
        except Exception as e:
            logger.warning(f"UserDirSink.write 失败, 跳过: {e}")

    def close(self) -> None:
        if self._video is not None:
            try:
                self._video.release()
            except Exception as e:
                logger.warning(f"UserDirSink.close release 失败 (已吞): {e}")
            finally:
                self._video = None


def _resolve_subdir(base: Path, name: str) -> Path:
    """自增子目录: predict → predict2 → predict3 ..."""
    candidate = base / name
    if not candidate.exists():
        return candidate
    i = 2
    while (base / f"{name}{i}").exists():
        i += 1
    return base / f"{name}{i}"
