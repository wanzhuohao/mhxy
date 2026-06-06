"""线程上下文 + 每窗口点击锁"""

import threading

_thread_ctx = threading.local()
_window_locks = {}
_window_locks_lock = threading.Lock()


def set_window_context(hwnd, rect):
    """设置当前线程关联的窗口句柄和区域"""
    _thread_ctx.hwnd = hwnd
    _thread_ctx.rect = rect


def get_window_rect():
    """获取当前线程的窗口区域 (x, y, w, h)"""
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
