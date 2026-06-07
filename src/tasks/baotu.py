"""宝图任务（全屏截图，分5区域处理）"""

import time
from core import log, _screenshot_gray, _match, TPL, _wait, _retry
from context import safe_click
from notify import send_feishu_msg
from tasks.shimen import REGIONS, _match_in_region, _retry_click_activity


def baotu_start(stop_event):
    """宝图：全屏截图 → 分区域找活动/宝图 → 等待完成"""
    log("宝图任务开始")

    # 第0步：先检查宝图任务按钮是否已经在屏幕上（活动面板已打开）
    shot = _screenshot_gray(full=True)
    found_baotu_direct = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['baoturenwu'], rect, yuzhi=0.70)
        if r:
            found_baotu_direct.append((i, r))
    if found_baotu_direct:
        log(f"活动面板已打开，直接找宝图任务按钮，找到{len(found_baotu_direct)}个")
        # 跳到第2步
    else:
        # 第1步：全屏截图，找5个窗口的活动按钮
        found_activity = []
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['huodong'], rect)
            if r:
                found_activity.append((i, r))
            else:
                missing.append(i)
        if missing:
            send_feishu_msg(f"⚠️ 宝图：{','.join(f'窗口{i+1}' for i in missing)} 未找到活动按钮")

        if not found_activity:
            # 循环等待：检查活动按钮或宝图任务按钮出现
            for _ in range(60):
                if stop_event.is_set():
                    return
                if _wait(5, stop_event):
                    return
                shot = _screenshot_gray(full=True)
                # 检查宝图任务按钮是否出现
                for i, rect in enumerate(REGIONS):
                    r = _match_in_region(shot, TPL['baoturenwu'], rect, yuzhi=0.70)
                    if r:
                        return baotu_start(stop_event)
                # 检查活动按钮是否出现
                for i, rect in enumerate(REGIONS):
                    r = _match_in_region(shot, TPL['huodong'], rect)
                    if r:
                        return baotu_start(stop_event)
            log("宝图等待超时", "WARN")
            return

        # 点击找到的活动按钮
        for i, (cx, cy, val) in found_activity:
            safe_click(cx, cy)
            log(f"窗口{i+1} 点击活动 ({cx},{cy})")
            time.sleep(0.3)

        if _wait(3, stop_event):
            return

    # 第2步：全屏截图，找宝图任务按钮（循环等待）
    found_baotu = []
    missing = []
    for _retry in range(20):  # 最多等100秒
        shot = _screenshot_gray(full=True)
        found_baotu = []
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['baoturenwu'], rect, yuzhi=0.70)
            if r:
                found_baotu.append((i, r))
            else:
                missing.append(i)
        if not missing:
            break
        # 未找到的窗口点击重试
        shot = _retry_click_activity(missing, stop_event) or shot
        still_missing = []
        for i in missing:
            rect = REGIONS[i]
            r = _match_in_region(shot, TPL['baoturenwu'], rect, yuzhi=0.70)
            if r:
                found_baotu.append((i, r))
            else:
                still_missing.append(i)
        missing = still_missing
        if not missing:
            break
        if _wait(5, stop_event):
            return

    if missing:
        for i in missing:
            log(f"窗口{i+1}：未找到宝图任务", "WARN")
        send_feishu_msg(f"⚠️ 宝图：{','.join(f'窗口{i+1}' for i in missing)} 未找到宝图任务")

    # 点击宝图任务右边
    for i, (cx, cy, val) in found_baotu:
        safe_click(cx + 130, cy + 15)
        log(f"窗口{i+1} 点击宝图任务右边 ({cx+130},{cy+15})")
        time.sleep(0.3)

    if _wait(3, stop_event):
        return

    # 第3步：全屏截图，找听听无妨并点击
    shot = _screenshot_gray(full=True)
    found_tingting = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['tingtingwufang'], rect, yuzhi=0.75)
        if r:
            found_tingting.append((i, r))
        else:
            log(f"窗口{i+1}：未找到听听无妨", "WARN")
            missing.append(f"窗口{i+1}")
    if missing:
        send_feishu_msg(f"⚠️ 宝图：{','.join(missing)} 未找到听听无妨")

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
        shot = _screenshot_gray(full=True)
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
