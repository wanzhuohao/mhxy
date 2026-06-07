"""秘境任务（全屏截图，分5区域处理）"""

import time
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from tasks.shimen import REGIONS, _match_in_region, _retry_click_activity


def mijing_start(stop_event):
    """秘境：全屏截图 → 点活动 → 点秘境右边 → 进入战斗/降妖"""
    log("秘境任务开始")

    # 第1步：全屏截图，找5个窗口的活动按钮
    shot = _screenshot_gray(full=True)
    found_activity = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['huodong'], rect)
        if r:
            found_activity.append((i, r))
        else:
            log(f"窗口{i+1}：未找到活动按钮", "WARN")
            missing.append(f"窗口{i+1}")
    if missing:
        send_feishu_msg(f"⚠️ 秘境：{','.join(missing)} 未找到活动按钮")

    if found_activity:
        # 点击找到的活动
        for i, (cx, cy, val) in found_activity:
            safe_click(cx, cy)
            log(f"窗口{i+1} 点击活动 ({cx},{cy})")
            time.sleep(0.3)

        if _wait(3, stop_event):
            return

        # 第2步：全屏截图，找秘境按钮并点击右边
        shot = _screenshot_gray(full=True)
        found_mijing = []
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['huodongmijing'], rect)
            if r:
                found_mijing.append((i, r))
            else:
                missing.append(i)

        # 未找到的窗口点击重试
        if missing:
            shot = _retry_click_activity(missing, stop_event) or shot
            still_missing = []
            for i in missing:
                r = _match_in_region(shot, TPL['huodongmijing'], REGIONS[i])
                if r:
                    found_mijing.append((i, r))
                else:
                    still_missing.append(i)
            missing = still_missing

        for i, r in found_mijing:
            safe_click(r[0] + 130, r[1] + 10)
            log(f"窗口{i+1} 点击秘境右边 ({r[0]+130},{r[1]+10})")
            time.sleep(0.3)

        if missing:
            for i in missing:
                log(f"窗口{i+1}：未找到秘境按钮", "WARN")
            send_feishu_msg(f"⚠️ 秘境：{','.join(f'窗口{i+1}' for i in missing)} 未找到秘境按钮")

        if _wait(2, stop_event):
            return

        # 第3步：全屏截图，等妖族的事出现
        log("等待妖族的事...")
        for _ in range(30):
            if stop_event.is_set():
                return
            shot = _screenshot_gray(full=True)
            found = False
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['yaozuodeshi'], rect)
                if r:
                    safe_click(r[0], r[1])
                    log(f"窗口{i+1} 点击妖族的事 ({r[0]},{r[1]})")
                    found = True
                    time.sleep(0.3)
            if found:
                break
            if _wait(3, stop_event):
                return

        if _wait(2, stop_event):
            return

        # 第4步：全屏截图，点继续
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['jixu'], rect)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 点击继续 ({r[0]},{r[1]})")
            time.sleep(0.3)

        if _wait(2, stop_event):
            return
    else:
        log("所有窗口都未找到活动按钮，直接进入战斗循环")

    # 第5步：循环找进入战斗和秘境降妖，检测失败标志
    log("等待秘境战斗...")
    done_windows = set()
    while not stop_event.is_set():
        shot = _screenshot_gray(full=True)

        # 检测失败标志，已完成的跳过
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['shibai'], rect)
            if r:
                log(f"窗口{i+1} 秘境已完成（检测到失败标志）")
                done_windows.add(i)

        if len(done_windows) == len(REGIONS):
            log("秘境任务全部完成，点击所有失败标志")
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['shibai'], rect)
                if r:
                    safe_click(r[0], r[1])
                    log(f"窗口{i+1} 点击失败标志 ({r[0]},{r[1]})")
                    time.sleep(0.3)

            # 点击5个离开
            if _wait(1, stop_event):
                break
            shot = _screenshot_gray(full=True)
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['likai'], rect)
                if r:
                    safe_click(r[0], r[1])
                    log(f"窗口{i+1} 点击离开 ({r[0]},{r[1]})")
                    time.sleep(0.3)
            break

        # 找进入战斗
        found = False
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['jinruzhandou'], rect, yuzhi=0.55)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 点击进入战斗 ({r[0]},{r[1]})")
                found = True
                time.sleep(0.3)

        if not found:
            # 找秘境降妖
            shot = _screenshot_gray(full=True)
            for i, rect in enumerate(REGIONS):
                if i in done_windows:
                    continue
                r = _match_in_region(shot, TPL['mijingxiangyao'], rect, yuzhi=0.5)
                if r:
                    safe_click(r[0], r[1])
                    log(f"窗口{i+1} 点击秘境降妖 ({r[0]},{r[1]})")
                    found = True
                    time.sleep(0.3)

        if _wait(3, stop_event):
            break

    log("秘境任务完成")
