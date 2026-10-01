"""组队任务（从参考稿 mhxy_code 移植：拖拽好友列表 + 图片识别"邀请入队"）"""

import random
import threading
import time
import win32gui
import win32api
import win32con
import pyautogui
from core import log, get_game_windows, find_pic, find_and_click, TPL
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

    _activate_window(first_hwnd)
    time.sleep(1)

    # 第一个点：连点2次，避免单次点不开
    for _ in range(2):
        _click_at(first_rect, 18 * 1.5, 313 * 1.5)
        time.sleep(0.5)
    time.sleep(1)

    # 先向上拖拽好友列表，滚过系统消息，露出4个好友
    drag_x = first_rect[0] + int(223 * 1.5)
    drag_y = first_rect[1] + int(300 * 1.5)
    pyautogui.moveTo(drag_x, drag_y)
    time.sleep(0.3)
    pyautogui.mouseDown()
    time.sleep(0.2)
    pyautogui.moveTo(drag_x, drag_y - 55, duration=0.3)
    pyautogui.mouseUp()
    time.sleep(0.5)

    friend_ys = [205, 241, 277, 317]  # 4 个好友（队伍最多 1 队长 + 4 队员）
    invite_pos = None  # 缓存邀请入队按钮位置
    for idx, fy in enumerate(friend_ys):
        if stop_event.is_set():
            return
        _click_at(first_rect, 223 * 1.5, fy * 1.5)
        time.sleep(1)
        if invite_pos is None:
            # 用图片识别找"邀请入队"位置（region 语义：(left, top, right, bottom)）
            pos = find_pic(TPL['yaoqingrudui'], yuzhi=0.6, region=first_rect)
            if pos:
                invite_pos = (pos[0], pos[1])
                safe_click(invite_pos[0], invite_pos[1])
                log(f"好友{idx+1}: 识别到邀请入队 ({invite_pos[0]},{invite_pos[1]}) ✓")
            else:
                log(f"好友{idx+1}: 未找到邀请入队，跳过", "WARN")
        else:
            # 用缓存的位置点击
            safe_click(invite_pos[0] + random.randint(-3, 3), invite_pos[1] + random.randint(-3, 3))
            log(f"好友{idx+1}: 邀请入队 ✓")
        time.sleep(0.5)

    if invite_pos is None:
        log("所有好友都未找到邀请入队按钮", "WARN")

    for i, (hwnd, rect) in enumerate(windows[1:5], 2):
        if stop_event.is_set():
            return
        try:
            _activate_window(hwnd)
            time.sleep(0.5)
            _click_at(rect, 300, 350, rand_x=10, rand_y=5 if i != 2 else 0)
            time.sleep(0.5)
        except Exception as e:
            log(f"处理窗口{i}出错: {e}", "ERR")

    # 回到窗口1，关闭好友面板
    _activate_window(first_hwnd)
    time.sleep(0.5)
    # 循环识别并关闭所有弹出面板（好友面板、队伍面板等）
    # region 语义为 (left, top, right, bottom)；限定窗口1右上区域避免误匹配到其他窗口
    x_region = (first_rect[0] + 500, first_rect[1] + 50,
                first_rect[0] + 500 + 370, first_rect[1] + 50 + 300)
    for _ in range(3):
        if stop_event.is_set():
            return
        if find_and_click(TPL['panel_x'], yuzhi=0.7, region=x_region):
            log("关闭面板 ✓")
            time.sleep(0.5)
        else:
            break
    log("组队完成")


def _activate_window(hwnd):
    """激活窗口到前台，多种方案兜底，失败不抛异常"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        return
    except Exception:
        pass
    try:
        # 模拟按一次 Alt 键解除前台锁定限制，再重试
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32gui.SetForegroundWindow(hwnd)
        return
    except Exception:
        pass


def _click_at(rect, rel_x, rel_y, rand_x=5, rand_y=5):
    x = rect[0] + int(rel_x) + random.randint(-rand_x, rand_x)
    y = rect[1] + int(rel_y) + random.randint(-rand_y, rand_y)
    safe_click(x, y)