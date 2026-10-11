"""趣闻鉴赏：进入空间，为五条尚未点赞的图文点赞。"""

from __future__ import annotations

import threading
import time

from context import activate_window, safe_click, safe_drag, safe_press
from core import (
    TPL,
    _screenshot_rgb,
    _wait,
    find_all,
    find_pic,
    get_game_windows,
    log,
    scroll_activity,
)
from notify import send_feishu_msg


ACTIVITY_THRESHOLD = 0.76
ENTRY_THRESHOLD = 0.78
LIKE_THRESHOLD = 0.86
COLLAPSE_THRESHOLD = 0.90
DETAIL_THRESHOLD = 0.90
MAX_NEW_LIKES = 5
MAX_SCROLLS = 14
MAX_DETAIL_RECOVERIES = 2

STARTED = "started"
START_FAILED = "failed"


def quwen_start(stop_event: threading.Event):
    """五窗口依次完成趣闻鉴赏，并关闭空间侧栏。"""
    log("趣闻鉴赏开始：五个账号依次进入空间并点赞")
    windows = get_game_windows()
    if len(windows) < 5:
        log(f"只找到{len(windows)}个游戏窗口，趣闻鉴赏已停止", "WARN")
        return
    windows.sort(key=lambda item: (item[1][1], item[1][0]))
    windows = windows[:5]

    completed: set[int] = set()
    start_failed: set[int] = set()
    timed_out: set[int] = set()

    for index, (hwnd, rect) in enumerate(windows):
        if stop_event.is_set():
            return

        status = _open_space(index, hwnd, rect, stop_event)
        if status != STARTED:
            start_failed.add(index)
            continue

        liked, exhausted, unexpected_detail = _like_visible_posts(
            index,
            hwnd,
            rect,
            stop_event,
            max_new_likes=MAX_NEW_LIKES,
        )
        collapsed = _collapse_space(index, hwnd, rect, stop_event)
        if stop_event.is_set():
            return
        if unexpected_detail or not collapsed:
            start_failed.add(index)
            log(f"窗口{index + 1} 趣闻页面异常，已停止后续窗口以免误点", "WARN")
            break
        if liked >= MAX_NEW_LIKES:
            completed.add(index)
            log(f"窗口{index + 1} 趣闻鉴赏完成，本次点赞{liked}条")
        elif exhausted:
            # 找不到候选按钮并不能证明已经完成：可能打开了错误页面，
            # 或滚动位置不对。
            timed_out.add(index)
            log(f"窗口{index + 1} 只确认点赞{liked}条，找不到更多按钮，未判定完成", "WARN")
        else:
            timed_out.add(index)
            log(f"窗口{index + 1} 趣闻鉴赏只确认点赞{liked}条", "WARN")

    if stop_event.is_set():
        log("趣闻鉴赏已停止")
        return

    summary = (
        f"趣闻鉴赏结束：完成{len(completed)}个，"
        f"未启动{len(start_failed)}个，超时{len(timed_out)}个"
    )
    level = "" if len(completed) == 5 and not start_failed and not timed_out else "WARN"
    log(summary, level)
    send_feishu_msg(summary)


def _find_quwen_entry(rect, stop_event, label=""):
    """滚动活动列表找到趣闻鉴赏入口（用现有 scroll_activity：滚轮 + 拖拽兜底）。"""
    # 先大幅滚回活动列表顶部
    scroll_activity(rect, direction=1, steps=1, amount=30, stop_event=stop_event)
    if _wait(0.8, stop_event):
        return None

    for _ in range(MAX_SCROLLS):
        pos = find_pic(TPL["quwen"], yuzhi=ENTRY_THRESHOLD, region=rect)
        if pos:
            return pos
        if stop_event.is_set():
            return None
        scroll_activity(rect, direction=-1, steps=1, stop_event=stop_event)
        if _wait(0.5, stop_event):
            return None

    log(f"{label}：活动列表未找到趣闻鉴赏", "WARN")
    return None


