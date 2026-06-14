"""领奖任务"""

import random
from core import log, get_game_windows, safe_click, _screenshot_gray, TPL, REGIONS, _match_in_region, _wait, time


def lingjiang_start(stop_event):
    """领取奖励：全屏找huodong → 点活动 → 每个窗口5个奖励按钮（按轮次）"""
    log("领取奖励开始")

    windows = get_game_windows()
    if not windows:
        log("领奖：未找到游戏窗口", "WARN")
        return

    if _wait(3, stop_event):
        return

    # 第1步：全屏截图找活动
    shot = _screenshot_gray(full=True)
    missing = []
    for i, (hwnd, rect) in enumerate(windows[:5]):
        r = _match_in_region(shot, TPL['huodong'], rect)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} [huodong] 点击活动 ({r[0]},{r[1]})")
        else:
            missing.append(i)
        time.sleep(0.3)

    if missing:
        log(f"未找到活动的窗口：{[str(i+1) for i in missing]}", "WARN")

    if _wait(3, stop_event):
        return

    # 第2步：每个窗口5个奖励按钮，按轮次点击
    reward_xs = [299, 405, 526, 640, 745]
    reward_y = 500
    for rx in reward_xs:
        if stop_event and stop_event.is_set():
            break
        for i, (hwnd, rect) in enumerate(windows[:5]):
            ox, oy = rect[0], rect[1]
            x = ox + rx + random.randint(-3, 3)
            y = oy + reward_y + random.randint(-3, 3)
            safe_click(x, y)
            log(f"窗口{i+1} 领取奖励 ({x},{y})")
            time.sleep(0.3)
        time.sleep(0.5)

    log("领取奖励完成")


