"""报警语音管理 — 内置 MP3 + 系统播放器."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_ALERT_MP3 = Path(__file__).resolve().parent / "assets" / "alert.mp3"


class AlertPlayer:
    """安全帽报警语音播放器 (纯离线, subprocess 播放 MP3)."""

    def play(self) -> None:
        logger.info("[报警] AlertPlayer.play() 被调用")
        subprocess.Popen(
            ["gst-play-1.0", "--no-interactive", str(_ALERT_MP3)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[报警] gst-play-1.0 已启动")
