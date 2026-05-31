import pyautogui
import time
import cv2
import numpy as np
import random
import os

pyautogui.FAILSAFE = False


def log(msg, level="INFO"):
    """带时间戳和级别的日志"""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {level:<4} {msg}")

# ========== 模板预加载 ==========
_TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(path):
    """加载灰度模板，失败时打印警告"""
    full = os.path.join(_TEMPLATE_DIR, path)
    tpl = cv2.imread(full, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        log(f"模板加载失败: {path}", "WARN")
    return tpl


# 预加载所有模板（模块级，只读一次磁盘）
TPL = {
    'fubentiaoguo':   _load('fubentiaoguo.bmp'),
    'baixiaoxianzi':  _load('baixiaoxianzi.bmp'),
    'zhuoguiqueding': _load('zhuoguiqueding.bmp'),
    'zhuoguirenwu':   _load('zhuoguirenwu.bmp'),
    'zhong':          _load('zhong.bmp'),
    'xuanzefuben':    _load('xuanzefuben.bmp'),
    'jinruzhandou':   _load('jinruzhandou.bmp'),
    'mijingxiangyao': _load('mijingxiangyao.bmp'),
    'queding':        _load('queding.bmp'),
    'yasongbiaoyin':  _load('yasongbiaoyin.jpg'),
    'qiuzhu':         _load('qiuzhu.bmp'),
    'qiuzhu2':        _load('qiuzhu2.bmp'),
    'shiyong':        _load('shiyong.bmp'),
}


# ========== 核心匹配 ==========

def _screenshot_gray(region=None):
    """截屏并转灰度 numpy 数组"""
    shot = pyautogui.screenshot(region=region)
    return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)


def _match(template, screenshot_gray):
    """在灰度截图上做模板匹配，返回 (max_val, max_loc)"""
    result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc


def find_pic(template, yuzhi=0.8, region=None):
    """查找模板，返回中心坐标 (x, y) 或 False"""
    shot = _screenshot_gray(region)
    max_val, max_loc = _match(template, shot)
    if max_val >= yuzhi:
        cx = max_loc[0] + template.shape[1] // 2 + (region[0] if region else 0)
        cy = max_loc[1] + template.shape[0] // 2 + (region[1] if region else 0)
        return (cx, cy)
    return False


def find_and_click(template, yuzhi=0.8, region=None):
    """查找模板并点击中心，返回 True/False"""
    pos = find_pic(template, yuzhi, region)
    if pos:
        pyautogui.click(pos[0], pos[1])
        log(f"点击: {pos}", "点击")
        return True
    return False


def find_and_click_offset(template, yuzhi=0.8, region=None, dx=0, dy=0):
    """查找模板并点击偏移位置，返回 True/False"""
    pos = find_pic(template, yuzhi, region)
    if pos:
        pyautogui.click(pos[0] + dx, pos[1] + dy)
        log(f"点击: ({pos[0]+dx}, {pos[1]+dy})", "点击")
        return True
    return False


def find_and_click_path(template_path, yuzhi=0.8, region=None, dx=0, dy=0):
    """按文件名查找并点击（内部用预加载模板，不重复读磁盘）"""
    name = os.path.splitext(os.path.basename(template_path))[0]
    tpl = TPL.get(name)
    if tpl is None:
        tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            log(f"无法加载: {template_path}", "ERR")
            return False
    return find_and_click_offset(tpl, yuzhi, region, dx, dy)


