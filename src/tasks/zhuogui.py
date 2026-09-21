"""捉鬼任务（组队型，只在队长窗口执行）"""

import random
import threading
import time
import win32gui
import win32con
import win32api
from core import log, TPL, REGIONS, find_pic, find_and_click, scroll_activity, _retry, _wait
from context import safe_click
from notify import send_feishu_msg


def _activate_window(hwnd, rect):
    """激活窗口到前台，多种方案兜底"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        return
    except Exception:
        pass
    try:
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32gui.SetForegroundWindow(hwnd)
        return
    except Exception:
        pass
    cx = (rect[0] + rect[2]) // 2
    safe_click(cx, rect[1] + 10)
    time.sleep(0.3)


def claim_double_points(stop_event):
    """逐个窗口打开挂机面板领取双倍点数，完成后关闭面板。
    参考 mhxy_code 的 claim_double_points 实现。"""
    from core import get_game_windows, find_and_click as _fac
    windows = get_game_windows()
    if not windows:
        log("领取双倍点数：未找到游戏窗口", "WARN")
        return

    for index, (hwnd, rect) in enumerate(windows[:5], start=1):
        if stop_event.is_set():
            return
        try:
            ox, oy = rect[0], rect[1]
            _activate_window(hwnd, rect)
            time.sleep(0.5)

            # 1. 点挂机按钮 (383,60)
            safe_click(ox + 383, oy + 60)
            log(f"窗口{index} 领取双倍：点击挂机 ({ox+383},{oy+60})")
            time.sleep(1)

            # 2. 点领取按钮 (726,560) 两次
            for attempt in range(1, 3):
                if stop_event.is_set():
                    return
                safe_click(ox + 726, oy + 560)
                log(f"窗口{index} 领取双倍：第{attempt}次点击领取 ({ox+726},{oy+560})")
                time.sleep(1)

            # 3. 关闭挂机面板
            close_region = (ox + 650, oy + 50, ox + 870, oy + 230)
            if _fac(TPL['panel_x'], yuzhi=0.7, region=close_region):
                log(f"窗口{index} 领取双倍：关闭挂机面板")
            else:
                safe_click(ox + 803, oy + 120)
                log(f"窗口{index} 领取双倍：坐标兜底关闭 ({ox+803},{oy+120})", "WARN")
            time.sleep(0.5)
        except Exception as e:
            log(f"窗口{index} 领取双倍失败: {e}", "ERR")

    log("领取双倍点数完成")


# 右上角捉鬼任务条识别区域（语义：left, top, right, bottom）。限制范围避免在其他文字中误匹配。
_ZHUOGUI_BAR_REGION = (679, 162, 861, 225)


def _trigger_task_bar(ox, oy, stop_event, prefix=""):
    """双击捉鬼任务条触发寻路：优先图片识别定位任务条，识别不到用固定坐标兜底。
    参考 mhxy_code 的 _trigger_task_bar（按主项目 left/top/right/bottom 语义重写）。"""
    if stop_event.wait(1):
        return False
    region = (ox + _ZHUOGUI_BAR_REGION[0], oy + _ZHUOGUI_BAR_REGION[1],
              ox + _ZHUOGUI_BAR_REGION[2], oy + _ZHUOGUI_BAR_REGION[3])
    pos = find_pic(TPL['zhuogui'], yuzhi=0.7, region=region)
    if pos:
        log(f"{prefix}识别到捉鬼任务条 ({pos[0]},{pos[1]})，双击触发寻路")
    else:
        pos = (ox + 770, oy + 206)
        log(f"{prefix}未识别到捉鬼任务条，双击兜底坐标 (770,206)")
    _random_click(pos[0], pos[1], 5, 5)
    if stop_event.wait(1):
        return False
    _random_click(pos[0], pos[1], 5, 5)
    if stop_event.wait(1):
        return False
    return True


def ling_shuang_start(stop_event: threading.Event):
    """领双：逐窗口打开挂机面板领取双倍点数（独立按钮，不再并入捉鬼）"""
    log("领双任务开始")
    claim_double_points(stop_event)
    log("领双任务完成")


def zhuogui_start(stop_event: threading.Event, rounds=2):
    """捉鬼：点击活动进入 → 点击去接受任务 → 等待完成 → 循环指定轮数

    完成图检测：检测 TPL['zhuoguiqueding']。
    注意：领取双倍已拆成独立任务 lingshuang，不再在捉鬼内自动执行。
    """
    log("捉鬼任务开始")

    # 固定取屏幕左上角的窗口1
    w1_rect = REGIONS[0]
    ox, oy = w1_rect[0], w1_rect[1]
    log(f"窗口1 rect={w1_rect}")

    # 第1步：点活动
    entered_from_activity = False
    if find_and_click(TPL['huodong'], region=w1_rect):
        log("点击活动")
        entered_from_activity = True
        if _wait(2, stop_event):
            return

        # 第2步：点捉鬼右边的按钮（未找到则点击重试）
        if not _retry(lambda: find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10)):
            # 如果屏幕上有活动按钮，先点击活动再重试
            if find_pic(TPL['huodong'], region=w1_rect):
                find_and_click(TPL['huodong'], region=w1_rect)
                log("重试前再次点击活动")
                if _wait(2, stop_event):
                    return
            else:
                safe_click(132, 188)
            if _wait(3, stop_event):
                return
            if not _retry(lambda: find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10)):
                # 滚动活动列表再找
                found_zhuogui = False
                for _ in range(4):
                    if stop_event.is_set():
                        return
                    scroll_activity(w1_rect, direction=-1, steps=3)
                    if find_and_click(TPL['zhuoguirenwu'], region=w1_rect, dx=130, dy=10):
                        found_zhuogui = True
                        break
                if not found_zhuogui:
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
                # 第1轮：从活动进入，识别钟馗对话"捉鬼任务"选项，再双击任务条触发寻路
                log("第1轮：等待钟馗对话，识别捉鬼任务选项...")
                _got_option = False
                for _ in range(30):
                    if stop_event.is_set():
                        break
                    if find_and_click(TPL['zhuogui_xuanxiang'], yuzhi=0.7, region=w1_rect):
                        log("第1轮：点击捉鬼任务选项 ✓")
                        _got_option = True
                        break
                    if stop_event.wait(1):
                        break
                if stop_event.is_set():
                    break
                if not _got_option:
                    log("第1轮：未识别到捉鬼任务选项，固定坐标兜底")
                    safe_click(ox + 707, oy + 242)
                if stop_event.wait(1):
                    break
                _trigger_task_bar(ox, oy, stop_event, prefix="第1轮")
                if stop_event.is_set():
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

            # 最后一轮：点退出(350,392)，不点领取任务
            if count >= rounds:
                log(f"捉鬼{rounds}轮已完成，退出")
                safe_click(ox + 350, oy + 392)
                send_feishu_msg(f"✅ 捉鬼任务完成，共{count}轮")
                stop_event.set()
                break

            # 中间轮次：点领取任务(511,392) → 等10秒 → 点确定 → 点按钮
            safe_click(ox + 511, oy + 392)
            log(f"点击领取任务 ({ox+511},{oy+392})")

            if stop_event.wait(10):
                break

            # 识别钟馗对话"捉鬼任务"选项，识别不到再固定坐标兜底
            _got_option = False
            for _ in range(20):
                if stop_event.is_set():
                    break
                if find_and_click(TPL['zhuogui_xuanxiang'], yuzhi=0.7, region=w1_rect):
                    log("中间轮：点击捉鬼任务选项 ✓")
                    _got_option = True
                    break
                if stop_event.wait(1):
                    break
            if stop_event.is_set():
                break
            if not _got_option:
                safe_click(ox + 707, oy + 242)
            if stop_event.wait(1):
                break

            _trigger_task_bar(ox, oy, stop_event)
            if stop_event.is_set():
                break

            continue
    except Exception as e:
        log(f"捉鬼任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 捉鬼任务异常: {e}")


def _random_click(x, y, rand_x=5, rand_y=5):
    """带随机偏移的点击"""
    cx = x + random.randint(-rand_x, rand_x)
    cy = y + random.randint(-rand_y, rand_y)
    safe_click(cx, cy)
