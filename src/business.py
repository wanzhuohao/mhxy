import pyautogui
import time
import cv2
import numpy as np
import random
import os
import subprocess
import json

pyautogui.FAILSAFE = True  # 鼠标移到左上角触发紧急停止，防止误操作

# 加载配置
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
_CONFIG = {}
if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
        _CONFIG = json.load(f)

FEISHU_CHAT_ID = _CONFIG.get('feishu_chat_id', '')
LARK_CLI_PATH = _CONFIG.get('lark_cli_path', 'lark-cli')


def send_feishu_msg(text):
    """发送飞书消息"""
    if not FEISHU_CHAT_ID:
        return
    try:
        subprocess.run(
            [LARK_CLI_PATH, 'im', '+messages-send', '--chat-id', FEISHU_CHAT_ID, '--as', 'bot', '--text', text],
            capture_output=True, timeout=10, shell=True
        )
    except Exception as e:
        log(f"飞书通知失败: {e}", "WARN")


def log(msg, level=""):
    """带时间戳的日志"""
    ts = time.strftime("%H:%M")
    prefix = f"[{ts}]" if not level else f"[{ts} {level}]"
    print(f"{prefix} {msg}")

# ========== 模板预加载 ==========
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')


def _load(path):
    """加载灰度模板，失败时打印警告"""
    full = os.path.join(_TEMPLATE_DIR, path)
    tpl = cv2.imread(full, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        log(f"模板加载失败: {path}", "WARN")
        return None
    return tpl


# 预加载所有模板（模块级，只读一次磁盘）
TPL = {
    'fubentiaoguo':   _load('fuben/fubentiaoguo.bmp'),
    'jinruzhandou':   _load('mijing/jinruzhandou.bmp'),
    'mijingxiangyao': _load('mijing/mijingxiangyao.bmp'),
    'queding':        _load('common/queding.bmp'),
    'yasongbiaoyin':  _load('yabiao/yasongbiaoyin.jpg'),
    'qiuzhu':         _load('dati/qiuzhu.bmp'),
    'qiuzhu2':        _load('dati/qiuzhu2.bmp'),
    'shiyong':        _load('common/shiyong.bmp'),
    'renwu':          _load('common/renwu.bmp'),
    # 师门任务模板
    'shimenrenwu':    _load('shimen/shimenrenwu.bmp'),
    'quwancheng':     _load('shimen/quwancheng.bmp'),
    'shimen_complete': _load('shimen/shimen_complete.bmp'),
    'shimen_confirm':  _load('shimen/shimen_confirm.bmp'),
    'shimen_x':        _load('shimen/shimen_x.bmp'),
    # 宝图任务模板
    'huodong':        _load('common/huodong.bmp'),
    'baoturenwu':     _load('baotu/baoturenwu.bmp'),
    'tingtingwufang': _load('baotu/tingtingwufang.bmp'),
    'renwu_baotu':    _load('baotu/renwu_baotu.bmp'),
}

# 宝图搜索区域（y < 300）
BAOTU_REGION = (0, 0, 2600, 300)


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


def find_and_click(template, yuzhi=0.8, region=None, dx=0, dy=0, rand=5):
    """查找模板并点击中心（+偏移+随机），返回 True/False"""
    pos = find_pic(template, yuzhi, region)
    if pos:
        x = pos[0] + dx + random.randint(-rand, rand)
        y = pos[1] + dy + random.randint(-rand, rand)
        pyautogui.click(x, y)
        log(f"({x},{y})", "点")
        return True
    return False


def find_and_click_path(template_path, yuzhi=0.8, region=None, dx=0, dy=0, rand=5):
    """按文件名查找并点击（内部用预加载模板，不重复读磁盘）"""
    name = os.path.splitext(os.path.basename(template_path))[0]
    tpl = TPL.get(name)
    if tpl is None:
        tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            log(f"无法加载: {template_path}", "ERR")
            return False
    return find_and_click(tpl, yuzhi, region, dx, dy, rand)


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
stop_shimen = False
stop_baotu = False


def stop_all():
    """停止所有任务"""
    global stop_watu, stop_mijing, stop_yabiao, stop_dati, stop_fuben, stop_shimen, stop_baotu
    stop_watu = stop_mijing = stop_yabiao = stop_dati = stop_fuben = stop_shimen = stop_baotu = True


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
    send_feishu_msg("🎮 挖图任务开始")
    try:
        while not stop_watu:
            find_and_click_path('shiyong.bmp', yuzhi=0.65, region=FULL_REGION)
            if _wait(3, lambda: stop_watu):
                break
        send_feishu_msg("✅ 挖图任务完成")
    except KeyboardInterrupt:
        log("挖图已终止")


def mijing_start():
    """秘境任务"""
    global stop_mijing
    stop_mijing = False
    send_feishu_msg("🎮 秘境任务开始")
    try:
        while not stop_mijing:
            if find_and_click_path('jinruzhandou.bmp', yuzhi=0.55, region=FULL_REGION):
                if _wait(3, lambda: stop_mijing):
                    break
                continue
            find_and_click_path('mijingxiangyao.bmp', yuzhi=0.5, region=FULL_REGION)
            if _wait(3, lambda: stop_mijing):
                break
        send_feishu_msg("✅ 秘境任务完成")
    except KeyboardInterrupt:
        log("秘境已终止")


def yabiao_start():
    """押镖任务"""
    global stop_yabiao
    stop_yabiao = False
    send_feishu_msg("🎮 押镖任务开始")
    try:
        while not stop_yabiao:
            if find_and_click_path('queding.bmp', region=FULL_REGION):
                if _wait(3, lambda: stop_yabiao):
                    break
                continue
            find_and_click_path('yasongbiaoyin.jpg', region=FULL_REGION)
            if _wait(3, lambda: stop_yabiao):
                break
        send_feishu_msg("✅ 押镖任务完成")
    except KeyboardInterrupt:
        log("押镖已终止")


def dati_start():
    """答题任务"""
    global stop_dati
    stop_dati = False
    send_feishu_msg("🎮 答题任务开始")
    try:
        while not stop_dati:
            find_and_click_path('qiuzhu.bmp', region=FULL_REGION, dy=-200)
            find_and_click_path('qiuzhu2.bmp', region=FULL_REGION, dy=-200)
            find_and_click_path('shiyong.bmp', region=FULL_REGION)
            if _wait(1, lambda: stop_dati):
                break
        send_feishu_msg("✅ 答题任务完成")
    except KeyboardInterrupt:
        log("答题已终止")


def fuben_start():
    """副本任务（坐标基于 FUBEN_REGION 左上角偏移）"""
    global stop_fuben
    stop_fuben = False
    ox, oy = FUBEN_REGION[0], FUBEN_REGION[1]
    send_feishu_msg("🎮 副本任务开始")
    try:
        while not stop_fuben:
            if find_and_click_path('fubentiaoguo.bmp', yuzhi=0.65, region=FUBEN_REGION):
                if _wait(5, lambda: stop_fuben):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                pyautogui.click(ox + 744 + dx, oy + 190 + dy)
                if _wait(5, lambda: stop_fuben):
                    break
                dx, dy = random.randint(-5, 5), random.randint(-5, 5)
                pyautogui.click(ox + 638 + dx, oy + 510 + dy)
                if _wait(3, lambda: stop_fuben):
                    break
                continue
            if find_and_click_path('queding.bmp', region=FUBEN_REGION):
                if _wait(10, lambda: stop_fuben):
                    break
                continue
            time.sleep(1)
        send_feishu_msg("✅ 副本任务完成")
    except KeyboardInterrupt:
        log("副本已终止")


def all_in_one():
    """一条龙：押镖 → 秘境"""
    log("══ 一条龙开始 ══")
    send_feishu_msg("🎮 一条龙任务开始（押镖→秘境）")
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
    send_feishu_msg("✅ 一条龙任务完成")


def shimen_start(windows=None):
    """师门任务自动化：所有窗口并行执行每个步骤

    Args:
        windows: 窗口列表 [(hwnd, rect), ...]，None时为单窗口模式
    """
    global stop_shimen
    stop_shimen = False
    max_tasks = 20  # 最多执行20个师门任务
    completed = 0

    # 单窗口模式（兼容旧调用）
    if windows is None:
        windows = [(None, None)]

    send_feishu_msg("🎮 师门任务开始")
    try:
        # 先尝试3次找到第一个任务图标
        first_found = False
        for attempt in range(3):
            if stop_shimen:
                return
            if _shimen_click_task_icon_all_windows(windows):
                first_found = True
                break
            log(f"师门任务：第 {attempt+1} 次未找到任务图标")
            time.sleep(2)

        if not first_found:
            log("师门任务：3次未找到任务图标，进入等待结束判断")
            send_feishu_msg("⏳ 师门任务3次未找到，进入等待结束判断")
            # 进入等待结束的判断
            _shimen_wait_completion_all_windows(windows, 0)
            send_feishu_msg("✅ 师门任务完成")
            return

        completed = 1
        log("── 师门任务 1 开始 ──")

        # 步骤2：所有窗口点击"去完成"
        if not _shimen_click_complete_all_windows(windows):
            log("师门任务：未找到去完成按钮")
            send_feishu_msg("✅ 师门任务完成（无任务）")
            return

        # 步骤3：等待所有窗口任务完成
        if not _shimen_wait_completion_all_windows(windows, 1):
            send_feishu_msg("✅ 师门任务完成")
            return

        log("师门任务 1 完成 ✓")

        for task_num in range(2, max_tasks + 1):
            if stop_shimen:
                log(f"师门任务结束，已完成 {completed} 个")
                send_feishu_msg(f"✅ 师门任务完成，共 {completed} 个")
                return

            log(f"── 师门任务 {task_num} 开始 ──")

            # 步骤1：所有窗口点击师门任务图标
            if not _shimen_click_task_icon_all_windows(windows):
                log(f"师门任务结束，共完成 {completed} 个")
                send_feishu_msg(f"✅ 师门任务完成，共 {completed} 个")
                return

            # 步骤2：所有窗口点击"去完成"
            if not _shimen_click_complete_all_windows(windows):
                log("师门任务：未找到去完成按钮")
                return

            # 步骤3：等待所有窗口任务完成
            if not _shimen_wait_completion_all_windows(windows, task_num):
                return

            completed += 1
            log(f"师门任务 {task_num} 完成 ✓")

            # 任务间隔，避免操作过快
            if _wait(3, lambda: stop_shimen):
                return

        log(f"师门任务全部完成，共 {completed} 个")
        send_feishu_msg(f"✅ 师门任务完成，共 {completed} 个")

    except KeyboardInterrupt:
        log("师门已终止")
    except Exception as e:
        log(f"师门任务出错: {e}", "ERR")
        send_feishu_msg(f"❌ 师门任务出错: {e}")


def _shimen_click_task_icon_all_windows(windows):
    """所有窗口点击师门任务图标，返回是否全部成功"""
    for i in range(15):
        if stop_shimen:
            return False

        success_count = 0
        for hwnd, rect in windows:
            # 切换到窗口
            if hwnd is not None:
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.5)
                except Exception:
                    continue

            if find_and_click(TPL['shimenrenwu'], yuzhi=0.85, dx=50, dy=10):
                success_count += 1
                log(f"窗口点击师门任务图标")

        if success_count == len(windows):
            if _wait(2, lambda: stop_shimen):
                return False
            return True

        time.sleep(1)
    return False


