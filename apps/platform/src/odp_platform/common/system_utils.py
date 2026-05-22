import logging
import platform
import os


def log_device_info(logger: logging.Logger) -> None:
    logger.info("─" * 40)
    logger.info("设备信息")
    logger.info(f"  系统: {platform.system()} {platform.release()}")
    logger.info(f"  架构: {platform.machine()}")
    logger.info(f"  CPU: {os.cpu_count()} 核")
    try:
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"  内存: {mem.total / (1024**3):.1f} GB")
    except ImportError:
        pass
    logger.info("─" * 40)
