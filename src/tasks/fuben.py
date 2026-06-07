"""副本任务（组队型，只在队长窗口执行）"""

import random
import threading
from core import log, find_pic, find_and_click, find_all, find_and_click_path, TPL, _wait, _retry
from context import safe_click, get_window_rect
from notify import send_feishu_msg

_jinru_index = 0  # 进入按钮轮流计数


def fuben_start(stop_event: threading.Event):
    """副本：跳过剧情、确定、战斗坐标"""
    log("副本任务开始")
    send_feishu_msg("🎮 副本任务开始")

    # 第1步：点活动（没找到则跳过，直接进主循环）
    if find_and_click(TPL['huodong']):
        log("点击活动")
        if _wait(2, stop_event):
            return

        # 第2步：点普通右边的按钮
        if not _retry(lambda: find_and_click(TPL['putong'], dx=100), label="点普通右边"):
            log("副本：未找到普通按钮", "WARN")
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
            return
        if _wait(2, stop_event):
            return
    else:
        log("未找到活动按钮，跳过准备步骤，直接进副本主循环")

    # 固定取屏幕左上角的窗口1
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
    rect = windows[0][1]
    ox, oy = rect[0], rect[1]
    try:
        while not stop_event.is_set():
            # 检测已完成，直接点击
            if find_and_click(TPL['yiwancheng'], yuzhi=0.5, region=rect):
                log("点击已完成，副本结束")
                break

            if _retry(lambda: find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=rect), label="副本跳过"):
                if _wait(5, stop_event):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                safe_click(ox + 744 + dx, oy + 190 + dy)
                if _wait(5, stop_event):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                safe_click(ox + 638 + dx, oy + 510 + dy)
                if _wait(3, stop_event):
                    break
                continue
            if _wait(1, stop_event):
                break
        send_feishu_msg("✅ 副本任务完成")
    except Exception as e:
        log(f"副本任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 副本任务异常: {e}")
