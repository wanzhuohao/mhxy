"""捉鬼任务（组队型，只在队长窗口执行）"""

import threading
import time
from core import log, get_game_windows, REGIONS, find_pic
from context import safe_click
from notify import send_feishu_msg


def zhuogui_start(stop_event: threading.Event, rounds=2):
    """捉鬼：点击活动进入 → 点击去接受任务 → 等待完成 → 循环指定轮数

    完成图检测：逐秒检测 TPL['zhuogui_wancheng']，每10秒打印一次当前匹配度，
    便于调整阈值。若图片匹配一直不准，可在 debug_match.py 中测试实际匹配度。
    """
    log("捉鬼任务开始")

    # 固定取屏幕左上角的窗口1
    w1_rect = REGIONS[0]
    ox, oy = w1_rect[0], w1_rect[1]
    log(f"窗口1 rect={w1_rect}")

    # 第1步：点活动
    from core import TPL, find_and_click, _retry, _wait, find_pic_debug
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

    # 完成检测：检测"捉鬼确定"按钮（1.py 原方案）
    WANCHENG_YUZHI = 0.7

    count = 0
    try:
        while not stop_event.is_set():
            if count == 0 and entered_from_activity:
                # 第1轮：从活动进入，先执行确定等操作，再开始检测完成图
                log("第1轮：从活动进入，执行确认操作")
                if stop_event.wait(10):
                    break
                safe_click(ox + 707, oy + 242)
                if stop_event.wait(1):
                    break
                _random_click(ox + 767, oy + 206, 15, 15)
                if stop_event.wait(1):
                    break
                _random_click(ox + 767, oy + 206, 10, 10)
                if stop_event.wait(1):
                    break
                log("第1轮确认操作完成，等待60秒后开始检测完成图")
            else:
                log(f"等待第{count+1}轮完成...")

            # 先等60秒再开始检测
            if stop_event.wait(60):
                break

            # 每60秒检测一次完成图，无上限
            while not stop_event.is_set():
                if find_pic(TPL['zhuoguiqueding'], yuzhi=WANCHENG_YUZHI, region=w1_rect):
                    log(f"  ✓ 检测到捉鬼完成图！")
                    break
                log(f"  未检测到完成图，60秒后再检测")
                if stop_event.wait(60):
                    break

            if stop_event.is_set():
                break

            count += 1
            log(f"第{count}轮捉鬼完成！")
            send_feishu_msg(f"完成第{count}轮捉鬼")

            # 检测到完成图后，点击领取任务（第1轮不点，因为第1轮没检测到图片）
            if count > 1 or not entered_from_activity:
                safe_click(ox + 511, oy + 392)
                log(f"点击领取任务 ({ox+511},{oy+392})")

            # 等10秒 → 点确定 → 点2次按钮
            if stop_event.wait(10):
                break

            safe_click(ox + 707, oy + 242)
            if stop_event.wait(1):
                break

            _random_click(ox + 767, oy + 206, 15, 15)
            if stop_event.wait(1):
                break
            _random_click(ox + 767, oy + 206, 10, 10)
            if stop_event.wait(1):
                break

                if count >= rounds:
                    log(f"捉鬼{rounds}轮已完成，退出")
                    safe_click(ox + 350, oy + 392)
                    send_feishu_msg(f"✅ 捉鬼任务完成，共{count}轮")
                    stop_event.set()
                    break

                continue
    except Exception as e:
        log(f"捉鬼任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 捉鬼任务异常: {e}")


def _random_click(x, y, rand_x=5, rand_y=5):
    """带随机偏移的点击"""
    import random
    cx = x + random.randint(-rand_x, rand_x)
    cy = y + random.randint(-rand_y, rand_y)
    safe_click(cx, cy)
