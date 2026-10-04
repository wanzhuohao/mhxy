"""截图、模板匹配、安全点击、重试"""

import mss
import cv2
import numpy as np
import threading
import win32gui
import os
import time
import random

from context import get_window_rect, safe_click
from notify import send_feishu_msg

_sct = mss.mss()
_sct_lock = threading.Lock()
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')


def log(msg, level=""):
    """带时间戳的日志"""
    ts = time.strftime("%H:%M")
    prefix = f"[{ts}]" if not level else f"[{ts} {level}]"
    print(f"{prefix} {msg}")


# ========== 模板预加载 ==========

def _load(path):
    """加载灰度模板，失败时打印警告"""
    full = os.path.join(_TEMPLATE_DIR, path)
    tpl = cv2.imread(full, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        log(f"模板加载失败: {path}", "WARN")
    return tpl


TPL = {
    'fubentiaoguo':   _load('fuben/fubentiaoguo.bmp'),
    'jinruzhandou':   _load('mijing/jinruzhandou.bmp'),
    'mijingxiangyao': _load('mijing/mijingxiangyao.bmp'),
    'huodongmijing':  _load('mijing/huodongmijing.bmp'),
    'yaozuodeshi':    _load('mijing/yaozuodeshi.bmp'),
    'jixu':           _load('mijing/jixu.bmp'),
    'xuanmijing':     _load('mijing/xuanmijing.bmp'),
    'mijing_jinru':   _load('mijing/jinru.bmp'),
    'shibai':         _load('mijing/shibai.bmp'),
    'likai':          _load('mijing/likai.bmp'),
    'queding':        _load('common/queding.bmp'),
    'yasongbiaoyin':  _load('yabiao/yasongbiaoyin.jpg'),
    'yunbiao':        _load('yabiao/yunbiao.bmp'),
    'tianti':         _load('yabiao/tianti.bmp'),
    'x':              _load('yabiao/x.bmp'),
    'qiuzhu':         _load('dati/qiuzhu.bmp'),
    'qiuzhu2':        _load('dati/qiuzhu2.bmp'),
    'sanjie':         _load('dati/sanjie.bmp'),
    'keju':           _load('dati/keju.jpg'),
    'kejujieshu':     _load('dati/kejujieshu.jpg'),
    'keju_x':         _load('dati/keju_x.jpg'),
    'jieshu':         _load('dati/jieshu.bmp'),
    'dati_x':         _load('dati/x.bmp'),
    'shiyong':        _load('common/shiyong.bmp'),
    'renwu':          _load('common/renwu.bmp'),
    'shimenrenwu':    _load('shimen/shimenrenwu.bmp'),
    'huodongshimen':  _load('shimen/huodongshimen.bmp'),
    'quwancheng':     _load('shimen/quwancheng.bmp'),
    'shimen_complete': _load('shimen/shimen_complete.bmp'),
    'shimen_confirm':  _load('shimen/shimen_confirm.bmp'),
    'shimen_x':        _load('shimen/shimen_x.bmp'),
    'huodong':        _load('common/huodong.bmp'),
    'duiwu':          _load('common/duiwu.bmp'),
    'qingli':         _load('common/qingli.bmp'),
    'panel_x':        _load('common/panel_x.bmp'),
    'yaoqingrudui':   _load('common/yaoqingrudui.bmp'),
    'baoturenwu':     _load('baotu/baoturenwu.bmp'),
    'tingtingwufang': _load('baotu/tingtingwufang.bmp'),
    'renwu_baotu':    _load('baotu/renwu_baotu.bmp'),
    'baoguo':         _load('watu/baoguo.bmp'),
    'watu_baotu':     _load('watu/baotu.bmp'),
    'zhengli':        _load('watu/zhengli.bmp'),
    'jihuo':          _load('watu/jihuo.jpg'),
    'putong':         _load('fuben/putong.bmp'),
    'xuanzefuben':    _load('fuben/xuanzefuben.bmp'),
    'jinru':          _load('fuben/jinru.bmp'),
    'yiwancheng':     _load('fuben/yiwancheng.bmp'),
    'qingxuanze':     _load('fuben/qingxuanze.bmp'),
    'zhan':           _load('fuben/zhan.bmp'),
    'guaguale_x':     _load('fuben/guaguale_x.jpg'),
    'guagua_close_big': _load('guagua/close.bmp'),
    'guagua_close_small': _load('guagua/close_small.bmp'),
    # 卖东西（出售）+ 打工
    'shangcheng':     _load('maidongxi/shangcheng.bmp'),
    'shanghui_tab':   _load('maidongxi/shanghui.bmp'),
    'woyaochushou_tab': _load('maidongxi/woyaochushou.bmp'),
    'chushou_btn':    _load('maidongxi/chushou.bmp'),
    'meiyoushangpin': _load('maidongxi/meiyoushangpin.bmp'),
    'huoli_x':        _load('common/huoli_x.bmp'),
    'qianwang':       _load('common/qianwang.png'),
    'zhuoguirenwu':   _load('zhuogui/zhuoguirenwu.bmp'),
    'zhuogui':        _load('zhuogui/zhuogui.bmp'),
    'zhuoguiqueding': _load('zhuogui/zhuoguiqueding.bmp'),
    'zhuogui_wancheng': _load('zhuogui/wancheng.bmp'),
    'zhuogui_xuanxiang': _load('zhuogui/zhuogui_xuanxiang.bmp'),
}

# 宝图搜索区域
BAOTU_REGION = (0, 0, 2600, 300)
# 副本区域
FUBEN_REGION = (0, 0, 2600, 1440)


# ========== 截图 + 匹配 ==========

def _screenshot_gray(region=None, full=False):
    """mss 截图。full=True 强制全屏，不使用线程窗口区域。

    region 语义统一为 (left, top, right, bottom) 边界坐标。
    """
    if full:
        monitor = _sct.monitors[0]
    elif region is None:
        region = get_window_rect()
        if region:
            monitor = {"left": region[0], "top": region[1],
                       "width": region[2] - region[0], "height": region[3] - region[1]}
        else:
            monitor = _sct.monitors[0]
    else:
        monitor = {"left": region[0], "top": region[1],
                   "width": region[2] - region[0], "height": region[3] - region[1]}
    with _sct_lock:
        shot = _sct.grab(monitor)
    arr = np.array(shot)[:, :, :3]
    return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)


