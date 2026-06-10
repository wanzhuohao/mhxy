"""解散队伍任务"""

import threading
import time
import random
from core import log, find_and_click, TPL
from context import safe_click


def jiesan_start(stop_event: threading.Event):
    """解散队伍：找队伍 → 循环踢人"""
    log("解散队伍开始")

    rect = (0, 0, 870, 692)
    ox, oy = rect[0], rect[1]

    # 找队伍图片并点击
    if not find_and_click(TPL['duiwu'], yuzhi=0.8, region=rect):
        log("未找到队伍按钮", "WARN")
        return
    log("点击队伍")
    time.sleep(1)

    # 前3次: (740,240) -> (599,299) -> (511,400)
    for i in range(3):
        for x, y in [(740, 240), (599, 299), (511, 400)]:
            if stop_event.is_set():
                return
            rx, ry = random.randint(-5, 5), random.randint(-5, 5)
            safe_click(ox + x + rx, oy + y + ry)
            time.sleep(0.5)
    # 第4次: (740,190) -> (599,248) -> (511,400)
    for x, y in [(740, 190), (599, 248), (511, 400)]:
        if stop_event.is_set():
            return
        rx, ry = random.randint(-5, 5), random.randint(-5, 5)
        safe_click(ox + x + rx, oy + y + ry)
        time.sleep(0.5)

    log("解散队伍完成")
