"""副本任务（组队型，只在队长窗口执行）"""

import random
import threading
import time
import win32gui
import win32con
import win32api
from core import log, find_pic, find_and_click, find_all, find_and_click_path, TPL, _wait, _retry, get_game_windows
from context import safe_click, get_window_rect, get_window_hwnd
from notify import send_feishu_msg

_jinru_index = 0  # 进入按钮轮流计数


def _activate_window(hwnd):
    """激活窗口到前台（非前台时点击不生效）。返回是否成功。"""
    for _ in range(4):
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32api.keybd_event(0x12, 0, 0, 0)  # Alt 解除前台锁定限制
            win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.25)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
    return False


def _clear_all_fail_dialogs(stop_event):
    """副本失败时组队的每个窗口都会弹"再接再厉/失败"框，且只有该窗口前台时点击才生效。
    逐个激活窗口并点空白处(相对窗口 435,95)返回主界面，避免失败框残留在屏幕上。"""
    for hwnd, wrect in get_game_windows():
        if stop_event.is_set():
            return
        _activate_window(hwnd)
        time.sleep(0.4)
        safe_click(wrect[0] + 435, wrect[1] + 95)  # 失败框上方空白处
        log(f"清除窗口({wrect[0]},{wrect[1]})失败画面")
        time.sleep(0.5)


def _enter_fuben(stop_event, rect):
    """打开活动面板 → 普通 → 选择副本 → 点进入。返回 True 表示成功进入"""
    global _jinru_index

    # 第1步：点活动
    if not _retry(lambda: find_and_click(TPL['huodong'], region=rect)):
        log("副本：未找到活动按钮", "WARN")
        return False
    log("[huodong] 点击活动")
    if _wait(2, stop_event):
        return False

    # 第2步：点普通右边的按钮（未找到则点击重试）
    if not _retry(lambda: find_and_click(TPL['putong'], dx=100, dy=10, region=rect)):
        safe_click(132, 188)
        if _wait(3, stop_event):
            return False
        if not _retry(lambda: find_and_click(TPL['putong'], dx=100, dy=10, region=rect)):
            log("副本：未找到普通按钮", "WARN")
            send_feishu_msg("⚠️ 副本：未找到普通按钮")
            return False
    if _wait(2, stop_event):
        return False

    # 第3步：轮询等待选择副本并点击
    for _ in range(15):
        if find_and_click(TPL['xuanzefuben'], region=rect):
            log("[xuanzefuben] 点击选择副本")
            break
        if _wait(1, stop_event):
            return False
    else:
        log("副本：未找到选择副本按钮", "WARN")
        send_feishu_msg("⚠️ 副本：未找到选择副本按钮")
        return False
    if _wait(2, stop_event):
        return False

    # 第4步：找进入按钮，轮流点击
    for _ in range(15):
        points = find_all(TPL['jinru'], region=rect)
        if points:
            points.sort(key=lambda p: p[0])  # 按x排序，保证轮换顺序稳定
            idx = _jinru_index % len(points)
            x, y = int(points[idx][0]), int(points[idx][1])
            safe_click(x, y, force=True)  # 进入按钮之一在聊天区(251,523)，force 绕过拦截
            log(f"[jinru] 点击进入按钮{idx+1}: ({x}, {y})")
            _jinru_index = (_jinru_index + 1) % len(points)
            break
        if _wait(1, stop_event):
            return False
    else:
        log("副本：未找到进入按钮", "WARN")
        send_feishu_msg("⚠️ 副本：未找到进入按钮")
        return False
    if _wait(2, stop_event):
        return False
    return True