def _shimen_click_complete_all_windows(windows):
    """所有窗口点击去完成按钮，返回是否全部成功"""
    for i in range(10):
        if stop_shimen:
            return False

        success_count = 0
        for hwnd, rect in windows:
            # 切换到窗口
            if hwnd is not None:
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.5)
                except Exception:
                    continue

            if find_and_click(TPL['quwancheng'], yuzhi=0.95):
                success_count += 1
                log(f"窗口点击去完成")

        if success_count == len(windows):
            if _wait(2, lambda: stop_shimen):
                return False
            return True

        time.sleep(1)
    return False


def _shimen_wait_completion_all_windows(windows, task_num):
    """等待所有窗口师门任务完成，返回是否全部成功"""
    log(f"等待师门任务 {task_num} 完成...")
    timeout = 120  # 最长等待2分钟
    start_time = time.time()

    # 跟踪每个窗口的完成状态
    window_completed = [False] * len(windows)

    while not stop_shimen:
        # 检查超时
        if time.time() - start_time > timeout:
            log(f"师门任务 {task_num} 等待超时", "WARN")
            return False

        # 检查每个窗口
        for idx, (hwnd, rect) in enumerate(windows):
            if window_completed[idx]:
                continue  # 已完成，跳过

            # 切换到窗口
            if hwnd is not None:
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.3)
                except Exception:
                    continue

            # 检测完成状态
            if find_pic(TPL['shimen_complete'], yuzhi=0.85):
                log(f"窗口 {idx+1} 检测到师门任务完成")
                if find_and_click(TPL['shimen_confirm'], yuzhi=0.85):
                    log(f"窗口 {idx+1} 点击确定")
                    if _wait(1, lambda: stop_shimen):
                        return False
                    find_and_click(TPL['shimen_x'], yuzhi=0.85)
                    log(f"窗口 {idx+1} 点击关闭")
                    window_completed[idx] = True

        # 检查是否全部完成
        if all(window_completed):
            return True

        time.sleep(5)  # 缩短检查间隔到5秒

    return False


