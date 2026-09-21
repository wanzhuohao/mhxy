"""帮派任务：点右下角加号 → 点弹出的帮派图标 → 点帮派界面内两个按钮 → 点 X 关闭。

坐标均为窗口内相对坐标，按 REGIONS 偏移映射到各窗口。
参考 mhxy_code 的一键登出：先点右下角加号(830,645)呼出菜单，再点菜单里的帮派图标。
"""

import time
from core import log, _wait, get_game_windows
from context import safe_click

# 右下角加号：窗口内相对坐标
_ADD_X, _ADD_Y = 830, 645
# 弹出菜单里的帮派图标：窗口内相对坐标
_BANGPAI_X, _BANGPAI_Y = 546, 642
# 帮派界面内按钮：窗口内相对坐标
_BTN_A_X, _BTN_A_Y = 820, 418
_BTN_B_X, _BTN_B_Y = 690, 456
# 关闭 X：窗口内相对坐标
_CLOSE_X, _CLOSE_Y = 780, 135


def bangpai_start(stop_event):
    """帮派：逐窗口 加号→帮派→(820,418)→(690,456)→关面板，5 个号各操作一次。"""
    log("帮派 任务开始")

    windows = get_game_windows()
    if not windows:
        log("帮派：未找到游戏窗口", "WARN")
        return

    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event.is_set():
            log("帮派 被停止")
            return
        ox, oy = rect[0], rect[1]

        # 点右下角加号呼出菜单
        ax, ay = ox + _ADD_X, oy + _ADD_Y
        safe_click(ax, ay)
        log(f"窗口{i+1} 点击右下角加号 ({ax},{ay})")
        if _wait(1, stop_event):
            return

        # 点弹出的帮派图标
        bx, by = ox + _BANGPAI_X, oy + _BANGPAI_Y
        safe_click(bx, by)
        log(f"窗口{i+1} 点击帮派图标 ({bx},{by})")
        if _wait(1, stop_event):
            return

        # 点帮派界面内按钮 (820,418)
        ax, ay = ox + _BTN_A_X, oy + _BTN_A_Y
        safe_click(ax, ay)
        log(f"窗口{i+1} 点击帮派按钮A ({ax},{ay})")
        if _wait(1, stop_event):
            return

        # 点帮派界面内按钮 (690,456)
        bx, by = ox + _BTN_B_X, oy + _BTN_B_Y
        safe_click(bx, by)
        log(f"窗口{i+1} 点击帮派按钮B ({bx},{by})")
        if _wait(1, stop_event):
            return

        # 点 X 关闭帮派面板
        cx, cy = ox + _CLOSE_X, oy + _CLOSE_Y
        safe_click(cx, cy)
        log(f"窗口{i+1} 点击关闭X ({cx},{cy})")
        if _wait(0.5, stop_event):
            return

    log("帮派 任务完成")