def fuben_start(stop_event: threading.Event):
    """副本：连打2轮（普通+侠士）。每轮：进入 → 跳过剧情/战斗 → 已完成领奖"""
    log("副本任务开始")

    # 固定窗口1坐标
    rect = (0, 0, 870, 692)

    # 第0步：先清掉可能残留的"已完成"结算画面（上次卡死残留），避免误计幽灵轮
    if find_and_click(TPL['yiwancheng'], yuzhi=0.8, region=rect):
        log("清除残留的已完成结算画面")
        _wait(2, stop_event)

    # 第1步：先检查跳过按钮是否已经在屏幕上（副本已进入）
    if find_pic(TPL['fubentiaoguo'], yuzhi=0.65, region=rect):
        log("副本已进入，直接进入主循环")
    elif _enter_fuben(stop_event, rect):
        pass
    else:
        log("准备步骤未完成，直接进副本主循环")

    global _jinru_index
    done_count = 0    # 已完成的副本轮数
    total_rounds = 2  # 共打2轮（普通+侠士）
    idle_count = 0    # 连续空转计数，用于卡死自恢复
    try:
        while not stop_event.is_set():
            # 检测失败画面（"再接再厉"）：先清掉所有窗口的失败框，再让队长回长安
            if find_pic(TPL['shibai'], yuzhi=0.7, region=rect):
                idle_count = 0
                log("[shibai] 副本失败，清除所有窗口失败画面")
                _clear_all_fail_dialogs(stop_event)
                if stop_event.is_set():
                    break
                # 清框时激活过其他窗口，回城操作前需重新激活队长窗口
                hwnd1 = get_window_hwnd()
                if hwnd1:
                    _activate_window(hwnd1)
                if _wait(1, stop_event):
                    break
                safe_click(rect[0] + 45, rect[1] + 55)
                log("点击左上角地图")
                if _wait(2, stop_event):
                    break
                safe_click(rect[0] + 415, rect[1] + 383)
                log("点击长安城，回城")
                if _wait(3, stop_event):
                    break
                continue

            # 检测已完成，直接点击领奖
            if find_and_click(TPL['yiwancheng'], yuzhi=0.8, region=rect):
                idle_count = 0
                done_count += 1
                log(f"[yiwancheng] 点击已完成，第{done_count}轮副本结束")
                if done_count >= total_rounds:
                    break
                # 等待领奖界面过渡后，重新打开活动面板进入下一轮
                if _wait(5, stop_event):
                    break
                if not _enter_fuben(stop_event, rect):
                    log("副本：无法进入下一轮，任务结束", "WARN")
                    break
                continue

            # 检测进入按钮（选择界面意外停留时兜底）
            points = find_all(TPL['jinru'], region=rect)
            if points:
                idle_count = 0
                points.sort(key=lambda p: p[0])
                idx = _jinru_index % len(points)
                x, y = int(points[idx][0]), int(points[idx][1])
                safe_click(x, y, force=True)  # 进入按钮之一在聊天区(251,523)，force 绕过拦截
                log(f"[jinru] 点击进入按钮{idx+1}: ({x}, {y})")
                _jinru_index = (_jinru_index + 1) % len(points)
                if _wait(2, stop_event):
                    break
                continue

            # 检测NPC对话"请选择要做的事"，点击第一个选项（侠士副本等）
            if find_and_click(TPL['xuanze_shi'], yuzhi=0.7, region=rect, dx=40, dy=56):
                idle_count = 0
                log("[xuanze_shi] 副本：点击对话选项")
                if _wait(2, stop_event):
                    break
                continue

            if _retry(lambda: find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=rect)):
                idle_count = 0
                # 跳过按钮匹配到后，轮询对话区域图片
                for _ in range(10):
                    if stop_event.is_set():
                        return
                    shot_hit = False
                    if find_and_click(TPL['qingxuanze'], yuzhi=0.8, region=rect, dx=50, dy=20):
                        log("[qingxuanze] 副本：点击请选取")
                        shot_hit = True
                    elif find_and_click(TPL['zhan'], yuzhi=0.8, region=rect):
                        log("[zhan] 副本：点击战")
                        shot_hit = True
                    elif find_and_click(TPL['xuanze_shi'], yuzhi=0.7, region=rect, dx=40, dy=56):
                        log("[xuanze_shi] 副本：点击对话选项")
                        shot_hit = True
                    if shot_hit:
                        if _wait(3, stop_event):
                            return
                    else:
                        if _wait(1, stop_event):
                            return
                continue

            # 本轮什么都没找到：累计空转。正常战斗每隔几秒就有一次点击，
            # 连续60秒毫无响应 => 判定副本失败/卡死，直接结束副本进下个任务
            idle_count += 1
            if idle_count >= 60:
                log("副本：连续60秒无响应，判定副本失败/卡死，结束副本", "WARN")
                send_feishu_msg("⚠️ 副本失败/卡死，已结束副本")
                # 退出副本回长安，避免角色卡在副本里影响后续任务（捉鬼等找不到活动按钮）
                _clear_all_fail_dialogs(stop_event)
                if not stop_event.is_set():
                    hwnd1 = get_window_hwnd()
                    if hwnd1:
                        _activate_window(hwnd1)
                    _wait(1, stop_event)
                    safe_click(rect[0] + 45, rect[1] + 55)    # 左上角地图
                    log("点击左上角地图")
                    _wait(2, stop_event)
                    safe_click(rect[0] + 415, rect[1] + 383)  # 长安城，回城
                    log("点击长安城，回城")
                    _wait(3, stop_event)
                break
            if _wait(1, stop_event):
                break
        log(f"副本任务完成，共{done_count}轮")
        send_feishu_msg(f"✅ 副本任务完成，共{done_count}轮")
    except Exception as e:
        log(f"副本任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 副本任务异常: {e}")
