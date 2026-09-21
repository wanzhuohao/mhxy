"""回家任务：点右下角加号 → 点(659,636) → 点(742,455)。

坐标均为窗口内相对坐标，按 REGIONS 偏移映射到各窗口。
参考帮派/一键登出：先点右下角加号(830,645)呼出菜单，再点回家相关按钮。
"""

import time
from core import log, _wait, get_game_windows
from context import safe_click

# 右下角加号：窗口内相对坐标
_ADD_X, _ADD_Y = 830, 645
# 回家菜单第一个按钮：窗口内相对坐标
_HOME_A_X, _HOME_A_Y = 659, 636
# 回家菜单第二个按钮：窗口内相对坐标
_HOME_B_X, _HOME_B_Y = 742, 455
# 回家后点击的位置：窗口内相对坐标
_AFTER_X, _AFTER_Y = 604, 140
# 最后一步前等待时间（秒），等前两步在所有窗口完成的过渡
_AFTER_WAIT = 3


def huijia_start(stop_event):
    """回家：阶段1 5个号先全部完成 加号→(659,636)→(742,455)，停一会儿后，
    阶段2 再统一让 5 个号点最后一下(604,140)。"""
    log("回家 任务开始")

    windows = get_game_windows()
    if not windows:
        log("回家：未找到游戏窗口", "WARN")
        return

    # 阶段1：5 个号都先完成前三步
    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event.is_set():
            log("回家 被停止")
            return
        ox, oy = rect[0], rect[1]

        # 点右下角加号呼出菜单
        ax, ay = ox + _ADD_X, oy + _ADD_Y
        safe_click(ax, ay)
        log(f"窗口{i+1} 点击右下角加号 ({ax},{ay})")
        if _wait(1, stop_event):
            return

        # 点回家按钮 (659,636)
        ax, ay = ox + _HOME_A_X, oy + _HOME_A_Y
        safe_click(ax, ay)
        log(f"窗口{i+1} 点击回家按钮A ({ax},{ay})")
        if _wait(1, stop_event):
            return

        # 点回家按钮 (742,455)
        bx, by = ox + _HOME_B_X, oy + _HOME_B_Y
        safe_click(bx, by)
        log(f"窗口{i+1} 点击回家按钮B ({bx},{by})")
        if _wait(1, stop_event):
            return

    # 等所有窗口完成前三步的过渡
    log(f"回家 前三步完成，等待 {_AFTER_WAIT}s 后统一点最后一下")
    if _wait(_AFTER_WAIT, stop_event):
        return

    # 阶段2：5 个号再统一点最后一下 (604,140)
    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event.is_set():
            log("回家 被停止")
            return
        ox, oy = rect[0], rect[1]
        cx, cy = ox + _AFTER_X, oy + _AFTER_Y
        safe_click(cx, cy)
        log(f"窗口{i+1} 回家后点击 ({cx},{cy})")
        if _wait(1, stop_event):
            return

    log("回家 任务完成")