"""副本任务（组队型，只在队长窗口执行）"""

import random
import threading
from core import log, find_and_click_path, _wait, _retry, FUBEN_REGION
from context import safe_click
from notify import send_feishu_msg


def fuben_start(stop_event: threading.Event):
    """副本：跳过剧情、确定、战斗坐标"""
    log("副本任务开始")
    send_feishu_msg("🎮 副本任务开始")
    ox, oy = FUBEN_REGION[0], FUBEN_REGION[1]
    try:
        while not stop_event.is_set():
            if _retry(lambda: find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=FUBEN_REGION), label="副本跳过"):
                if _wait(5, stop_event):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                safe_click(ox + 744 + dx, oy + 190 + dy)
                if _wait(5, stop_event):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                safe_click(ox + 638 + dx, oy + 510 + dy)
                if _wait(3, stop_event):
                    break
                continue
            if _retry(lambda: find_and_click_path('queding.bmp', region=FUBEN_REGION), label="副本确定"):
                if _wait(10, stop_event):
                    break
                continue
            if _wait(1, stop_event):
                break
        send_feishu_msg("✅ 副本任务完成")
    except Exception as e:
        log(f"副本任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 副本任务异常: {e}")
