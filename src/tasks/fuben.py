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

    # 第1步：点活动（没找到则跳过，直接进主循环）
    if find_and_click(TPL['huodong']):
        log("点击活动")
        if _wait(2, stop_event):
            return

        # 第2步：点普通右边的按钮（未找到则点击重试）
        if not _retry(lambda: find_and_click(TPL['putong'], dx=100)):
            safe_click(132, 188)
            if _wait(3, stop_event):
                return
            if not _retry(lambda: find_and_click(TPL['putong'], dx=100)):
                log("副本：未找到普通按钮", "WARN")
                send_feishu_msg("⚠️ 副本：未找到普通按钮")
                return
        if _wait(2, stop_event):
            return

        # 第3步：轮询等待选择副本并点击
        for _ in range(15):
            if find_and_click(TPL['xuanzefuben']):
                log("点击选择副本")
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
            points = find_all(TPL['jinru'])
            if points:
                idx = _jinru_index % len(points)
                x, y = int(points[idx][0]), int(points[idx][1])
                safe_click(x, y)
                log(f"点击进入按钮{idx+1}: ({x}, {y})")
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

    # 固定窗口1坐标（2560×1440分辨率，窗口870×692）
    rect = (0, 0, 870, 692)
    ox, oy = rect[0], rect[1]
    try:
        while not stop_event.is_set():
            # 检测已完成，直接点击
            if find_and_click(TPL['yiwancheng'], yuzhi=0.8, region=rect):
                log("点击已完成，副本结束")
                break

            if _retry(lambda: find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=rect)):
                # 跳过按钮匹配到后，轮询对话区域图片
                for _ in range(10):
                    if stop_event.is_set():
                        return
                    shot_hit = False
                    if find_and_click(TPL['kuaijin'], yuzhi=0.65, region=rect):
                        log("副本：点击快进")
                        shot_hit = True
                    if find_and_click(TPL['qingxuanze'], yuzhi=0.65, region=rect):
                        log("副本：点击请选取")
                        shot_hit = True
                    if find_and_click(TPL['zhan'], yuzhi=0.65, region=rect):
                        log("副本：点击战")
                        shot_hit = True
                    if shot_hit:
                        if _wait(3, stop_event):
                            return
                    else:
                        if _wait(1, stop_event):
                            return
                continue
            if _wait(1, stop_event):
                break
        log("副本任务完成")
    except Exception as e:
        log(f"副本任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 副本任务异常: {e}")
