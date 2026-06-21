"""副本任务（组队型，只在队长窗口执行）"""

import random
import threading
from core import log, find_pic, find_and_click, find_all, find_and_click_path, TPL, _wait, _retry, get_game_windows
from context import safe_click, get_window_rect
from notify import send_feishu_msg

_jinru_index = 0  # 进入按钮轮流计数


def fuben_start(stop_event: threading.Event):
    """副本：跳过剧情、确定、战斗坐标"""
    log("副本任务开始")

    # 固定窗口1坐标
    rect = (0, 0, 870, 692)

    # 第0步：先检查跳过按钮是否已经在屏幕上（副本已进入）
    if find_pic(TPL['fubentiaoguo'], yuzhi=0.6, region=rect):
        log("副本已进入，直接进入主循环")
    # 第1步：点活动（没找到则跳过，直接进主循环）
    elif find_and_click(TPL['huodong'], region=rect):
        log("[huodong] 点击活动")
        if _wait(2, stop_event):
            return

        # 第2步：点普通右边的按钮（未找到则点击重试）
        if not _retry(lambda: find_and_click(TPL['putong'], dx=100, dy=10, region=rect)):
            # 如果屏幕上有活动按钮，先点击活动再重试
            if find_pic(TPL['huodong'], region=rect):
                find_and_click(TPL['huodong'], region=rect)
                log("[huodong] 重试前再次点击活动")
                if _wait(2, stop_event):
                    return
            else:
                safe_click(132, 188)
            if _wait(3, stop_event):
                return
            if not _retry(lambda: find_and_click(TPL['putong'], dx=100, dy=10, region=rect)):
                log("副本：未找到普通按钮", "WARN")
                send_feishu_msg("⚠️ 副本：未找到普通按钮")
                return
        if _wait(2, stop_event):
            return

        # 检测刮挂了X按钮，有则点击关闭
        if find_and_click(TPL['guaguale_x'], yuzhi=0.8, region=rect):
            log("[guaguale_x] 点击刮挂了关闭")
            if _wait(2, stop_event):
                return

        # 第3步：轮询等待选择副本并点击
        for _ in range(15):
            if find_and_click(TPL['xuanzefuben'], region=rect):
                log("[xuanzefuben] 点击选择副本")
                break
            if _wait(1, stop_event):
                return
        else:
            log("副本：未找到选择副本按钮", "WARN")
            send_feishu_msg("⚠️ 副本：未找到选择副本按钮")
            return
        if _wait(2, stop_event):
            return

        # 第4步：找进入按钮，轮流点击
        global _jinru_index
        for _ in range(15):
            points = find_all(TPL['jinru'], region=rect)
            if points:
                idx = _jinru_index % len(points)
                x, y = int(points[idx][0]), int(points[idx][1])
                safe_click(x, y)
                log(f"[jinru] 点击进入按钮{idx+1}: ({x}, {y})")
                _jinru_index = (_jinru_index + 1) % len(points)
                break
            if _wait(1, stop_event):
                return
        else:
            log("副本：未找到进入按钮", "WARN")
            send_feishu_msg("⚠️ 副本：未找到进入按钮")
            return
        if _wait(2, stop_event):
            return
    else:
        log("未找到活动按钮，跳过准备步骤，直接进副本主循环")

    ox, oy = rect[0], rect[1]
    zhan_rect = (ox + 758, oy + 190, ox + 870, oy + 252)
    try:
        while not stop_event.is_set():
            # 检测已完成，直接点击
            if find_and_click(TPL['yiwancheng'], yuzhi=0.8, region=rect):
                log("[yiwancheng] 点击已完成，副本结束")
                break

            # 持续检测跳过按钮
            if _retry(lambda: find_and_click_path('fubentiaoguo.bmp', yuzhi=0.6, region=rect)):
                # 跳过按钮匹配到后，轮询战按钮（多次重试）
                for _ in range(10):
                    if stop_event.is_set():
                        return
                    if find_and_click(TPL['zhan'], yuzhi=0.8, region=zhan_rect, dx=-20, dy=-5):
                        log("[zhan] 副本：点击战")
                        _wait(2, stop_event)
                        break
                    if _wait(1, stop_event):
                        return

            # 持续检测请选择（不依赖跳过按钮）
            if find_and_click(TPL['qingxuanze'], yuzhi=0.7, region=rect, dx=50, dy=20):
                log("[qingxuanze] 副本：点击请选取")
                _wait(2, stop_event)
                continue

            # 持续检测战按钮（不依赖跳过按钮）
            if find_and_click(TPL['zhan'], yuzhi=0.8, region=zhan_rect, dx=-20, dy=-5):
                log("[zhan] 副本：点击战")
                _wait(2, stop_event)
                continue

            if _wait(1, stop_event):
                break
        log("副本任务完成")
    except Exception as e:
        log(f"副本任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 副本任务异常: {e}")
