"""押镖任务（全屏截图，分5区域处理）"""

import time
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from core import _match_in_region, _retry_click_activity, REGIONS


def yabiao_start(stop_event):
    """押镖：全屏截图 → 点活动 → 点运镖右边 → 点确定 → 点运送镖银"""
    log("押镖任务开始")

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
        send_feishu_msg(f"⚠️ 押镖：{','.join(missing)} 未找到活动按钮")

    if found_activity:
        for i, (cx, cy, val) in found_activity:
            safe_click(cx, cy)
            log(f"窗口{i+1} [huodong] 点击活动 ({cx},{cy})")
            time.sleep(0.3)

        if _wait(3, stop_event):
            return

        # 第2步：全屏截图，找运镖按钮并点击右边（dx=230, dy=10）
        shot = _screenshot_gray(full=True)
        found_yunbiao = []
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['yunbiao'], rect)
            if r:
                found_yunbiao.append((i, r))
            else:
                missing.append(i)

        # 未找到的窗口点击重试
        if missing:
            result = _retry_click_activity(missing, stop_event)
            if result is not None:
                shot = result
            still_missing = []
            for i in missing:
                r = _match_in_region(shot, TPL['yunbiao'], REGIONS[i])
                if r:
                    found_yunbiao.append((i, r))
                else:
                    still_missing.append(i)
            missing = still_missing

        for i, r in found_yunbiao:
            safe_click(r[0] + 180, r[1] + 10)
            log(f"窗口{i+1} [yunbiao] 点击运镖右边 ({r[0]+180},{r[1]+10})")
            time.sleep(0.3)

        if missing:
            for i in missing:
                log(f"窗口{i+1}：未找到运镖按钮", "WARN")
            send_feishu_msg(f"⚠️ 押镖：{','.join(f'窗口{i+1}' for i in missing)} 未找到运镖按钮")

        if _wait(2, stop_event):
            return
    else:
        log("所有窗口都未找到活动按钮，直接进入押镖循环")

    # 第3步：循环找运送镖银 → 确定
    tianti_count = 0  # 剑会群雄弹窗关闭累计，超限停止防死循环误点
    while not stop_event.is_set():
        shot = _screenshot_gray(full=True)
        found_any = False

        # 检测剑会群雄弹窗，在标题附近(右上区域)找x关闭，避开左下聊天框误匹配
        # 累计超过6次仍检测到则跳过(关不掉，避免死循环误开聊天)
        if tianti_count < 6:
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['tianti'], rect)
                if r:
                    xr = (max(rect[0], r[0] - 60), max(rect[1], r[1] - 120),
                          min(rect[2], r[0] + 300), min(rect[3], r[1] + 80))
                    r_x = _match_in_region(shot, TPL['x'], xr)
                    if r_x:
                        safe_click(r_x[0], r_x[1])
                        log(f"窗口{i+1} 关闭剑会群雄弹窗 ({r_x[0]},{r_x[1]})")
                        found_any = True
                        tianti_count += 1
                        time.sleep(0.3)

        # 找运送镖银并点击
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['yasongbiaoyin'], rect)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [yasongbiaoyin] 点击运送镖银 ({r[0]},{r[1]})")
                found_any = True
                time.sleep(0.3)

        if _wait(3, stop_event):
            break

        # 找确定并点击
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['queding'], rect)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [queding] 点击确定 ({r[0]},{r[1]})")
                found_any = True
                time.sleep(0.3)

        # 判断结束：有5个活动按钮且没有确定/运送镖银
        if not found_any:
            shot = _screenshot_gray(full=True)
            activity_count = 0
            for i, rect in enumerate(REGIONS):
                r = _match_in_region(shot, TPL['huodong'], rect)
                if r:
                    activity_count += 1
            if activity_count >= 5:
                log("5个窗口都有活动按钮，押镖结束")
                break

        if _wait(3, stop_event):
            break

    log("押镖任务完成")