def _open_space(index, hwnd, rect, stop_event):
    if _detail_close_button(rect):
        log(f"窗口{index + 1} 检测到遗留的图文详情弹层，先关闭", "WARN")
        if not _close_detail(index, hwnd, rect, stop_event):
            return START_FAILED
    if find_pic(TPL["quwen_collapse"], yuzhi=COLLAPSE_THRESHOLD, region=rect):
        log(f"窗口{index + 1} 已在空间图文页，继续")
        return STARTED
    if not _activate(hwnd, rect, stop_event):
        return START_FAILED

    activity = find_pic(TPL["huodong"], yuzhi=ACTIVITY_THRESHOLD, region=rect)
    if not activity:
        log(f"窗口{index + 1} 未找到活动入口", "WARN")
        return START_FAILED
    safe_click(activity[0], activity[1])
    if _wait(0.8, stop_event):
        return START_FAILED

    entry = _find_quwen_entry(rect, stop_event, label=f"窗口{index + 1} 趣闻鉴赏")
    if not entry:
        log(f"窗口{index + 1} 活动列表没有趣闻鉴赏", "WARN")
        _close_panel(hwnd)
        return START_FAILED

    safe_click(entry[0] + 130, entry[1] + 10)
    if _wait(2.0, stop_event):
        return START_FAILED
    if find_pic(TPL["quwen_collapse"], yuzhi=COLLAPSE_THRESHOLD, region=rect):
        log(f"窗口{index + 1} 已进入空间图文页")
        return STARTED
    if find_pic(TPL["quwen"], yuzhi=ENTRY_THRESHOLD, region=rect):
        log(f"窗口{index + 1} 趣闻鉴赏入口仍显示，不能确认已完成", "WARN")
        _close_panel(hwnd)
        return START_FAILED
    log(f"窗口{index + 1} 点击趣闻鉴赏后未识别到空间页", "WARN")
    return START_FAILED


