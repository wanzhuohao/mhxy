"""捉鬼任务（组队型，只在队长窗口执行）"""

import threading
import time
import pyautogui
from core import log
from context import safe_click
from notify import send_feishu_msg


def _get_window1_rect():
    """固定取屏幕左上角的窗口1"""
    import win32gui
    windows = []
    def _enum(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if '梦幻西游' in title or 'MyLauncher' in title:
                rect = win32gui.GetWindowRect(hwnd)
                windows.append((hwnd, rect))
    win32gui.EnumWindows(_enum, None)
    windows.sort(key=lambda w: (w[1][1], w[1][0]))
    return windows[0][1] if windows else None


def zhuogui_start(stop_event: threading.Event, rounds=2):
    """捉鬼：检测弹窗颜色 → 点击 → 等待 → 循环"""
    log("捉鬼任务开始")
    send_feishu_msg("🎮 捉鬼任务开始")

    # 固定取屏幕左上角的窗口1
    w1_rect = _get_window1_rect()
    if not w1_rect:
        log("未找到游戏窗口", "WARN")
        return
    ox, oy = w1_rect[0], w1_rect[1]
    log(f"窗口1 rect={w1_rect}")

    # 第1步：点活动
    from core import TPL, find_pic, find_and_click, _retry, _wait
    entered_from_activity = False
    if find_and_click(TPL['huodong'], region=w1_rect):
        log("点击活动")
        entered_from_activity = True
        if _wait(2, stop_event):
            return

        # 第2步：点捉鬼右边的按钮
        if not _retry(lambda: find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10), label="点捉鬼右边"):
            log("捉鬼：未找到捉鬼按钮", "WARN")
            return
        if _wait(2, stop_event):
            return
    else:
        log("未找到活动按钮，直接检测完成图")

    count = 0
    first_round = True
    try:
        while not stop_event.is_set():
            if first_round and entered_from_activity:
                # 从活动进入，第一次不检测
                first_round = False
            else:
                # 检测完成图片
                first_round = False
                if not find_pic(TPL['zhuogui_wancheng'], yuzhi=0.8, region=w1_rect):
                    if stop_event.wait(3):
                        break
                    continue

            count += 1
            log(f"第{count}轮捉鬼")
            send_feishu_msg(f"完成第{count}轮捉鬼")
            if count >= rounds:
                log(f"捉鬼{rounds}轮已完成")
                # 最后一轮点 (350, 392) 退出
                safe_click(ox + 350, oy + 392)
                send_feishu_msg(f"✅ 捉鬼任务完成，共{count}轮")
                stop_event.set()
                break

            # 点击弹窗
            safe_click(ox + 511, oy + 392)
            if stop_event.wait(1):
                break

            # 等10秒
            if stop_event.wait(10):
                break

            # 点击确认
            safe_click(ox + 707, oy + 242)
            if stop_event.wait(1):
                break

            # 点击两个随机位置
            _random_click(ox + 767, oy + 206, 15, 15)
            if stop_event.wait(1):
                break
            _random_click(ox + 767, oy + 206, 10, 10)
            if stop_event.wait(1):
                break

            log("等待60秒后重新检测...")
            if stop_event.wait(60):
                break
    except Exception as e:
        log(f"捉鬼任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 捉鬼任务异常: {e}")


def _check_color_at(x, y, target_rgb, tolerance=8):
    """检测指定坐标颜色"""
    shot = pyautogui.screenshot(region=(x - 2, y - 2, 5, 5))
    for dx in range(5):
        for dy in range(5):
            pixel = shot.getpixel((dx, dy))
            if all(abs(pixel[i] - target_rgb[i]) <= tolerance for i in range(3)):
                return True, pixel
    return False, None


def _random_click(x, y, rand_x=5, rand_y=5):
    """带随机偏移的点击"""
    import random
    cx = x + random.randint(-rand_x, rand_x)
    cy = y + random.randint(-rand_y, rand_y)
    safe_click(cx, cy)
