"""
指标统计模块
记录请求计数、错误数、耗时等
"""

import threading
from collections import defaultdict

_metrics = {
    "request_count": 0,
    "error_count": 0,
    "total_duration": 0.0,
    "by_path": defaultdict(lambda: {"count": 0, "errors": 0, "duration": 0.0}),
}
_metrics_lock = threading.Lock()


def _record_metric(path: str, method: str, status_code: int, duration: float):
    """记录请求指标（线程安全）"""
    with _metrics_lock:
        _metrics["request_count"] += 1
        _metrics["total_duration"] += duration
        if status_code >= 400:
            _metrics["error_count"] += 1

        key = f"{method} {path}"
        _metrics["by_path"][key]["count"] += 1
        _metrics["by_path"][key]["duration"] += duration
        if status_code >= 400:
            _metrics["by_path"][key]["errors"] += 1


def get_metrics() -> dict:
    """获取指标快照"""
    result = dict(_metrics)
    result["by_path"] = dict(_metrics["by_path"])
    result["avg_duration"] = (
        _metrics["total_duration"] / _metrics["request_count"]
        if _metrics["request_count"] > 0 else 0.0
    )
    return result