def find_all(template, yuzhi=0.8, region=None):
    """查找模板的所有匹配位置，返回 [(cx, cy), ...]"""
    shot = _screenshot_gray(region)
    result = cv2.matchTemplate(shot, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= yuzhi)
    points = []
    h, w = template.shape[:2]
    for pt_y, pt_x in zip(*locations):
        cx = pt_x + w // 2 + (region[0] if region else 0)
        cy = pt_y + h // 2 + (region[1] if region else 0)
        # 去重：距离太近的算同一个
        if not any(abs(cx - px) < w // 2 and abs(cy - py) < h // 2 for px, py in points):
            points.append((cx, cy))
    return points


def find_all_path(template_path, yuzhi=0.8, region=None):
    """按文件名查找所有匹配位置"""
    name = os.path.splitext(os.path.basename(template_path))[0]
    tpl = TPL.get(name)
    if tpl is None:
        tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            return []
    return find_all(tpl, yuzhi, region)


# ========== 停止标志（兼容旧接口 business.stop_xxx = True） ==========

stop_watu = False
stop_mijing = False
stop_yabiao = False
stop_dati = False
stop_fuben = False


def stop_all():
    """停止所有任务"""
    global stop_watu, stop_mijing, stop_yabiao, stop_dati, stop_fuben
    stop_watu = stop_mijing = stop_yabiao = stop_dati = stop_fuben = True


# ========== 默认区域 ==========

FULL_REGION = (0, 0, 2600, 1300)
FUBEN_REGION = (0, 0, 880, 700)


# ========== 可中断等待 ==========

def _wait(seconds, check_fn):
    """可中断等待，check_fn 返回 True 时提前退出"""
    for _ in range(int(seconds * 10)):
        if check_fn():
            return True
        time.sleep(0.1)
    return False


# ========== 任务实现 ==========

def watu_start():
    """挖图任务"""
    global stop_watu
    stop_watu = False
    try:
        while not stop_watu:
            find_and_click_path('shiyong.bmp', yuzhi=0.65, region=FULL_REGION)
            if _wait(3, lambda: stop_watu):
                break
    except KeyboardInterrupt:
        log("挖图已终止")


def mijing_start():
    """秘境任务"""
    global stop_mijing
    stop_mijing = False
    try:
        while not stop_mijing:
            if find_and_click_path('jinruzhandou.bmp', yuzhi=0.55, region=FULL_REGION):
                if _wait(3, lambda: stop_mijing):
                    break
                continue
            find_and_click_path('mijingxiangyao.bmp', yuzhi=0.5, region=FULL_REGION)
            if _wait(3, lambda: stop_mijing):
                break
    except KeyboardInterrupt:
        log("秘境已终止")


def yabiao_start():
    """押镖任务"""
    global stop_yabiao
    stop_yabiao = False
    try:
        while not stop_yabiao:
            if find_and_click_path('queding.bmp', region=FULL_REGION):
                if _wait(3, lambda: stop_yabiao):
                    break
                continue
            find_and_click_path('yasongbiaoyin.jpg', region=FULL_REGION)
            if _wait(3, lambda: stop_yabiao):
                break
    except KeyboardInterrupt:
        log("押镖已终止")


def dati_start():
    """答题任务"""
    global stop_dati
    stop_dati = False
    try:
        while not stop_dati:
            find_and_click_path('qiuzhu.bmp', region=FULL_REGION, dy=-200)
            find_and_click_path('qiuzhu2.bmp', region=FULL_REGION, dy=-200)
            find_and_click_path('shiyong.bmp', region=FULL_REGION)
            if _wait(1, lambda: stop_dati):
                break
    except KeyboardInterrupt:
        log("答题已终止")


def fuben_start():
    """副本任务"""
    global stop_fuben
    stop_fuben = False
    try:
        while not stop_fuben:
            if find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=FUBEN_REGION):
                if _wait(5, lambda: stop_fuben):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                pyautogui.click(744 + dx, 190 + dy)
                if _wait(5, lambda: stop_fuben):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                pyautogui.click(638 + dx, 510 + dy)
                if _wait(3, lambda: stop_fuben):
                    break
                continue
            if find_and_click_path('queding.bmp', region=FUBEN_REGION):
                if _wait(10, lambda: stop_fuben):
                    break
                continue
            time.sleep(1)
    except KeyboardInterrupt:
        log("副本已终止")


def all_in_one():
    """一条龙：押镖 → 秘境"""
    log("══ 一条龙开始 ══")
    tasks = [
        ('押镖', yabiao_start),
        ('秘境', mijing_start),
    ]
    for name, func in tasks:
        log(f"── {name} 开始 ──")
        func()
        log(f"── {name} 完成 ──")
        time.sleep(2)
    log("══ 一条龙完成 ══")
