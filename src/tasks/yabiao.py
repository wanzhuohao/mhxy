"""押镖任务"""

import threading
from core import log, find_and_click_path, _wait, _retry
from notify import send_feishu_msg


def yabiao_start(stop_event: threading.Event):
    """押镖：点确定和运送镖银"""
    log("押镖任务开始")
    send_feishu_msg("🎮 押镖任务开始")
    try:
        while not stop_event.is_set():
            if _retry(lambda: find_and_click_path('queding.bmp'), label="押镖确定"):
                if _wait(3, stop_event):
                    break
                continue
            _retry(lambda: find_and_click_path('yasongbiaoyin.jpg'), label="押镖镖银")
            if _wait(3, stop_event):
                break
        send_feishu_msg("✅ 押镖任务完成")
    except Exception as e:
        log(f"押镖任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 押镖任务异常: {e}")
