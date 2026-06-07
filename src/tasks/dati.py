"""答题任务（全屏截图，分5区域处理）"""

import time
import datetime
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from tasks.shimen import REGIONS, _match_in_region


def dati_start(stop_event):
    """答题：根据时间判断触发三界答题或科举"""
    now = datetime.datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=周一, 6=周日

    # 周一到周五 且 大于17点 → 科举
    if weekday < 5 and hour >= 17:
        log("答题任务开始（科举模式）")
        _dati_keju(stop_event)
    # 大于11点 → 三界答题
    elif hour >= 11:
        log("答题任务开始（三界答题模式）")
        _dati_sanjie(stop_event)
    else:
        log(f"答题：当前时间 {now.strftime('%H:%M')}，不满足触发条件")
        return


def _dati_keju(stop_event):
    """科举答题"""
    log("科举答题开始")
    while not stop_event.is_set():
        shot = _screenshot_gray()

        # 找求助1并点击（偏移 dy=-200）
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助1")
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）
        shot = _screenshot_gray()
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助2")
                time.sleep(0.3)

        # 找使用并点击
        shot = _screenshot_gray()
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 点击使用")
                time.sleep(0.3)

        if _wait(1, stop_event):
            break

    log("答题任务完成")


def _dati_sanjie(stop_event):
    """三界答题"""
    log("三界答题开始")
    while not stop_event.is_set():
        shot = _screenshot_gray()

        # 找求助1并点击（偏移 dy=-200）
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助1")
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）
        shot = _screenshot_gray()
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助2")
                time.sleep(0.3)

        # 找使用并点击
        shot = _screenshot_gray()
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 点击使用")
                time.sleep(0.3)

        if _wait(1, stop_event):
            break

    log("三界答题完成")
