"""答题任务（全屏截图，分5区域处理）"""

import time
import datetime
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from tasks.shimen import REGIONS, _match_in_region, _retry_click_activity


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
        shot = _screenshot_gray(full=True)

        # 找求助1并点击（偏移 dy=-200）
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助1")
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助2")
                time.sleep(0.3)

        # 找使用并点击
        shot = _screenshot_gray(full=True)
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
    """三界答题：全屏截图 → 点活动 → 点三界右边 → 求助/使用"""
    log("三界答题开始")

    # 第1步：全屏截图，找活动按钮
    shot = _screenshot_gray(full=True)
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['huodong'], rect)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} 点击活动 ({r[0]},{r[1]})")
        else:
            log(f"窗口{i+1}：未找到活动按钮", "WARN")
            missing.append(f"窗口{i+1}")
        time.sleep(0.3)
    if missing:
        send_feishu_msg(f"⚠️ 三界答题：{','.join(missing)} 未找到活动按钮")

    # 所有窗口都未找到活动按钮，循环等待
    if len(missing) == len(REGIONS):
        for _ in range(60):  # 最多等5分钟
            if stop_event.is_set():
                return
            if _wait(5, stop_event):
                return
            shot = _screenshot_gray(full=True)
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['huodong'], rect)
                if r:
                    return _dati_sanjie(stop_event)
        log("答题等待活动按钮超时", "WARN")

    if _wait(3, stop_event):
        return

    # 第2步：全屏截图，找三界按钮并点击右边
    shot = _screenshot_gray(full=True)
    found_sanji = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['sanjie'], rect)
        if r:
            found_sanji.append((i, r))
        else:
            missing.append(i)

    # 未找到的窗口点击重试
    if missing:
        shot = _retry_click_activity(missing, stop_event) or shot
        still_missing = []
        for i in missing:
            r = _match_in_region(shot, TPL['sanjie'], REGIONS[i])
            if r:
                found_sanji.append((i, r))
            else:
                still_missing.append(i)
        missing = still_missing

    for i, r in found_sanji:
        safe_click(r[0] + 130, r[1] + 10)
        log(f"窗口{i+1} 点击三界右边 ({r[0]+130},{r[1]+10})")
        time.sleep(0.3)

    if missing:
        for i in missing:
            log(f"窗口{i+1}：未找到三界按钮", "WARN")
        send_feishu_msg(f"⚠️ 三界答题：{','.join(f'窗口{i+1}' for i in missing)} 未找到三界按钮")

    if _wait(2, stop_event):
        return

    # 第3步：循环找求助/使用，检测结束标志
    done_windows = set()
    while not stop_event.is_set():
        shot = _screenshot_gray(full=True)

        # 检测结束标志
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['jieshu'], rect)
            if r:
                log(f"窗口{i+1} 三界答题已完成")
                done_windows.add(i)

        if len(done_windows) == len(REGIONS):
            log("三界答题全部完成，点击关闭")
            shot = _screenshot_gray(full=True)
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['dati_x'], rect)
                if r:
                    safe_click(r[0], r[1])
                    log(f"窗口{i+1} 点击关闭 ({r[0]},{r[1]})")
                    time.sleep(0.3)
            break

        # 找求助1并点击（偏移 dy=-200）
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助1")
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} 点击求助2")
                time.sleep(0.3)

        # 找使用并点击
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 点击使用")
                time.sleep(0.3)

        if _wait(1, stop_event):
            break

    log("三界答题完成")
