"""捉鬼任务（组队型，只在队长窗口执行）"""

import threading
import time
from core import log, get_game_windows, close_popups
from context import safe_click
from notify import send_feishu_msg


def _get_window1_rect():
    """固定窗口1坐标（2560×1440分辨率，窗口870×692）"""
    return (0, 0, 870, 692)


# 右上角捉鬼任务条识别区域（左、上、宽、高）。限制范围避免在其他场景文字中误匹配。
_ZHUOGUI_BAR_REGION = (679, 162, 182, 63)  # 对应边界 (679,162)-(861,225)


def _trigger_task_bar(ox, oy, stop_event, prefix=""):
    """领取任务后双击任务条；限定区域识别失败时使用固定坐标兜底。"""
    if stop_event.wait(1):
        return False

    from core import find_pic, TPL
    region = (ox + _ZHUOGUI_BAR_REGION[0], oy + _ZHUOGUI_BAR_REGION[1],
              _ZHUOGUI_BAR_REGION[2], _ZHUOGUI_BAR_REGION[3])
    pos = find_pic(TPL['zhuogui'], yuzhi=0.7, region=region)
    if pos:
        tx, ty = pos
        log(f"{prefix}识别到捉鬼任务条 ({tx},{ty})，双击触发寻路")
    else:
        tx, ty = ox + 770, oy + 206
        log(f"{prefix}未识别到任务条，双击兜底坐标 (770,206)")

    _random_click(tx, ty, 5, 5, double=True)
    if stop_event.wait(0.3):
        return False
    return True


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
        if _wait(4, stop_event):
            return
    else:
        log("未找到活动按钮，直接检测完成图")

    count = 0
    try:
        while not stop_event.is_set():
            if count == 0 and entered_from_activity:
                # 第1轮：等待自动寻路到钟馗弹出对话，图片识别点击"捉鬼任务"选项
                log("第1轮：等待钟馗对话，识别捉鬼任务选项...")
                for _ in range(30):
                    if stop_event.is_set():
                        return
                    if find_and_click(TPL['zhuogui_xuanxiang'], yuzhi=0.7, region=w1_rect, force=True):
                        log("[zhuogui_xuanxiang] 点击捉鬼任务选项 ✓")
                        break
                    if stop_event.wait(1):
                        return
                else:
                    log("未找到捉鬼任务选项", "WARN")
                # 第1轮点完选项后，双击任务栏触发自动寻路去打鬼
                if not _trigger_task_bar(ox, oy, stop_event, prefix="第1轮"):
                    break
                entered_from_activity = False  # 只点一次，之后进入完成图检测
                if stop_event.wait(3):
                    break
            else:
                # 后续轮次：等待并检测完成图
                log(f"等待第{count+1}轮完成图...")
                found = False
                # 最多等待90秒检测完成图
                for _w in range(90):
                    if stop_event.is_set():
                        return
                    # 完成框"少侠已经捉完N轮鬼"——模板只取"已经捉完"(不含数字，1/2轮通用；中途框无此字样)
                    # 必须先于 jixu 检测：完成框也含"是否继续捉鬼"，若被 jixu 抢先会误判为中途框导致轮数不增（卡死主因）
                    if find_pic(TPL['zhuogui_wancheng'], yuzhi=0.72, region=w1_rect):
                        found = True
                        break
                    # 中途"捉了X只鬼，是否继续捉鬼?"询问框：主动点确定继续，免等 297 秒倒计时（大幅加速）
                    if find_pic(TPL['zhuogui_jixu'], yuzhi=0.75, region=w1_rect):
                        safe_click(ox + 513, oy + 398)
                        log("[zhuogui_jixu] 中途询问，点确定继续")
                        if stop_event.wait(2):
                            return
                        continue
                    # 钟馗对话选项（两轮之间游戏可能弹出选择接任务对话框）
                    if find_and_click(TPL['zhuogui_xuanxiang'], yuzhi=0.7, region=w1_rect, force=True):
                        log("[zhuogui_xuanxiang] 点击捉鬼任务选项 ✓")
                        if not _trigger_task_bar(ox, oy, stop_event):
                            return
                        if stop_event.wait(1):
                            return
                        continue
                    # 每10秒扫描5个窗口，关闭随机弹窗
                    if _w % 10 == 0:
                        close_popups()
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
                    if stop_event.wait(2):
                        break
                    # 点队伍（3次匹配不上用固定坐标(820,131)兜底）
                    _team_clicked = False
                    for _att in range(3):
                        if find_and_click(TPL['duiwu'], yuzhi=0.65, region=w1_rect):
                            _team_clicked = True
                            break
                        if stop_event.wait(0.5):
                            break
                    if not _team_clicked:
                        safe_click(ox + 820, oy + 131)
                        log("队伍按钮3次未识别，固定坐标(820,131)兜底")
                    if stop_event.wait(1):
                        break
                    # 点击 (740,240) 然后 (599,299)，循环4次
                    import random as _rand
                    # 前3次: (740,240) -> (599,299) -> (511,400)
                    for _ in range(3):
                        safe_click(ox + 740 + _rand.randint(-5, 5), oy + 240 + _rand.randint(-5, 5))
                        if stop_event.wait(0.5):
                            break
                        safe_click(ox + 599 + _rand.randint(-5, 5), oy + 299 + _rand.randint(-5, 5))
                        if stop_event.wait(0.5):
                            break
                        safe_click(ox + 511 + _rand.randint(-5, 5), oy + 400 + _rand.randint(-5, 5))
                        if stop_event.wait(0.5):
                            break
                    # 第4次: (740,190) -> (599,248) -> (511,400)
                    safe_click(ox + 740 + _rand.randint(-5, 5), oy + 190 + _rand.randint(-5, 5))
                    if stop_event.wait(0.5):
                        return
                    safe_click(ox + 599 + _rand.randint(-5, 5), oy + 248 + _rand.randint(-5, 5))
                    if stop_event.wait(0.5):
                        return
                    safe_click(ox + 511 + _rand.randint(-5, 5), oy + 400 + _rand.randint(-5, 5))
                    stop_event.set()
                    break

                # 未达到目标轮数，点完成框的"确定"继续下一轮（确定按钮中心 513,398）
                log(f"点确定继续第{count+1}轮")
                safe_click(ox + 513, oy + 398)
                if stop_event.wait(1):
                    break

            # 等待10秒
            if stop_event.wait(10):
                break

            # 第1轮已在上面处理过识别选项和双击，这里跳过；第2轮起才需要重新识别
            if count == 0:
                log("等待60秒后重新检测...")
                if stop_event.wait(60):
                    break
                continue

            # 识别并点击捉鬼任务选项（第2轮起游戏多为自动接，识别不到属正常）
            _got = False
            for _ in range(10):
                if stop_event.is_set():
                    break
                if find_and_click(TPL['zhuogui_xuanxiang'], yuzhi=0.7, region=w1_rect, force=True):
                    log("[zhuogui_xuanxiang] 点击捉鬼任务选项 ✓")
                    _got = True
                    break
                if stop_event.wait(1):
                    break
            if _got:
                if not _trigger_task_bar(ox, oy, stop_event):
                    break
            else:
                # 没识别到选项=任务未领取，双击任务栏无意义（栏里没捉鬼条），跳过，等下轮循环重试
                log("未识别到捉鬼选项，跳过双击，等待重试")

            log("等待60秒后重新检测...")
            if stop_event.wait(60):
                break
    except Exception as e:
        log(f"捉鬼任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 捉鬼任务异常: {e}")


def _random_click(x, y, rand_x=5, rand_y=5, double=False):
    """带随机偏移的点击。double=True 时双击。"""
    import random
    cx = x + random.randint(-rand_x, rand_x)
    cy = y + random.randint(-rand_y, rand_y)
    safe_click(cx, cy, double=double)
