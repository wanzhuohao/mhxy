"""挖图任务"""

import threading
from core import log, find_and_click_path, _wait, _retry
from notify import send_feishu_msg


def watu_start(stop_event: threading.Event):
    """挖图：循环使用宝图"""
    log("挖图任务开始")
    send_feishu_msg("🎮 挖图任务开始")
    try:
        while not stop_event.is_set():
            _retry(lambda: find_and_click_path('shiyong.bmp', yuzhi=0.65), label="挖图")
            if _wait(3, stop_event):
                break
        send_feishu_msg("✅ 挖图任务完成")
    except Exception as e:
        log(f"挖图任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 挖图任务异常: {e}")
