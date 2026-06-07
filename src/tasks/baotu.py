"""宝图任务（全屏截图，分5区域处理）"""

import time
from core import log, _screenshot_gray, _match, TPL, _wait, _retry
from context import safe_click
from notify import send_feishu_msg
from tasks.shimen import REGIONS, _match_in_region


def baotu_start(stop_event):
    """宝图：全屏截图 → 分区域找活动/宝图 → 等待完成"""
    log("宝图任务开始")

    # 第1步：全屏截图，找5个窗口的活动按钮
    shot = _screenshot_gray()
    found_activity = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['huodong'], rect)
        if r:
            found_activity.append((i, r))
        else:
            log(f"窗口{i+1}：未找到活动按钮", "WARN")
            send_feishu_msg(f"⚠️ 窗口{i+1}未找到活动按钮")

    if not found_activity:
        log("所有窗口都未找到活动按钮", "WARN")
        return

    # 点击找到的活动按钮
    for i, (cx, cy, val) in found_activity:
        safe_click(cx, cy)
        log(f"窗口{i+1} 点击活动 ({cx},{cy})")
        time.sleep(0.3)

    if _wait(3, stop_event):
        return

    # 第2步：全屏截图，找宝图任务按钮
    shot = _screenshot_gray()
    found_baotu = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['baoturenwu'], rect, yuzhi=0.75)
        if r:
            found_baotu.append((i, r))
        else:
            log(f"窗口{i+1}：未找到宝图任务", "WARN")
            send_feishu_msg(f"⚠️ 窗口{i+1}未找到宝图任务")

    # 点击宝图任务右边
    for i, (cx, cy, val) in found_baotu:
        safe_click(cx + 130, cy + 15)
        log(f"窗口{i+1} 点击宝图任务右边 ({cx+130},{cy+15})")
        time.sleep(0.3)

    if _wait(3, stop_event):
        return

    # 第3步：全屏截图，找听听无妨并点击
    shot = _screenshot_gray()
    found_tingting = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['tingtingwufang'], rect, yuzhi=0.75)
        if r:
            found_tingting.append((i, r))
        else:
            log(f"窗口{i+1}：未找到听听无妨", "WARN")
            send_feishu_msg(f"⚠️ 窗口{i+1}未找到听听无妨")

    for i, (cx, cy, val) in found_tingting:
        safe_click(cx, cy)
        log(f"窗口{i+1} 点击听听无妨 ({cx},{cy})")
        time.sleep(0.3)

    if _wait(2, stop_event):
        return

    # 第4步：循环等待宝图任务完成
    log("等待宝图任务完成...")
    done_windows = set()  # 已完成的窗口
    while not stop_event.is_set():
        shot = _screenshot_gray()
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue  # 已完成，跳过

            has_renwu = _match_in_region(shot, TPL['renwu'], rect, yuzhi=0.8) is not None
            has_baotu = _match_in_region(shot, TPL['renwu_baotu'], rect, yuzhi=0.8) is not None

            if has_renwu and not has_baotu:
                log(f"窗口{i+1} 宝图完成")
                done_windows.add(i)
            elif has_baotu:
                r = _match_in_region(shot, TPL['renwu_baotu'], rect, yuzhi=0.8)
                if r:
                    safe_click(r[0] + 50, r[1] + 10)
                    log(f"窗口{i+1} 点击宝图追踪")

        if len(done_windows) == len(REGIONS):
            log("宝图任务全部完成")
            return

        if _wait(30, stop_event):
            return
