"""解散队伍任务"""

import threading
import time
import random
from core import log, find_and_click, TPL
from context import safe_click


def jiesan_start(stop_event: threading.Event):
    """解散队伍：优先找队伍图片 → 找不到再点固定位置 → 循环踢人"""
    log("解散队伍开始")

    rect = (0, 0, 870, 692)
    ox, oy = rect[0], rect[1]

    # 队伍按钮固定位置 (右上角)
    team_btn_x, team_btn_y = 827, 165

    # 优先找图片匹配
    if find_and_click(TPL['duiwu'], yuzhi=0.7, region=rect):
        log("图片匹配成功，点击队伍")
    else:
        # 图片匹配失败，点击固定位置
        log("未找到队伍按钮，点击固定位置")
        safe_click(ox + team_btn_x + random.randint(-5, 5), oy + team_btn_y + random.randint(-5, 5))
    time.sleep(1)

    # 前4次: (740,240) -> (599,299) -> (511,400)
    for i in range(4):
        for x, y in [(740, 240), (599, 299), (511, 400)]:
            if stop_event.is_set():
                return
            rx, ry = random.randint(-5, 5), random.randint(-5, 5)
            safe_click(ox + x + rx, oy + y + ry)
            time.sleep(0.5)
    # 第5次: (740,190) -> (599,248) -> (511,400)
    for x, y in [(740, 190), (599, 248), (511, 400)]:
        if stop_event.is_set():
            return
        rx, ry = random.randint(-5, 5), random.randint(-5, 5)
        safe_click(ox + x + rx, oy + y + ry)
        time.sleep(0.5)

    log("解散队伍完成")
