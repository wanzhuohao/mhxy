"""捉鬼任务（组队型，只在队长窗口执行）"""

import threading
import time
import pyautogui
from core import log
from context import safe_click
from notify import send_feishu_msg


def zhuogui_start(stop_event: threading.Event):
    """捉鬼：检测弹窗颜色 → 点击 → 等待 → 循环"""
    log("捉鬼任务开始")
    send_feishu_msg("🎮 捉鬼任务开始")
    count = 0
    try:
        while not stop_event.is_set():
            p1_ok, _ = _check_color_at(514, 346, (163, 124, 83))
            p2_ok, _ = _check_color_at(511, 392, (243, 202, 105))
            if p1_ok and p2_ok:
                count += 1
                log(f"检测到捉鬼弹窗，第{count}次")
                send_feishu_msg(f"完成第{count}轮捉鬼")
                safe_click(511, 392)
                if stop_event.wait(10):
                    break
                safe_click(707, 242)
                if stop_event.wait(1):
                    break
                _random_click(767, 206, 15, 15)
                if stop_event.wait(1):
                    break
                _random_click(767, 206, 10, 10)
                if stop_event.wait(1):
                    break
                log("等待60秒后重新检测...")
                if stop_event.wait(60):
                    break
            else:
                if stop_event.wait(3):
                    break
        send_feishu_msg(f"✅ 捉鬼任务完成，共{count}轮")
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
