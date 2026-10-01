"""刮刮乐任务（组队型，5 个窗口各刮一张，刮完自动关闭弹窗，刮+关一个流程）

参考 mhxy_code 的 guagua.py：点刮刮乐按钮 → 在刮奖区蛇形涂抹刮开 → 自动关闭结束画面/福利页。
坐标均为窗口内相对坐标（窗口 870x692），按 REGIONS 偏移映射到各窗口。
"""

import time
import random
import pyautogui

from core import log, REGIONS, TPL, _wait, _screenshot_gray, _match_in_region, get_game_windows
from context import safe_click

# 刮刮乐入口按钮：窗口内相对坐标
_BTN_X, _BTN_Y = 699, 551
# 福利图标：窗口内相对坐标（刮奖前需先点它进入）
_FULI_X, _FULI_Y = 30, 140
# 刮奖区矩形：窗口内相对坐标（左上、右下）
_AREA = (445, 353, 723, 435)


def guagua_start(stop_event):
    """刮刮乐：逐窗口点按钮+涂抹刮奖，最后自动关闭结束画面和福利页（一个完整流程）"""
    log("刮刮乐 任务开始")

    windows = get_game_windows()
    if not windows:
        log("刮刮乐：未找到游戏窗口", "WARN")
        return

    # 阶段1：每个窗口刮一张
    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event.is_set():
            log("刮刮乐 被停止")
            return
        ox, oy = rect[0], rect[1]

        # 阶段0：先点福利图标（30,140）进入刮刮乐（需点2次才生效）
        fx, fy = ox + _FULI_X, oy + _FULI_Y
        for _ in range(2):
            safe_click(fx, fy)
            log(f"窗口{i+1} 点击福利图标 ({fx},{fy})")
            if _wait(0.3, stop_event):
                return

        # 点刮刮乐按钮
        bx, by = ox + _BTN_X, oy + _BTN_Y
        safe_click(bx, by)
        log(f"窗口{i+1} 点击刮刮乐按钮 ({bx},{by})")
        if _wait(1, stop_event):
            return

        # 涂抹刮奖区
        x0, y0 = ox + _AREA[0], oy + _AREA[1]
        x1, y1 = ox + _AREA[2], oy + _AREA[3]
        _scratch_area(x0, y0, x1, y1, stop_event)
        log(f"窗口{i+1} 涂抹刮奖区 ({x0},{y0})-({x1},{y1})")
        if _wait(0.5, stop_event):
            return

    # 阶段2：刮完全部后自动关闭结束画面（大X）与福利页（小X）
    close_guagua_panels(stop_event)

    log("刮刮乐 任务完成")


def close_guagua_panels(stop_event):
    """识别并关闭各窗口刮刮乐的结束画面大X 与返回福利页的小X。"""
    shot = _screenshot_gray(full=True)
    big = 0
    for i, rect in enumerate(REGIONS):
        if stop_event.is_set():
            return
        match = _match_in_region(shot, TPL['guagua_close_big'], rect, yuzhi=0.8)
        if not match:
            continue
        safe_click(match[0], match[1])
        log(f"窗口{i+1} 点击刮刮乐大X ({match[0]},{match[1]})")
        big += 1
        time.sleep(0.3)

    if big:
        time.sleep(1)

    shot = _screenshot_gray(full=True)
    small = 0
    for i, rect in enumerate(REGIONS):
        if stop_event.is_set():
            return
        match = _match_in_region(shot, TPL['guagua_close_small'], rect, yuzhi=0.8)
        if not match:
            continue
        safe_click(match[0], match[1])
        log(f"窗口{i+1} 点击福利页小X ({match[0]},{match[1]})")
        small += 1
        time.sleep(0.3)

    log(f"关闭刮刮乐完成：大X {big} 个，小X {small} 个")


def _human_drag_to(tx, ty, segments=3):
    """分段移动到目标点，每段轻随机抖动和变速，模拟人手拖动。"""
    cur_x, cur_y = pyautogui.position()
    for s in range(1, segments + 1):
        ix = cur_x + (tx - cur_x) * s / segments + random.randint(-4, 4)
        iy = cur_y + (ty - cur_y) * s / segments + random.randint(-3, 3)
        pyautogui.moveTo(ix, iy, duration=random.uniform(0.03, 0.08))


def _scratch_area(x0, y0, x1, y1, stop_event):
    """在矩形区域内按住鼠标蛇形来回涂抹刮开涂层。异常安全，保证松开鼠标。"""
    pyautogui.moveTo(x0 + random.randint(0, 8), y0 + random.randint(3, 8))
    time.sleep(random.uniform(0.08, 0.15))
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.05, 0.10))
    try:
        height = y1 - y0
        rows = max(4, height // 13)          # 行数，行距约 13px
        step = height / rows
        # 向下蛇形 + 向上蛇形各一遍，确保刮干净
        ys = [y0 + int(r * step) for r in range(rows + 1)]
        ys = ys + ys[::-1]
        direction = 1                        # 1=向右，-1=向左
        for y in ys:
            if stop_event.is_set():
                break
            y = max(y0, min(y1, y + random.randint(-3, 3)))
            tx = (x1 - random.randint(0, 6)) if direction == 1 else (x0 + random.randint(0, 6))
            _human_drag_to(tx, y)
            direction *= -1
    finally:
        pyautogui.mouseUp()