def _match(template, screenshot_gray):
    """模板匹配，返回 (max_val, max_loc)"""
    result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc


def _match_in_region(shot_full, template, region, yuzhi=0.8):
    """在全屏截图的指定区域内匹配模板，返回中心绝对坐标或 None"""
    x0, y0, x1, y1 = region
    crop = shot_full[y0:y1, x0:x1]
    max_val, max_loc = _match(template, crop)
    if max_val >= yuzhi:
        cx = max_loc[0] + template.shape[1] // 2 + x0
        cy = max_loc[1] + template.shape[0] // 2 + y0
        return (cx, cy, max_val)
    return None


def _retry_click_activity(missing_indices, stop_event):
    """对未找到按钮的窗口重试：如果屏幕上有活动按钮就先点活动，否则点(132,188)"""
    if not missing_indices:
        return None
    for i in missing_indices:
        x0, y0 = REGIONS[i][0], REGIONS[i][1]
        # 如果屏幕上有活动按钮，先点击活动
        if find_pic(TPL['huodong'], region=REGIONS[i]):
            find_and_click(TPL['huodong'], region=REGIONS[i])
            log(f"窗口{i+1} 重试前再次点击活动")
        else:
            safe_click(x0 + 132, y0 + 188)
            log(f"窗口{i+1} 点击重试 ({x0+132},{y0+188})")
        time.sleep(0.3)
    if _wait(3, stop_event):
        return None
    return _screenshot_gray(full=True)


def _screenshot_rgb(region=None):
    """RGB 截图，region=(x0,y0,x1,y1) 或 None 全屏"""
    region = _resolve_region(region)
    x0, y0, x1, y1 = region
    w, h = x1 - x0, y1 - y0
    with _sct_lock:
        raw = _sct.grab({"left": x0, "top": y0, "width": w, "height": h})
    arr = np.array(raw, dtype=np.uint8)[:, :, :3]
    return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)


