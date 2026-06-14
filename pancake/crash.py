"""异常处理模块 — 完整异常写入 crash/ 目录，用户看到简化信息"""

import datetime
import logging
import os
import traceback

logger = logging.getLogger(__name__)


def handle_exception(exc: Exception, crash_dir: str = "crash") -> str:
    """处理异常：写入完整信息到 crash/ 目录，返回简化消息

    Args:
        exc: 捕获的异常
        crash_dir: crash 日志存放目录

    Returns:
        给用户看的简化错误消息
    """
    # 确保 crash 目录存在
    os.makedirs(crash_dir, exist_ok=True)

    # 生成文件名：crash_20260614_153000.txt
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"crash_{timestamp}.txt"
    filepath = os.path.join(crash_dir, filename)

    # 写入完整异常信息
    full_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Pancake Framework Crash Report\n")
        f.write(f"{'=' * 40}\n")
        f.write(f"Time: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Exception: {type(exc).__name__}: {exc}\n")
        f.write(f"{'=' * 40}\n\n")
        f.write(full_trace)

    # 返回简化消息
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    if exc_msg:
        simplified = f"{exc_type}: {exc_msg}"
    else:
        simplified = exc_type

    return simplified, filepath
