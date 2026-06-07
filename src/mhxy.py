import subprocess
import os
import json
import time
import threading
import random
import tkinter as tk
from tkinter import messagebox
import win32gui
import win32con
import win32api
import pyautogui
from pynput import mouse

import core
from core import log
import context
import notify
from tasks import TASK_FUNCS, INDEPENDENT_TASKS, TEAM_TASKS


# ========== 颜色主题（深色游戏风） ==========
C_BG = "#1a1a2e"            # 主背景（深海蓝）
C_FRAME = "#16213e"         # 面板背景
C_BTN = "#0f3460"           # 普通按钮（靛蓝）
C_BTN_HOVER = "#1a5276"     # 按钮悬停
C_BTN_STOP = "#e74c3c"      # 停止按钮（朱红）
C_BTN_STOP_HOVER = "#ff6b6b"
C_BTN_SPECIAL = "#00b894"   # 特殊按钮（薄荷绿）
C_BTN_SPECIAL_HOVER = "#00cec9"
C_TASK = "#e17055"          # 任务按钮（珊瑚橙）
C_TASK_HOVER = "#fab1a0"
C_ALL_IN_ONE = "#0984e3"    # 一条龙按钮（宝石蓝）
C_ALL_IN_ONE_HOVER = "#74b9ff"
C_TASK_HIGHLIGHT = "#6c5ce7" # 中途继续高亮（星空紫）
C_TEXT = "#dfe6e9"          # 文字（月光白）
C_BORDER = "#2d3436"        # 边框
C_TITLE_BG = "#0c0c1d"      # 标题栏（深夜）