def _is_baotu_complete():
    """宝图任务完成判断：有 renwu 且没有 renwu_baotu"""
    has_renwu = find_pic(TPL['renwu'], yuzhi=0.8) is not False
    has_baotu = find_pic(TPL['renwu_baotu'], yuzhi=0.8) is not False
    return has_renwu and not has_baotu


def baotu_start():
    """宝图任务（一次性启动，循环等待图片出现）"""
    global stop_baotu
    stop_baotu = False
    max_wait = 10  # 最多等待 10 次
    send_feishu_msg("🎮 宝图任务开始")
    try:
        # 先尝试3次找到活动按钮
        first_found = False
        for attempt in range(3):
            if stop_baotu:
                return
            if find_and_click(TPL['huodong'], yuzhi=0.85):
                log("点击活动")
                first_found = True
                break
            log(f"宝图任务：第 {attempt+1} 次未找到活动按钮")
            time.sleep(2)

        if not first_found:
            log("宝图任务：3次未找到活动按钮，进入等待结束判断")
            send_feishu_msg("⏳ 宝图任务3次未找到，进入等待结束判断")
            # 进入等待结束的判断
            while not stop_baotu:
                if _is_baotu_complete():
                    log("宝图任务完成！")
                    send_feishu_msg("✅ 宝图任务完成")
                    break
                time.sleep(30)
            return

        # 点击宝图任务和听听无妨
        if _wait(2, lambda: stop_baotu):
            return
        if find_and_click(TPL['baoturenwu'], yuzhi=0.75, dx=130, dy=15):
            log("点击宝图任务")
            if _wait(3, lambda: stop_baotu):
                return
            find_and_click(TPL['tingtingwufang'], yuzhi=0.75)
            log("点击听听无妨")

        # 循环等待宝图任务完成，间隔30秒
        log("等待宝图任务完成...")
        while not stop_baotu:
            if _is_baotu_complete():
                log("宝图任务完成！")
                send_feishu_msg("✅ 宝图任务完成")
                break
            # 未完成，点击 renwu_baotu（x+50, y+10）
            find_and_click(TPL['renwu_baotu'], yuzhi=0.8, dx=50, dy=10)
            time.sleep(30)

    except KeyboardInterrupt:
        log("宝图已终止")
