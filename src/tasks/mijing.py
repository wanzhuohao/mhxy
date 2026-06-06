"""秘境任务"""

import threading
from core import log, find_and_click_path, _wait, _retry
from notify import send_feishu_msg


def mijing_start(stop_event: threading.Event):
    """秘境：找进入战斗和秘境降妖"""
    log("秘境任务开始")
    send_feishu_msg("🎮 秘境任务开始")
    try:
        while not stop_event.is_set():
            if _retry(lambda: find_and_click_path('jinruzhandou.bmp', yuzhi=0.55), label="秘境战斗"):
                if _wait(3, stop_event):
                    break
                continue
            _retry(lambda: find_and_click_path('mijingxiangyao.bmp', yuzhi=0.5), label="秘境降妖")
            if _wait(3, stop_event):
                break
        send_feishu_msg("✅ 秘境任务完成")
    except Exception as e:
        log(f"秘境任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 秘境任务异常: {e}")