class GameLauncherApp:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "window.json")

    def __init__(self, root):
        self.root = root
        self.root.title("梦幻助手")
        self.root.configure(bg=C_BG)
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))

        # 恢复窗口位置和大小
        geo = self._load_geometry()
        self.root.geometry(geo)

        # 关闭时保存位置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.game_launcher_path = r"C:\Program Files\梦幻西游时空\MyLauncher_x64r.exe"

        # 任务配置：(名称, 显示文本, 行, 列)
        self.TASK_DEFS = [
            ('fuben',   '副本', 0, 0),
            ('zhuogui', '捉鬼', 0, 1),
            ('shimen',  '师门', 1, 0),
            ('baotu',   '宝图', 1, 1),
            ('mijing',  '秘境', 2, 0),
            ('watu',    '挖图', 2, 1),
            ('yabiao',  '押镖', 3, 0),
            ('dati',    '答题', 3, 1),
        ]

        self.task_running = {}
        self.task_stop_events = {}  # 每个任务的 stop_event
        self.task_windows = {}      # 跟踪每个任务运行在哪些窗口
        self.arrange_index = 0
        self._selecting_start_step = False  # 中途继续选择模式

        self._build_ui()
        self._check_launcher()

    def _load_geometry(self):
        """从配置文件读取上次的窗口位置和大小"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                w, h = cfg.get('width', 380), cfg.get('height', 460)
                x, y = cfg.get('x', 1700), cfg.get('y', 200)
                return f"{w}x{h}+{x}+{y}"
        except Exception:
            pass
        return "380x460+1700+200"

    def _save_geometry(self):
        """保存当前窗口位置和大小到配置文件"""
        try:
            geo = self.root.geometry()
            parts = geo.replace('x', ' ').replace('+', ' ').split()
            cfg = {
                'width': int(parts[0]),
                'height': int(parts[1]),
                'x': int(parts[2]),
                'y': int(parts[3])
            }
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def _on_close(self):
        """关闭窗口时保存位置"""
        self._save_geometry()
        self.root.destroy()

    def _toggle_topmost(self):
        """切换窗口置顶"""
        current = self.root.attributes('-topmost') in (True, 'true', 1)
        self.root.attributes('-topmost', not current)
        if current:
            self.topmost_btn.config(text="置顶")
            log("取消置顶")
        else:
            self.topmost_btn.config(text="取消置顶")
            log("窗口已置顶")

    # ========== 按钮工厂 ==========

    def _make_btn(self, parent, text, command, color=C_BTN, hover=C_BTN_HOVER):
        """创建统一风格按钮"""
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Microsoft YaHei", 9, "bold"),
            fg=C_TEXT, bg=color, activebackground=hover,
            activeforeground=C_TEXT, relief='flat', bd=0,
            cursor='hand2', padx=6, pady=4
        )
        btn.bind('<Enter>', lambda e, b=btn, h=hover: b.config(bg=h))
        btn.bind('<Leave>', lambda e, b=btn, c=color: b.config(bg=c))
        return btn

    # ========== UI 构建 ==========

    def _build_ui(self):
        # ---- 主容器 ----
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # 统一 2 列 grid
        btn_frame = tk.Frame(main, bg=C_BG)
        btn_frame.pack(fill=tk.X, pady=(0, 2))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        r = 0

        # 窗口管理
        self._make_btn(btn_frame, "启动一个", self.launch_game_once).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        self._make_btn(btn_frame, "启动五个", self.launch_game_five_times).grid(
            row=r, column=1, padx=2, pady=1, sticky='ew')
        r += 1
        self._make_btn(btn_frame, "排列窗口", self.arrange_game_windows).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        self.topmost_btn = self._make_btn(btn_frame, "置顶", self._toggle_topmost, C_BTN_SPECIAL)
        self.topmost_btn.grid(row=r, column=1, padx=2, pady=1, sticky='ew')
        r += 1

        # 组队 / 解散队伍
        self._make_btn(btn_frame, "组  队", self.create_team, C_BTN_SPECIAL).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        self._make_btn(btn_frame, "解散队伍", self.disband_team, C_BTN_SPECIAL).grid(
            row=r, column=1, padx=2, pady=1, sticky='ew')
        r += 1

        # 无限鬼 / 抓点+分辨率（半宽）
        self._make_btn(btn_frame, "无限鬼", lambda: self.toggle_task('zhuogui', 99), C_BTN_SPECIAL).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        half_frame = tk.Frame(btn_frame, bg=C_BG)
        half_frame.grid(row=r, column=1, padx=2, pady=1, sticky='ew')
        half_frame.columnconfigure(0, weight=1)
        half_frame.columnconfigure(1, weight=1)
        self._make_btn(half_frame, "抓点", self.get_mouse_position_and_color, C_BTN_SPECIAL).grid(
            row=0, column=0, padx=1, sticky='ew')
        self._make_btn(half_frame, "分辨率", self.get_window_resolution, C_BTN_SPECIAL).grid(
            row=0, column=1, padx=1, sticky='ew')
        r += 1

        # 任务按钮（橙色）
        self.task_buttons = {}
        for name, text, t_row, t_col in self.TASK_DEFS:
            btn = self._make_btn(btn_frame, text, lambda n=name: self.toggle_task(n), C_TASK, C_TASK_HOVER)
            btn.grid(row=r + t_row, column=t_col, padx=2, pady=1, sticky='ew')
            self.task_buttons[name] = btn
            self.task_running[name] = False
        r += 4

        # 一条龙 / 中途继续
        self._make_btn(btn_frame, "一条龙", self.all_in_one, C_ALL_IN_ONE, C_ALL_IN_ONE_HOVER).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        self._midway_btn = self._make_btn(btn_frame, "中途继续", self._toggle_midway, C_ALL_IN_ONE, C_ALL_IN_ONE_HOVER)
        self._midway_btn.grid(row=r, column=1, padx=2, pady=1, sticky='ew')
        r += 1

        # 停止
        self.stop_btn = self._make_btn(btn_frame, "停止", self.stop_all_tasks, C_BTN_STOP, C_BTN_STOP_HOVER)
        self.stop_btn.grid(row=r, column=0, columnspan=2, padx=2, pady=1, sticky='ew')

    def _check_launcher(self):
        if not os.path.exists(self.game_launcher_path):
            log("[WARN] 未找到游戏启动器")

    # ========== 窗口枚举 ==========

    def _get_game_windows(self):
        return core.get_game_windows()

    # ========== 启动游戏 ==========

    def launch_game_once(self):
        self._launch_game(1)

    def launch_game_five_times(self):
        current = len(self._get_game_windows())
        need = max(0, 5 - current)
        if need == 0:
            log("已有5个或更多窗口", "WARN")
            return
        threading.Thread(target=self._launch_five_thread, args=(need,), daemon=True).start()

    def _launch_five_thread(self, need):
        self._launch_game(need)
        # 轮询等待窗口出现，最多等60秒
        for _ in range(60):
            if len(core.get_game_windows()) >= need:
                break
            time.sleep(1)
        self.arrange_game_windows()

    def _launch_game(self, count):
        if not os.path.exists(self.game_launcher_path):
            messagebox.showerror("错误", f"未找到: {self.game_launcher_path}")
            return
        for i in range(count):
            log(f"启动第{i+1}个客户端...")
            subprocess.Popen([self.game_launcher_path], shell=True,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            if i < count - 1:
                time.sleep(2)

    # ========== 窗口排列 ==========

    def arrange_game_windows(self):
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return

        to_arrange = [w for w, _ in windows[:5]]
        to_arrange.sort()  # 按句柄排序（窗口标题都一样，不能按标题排）
        if len(to_arrange) > 1:
            idx = self.arrange_index % len(to_arrange)
            first = to_arrange.pop(idx)
            to_arrange.insert(0, first)
            self.arrange_index = (self.arrange_index + 1) % len(to_arrange)

        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        positions = [
            (0, 0), (screen_w // 3, 0), (screen_w * 2 // 3, 0),
            (0, screen_h // 2 - 30), (screen_w // 3, screen_h // 2 - 30),
        ]

        for i, hwnd in enumerate(to_arrange):
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                rect = win32gui.GetWindowRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
                x, y = positions[i]
                win32gui.MoveWindow(hwnd, x, y, w, h, True)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                time.sleep(0.5)
            except Exception as e:
                log(f"排列窗口{i+1}出错: {e}", "ERR")
        log("窗口排列完成")

    # ========== 组队 ==========

    def create_team(self):
        """自动组队（窗口 1 为队长）"""
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return

        windows.sort(key=lambda w: (w[1][1], w[1][0]))
        first_hwnd, first_rect = windows[0]

        win32gui.SetForegroundWindow(first_hwnd)
        time.sleep(1)

        self._click_at(first_rect, 18 * 1.5, 313 * 1.5)
        time.sleep(1)

        friend_ys = [241, 277, 317, 350]
        for fy in friend_ys:
            self._click_at(first_rect, 223 * 1.5, fy * 1.5)
            time.sleep(0.5)
            self._click_at(first_rect, 352 * 1.5, 230 * 1.5)
            time.sleep(0.5)

        for i, (hwnd, rect) in enumerate(windows[1:5], 2):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.5)
                self._click_at(rect, 300, 350, rand_x=10, rand_y=5 if i != 2 else 0)
                time.sleep(0.5)
            except Exception as e:
                log(f"处理窗口{i}出错: {e}", "ERR")
        # 最后点击 (802, 136)
        context.safe_click(802 + random.randint(-3, 3), 136 + random.randint(-3, 3))
        log("组队完成")

    def disband_team(self):
        """解散队伍：找队伍 → 点击操作"""
        rect = (0, 0, 870, 692)
        ox, oy = rect[0], rect[1]

        # 找队伍图片并点击
        if not core.find_and_click(core.TPL['duiwu'], yuzhi=0.8, region=rect):
            log("未找到队伍按钮", "WARN")
            return
        log("点击队伍")
        time.sleep(1)

        # 前3次: (740,240) -> (599,299) -> (511,400)
        for i in range(3):
            for x, y in [(740, 240), (599, 299), (511, 400)]:
                rx, ry = random.randint(-5, 5), random.randint(-5, 5)
                context.safe_click(ox + x + rx, oy + y + ry)
                time.sleep(0.5)
        # 第4次: (740,190) -> (599,248) -> (511,400)
        for x, y in [(740, 190), (599, 248), (511, 400)]:
            rx, ry = random.randint(-5, 5), random.randint(-5, 5)
            context.safe_click(ox + x + rx, oy + y + ry)
            time.sleep(0.5)

        log("解散队伍完成")

    def _click_at(self, rect, rel_x, rel_y, rand_x=5, rand_y=5):
        x = rect[0] + int(rel_x) + random.randint(-rand_x, rand_x)
        y = rect[1] + int(rel_y) + random.randint(-rand_y, rand_y)
        context.safe_click(x, y)

    # ========== 任务调度 ==========

    def toggle_task(self, name, rounds=None):
        """启动/停止任务，rounds 可指定轮数"""
        # 中途继续模式：点击黄色按钮从该任务开始一条龙
        if self._selecting_start_step:
            self._selecting_start_step = False
            self._midway_btn.config(text="中途继续")
            # 恢复黄色按钮原色
            for n in self.task_buttons:
                self._set_btn_idle(n)
            self._start_all_in_one_from(name)
            return

        btn = self.task_buttons[name]
        btn.config(state=tk.DISABLED)
        self.root.after(300, lambda: btn.config(state=tk.NORMAL))

        if self.task_running[name]:
            # 停止
            stop_event = self.task_stop_events.get(name)
            if stop_event:
                stop_event.set()
            self.task_running[name] = False
            self.task_windows.pop(name, None)
            self._set_btn_idle(name)
            log(f"停止{name}")
        else:
            # 启动
            self.task_running[name] = True
            self._set_btn_running(name)
            stop_event = threading.Event()
            self.task_stop_events[name] = stop_event
            func = TASK_FUNCS.get(name)
            if func:
                threading.Thread(target=self._dispatch_task, args=(name, func, stop_event, rounds), daemon=True).start()
            log(f"启动{name}")

    def _dispatch_task(self, name, func, stop_event, rounds=None):
        """根据任务类型调度：独立型每窗口一个线程，组队型只在窗口 1 执行"""
        all_windows = self._get_game_windows()
        if not all_windows:
            log("未找到游戏窗口", "WARN")
            self.task_running[name] = False
            self.root.after(0, lambda: self._set_btn_idle(name))
            return

        if name in TEAM_TASKS:
            # 组队型/全屏截图型：只执行一次，用窗口1的上下文
            hwnd, rect = all_windows[0]
            self.task_windows[name] = {hwnd}
            log(f"── 执行 {name} ──")
            self._run_single_task(hwnd, rect, func, stop_event, rounds)
        else:
            # 独立型：全部窗口并行
            windows = all_windows
            log(f"── 全部窗口 ──")

            self.task_windows[name] = set(hwnd for hwnd, _ in windows)

            # 每个窗口一个线程
            threads = []
            for hwnd, rect in windows:
                t = threading.Thread(
                    target=self._run_single_task,
                    args=(hwnd, rect, func, stop_event, rounds),
                    daemon=True
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        self.task_running[name] = False
        self.task_windows.pop(name, None)
        self.task_stop_events.pop(name, None)
        self.root.after(0, lambda: self._set_btn_idle(name))
        log(f"{name}完成")

    def _run_single_task(self, hwnd, rect, func, stop_event, rounds=None):
        """单个窗口的任务线程：设置上下文，执行任务"""
        try:
            context.set_window_context(hwnd, rect)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            if rounds is not None:
                func(stop_event, rounds=rounds)
            else:
                func(stop_event)
        except Exception as e:
            log(f"窗口执行出错: {e}", "ERR")

    def _set_btn_running(self, name):
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=f"■ {text}", bg=C_BTN_STOP, activebackground=C_BTN_STOP_HOVER)
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')

    def _set_btn_idle(self, name):
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=text, bg=C_TASK, activebackground=C_TASK_HOVER)
        btn.bind('<Enter>', lambda e, b=btn: b.config(bg=C_TASK_HOVER))
        btn.bind('<Leave>', lambda e, b=btn: b.config(bg=C_TASK))

    def _set_btn_current(self, name):
        """一条龙当前执行的按钮（粉色高亮）"""
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=f"▶ {text}", bg=C_TASK_HIGHLIGHT, activebackground=C_TASK_HIGHLIGHT)
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')

    def _set_btn_done(self, name):
        """一条龙已完成的按钮（绿色）"""
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=f"✓ {text}", bg=C_BTN_SPECIAL, activebackground=C_BTN_SPECIAL_HOVER)
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')

    def _reset_all_task_btns(self):
        """恢复所有任务按钮原色"""
        for name in self.task_buttons:
            self._set_btn_idle(name)

    def _get_display_name(self, name):
        for n, text, *_ in self.TASK_DEFS:
            if n == name:
                return text
        return name

    # ========== 抓点 ==========

    def get_mouse_position_and_color(self):
        self.task_buttons['zhuogui'].config(state=tk.DISABLED)
        self._capture_listener = mouse.Listener(on_click=self._on_global_click)
        self._capture_listener.start()

    def _on_global_click(self, x, y, button, pressed):
        if not pressed or button != mouse.Button.left:
            return
        self._capture_listener.stop()
        shot = pyautogui.screenshot()
        color = shot.getpixel((x, y))
        self.root.after(0, lambda: self._show_capture_result(x, y, color))

    def _show_capture_result(self, x, y, color):
        self.task_buttons['zhuogui'].config(state=tk.NORMAL)
        self.root.attributes('-topmost', True)
        messagebox.showinfo("抓点", f"坐标: X={x}, Y={y}\n颜色: RGB({color[0]}, {color[1]}, {color[2]})", parent=self.root)
        self.root.attributes('-topmost', False)

    # ========== 其他 ==========

    def get_window_resolution(self):
        windows = self._get_game_windows()
        if not windows:
            messagebox.showwarning("提示", "未找到游戏窗口")
            return
        _, rect = windows[0]
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        messagebox.showinfo("窗口分辨率", f"{w}x{h}")

    def _toggle_midway(self):
        """切换中途继续选择模式"""
        if self._selecting_start_step:
            self._selecting_start_step = False
            self._midway_btn.config(text="中途继续")
            # 恢复黄色按钮原色
            for name in self.task_buttons:
                self._set_btn_idle(name)
            log("已取消中途继续选择")
        else:
            self._selecting_start_step = True
            self._midway_btn.config(text="★ 选择中")
            # 高亮黄色按钮，禁用悬停效果
            for btn in self.task_buttons.values():
                btn.config(bg=C_TASK_HIGHLIGHT, activebackground=C_TASK_HIGHLIGHT)
                btn.unbind('<Enter>')
                btn.unbind('<Leave>')
            log("请点击要开始的黄色任务按钮")

    def _start_all_in_one_from(self, start_name):
        """从指定任务开始一条龙"""
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return
        log(f"中途继续一条龙，从 {start_name} 起")
        stop_event = threading.Event()
        self.task_stop_events['all_in_one'] = stop_event
        threading.Thread(target=self._all_in_one_thread, args=(windows, stop_event, start_name), daemon=True).start()

    def all_in_one(self):
        """一条龙：组队→副本x2→捉鬼→师门→宝图→秘境→挖图→押镖→答题→领取奖励"""
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return

        log("开始一条龙")
        # 高亮所有任务按钮
        for btn in self.task_buttons.values():
            btn.config(bg=C_TASK_HIGHLIGHT, activebackground=C_TASK_HIGHLIGHT)
            btn.unbind('<Enter>')
            btn.unbind('<Leave>')
        stop_event = threading.Event()
        self.task_stop_events['all_in_one'] = stop_event
        threading.Thread(target=self._all_in_one_thread, args=(windows, stop_event), daemon=True).start()

    # 一条龙步骤顺序：(任务名, 显示名, 轮数)
    _ALL_IN_ONE_STEPS = [
        ('zhuogui', '捉鬼', 2),
        ('shimen',  '师门', None),
        ('baotu',   '宝图', None),
        ('mijing',  '秘境', None),
        ('watu',    '挖图', None),
        ('yabiao',  '押镖', None),
        ('dati',    '答题', None),
    ]

    def _all_in_one_thread(self, windows, stop_event, start_from=None):
        """一条龙：组队→副本x2→捉鬼(含解散)→师门→宝图→秘境→挖图→押镖→答题→领取奖励"""
        started = start_from is None
        hwnd, rect = windows[0]

        # 组队
        if not started:
            if 'zhuogui' == start_from:
                started = True
            else:
                pass  # 跳过组队
        if started and not stop_event.is_set():
            log("── 组队 开始 ──")
            self.root.after(0, lambda: self._set_btn_current('zhuogui'))
            self.create_team()
            time.sleep(2)

        # 副本x2
        if not started and start_from == 'fuben':
            started = True
        if started and not stop_event.is_set():
            fuben_times = 1 if start_from == 'fuben' else 2
            for i in range(fuben_times):
                if stop_event.is_set():
                    break
                log(f"── 副本 第{i+1}次 开始 ──")
                self.root.after(0, lambda: self._set_btn_current('fuben'))
                task_stop = threading.Event()
                self.task_stop_events['all_in_one_current'] = task_stop
                self._run_single_task(hwnd, rect, TASK_FUNCS['fuben'], task_stop)
                self.root.after(0, lambda: self._set_btn_done('fuben'))

        # 按顺序执行任务
        for task_name, display, rounds in self._ALL_IN_ONE_STEPS:
            if not started:
                if task_name == start_from:
                    started = True
                    # 中途继续捉鬼只跑1轮
                    if task_name == 'zhuogui':
                        rounds = 1
                else:
                    continue
            if stop_event.is_set():
                return
            log(f"── {display} 开始 ──")
            self.root.after(0, lambda n=task_name: self._set_btn_current(n))
            func = TASK_FUNCS[task_name]
            task_stop = threading.Event()
            self.task_stop_events['all_in_one_current'] = task_stop
            self._run_single_task(hwnd, rect, func, task_stop, rounds=rounds)
            if stop_event.is_set():
                return
            self.root.after(0, lambda n=task_name: self._set_btn_done(n))

        # 领取奖励
        if stop_event.is_set():
            return
        log("等待5秒后领取奖励...")
        time.sleep(5)
        if stop_event.is_set():
            return
        log("── 领取奖励 ──")
        import core
        # 检查活动按钮是否存在
        shot = core._screenshot_gray(full=True)
        found_activity = False
        for hwnd, rect in windows[:5]:
            if core._match_in_region(shot, core.TPL['huodong'], rect):
                found_activity = True
                break
        if not found_activity:
            log("领取奖励：未找到活动按钮，跳过")
            return

        # 找活动按钮并点击
        for hwnd, rect in windows[:5]:
            r = core._match_in_region(shot, core.TPL['huodong'], rect)
            if r:
                context.safe_click(r[0], r[1])
                log(f"窗口{windows.index((hwnd,rect))+1} 点击活动")
                time.sleep(0.3)
        time.sleep(3)

        # 每个窗口5个奖励按钮，按轮次点击（先5个窗口的按钮1，再按钮2...）
        reward_xs = [299, 405, 526, 640, 745]
        reward_y = 500
        for rx in reward_xs:
            for i, (hwnd, rect) in enumerate(windows[:5]):
                ox, oy = rect[0], rect[1]
                x = ox + rx + random.randint(-3, 3)
                y = oy + reward_y + random.randint(-3, 3)
                context.safe_click(x, y)
                log(f"窗口{i+1} 领取奖励 ({x},{y})")
                time.sleep(0.3)
            time.sleep(0.5)

        log("一条龙任务完成")
        notify.send_feishu_msg("✅ 一条龙任务完成")
        # 恢复所有按钮原色
        self.root.after(0, self._reset_all_task_btns)
        self.task_stop_events.pop('all_in_one', None)
        log("一条龙全部完成")

    def stop_all_tasks(self):
        """停止所有任务"""
        for name, stop_event in list(self.task_stop_events.items()):
            stop_event.set()
        for name in self.task_running:
            self.task_running[name] = False
            if name in self.task_buttons:
                self._set_btn_idle(name)
        self.task_windows.clear()
        self.task_stop_events.clear()
        log("停止完成")


if __name__ == "__main__":
    root = tk.Tk()
    app = GameLauncherApp(root)
    root.bind('<F12>', lambda e: app.stop_all_tasks())
    root.mainloop()
