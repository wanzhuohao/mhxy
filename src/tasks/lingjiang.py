"""领奖任务"""

import random
import time
from core import log, get_game_windows, safe_click, _screenshot_gray, TPL, REGIONS, _match_in_region, _wait


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

    # 第3步：关闭奖励面板
    # 参考 core.close_random_popups / zhuogui 领取双倍：全窗口识别 panel_x 关闭，
    # 识别不到就不点（避免固定坐标点错），仅告警。
    if _wait(1, stop_event):
        return
    shot_close = _screenshot_gray(full=True)
    closed = 0
    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event and stop_event.is_set():
            break
        r = _match_in_region(shot_close, TPL['panel_x'], rect, yuzhi=0.7)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} [panel_x] 关闭奖励面板 ({r[0]},{r[1]})")
            time.sleep(0.3)
            closed += 1
        else:
            log(f"窗口{i+1} 未识别到关闭按钮，跳过", "WARN")
    if closed == 0:
        log("领奖：未识别到任何关闭按钮", "WARN")

    log("领取奖励完成")


