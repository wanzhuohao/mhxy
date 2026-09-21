"""卖东西 —— Alt+A 打开，切到我要出售，循环点物品+出售

第一步打开用 Alt+A（SendInput 硬件扫描码，梦幻不认 keybd_event/pyautogui 的虚拟键）
替代原来的点商城图标；后续沿用原逻辑。多窗口并行时用锁串行"激活+发键"，
避免键盘焦点竞争把 Alt+A 发到别的窗口。
"""

import time
import random
import threading
import ctypes
from core import log, _wait, safe_click, find_pic, find_and_click, TPL, REGIONS, get_game_windows
import win32gui


# ---- SendInput 发硬件扫描码（虚拟键游戏不认，必须扫描码）----
_PUL = ctypes.POINTER(ctypes.c_ulong)
class _KBD(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", _PUL)]
class _MOU(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", _PUL)]
class _INU(ctypes.Union):
    _fields_ = [("mi", _MOU), ("ki", _KBD)]
class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _INU)]

_SCANCODE = 0x0008
_KEYUP = 0x0002

def _scan(code, up=False):
    flags = _SCANCODE | (_KEYUP if up else 0)
    inp = _INPUT(); inp.type = 1; inp.ki = _KBD(0, code, flags, 0, None)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

# 键盘全局锁：Alt+A 依赖前台焦点，多窗口并行会互抢前台把键发错窗口，必须串行
_hotkey_lock = threading.Lock()

def _open_by_hotkey(hwnd):
    """激活窗口并按 Alt+A 打开（全局串行，保证键发给正确窗口）。Alt=0x38 A=0x1E"""
    with _hotkey_lock:
        if hwnd:
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            time.sleep(0.4)
        _scan(0x38); time.sleep(0.04)
        _scan(0x1E); time.sleep(0.04)
        _scan(0x1E, True); time.sleep(0.04)
        _scan(0x38, True)
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
    """对单个窗口执行出售流程：Alt+A打开→切商会→切我要出售→循环出售→关闭。
    返回出售次数。"""
    x0, y0 = rect[0], rect[1]
    label = _window_label(rect)

    # 1. 打开（Alt+A 替代点商城），并激活该窗口
    log(f"[卖东西] {label} 打开(Alt+A)")
    _open_by_hotkey(hwnd)
    if _wait(2.5, stop_event):
        return 0

    # 2. 点击右侧"商会"标签（Alt+A 打开的是摆摊，需切到商会）
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
    """出售：遍历 5 个窗口，逐个 Alt+A→切商会→切我要出售→循环出售→关闭。"""
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
