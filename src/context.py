"""线程上下文 + 每窗口点击锁"""

import threading

import win32gui
import win32api
import win32con

_thread_ctx = threading.local()
_window_locks = {}
_window_locks_lock = threading.Lock()


def set_window_context(hwnd, rect):
    """设置当前线程关联的窗口句柄和区域"""
    _thread_ctx.hwnd = hwnd
    _thread_ctx.rect = rect


def get_window_rect():
    """获取当前线程的窗口区域，语义为 (left, top, right, bottom)
    来源是 win32gui.GetWindowRect(hwnd)，与项目统一 region 边界坐标一致"""
    return getattr(_thread_ctx, 'rect', None)


def get_window_hwnd():
    """获取当前线程的窗口句柄"""
    return getattr(_thread_ctx, 'hwnd', None)


def get_window_lock(hwnd):
    """获取指定窗口的点击锁，不同窗口互不阻塞"""
    with _window_locks_lock:
        if hwnd not in _window_locks:
            _window_locks[hwnd] = threading.Lock()
        return _window_locks[hwnd]


def safe_click(x, y):
    """带锁点击，同窗口串行，不同窗口并行"""
    import pyautogui
    hwnd = get_window_hwnd()
    if hwnd:
        lock = get_window_lock(hwnd)
        with lock:
            pyautogui.click(x, y)
    else:
        pyautogui.click(x, y)


def safe_double_click(x, y):
    """带锁双击，同窗口串行，不同窗口并行（供需要双击的地方使用）"""
    import pyautogui
    hwnd = get_window_hwnd()
    if hwnd:
        lock = get_window_lock(hwnd)
        with lock:
            pyautogui.doubleClick(x, y)
    else:
        pyautogui.doubleClick(x, y)


def activate_window(hwnd, rect=None):
    """把窗口激活到前台，多种方案兜底，失败不抛异常（返回是否成功）。

    Windows 有"前台窗口激活限制"：当脚本进程不是前台进程、或屏幕被锁/窗口被
    覆盖时，SetForegroundWindow 会静默失败，直接调用会抛 pywintypes.error
    (0, 'SetForegroundWindow', ...)，导致任务在第一行就中止。这里先用标准调用，
    失败则模拟按一次 Alt 键解除前台锁定再重试；仍失败就放弃并返回 False，
    由调用方决定如何继续（任务本身靠窗口矩形坐标 + safe_click 定位，不强制置前）。
    """
    try:
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        pass
    try:
        # 模拟按一次 Alt 键解除前台锁定限制，再重试
        win32api.keybd_event(0x12, 0, 0, 0)
        win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        pass
    return False
