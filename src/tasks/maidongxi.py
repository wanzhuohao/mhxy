"""卖东西 —— 点商城图标打开，切到我要出售，循环点物品+出售

第一步打开用鼠标点商城图标（相对窗口 41,200），不再用 Alt+A 快捷键；后续沿用原逻辑。
"""

import time
import random
from core import log, _wait, safe_click, find_pic, find_and_click, TPL, REGIONS, get_game_windows
import win32gui


# 商城图标相对窗口坐标（替代原来的 Alt+A 快捷键）
_OPEN_REL = (41, 200)


def _open_by_click(hwnd, rect):
    """激活窗口并点击商城图标打开（不再用 Alt+A）。"""
    if hwnd:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.4)
    x = rect[0] + _OPEN_REL[0] + random.randint(-3, 3)
    y = rect[1] + _OPEN_REL[1] + random.randint(-3, 3)
    safe_click(x, y)
    time.sleep(0.3)


# 后续步骤相对坐标（商会界面校准值，保留）
_REL_SHANGHUI_TAB = (810, 225)   # 右侧"商会"灯笼标签
_REL_WOYAOCHUSHOU = (233, 154)   # "我要出售"标签
_REL_FIRST_ITEM   = (125, 305)   # 第一个物品（原205，y+100）
_REL_CHUSHOU_BTN  = (664, 574)   # "出售"按钮（右移15px）


def _click_rel(x0, y0, rel, rand=3):
    x = x0 + rel[0] + random.randint(-rand, rand)
    y = y0 + rel[1] + random.randint(-rand, rand)
    safe_click(x, y)


def _click_tpl_or_rel(tpl_key, x0, y0, rel, stop_event, yuzhi=0.8, tries=3, label="", rect=None):
    for _ in range(tries):
        if stop_event.is_set():
            return False
        if find_and_click(TPL[tpl_key], yuzhi=yuzhi, region=rect):
            return True
        _wait(0.8, stop_event)
    log(f"[卖东西] {label}未识别，回退坐标点击", "WARN")
    _click_rel(x0, y0, rel)
    return False


def _window_label(rect):
    x, y = rect[0], rect[1]
    for i, (left, top, right, bottom) in enumerate(REGIONS, start=1):
        if left <= x < right and top <= y < bottom:
            return f"窗口{i}"
    return f"窗口({x},{y})"


def _close_shop_panel(stop_event, label, tries=3, rect=None):
    """在指定窗口区域内识别并关闭商会面板。"""
    for attempt in range(1, tries + 1):
        if stop_event.is_set():
            return False
        if find_and_click(TPL['panel_x'], yuzhi=0.85, region=rect):
            log(f"[卖东西] {label} 第{attempt}次识别并关闭X成功")
            return True
        if _wait(0.5, stop_event):
            return False
    log(f"[卖东西] {label} 连续{tries}次未识别到关闭X", "WARN")
    return False


def _sell_one_window(hwnd, rect, stop_event):
    """对单个窗口执行出售流程：点商城打开→切商会→切我要出售→循环出售→关闭。
    返回出售次数。"""
    x0, y0 = rect[0], rect[1]
    label = _window_label(rect)

    # 1. 打开商城（点商城图标，不再用 Alt+A）
    log(f"[卖东西] {label} 打开(点商城)")
    _open_by_click(hwnd, rect)
    if _wait(2.5, stop_event):
        return 0

    # 2. 点击右侧"商会"标签（打开的是摆摊/商城，需切到商会）
    log(f"[卖东西] {label} 切换到商会")
    _click_tpl_or_rel('shanghui_tab', x0, y0, _REL_SHANGHUI_TAB, stop_event, label="商会", rect=rect)
    if _wait(2, stop_event):
        return 0

    # 3. 切换到"我要出售"
    log(f"[卖东西] {label} 切换到我要出售")
    _click_tpl_or_rel('woyaochushou_tab', x0, y0, _REL_WOYAOCHUSHOU, stop_event, yuzhi=0.70, label="我要出售", rect=rect)
    if _wait(2, stop_event):
        return 0

    # 4. 只选中一次第一个物品，后续连续点击出售即可
    sold = 0
    if find_pic(TPL['meiyoushangpin'], yuzhi=0.8, region=rect):
        log(f"[卖东西] {label} 已无可出售商品，关闭窗口（共出售 {sold} 次）")
        _close_shop_panel(stop_event, label, rect=rect)
        return 0

    _click_rel(x0, y0, _REL_FIRST_ITEM)
    time.sleep(0.5)

    while not stop_event.is_set():
        if find_pic(TPL['meiyoushangpin'], yuzhi=0.8, region=rect):
            log(f"[卖东西] {label} 已无可出售商品，关闭窗口（共出售 {sold} 次）")
            _close_shop_panel(stop_event, label, rect=rect)
            return sold

        if not find_and_click(TPL['chushou_btn'], yuzhi=0.85, dx=15, region=rect):
            _click_rel(x0, y0, _REL_CHUSHOU_BTN, rand=2)
        sold += 1

        if _wait(1, stop_event):
            break

        if sold % 10 == 0:
            log(f"[卖东西] {label} 已出售 {sold} 次")

    log(f"[卖东西] {label} 结束，共操作 {sold} 次")
    return sold


def maidongxi_start(stop_event):
    """出售：遍历 5 个窗口，逐个点商城→切商会→切我要出售→循环出售→关闭。"""
    log("[卖东西] 任务开始")

    windows = get_game_windows()
    if not windows:
        log("[卖东西] 未找到游戏窗口", "WARN")
        return

    for i, (hwnd, rect) in enumerate(windows[:5]):
        if stop_event.is_set():
            log("[卖东西] 被停止")
            return
        _sell_one_window(hwnd, rect, stop_event)

    log("[卖东西] 任务完成")
