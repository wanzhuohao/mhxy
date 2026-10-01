"""打工任务（点击人物头像 → 点击使用 → 点击打工按钮）

参考 mhxy_code 的 shiyonggongju.py，仅保留"打工"部分：
每个窗口 点头像(825,35) → 点使用(727,287) → 打工按钮(682,279) 点20次 → 关闭面板。
坐标均为窗口内相对坐标，按 REGIONS 偏移映射。当前项目 safe_click 无 force 参数，已去掉。
"""

import time
from core import log, _screenshot_gray, TPL, _wait, REGIONS, _match_in_region
from context import safe_click


def _open_and_use(stop_event):
    """点击人物头像 → 点击使用按钮。返回 True 成功，None 表示中途停止"""
    avatar_x_offset = 825
    avatar_y_offset = 55  # 人物头像（原35，y+20）
    for i, rect in enumerate(REGIONS):
        if stop_event.is_set():
            return None
        avatar_x = rect[0] + avatar_x_offset
        avatar_y = rect[1] + avatar_y_offset
        safe_click(avatar_x, avatar_y)
        log(f"窗口{i+1} 点击人物头像 ({avatar_x},{avatar_y})")
        time.sleep(0.4)

    if _wait(2, stop_event):
        return None

    # 点击"使用"按钮
    use_x_offset = 727
    use_y_offset = 287
    for i, rect in enumerate(REGIONS):
        if stop_event.is_set():
            return None
        ux = rect[0] + use_x_offset
        uy = rect[1] + use_y_offset
        safe_click(ux, uy)
        log(f"窗口{i+1} 点击使用按钮 ({ux},{uy})")
        time.sleep(0.4)
    return True


def _click_sub_button(stop_event, name, bx_offset, by_offset, repeats=1, pre_close=None):
    """按指定次数点击5个窗口的同层子按钮；再（可选）先点 pre_close 位置，随后关闭人物面板。"""
    if _wait(1, stop_event):
        return
    for attempt in range(1, repeats + 1):
        for i, rect in enumerate(REGIONS):
            if stop_event.is_set():
                return
            bx = rect[0] + bx_offset
            by = rect[1] + by_offset
            safe_click(bx, by)
            log(f"窗口{i+1} 第{attempt}/{repeats}次点击[{name}] ({bx},{by})")
            time.sleep(0.3)

    # 关闭面板前先点 pre_close（用户指定，打工为第一个X 742,141）
    if pre_close:
        px, py = pre_close
        for i, rect in enumerate(REGIONS):
            if stop_event.is_set():
                return
            sx = rect[0] + px
            sy = rect[1] + py
            safe_click(sx, sy)
            log(f"窗口{i+1} 关闭前先点 ({sx},{sy})")
            time.sleep(0.3)

    _close_panels(stop_event, rounds=2)


def _close_panels(stop_event, rounds=1):
    """每轮重新截图，按面板 X 关闭人物/活力相关面板。"""
    for layer in range(1, rounds + 1):
        if _wait(1, stop_event):
            return

        log(f"关闭人物相关面板：第{layer}/{rounds}层")
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if stop_event.is_set():
                return
            # 活力窗口的 X 在前景窗口内，用专用模板避免通用 X 匹配到别的窗口
            if layer == 2:
                x0, y0, x1, y1 = rect
                huoli_region = (x0 + 650, y0 + 60, x1, y0 + 220)
                r = _match_in_region(shot, TPL['huoli_x'], huoli_region, yuzhi=0.78)
            else:
                r = None
            if not r:
                r = _match_in_region(shot, TPL['panel_x'], rect, yuzhi=0.7)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} 关闭第{layer}层面板 ({r[0]},{r[1]})")
                time.sleep(0.3)


def shiyonggongju_start(stop_event):
    """打工：头像一次 → 使用一次 → 打工按钮20次。"""
    log("打工任务开始")
    if _open_and_use(stop_event) is None:
        return
    if _wait(2, stop_event):  # 等待新页面加载
        return
    _click_sub_button(stop_event, "打工", 682, 279, repeats=20, pre_close=(742, 141))
    log("打工任务完成")