def _like_visible_posts(index, hwnd, rect, stop_event, *, max_new_likes=MAX_NEW_LIKES):
    liked = 0
    scrolls = 0
    no_candidate_pages = 0
    detail_recoveries = 0
    rejected_points: list[tuple[int, int]] = []

    while liked < max_new_likes and scrolls <= MAX_SCROLLS and not stop_event.is_set():
        if _detail_close_button(rect):
            detail_recoveries += 1
            if not _recover_detail(index, hwnd, rect, stop_event):
                return liked, False, True
            if detail_recoveries >= MAX_DETAIL_RECOVERIES:
                log(f"窗口{index + 1} 连续误入图文详情，已安全停下", "WARN")
                return liked, False, True
            continue
        candidates = _without_rejected(_find_unliked_hearts(rect), rejected_points)
        if candidates:
            no_candidate_pages = 0
            if not _activate(hwnd, rect, stop_event):
                break
            if _detail_close_button(rect):
                continue
            # 切换窗口后重新识别，防止使用旧坐标。
            candidates = _without_rejected(_find_unliked_hearts(rect), rejected_points)
            if not candidates:
                continue
            point = candidates[0]
            safe_click(point[0], point[1])
            if _wait(0.8, stop_event):
                break
            if _detail_close_button(rect):
                rejected_points.append(point)
                detail_recoveries += 1
                log(f"窗口{index + 1} 点赞误入图文详情，关闭后跳过该位置", "WARN")
                if not _recover_detail(index, hwnd, rect, stop_event):
                    return liked, False, True
                if detail_recoveries >= MAX_DETAIL_RECOVERIES:
                    log(f"窗口{index + 1} 连续误入图文详情，已安全停下", "WARN")
                    return liked, False, True
                continue
            if _heart_is_selected(rect, point):
                liked += 1
                detail_recoveries = 0
                log(f"窗口{index + 1} 趣闻鉴赏已确认点赞 {liked}/{max_new_likes}")
            else:
                rejected_points.append(point)
                log(f"窗口{index + 1} 点赞颜色未变化，重新识别", "WARN")
            continue

        no_candidate_pages += 1
        if no_candidate_pages >= 3 and scrolls >= 2:
            break
        if not _activate(hwnd, rect, stop_event):
            break
        left, top, right, bottom = map(int, rect)
        x = left + min(390, max(220, (right - left) * 45 // 100))
        safe_drag(x, top + min(570, bottom - top - 70), x, top + 175, jitter=5)
        scrolls += 1
        rejected_points.clear()
        log(f"窗口{index + 1} 趣闻图文向下翻页 {scrolls}/{MAX_SCROLLS}")
        if _wait(0.8, stop_event):
            break

    exhausted = liked < max_new_likes and no_candidate_pages >= 3
    return liked, exhausted, False


def _without_rejected(candidates, rejected_points):
    return [
        point for point in candidates
        if all(abs(point[0] - rejected[0]) > 8 or abs(point[1] - rejected[1]) > 8
               for rejected in rejected_points)
    ]


def _find_unliked_hearts(rect):
    left, top, right, bottom = map(int, rect)
    region = (
        left + 145,
        top + 105,
        # 真实点赞按钮中心约 x=161；正文表情约 x=181，外观相似，
        # 宽范围模板匹配会把表情当点赞并打开图文详情。
        min(right, left + 178),
        min(bottom, top + 620),
    )
    points = find_all(TPL["quwen_like"], yuzhi=LIKE_THRESHOLD, region=region)
    shot = _screenshot_rgb(rect)
    result = []
    for x, y in points:
        local_x = int(x) - left
        local_y = int(y) - top
        if not 153 <= local_x <= 170:
            continue
        if not (0 <= local_y < shot.shape[0] and 0 <= local_x < shot.shape[1]):
            continue
        blue, green, red = map(int, shot[local_y, local_x])
        # 未点赞为棕色（R>G>B），点赞后为粉色（B>G）。
        if red > green + 25 and green > blue + 15 and blue < 100:
            result.append((int(x), int(y)))
    result.sort(key=lambda point: (point[1], point[0]))
    return result


def _heart_is_selected(rect, point):
    left, top, _right, _bottom = map(int, rect)
    shot = _screenshot_rgb(rect)
    local_x = int(point[0]) - left
    local_y = int(point[1]) - top
    if not (0 <= local_y < shot.shape[0] and 0 <= local_x < shot.shape[1]):
        return False
    blue, green, red = map(int, shot[local_y, local_x])
    return red > 180 and blue > green + 25


def _collapse_space(index, hwnd, rect, stop_event):
    if _detail_close_button(rect) and not _close_detail(index, hwnd, rect, stop_event):
        return False
    if not _activate(hwnd, rect, stop_event):
        return False
    collapse = find_pic(TPL["quwen_collapse"], yuzhi=COLLAPSE_THRESHOLD, region=rect)
    if not collapse:
        return not bool(_detail_close_button(rect))
    safe_click(collapse[0], collapse[1])
    if _wait(1.0, stop_event):
        return False
    closed = not find_pic(TPL["quwen_collapse"], yuzhi=COLLAPSE_THRESHOLD, region=rect)
    log(f"窗口{index + 1} 空间侧栏{'已关闭' if closed else '关闭未确认'}")
    return closed


def _detail_close_button(rect):
    left, top, right, bottom = map(int, rect)
    region = (left + 740, top + 55, min(right, left + 865), min(bottom, top + 160))
    return find_pic(TPL["quwen_detail_close"], yuzhi=DETAIL_THRESHOLD, region=region)


def _close_detail(index, hwnd, rect, stop_event):
    button = _detail_close_button(rect)
    if not button:
        return True
    if not _activate(hwnd, rect, stop_event):
        return False
    button = _detail_close_button(rect)
    if not button:
        return True
    safe_click(button[0], button[1])
    if _wait(0.8, stop_event):
        return False
    closed = not bool(_detail_close_button(rect))
    log(f"窗口{index + 1} 图文详情{'已关闭' if closed else '关闭未确认'}")
    return closed


def _recover_detail(index, hwnd, rect, stop_event):
    if not _close_detail(index, hwnd, rect, stop_event):
        log(f"窗口{index + 1} 图文详情未能关闭", "WARN")
        return False
    if not find_pic(TPL["quwen_collapse"], yuzhi=COLLAPSE_THRESHOLD, region=rect):
        log(f"窗口{index + 1} 详情已消失，但未确认回到空间图文列表", "WARN")
        return False
    log(f"窗口{index + 1} 已从图文详情恢复到列表")
    return True


def _activate(hwnd, rect, stop_event, delay=0.25):
    try:
        if not activate_window(hwnd, rect):
            raise RuntimeError("窗口没有获得前台焦点")
    except Exception as exc:
        log(f"切换游戏窗口失败: {exc}", "WARN")
        return False
    return not _wait(delay, stop_event)


def _close_panel(hwnd):
    try:
        if activate_window(hwnd):
            time.sleep(0.2)
            safe_press("esc")
    except Exception:
        pass
