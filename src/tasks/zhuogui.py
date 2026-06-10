"""捉鬼任务（组队型，只在队长窗口执行）"""

import threading
import time
from core import log, get_game_windows
from context import safe_click
from notify import send_feishu_msg


def _get_window1_rect():
    """固定窗口1坐标（2560×1440分辨率，窗口870×692）"""
    return (0, 0, 870, 692)


def zhuogui_start(stop_event: threading.Event, rounds=2):
    """捉鬼：点击活动进入 → 点击去接受任务 → 等待完成 → 循环指定轮数"""
    log("捉鬼任务开始")

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

        # 第2步：点捉鬼右边的按钮（未找到则点击重试）
        if not _retry(lambda: find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10)):
            safe_click(132, 188)
            if _wait(3, stop_event):
                return
            if not _retry(lambda: find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10)):
                log("捉鬼：未找到捉鬼按钮", "WARN")
                return
        if _wait(2, stop_event):
            return
    else:
        log("未找到活动按钮，直接检测完成图")

    count = 0
    try:
        while not stop_event.is_set():
            if count == 0 and entered_from_activity:
                # 第1轮：从活动进入，不点去接受任务，直接等10秒→确认→等60秒→检测完成图
                log("第1轮：从活动进入，直接开始")
            else:
                # 后续轮次：等待并检测完成图
                log(f"等待第{count+1}轮完成图...")
                found = False
                # 最多等待90秒检测完成图
                for _ in range(90):
                    if stop_event.is_set():
                        return
                    if find_pic(TPL['zhuogui_wancheng'], yuzhi=0.5, region=w1_rect):
                        found = True
                        break
                    if stop_event.wait(1):
                        return

                if not found:
                    log("未检测到完成图，继续等待...")
                    continue

                # 检测到完成图，轮数+1
                count += 1
                log(f"第{count}轮捉鬼完成")
                send_feishu_msg(f"完成第{count}轮捉鬼")

                # 检查是否达到目标轮数
                if count >= rounds:
                    log(f"捉鬼{rounds}轮已完成")
                    # 点 (350, 392) 退出
                    safe_click(ox + 350, oy + 392)
                    send_feishu_msg(f"✅ 捉鬼任务完成，共{count}轮")
                    stop_event.set()
                    break

                # 未达到目标轮数，点击去接受任务开始下一轮
                log(f"点击去接受任务开始第{count+1}轮")
                safe_click(ox + 511, oy + 392)
                if stop_event.wait(1):
                    break

            # 等待10秒
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


def _random_click(x, y, rand_x=5, rand_y=5):
    """带随机偏移的点击"""
    import random
    cx = x + random.randint(-rand_x, rand_x)
    cy = y + random.randint(-rand_y, rand_y)
    safe_click(cx, cy)
