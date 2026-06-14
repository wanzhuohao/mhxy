"""挖图任务（全屏截图，分5区域处理）"""

import time
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from core import _match_in_region, REGIONS


def watu_start(stop_event):
    """挖图：全屏截图 → 点包裹 → 点宝图 → 使用"""
    log("挖图任务开始")

    # 第1步：全屏截图，找5个窗口的包裹按钮
    shot = _screenshot_gray(full=True)
    found_baoguo = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['baoguo'], rect)
        if r:
            found_baoguo.append((i, r))
        else:
            log(f"窗口{i+1}：未找到包裹按钮", "WARN")
            missing.append(f"窗口{i+1}")
    if missing:
        send_feishu_msg(f"⚠️ 挖图：{','.join(missing)} 未找到包裹按钮")

    if not found_baoguo:
        # 循环等待：检查包裹按钮出现
        for _ in range(60):  # 最多等5分钟
            if stop_event.is_set():
                return
            if _wait(5, stop_event):
                return
            shot = _screenshot_gray(full=True)
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['baoguo'], rect)
                if r:
                    return watu_start(stop_event)
        log("挖图等待包裹按钮超时", "WARN")

    # 点击找到的包裹
    for i, (cx, cy, val) in found_baoguo:
        safe_click(cx, cy)
        log(f"窗口{i+1} [baoguo] 点击包裹 ({cx},{cy})")
        time.sleep(0.3)

    if _wait(3, stop_event):
        return

    # 第2步：全屏截图，找整理按钮并点击
    shot = _screenshot_gray(full=True)
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['zhengli'], rect)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} [zhengli] 点击整理 ({r[0]},{r[1]})")
        else:
            log(f"窗口{i+1}：未找到整理按钮", "WARN")
            missing.append(f"窗口{i+1}")
        time.sleep(0.3)
    if missing:
        send_feishu_msg(f"⚠️ 挖图：{','.join(missing)} 未找到整理按钮")

    if _wait(2, stop_event):
        return

    # 第3步：全屏截图，找宝图按钮并点击
    shot = _screenshot_gray(full=True)
    found_baotu = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['watu_baotu'], rect)
        if r:
            found_baotu.append((i, r))
        else:
            log(f"窗口{i+1}：未找到宝图", "WARN")
            missing.append(f"窗口{i+1}")
    if missing:
        send_feishu_msg(f"⚠️ 挖图：{','.join(missing)} 未找到宝图")

    for i, (cx, cy, val) in found_baotu:
        import pyautogui
        pyautogui.doubleClick(cx, cy)
        log(f"窗口{i+1} 双击宝图 ({cx},{cy})")
        time.sleep(0.3)

    if _wait(2, stop_event):
        return

    # 第3步：轮询找使用按钮，连续1分钟没有则结束
    log("等待使用按钮...")
    no_count = 0
    while not stop_event.is_set():
        shot = _screenshot_gray(full=True)
        found_any = False

        # 检测激活弹窗，有则点击固定坐标(641,201)加窗口偏移和随机偏移
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['jihuo'], rect, yuzhi=0.8)
            if r:
                import random
                ox, oy = rect[0], rect[1]
                rx = random.randint(-3, 3)
                ry = random.randint(-3, 3)
                safe_click(ox + 641 + rx, oy + 201 + ry)
                log(f"窗口{i+1} [jihuo] 点击激活 ({ox+641+rx},{oy+201+ry})")
                found_any = True
                time.sleep(0.3)

        # 找使用按钮并点击（共用同一张截图）
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [shiyong] 点击使用 ({r[0]},{r[1]})")
                found_any = True
                time.sleep(0.3)

        if found_any:
            no_count = 0
        else:
            no_count += 1
            if no_count >= 12:  # 12次 × 5秒 = 60秒
                log("连续1分钟未找到使用按钮，挖图结束")
                break

        if _wait(5, stop_event):
            break

    log("挖图任务完成")
