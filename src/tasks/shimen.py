"""师门任务（全屏截图，分5区域处理）"""

import time
import threading
from core import log, _screenshot_gray, _match, find_and_click, TPL, _wait, _retry
from context import safe_click
from notify import send_feishu_msg

# 5个窗口区域
REGIONS = [
    (0, 0, 870, 692),
    (853, 0, 1723, 692),
    (1706, 0, 2576, 692),
    (0, 690, 870, 1382),
    (853, 690, 1723, 1382),
]


def _match_in_region(shot_full, template, region, yuzhi=0.8):
    """在全屏截图的指定区域内匹配模板，返回中心绝对坐标或 None"""
    x0, y0, x1, y1 = region
    crop = shot_full[y0:y1, x0:x1]
    max_val, max_loc = _match(template, crop)
    if max_val >= yuzhi:
        cx = max_loc[0] + template.shape[1] // 2 + x0
        cy = max_loc[1] + template.shape[0] // 2 + y0
        return (cx, cy, max_val)
    return None


def shimen_start(stop_event: threading.Event):
    """师门：全屏截图 → 分区域找活动/师门 → 逐窗口去完成"""
    log("师门任务开始")

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

    # 等待界面刷新
    if _wait(3, stop_event):
        return

    # 第2步：全屏截图，找师门右边按钮
    shot = _screenshot_gray()
    found_shimen = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['huodongshimen'], rect)
        if r:
            found_shimen.append((i, r))
        else:
            log(f"窗口{i+1}：未找到师门按钮", "WARN")
            send_feishu_msg(f"⚠️ 窗口{i+1}未找到师门按钮")

    # 点击师门右边
    for i, (cx, cy, val) in found_shimen:
        safe_click(cx + 130, cy + 10)
        log(f"窗口{i+1} 点击师门右边 ({cx+130},{cy+10})")
        time.sleep(0.3)

    if _wait(2, stop_event):
        return

    # 第3步：每个窗口找去完成 → 等待完成
    completed = [0] * len(REGIONS)
    max_tasks = 20

    for task_num in range(1, max_tasks + 1):
        if stop_event.is_set():
            break

        log(f"── 师门任务 {task_num} ──")

        # 全屏截图，找所有窗口的去完成
        shot = _screenshot_gray()
        found_qu = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['quwancheng'], rect, yuzhi=0.95)
            if r:
                found_qu.append((i, r))
            else:
                log(f"窗口{i+1}：未找到去完成", "WARN")
                send_feishu_msg(f"⚠️ 窗口{i+1}未找到去完成")

        if not found_qu:
            log("所有窗口都没有去完成，任务结束")
            break

        # 逐个点击去完成
        for i, (cx, cy, val) in found_qu:
            safe_click(cx, cy)
            log(f"窗口{i+1} 点击去完成 ({cx},{cy})")
            completed[i] += 1

        # 等待完成
        _wait_completion_all(stop_event, found_qu, task_num, completed)

    # 汇总
    total = sum(completed)
    log(f"师门任务全部完成，共 {total} 个")


def _wait_completion_all(stop_event, found_qu, task_num, completed):
    """等待所有窗口的师门任务完成"""
    timeout = 900
    start = time.time()
    pending = {i for i, _ in found_qu}

    while not stop_event.is_set() and pending:
        if time.time() - start > timeout:
            log(f"师门任务 {task_num} 等待超时", "WARN")
            break

        shot = _screenshot_gray()
        for i in list(pending):
            rect = REGIONS[i]
            r = _match_in_region(shot, TPL['shimen_complete'], rect, yuzhi=0.85)
            if r:
                # 找确认按钮并点击
                r_confirm = _match_in_region(shot, TPL['shimen_confirm'], rect, yuzhi=0.85)
                if r_confirm:
                    safe_click(r_confirm[0], r_confirm[1])
                time.sleep(0.5)
                # 找关闭按钮并点击
                shot2 = _screenshot_gray()
                r2 = _match_in_region(shot2, TPL['shimen_x'], rect, yuzhi=0.85)
                if r2:
                    safe_click(r2[0], r2[1])
                log(f"窗口{i+1} 师门任务 {task_num} 完成 ✓")
                pending.discard(i)

        if pending:
            if _wait(5, stop_event):
                break

    for i in pending:
        log(f"窗口{i+1} 师门任务 {task_num} 未完成", "WARN")