def get_pixel_rgb(x, y):
    """获取屏幕绝对坐标 (x,y) 的 RGB 颜色值，返回 (R, G, B)"""
    shot = _screenshot_rgb((x, y, x + 2, y + 2))
    b, g, r = shot[0, 0]
    return (int(r), int(g), int(b))


def check_color_at(x, y, target_rgb, tolerance=30):
    """检查屏幕绝对坐标 (x,y) 的颜色是否接近 target_rgb=(R,G,B)
    tolerance 为 RGB 每个通道允许的最大差值"""
    r, g, b = get_pixel_rgb(x, y)
    tr, tg, tb = target_rgb
    return (abs(r - tr) <= tolerance and
            abs(g - tg) <= tolerance and
            abs(b - tb) <= tolerance)


def check_any_color(points, tolerance=30):
    """检查一组点 [(x,y,target_rgb), ...]，只要有一个命中就返回 True"""
    for x, y, target_rgb in points:
        if check_color_at(x, y, target_rgb, tolerance):
            return True
    return False


# 5个窗口区域
REGIONS = [
    (0, 0, 870, 692),
    (853, 0, 1723, 692),
    (1706, 0, 2576, 692),
    (0, 690, 870, 1382),
    (853, 690, 1723, 1382),
]


def _resolve_region(region):
    """解析 region，None 时 fallback 到窗口或全屏"""
    if region is None:
        region = get_window_rect()
    if region is None:
        region = (0, 0, 2600, 1440)
    return region


def find_pic(template, yuzhi=0.8, region=None):
    """查找模板，返回中心坐标 (x, y) 或 False"""
    region = _resolve_region(region)
    shot = _screenshot_gray(region)
    max_val, max_loc = _match(template, shot)
    if max_val >= yuzhi:
        cx = max_loc[0] + template.shape[1] // 2 + region[0]
        cy = max_loc[1] + template.shape[0] // 2 + region[1]
        return (cx, cy)
    return False


# "前往参与"弹窗关闭按钮 ×（相对窗口坐标）
QIANWANG_CLOSE_X, QIANWANG_CLOSE_Y = 613, 472


def close_qianwang(rect, yuzhi=0.8):
    """检测"前往参与"弹窗，出现则点右上角 ×(相对窗口 613,472) 关闭。
    返回 True 表示检测到并已点击关闭。供副本/组队等任务复用。"""
    if find_pic(TPL['qianwang'], yuzhi=yuzhi, region=rect):
        safe_click(rect[0] + QIANWANG_CLOSE_X, rect[1] + QIANWANG_CLOSE_Y)
        log(f"[qianwang] 检测到前往参与弹窗，点击关闭 ({rect[0]+QIANWANG_CLOSE_X},{rect[1]+QIANWANG_CLOSE_Y})")
        return True
    return False


def find_pic_debug(template, yuzhi=0.8, region=None):
    """同 find_pic，但返回 (cx, cy, max_val) 三元组，未命中返回 (None, None, max_val)
    用于调试：打印当前匹配度，帮助判断阈值是否合理"""
    region = _resolve_region(region)
    shot = _screenshot_gray(region)
    max_val, max_loc = _match(template, shot)
    if max_val >= yuzhi:
        cx = max_loc[0] + template.shape[1] // 2 + region[0]
        cy = max_loc[1] + template.shape[0] // 2 + region[1]
        return (cx, cy, max_val)
    return (None, None, max_val)


def find_and_click(template, yuzhi=0.8, region=None, dx=0, dy=0, rand=5):
    """查找模板并点击中心，返回 True/False"""
    pos = find_pic(template, yuzhi, region)
    if pos:
        x = pos[0] + dx + random.randint(-rand, rand)
        y = pos[1] + dy + random.randint(-rand, rand)
        safe_click(x, y)
        log(f"({x},{y})", "点")
        return True
    return False


def _get_template(template_path):
    """按路径获取模板，优先从 TPL 字典查找"""
    name = os.path.splitext(os.path.basename(template_path))[0]
    tpl = TPL.get(name)
    if tpl is None:
        tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    return tpl


def find_and_click_path(template_path, yuzhi=0.8, region=None, dx=0, dy=0, rand=5):
    """按文件名查找并点击"""
    tpl = _get_template(template_path)
    if tpl is None:
        log(f"无法加载: {template_path}", "ERR")
        return False
    return find_and_click(tpl, yuzhi, region, dx, dy, rand)


