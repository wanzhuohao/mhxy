"""答题任务"""

import threading
from core import log, find_and_click_path, _wait, _retry
from notify import send_feishu_msg


def dati_start(stop_event: threading.Event):
    """答题：求助和使用"""
    log("答题任务开始")
    send_feishu_msg("🎮 答题任务开始")
    try:
        while not stop_event.is_set():
            _retry(lambda: find_and_click_path('qiuzhu.bmp', dy=-200), label="答题求助1")
            _retry(lambda: find_and_click_path('qiuzhu2.bmp', dy=-200), label="答题求助2")
            _retry(lambda: find_and_click_path('shiyong.bmp'), label="答题使用")
            if _wait(1, stop_event):
                break
        send_feishu_msg("✅ 答题任务完成")
    except Exception as e:
        log(f"答题任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 答题任务异常: {e}")
