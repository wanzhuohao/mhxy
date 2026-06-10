"""组队任务"""

import threading
import time
import random
import win32gui
from core import log, get_game_windows
from context import safe_click


def zudui_start(stop_event: threading.Event):
    """自动组队（窗口 1 为队长）"""
    log("组队开始")

    windows = get_game_windows()
    if not windows:
        log("未找到游戏窗口", "WARN")
        return

    windows.sort(key=lambda w: (w[1][1], w[1][0]))
    first_hwnd, first_rect = windows[0]

    win32gui.SetForegroundWindow(first_hwnd)
    time.sleep(1)

    _click_at(first_rect, 18 * 1.5, 313 * 1.5)
    time.sleep(1)

    friend_ys = [241, 277, 317, 350]
    for fy in friend_ys:
        if stop_event.is_set():
            return
        _click_at(first_rect, 223 * 1.5, fy * 1.5)
        time.sleep(0.5)
        _click_at(first_rect, 352 * 1.5, 230 * 1.5)
        time.sleep(0.5)

    for i, (hwnd, rect) in enumerate(windows[1:5], 2):
        if stop_event.is_set():
            return
        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            _click_at(rect, 300, 350, rand_x=10, rand_y=5 if i != 2 else 0)
            time.sleep(0.5)
        except Exception as e:
            log(f"处理窗口{i}出错: {e}", "ERR")
    # 最后点击 (802, 136)
    safe_click(802 + random.randint(-3, 3), 136 + random.randint(-3, 3))
    log("组队完成")


def _click_at(rect, rel_x, rel_y, rand_x=5, rand_y=5):
    x = rect[0] + int(rel_x) + random.randint(-rand_x, rand_x)
    y = rect[1] + int(rel_y) + random.randint(-rand_y, rand_y)
    safe_click(x, y)