def find_all(template, yuzhi=0.8, region=None):
    """查找模板的所有匹配位置"""
    region = _resolve_region(region)
    shot = _screenshot_gray(region)
    result = cv2.matchTemplate(shot, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= yuzhi)
    points = []
    h, w = template.shape[:2]
    grid = {}  # 网格去重，(x//w, y//h) -> (cx, cy)
    for pt_y, pt_x in zip(*locations):
        cx = pt_x + w // 2 + region[0]
        cy = pt_y + h // 2 + region[1]
        key = (pt_x // w, pt_y // h)
        if key not in grid:
            grid[key] = (cx, cy)
    points = list(grid.values())
    return points


def find_all_path(template_path, yuzhi=0.8, region=None):
    """按文件名查找所有匹配位置"""
    tpl = _get_template(template_path)
    if tpl is None:
        return []
    return find_all(tpl, yuzhi, region)


# ========== 重试 ==========

def _retry(func, max_retries=3, delay=2, label=""):
    """单步重试，失败重试 N 次"""
    for i in range(max_retries):
        try:
            result = func()
            if result is not False and result is not None:
                return result
        except Exception as e:
            log(f"{label}第{i+1}次失败: {e}", "WARN")
        if i < max_retries - 1:
            time.sleep(delay)
    if label:
        log(f"{label}重试{max_retries}次均失败", "WARN")
    return False


def _wait(seconds, stop_event):
    """可中断等待，返回 True 表示被停止"""
    return stop_event.wait(timeout=seconds)


def get_game_windows():
    """枚举所有游戏窗口，返回 [(hwnd, rect), ...] 按屏幕坐标排序"""
    windows = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if '梦幻西游' in title or 'MyLauncher' in title:
                rect = win32gui.GetWindowRect(hwnd)
                windows.append((hwnd, rect))
    win32gui.EnumWindows(callback, None)
    windows.sort(key=lambda w: (w[1][1], w[1][0]))
    return windows


# ========== 活动列表滚动 ==========

def scroll_activity(rect, direction=-1, steps=3, amount=3, stop_event=None):
    """在指定窗口区域内滚动活动列表。
    direction: -1=向下滚（看列表下方），1=向上滚（回顶部）
    steps: 滚动次数；amount: 每次滚轮刻度（回顶用大幅值一次到位，找任务用小幅逐步）
    stop_event: 传入后滚动过程中可被停止信号中断。
    参考 mhxy_code 的 _scroll_role_page：滚轮无效时用拖动兜底。"""
    import pyautogui
    if stop_event is not None and stop_event.is_set():
        return
    ox, oy = rect[0], rect[1]
    # 活动面板列表区域中心（相对窗口坐标约 435, 380）
    sx, sy = ox + 435, oy + 380
    # 滚动前截图，用于判断滚轮是否生效
    before = _screenshot_gray((ox + 100, oy + 100, ox + 770, oy + 580))
    pyautogui.moveTo(sx, sy)
    for _ in range(steps):
        if stop_event is not None and stop_event.is_set():
            return
        pyautogui.scroll(direction * amount)
        time.sleep(0.12)
    time.sleep(0.4)
    if stop_event is not None and stop_event.is_set():
        return
    # 判断滚轮是否生效（对比滚动前后截图）
    after = _screenshot_gray((ox + 100, oy + 100, ox + 770, oy + 580))
    try:
        changed = float(abs(after.astype("int16") - before.astype("int16")).mean()) > 1.0
    except Exception:
        changed = True
    if not changed:
        if stop_event is not None and stop_event.is_set():
            return
        log("滚轮未生效，用拖动兜底", "WARN")
        pyautogui.moveTo(sx, sy)
        pyautogui.mouseDown()
        time.sleep(0.25)
        target_y = sy + (100 if direction < 0 else -100)
        # 分段移动，途中可被停止中断（松开鼠标后返回）
        for i in range(6):
            if stop_event is not None and stop_event.is_set():
                pyautogui.mouseUp()
                return
            pyautogui.moveTo(sx, sy + int((target_y - sy) * (i + 1) / 6), duration=0.1)
        pyautogui.mouseUp()
        time.sleep(0.5)


def _nudge_down(rect, dy=50, stop_event=None):
    """找到按钮后微调：向上拖 dy 像素，让按钮离开列表底部边缘（内容下移、按钮上移）。
    dy>0 向上拖；dy<0 反向（回拖恢复用）。"""
    import pyautogui
    if stop_event is not None and stop_event.is_set():
        return
    ox, oy = rect[0], rect[1]
    sx, sy = ox + 435, oy + 380
    pyautogui.moveTo(sx, sy)
    time.sleep(0.2)
    if stop_event is not None and stop_event.is_set():
        return
    pyautogui.mouseDown()
    time.sleep(0.15)
    if stop_event is not None and stop_event.is_set():
        pyautogui.mouseUp()
        return
    pyautogui.moveTo(sx, sy - dy, duration=0.4)
    pyautogui.mouseUp()
    time.sleep(0.4)


def scroll_and_recheck(template, regions, missing_indices, yuzhi=0.8, stop_event=None,
                       max_scrolls=12, top_amount=30):
    """对未找到目标的窗口：先把活动列表滚回顶部，再从顶往下小步滚动逐个找任务。
    这样即使面板打开时停在列表中间，也不会漏掉顶部的目标。
    返回 (found_list, still_missing, new_shot)。
    found_list: [(index, (cx, cy, val)), ...]
    still_missing: [index, ...]
    new_shot: 滚动后的全屏截图（供调用方继续用）"""
    found_list = []
    still_missing = list(missing_indices)
    if not still_missing:
        return found_list, still_missing, _screenshot_gray(full=True)

    # 1) 先一次性大幅向上滚回活动列表顶部
    for i in list(still_missing):
        rect = regions[i]
        scroll_activity(rect, direction=1, steps=1, amount=top_amount, stop_event=stop_event)

    # 2) 在顶部先匹配一次
    shot = _screenshot_gray(full=True)
    new_still = []
    for i in still_missing:
        rect = regions[i]
        r = _match_in_region(shot, template, rect, yuzhi)
        if r:
            found_list.append((i, r))
        else:
            new_still.append(i)
    still_missing = new_still

    # 3) 从顶部开始，每轮往下滚一小步，逐个向下找
    for scroll_round in range(max_scrolls):
        if not still_missing:
            break
        if stop_event and stop_event.is_set():
            break
        for i in list(still_missing):
            rect = regions[i]
            scroll_activity(rect, direction=-1, steps=1, stop_event=stop_event)
        # 滚动后全屏截图，重新匹配
        shot = _screenshot_gray(full=True)
        new_still = []
        found_this_round = []
        for i in still_missing:
            rect = regions[i]
            r = _match_in_region(shot, template, rect, yuzhi)
            if r:
                found_list.append((i, r))
                found_this_round.append(i)
            else:
                new_still.append(i)
        still_missing = new_still

        # 本轮找到的窗口再向下拖 50px 微调后重新匹配，用新坐标覆盖旧坐标，
        # 避免按钮刚露出时贴着列表底部边缘，点击右边偏移位置点不到。
        # 微调后匹配不到就反向拖回恢复原坐标；恢复也失败则放弃该窗口，
        # 绝不保留滚动前的过期坐标去点击。
        if found_this_round:
            for i in found_this_round:
                _nudge_down(regions[i], dy=50, stop_event=stop_event)
            shot2 = _screenshot_gray(full=True)
            for i in found_this_round:
                r2 = _match_in_region(shot2, template, regions[i], yuzhi)
                if r2:
                    for idx, (fi, _fr) in enumerate(found_list):
                        if fi == i:
                            found_list[idx] = (i, r2)
                            break
                else:
                    _nudge_down(regions[i], dy=-30, stop_event=stop_event)
                    shot3 = _screenshot_gray(full=True)
                    r3 = _match_in_region(shot3, template, regions[i], yuzhi)
                    if r3:
                        for idx, (fi, _fr) in enumerate(found_list):
                            if fi == i:
                                found_list[idx] = (i, r3)
                                break
                    else:
                        found_list[:] = [x for x in found_list if x[0] != i]

    return found_list, still_missing, _screenshot_gray(full=True)
