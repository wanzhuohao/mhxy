"""CLI 命令实现 - 复用 business.py 和 mhxy.py 的窗口管理功能"""

import os
import signal
import sys
import time
import threading

# 导入业务模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import business
from mhxy import GameLauncherApp


def _signal_handler(signum, frame):
    """Ctrl+C 信号处理"""
    print("\n正在停止所有任务...")
    business.stop_all()
    sys.exit(0)


# 注册信号处理
signal.signal(signal.SIGINT, _signal_handler)


def run_task(task_name, windows=None):
    """运行指定任务

    Args:
        task_name: 任务名称 (shimen, baotu, fuben, mijing, yabiao, watu, dati)
        windows: 窗口列表，None 时自动获取
    """
    func = getattr(business, f'{task_name}_start', None)
    if func is None:
        print(f"未知任务: {task_name}")
        return False

    if windows is None:
        app = GameLauncherApp.__new__(GameLauncherApp)
        windows = app._get_game_windows()

    if not windows:
        print("未找到游戏窗口")
        return False

    print(f"开始执行: {task_name}")
    try:
        if task_name == 'shimen':
            func(windows=windows)
        else:
            for i, (hwnd, rect) in enumerate(windows):
                print(f"窗口 {i+1}/{len(windows)}")
                import win32gui
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(1)
                func()
                time.sleep(2)
        print(f"{task_name} 完成")
        return True
    except KeyboardInterrupt:
        print(f"{task_name} 已中断")
        return False


def run_all_in_one():
    """运行一条龙任务"""
    print("开始一条龙任务")
    try:
        business.all_in_one()
        print("一条龙完成")
    except KeyboardInterrupt:
        print("一条龙已中断")


def arrange_windows():
    """排列游戏窗口"""
    app = GameLauncherApp.__new__(GameLauncherApp)
    app.arrange_index = 0
    app.arrange_game_windows()


def launch_game(count=1):
    """启动游戏客户端

    Args:
        count: 启动数量
    """
    app = GameLauncherApp.__new__(GameLauncherApp)
    app.game_launcher_path = r"C:\Program Files\梦幻西游时空\MyLauncher_x64r.exe"
    app._launch_game(count)


def create_team():
    """自动组队"""
    app = GameLauncherApp.__new__(GameLauncherApp)
    app.create_team()


def list_tasks():
    """列出所有可用任务"""
    tasks = [
        ('shimen', '师门任务'),
        ('baotu', '宝图任务'),
        ('fuben', '副本任务'),
        ('mijing', '秘境任务'),
        ('yabiao', '押镖任务'),
        ('watu', '挖图任务'),
        ('dati', '答题任务'),
    ]
    print("可用任务:")
    for name, desc in tasks:
        print(f"  {name:10s} - {desc}")
