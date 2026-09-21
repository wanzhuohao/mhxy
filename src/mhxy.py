import subprocess
import os
import json
import time
import datetime
import threading
import random
import tkinter as tk
from tkinter import messagebox
import win32gui
import win32con
import win32api
import pyautogui
pyautogui.FAILSAFE = False
from pynput import mouse

import core
from core import log
import context
import notify
from tasks import TASK_FUNCS, TEAM_TASKS


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

    # ========== 统一任务顺序源（按钮 / 一条龙 / 中途继续共用，只在此处维护顺序） ==========
    _TASK_ORDER = [
        ('guagua',    '刮刮乐'),
        ('zudui',     '组队'),
        ('fuben',     '副本'),
        ('lingshuang','领双'),
        ('zhuogui',   '捉鬼'),
        ('jiesan',    '解散'),
        ('shimen',    '师门'),
        ('baotu',     '宝图'),
        ('mijing',    '秘境'),
        ('watu',      '挖图'),
        ('yabiao',    '押镖'),
        ('sanjie',    '三界'),
        ('keju',      '科举'),
        ('lingjiang', '领奖'),
        ('bangpai',   '帮派'),
        ('shiyonggongju', '打工'),
        ('maidongxi', '出售'),
        ('huijia',    '回家'),
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("梦幻助手")
        self.root.configure(bg=C_BG)
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))

        # 加载用户配置（含窗口几何、捉鬼轮数、是否跳过师门）
        self.cfg = {}
        self._load_cfg()

        # 恢复窗口位置和大小
        geo = self._load_geometry()
        self.root.geometry(geo)

        # 关闭时保存位置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.game_launcher_path = r"C:\Program Files\梦幻西游时空\MyLauncher_x64r.exe"

        # 任务配置：按 _TASK_ORDER 顺序每行 3 个自动排布 (名称, 显示文本, 行, 列)
        self.TASK_DEFS = [
            (name, text, i // 3, i % 3)
            for i, (name, text) in enumerate(self._TASK_ORDER)
        ]

        self.task_running = {}
        self.task_stop_events = {}  # 每个任务的 stop_event
        self.task_windows = {}      # 跟踪每个任务运行在哪些窗口
        self.arrange_index = 0

        self._build_ui()
        self._check_launcher()
        self._start_button_update_timer()

    def _load_cfg(self):
        """加载用户配置到 self.cfg（window.json），不存在或损坏时用默认"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.cfg = json.load(f)
        except Exception:
            self.cfg = {}
        if not isinstance(self.cfg, dict):
            self.cfg = {}

    def _save_cfg(self):
        """将 self.cfg 写回 window.json（保留既有字段）"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cfg, f)
        except Exception:
            pass

    def _load_geometry(self):
        """从 self.cfg 读取上次的窗口位置和大小"""
        try:
            cfg = self.cfg or {}
            w, h = cfg.get('width', 380), cfg.get('height', 520)
            # 高度下限：保证窗口能容纳当前分区布局，防止旧配置截断底部
            h = max(h, 520)
            x, y = cfg.get('x', 1700), cfg.get('y', 200)
            return f"{w}x{h}+{x}+{y}"
        except Exception:
            pass
        return "380x520+1700+200"

    def _save_geometry(self):
        """保存当前窗口位置和大小到配置文件"""
        try:
            geo = self.root.geometry()
            parts = geo.replace('x', ' ').replace('+', ' ').split()
            self.cfg['width'] = int(parts[0])
            self.cfg['height'] = int(parts[1])
            self.cfg['x'] = int(parts[2])
            self.cfg['y'] = int(parts[3])
            self._save_cfg()
        except Exception:
            pass

    def _on_close(self):
        """关闭窗口时保存位置"""
        self._save_geometry()
        self.root.destroy()

    def _make_btn(self, parent, text, command, color=C_BTN, hover=C_BTN_HOVER,
                  font_size=9, pad_x=6, pad_y=4):
        """创建统一风格按钮；font_size/pad_x/pad_y 用于放大个别按钮（如弹窗）"""
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Microsoft YaHei", font_size, "bold"),
            fg=C_TEXT, bg=color, activebackground=hover,
            activeforeground=C_TEXT, relief='flat', bd=0,
            cursor='hand2', padx=pad_x, pady=pad_y
        )
        btn.bind('<Enter>', lambda e, b=btn, h=hover: b.config(bg=h))
        btn.bind('<Leave>', lambda e, b=btn, c=color: b.config(bg=c))
        return btn

    # ========== UI 构建 ==========

    def _build_ui(self):
        # ---- 主容器 ----
        main = tk.Frame(self.root, bg=C_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # 读取配置（捉鬼轮数/跳过师门）
        cfg = self.cfg or {}
        self.zhuogui_rounds_var = tk.IntVar(value=int(cfg.get('zhuogui_rounds', 5)))
        self.skip_shimen_var = tk.BooleanVar(value=cfg.get('skip_shimen', True))

        # 统一 3 列 grid（任务按钮一排 3 个）
        btn_frame = tk.Frame(main, bg=C_BG)
        btn_frame.pack(fill=tk.X, pady=(0, 2))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        r = 0

        # 窗口管理 + 特殊操作（一排 3 个）
        self._make_btn(btn_frame, "启动一个", self.launch_game_once).grid(
            row=r, column=0, padx=2, pady=2, sticky='ew')
        self._make_btn(btn_frame, "启动五个", self.launch_game_five_times).grid(
            row=r, column=1, padx=2, pady=2, sticky='ew')
        self._make_btn(btn_frame, "排列窗口", self.arrange_game_windows).grid(
            row=r, column=2, padx=2, pady=2, sticky='ew')
        r += 1
        self._make_btn(btn_frame, "无限鬼", lambda: self.toggle_task('zhuogui', 99), C_BTN_SPECIAL).grid(
            row=r, column=0, padx=2, pady=2, sticky='ew')
        self._make_btn(btn_frame, "抓点", self.get_mouse_position_and_color, C_BTN_SPECIAL).grid(
            row=r, column=1, padx=2, pady=2, sticky='ew')
        self._make_btn(btn_frame, "分辨率", self.get_window_resolution, C_BTN_SPECIAL).grid(
            row=r, column=2, padx=2, pady=2, sticky='ew')
        r += 1

        # 任务按钮（橙色），每行 3 个。所有按钮统一单列宽度（含领奖），
        # 后续要新增按钮直接按 (row, col) 追加到 TASK_DEFS 即可，无需改动布局。
        self.task_buttons = {}
        for _, (name, text, t_row, t_col) in enumerate(self.TASK_DEFS):
            btn = self._make_btn(btn_frame, text, lambda n=name: self.toggle_task(n), C_TASK, C_TASK_HOVER)
            btn.grid(row=r + t_row, column=t_col, padx=2, pady=2, sticky='ew')
            self.task_buttons[name] = btn
            self.task_running[name] = False
        r += 6

        # 一条龙配置：捉鬼轮数（加减按钮）+ 跳过师门
        cfg_line = tk.Frame(btn_frame, bg=C_BG)
        cfg_line.grid(row=r, column=0, columnspan=3, padx=2, pady=(3, 2), sticky='ew')
        cfg_line.columnconfigure(0, weight=1)
        cfg_line.columnconfigure(1, weight=1)

        # 左：捉鬼轮数 [−] 数字 [+]
        left = tk.Frame(cfg_line, bg=C_BG)
        left.grid(row=0, column=0, sticky='w')
        tk.Label(left, text="捉鬼轮数", fg=C_TEXT, bg=C_BG,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=(2, 6))
        self._make_btn(left, "−", self._dec_zhuogui_rounds,
                       C_TASK, C_TASK_HOVER).pack(side=tk.LEFT, padx=2)
        self.rounds_val_lbl = tk.Label(left, textvariable=self.zhuogui_rounds_var,
                                       fg=C_TEXT, bg=C_FRAME, width=3,
                                       font=("Microsoft YaHei", 11, "bold"))
        self.rounds_val_lbl.pack(side=tk.LEFT, padx=4, ipady=2)
        self._make_btn(left, "＋", self._inc_zhuogui_rounds,
                       C_TASK, C_TASK_HOVER).pack(side=tk.LEFT, padx=2)

        # 右：跳过师门开关
        self.skip_shimen_check = tk.Checkbutton(
            cfg_line, text="跳过师门", variable=self.skip_shimen_var,
            command=self._save_gui_prefs,
            fg=C_TEXT, bg=C_BG, activebackground=C_BG, activeforeground=C_TEXT,
            selectcolor=C_BG, font=("Microsoft YaHei", 10, "bold"), highlightthickness=0,
            padx=4, pady=2)
        self.skip_shimen_check.grid(row=0, column=1, sticky='e')
        r += 1

        # 一条龙 / 中途继续 / 打开日志
        self._make_btn(btn_frame, "一条龙", self.all_in_one, C_ALL_IN_ONE, C_ALL_IN_ONE_HOVER).grid(
            row=r, column=0, padx=2, pady=2, sticky='ew')
        self._midway_btn = self._make_btn(btn_frame, "中途继续", self._toggle_midway, C_ALL_IN_ONE, C_ALL_IN_ONE_HOVER)
        self._midway_btn.grid(row=r, column=1, padx=2, pady=2, sticky='ew')
        self.log_btn = self._make_btn(btn_frame, "打开日志", self._toggle_console, C_BTN_SPECIAL)
        self.log_btn.grid(row=r, column=2, padx=2, pady=2, sticky='ew')
        r += 1

        # 停止 / 关闭游戏（同一排，停止在左）。
        # 用整行容器占满 3 列、内部等比拆分，使该排总宽与其他 3 按钮排一致（右侧不再留空）；
        # 日后要在此行追加按钮，继续在容器内加列即可，无需改动外层布局。
        bottom_frame = tk.Frame(btn_frame, bg=C_BG)
        bottom_frame.grid(row=r, column=0, columnspan=3, padx=0, pady=2, sticky='ew')
        # uniform 使两列严格等宽：停止/关闭游戏各占半行，合计与上面 3 按钮排同宽
        bottom_frame.columnconfigure(0, weight=1, uniform='bottom_row')
        bottom_frame.columnconfigure(1, weight=1, uniform='bottom_row')
        self.stop_btn = self._make_btn(bottom_frame, "停止", self.stop_all_tasks, C_BTN_STOP, C_BTN_STOP_HOVER)
        self.stop_btn.grid(row=0, column=0, padx=2, pady=0, sticky='ew')
        self._make_btn(bottom_frame, "关闭游戏", self.close_all_games, C_BTN_STOP, C_BTN_STOP_HOVER).grid(
            row=0, column=1, padx=2, pady=0, sticky='ew')

    def _console_hwnd(self):
        """取当前进程控制台窗口句柄，无则返回 0"""
        try:
            import ctypes
            return ctypes.windll.kernel32.GetConsoleWindow()
        except Exception:
            return 0

    def _toggle_console(self):
        """打开/关闭控制台日志窗口（仅切换显示隐藏）"""
        hwnd = self._console_hwnd()
        if not hwnd:
            log("未找到控制台窗口", "WARN")
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            if user32.IsWindowVisible(hwnd):
                user32.ShowWindow(hwnd, 0)  # SW_HIDE
                self.log_btn.config(text="打开日志")
                log("控制台已隐藏")
            else:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
                self.log_btn.config(text="关闭日志")
                log("控制台已显示")
        except Exception as e:
            log(f"切换控制台出错: {e}", "ERR")

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
                x, y = positions[i]
                # 游戏窗口强制 4:3，870 宽必须配 680 高（客户区 854×641），
                # 用 692 会因比例不符被游戏吸附回 864×675
                win32gui.MoveWindow(hwnd, x, y, 870, 680, True)
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

        if not context.activate_window(first_hwnd, first_rect):
            log("队长窗口激活到前台失败，继续尝试", "WARN")
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
            if not context.activate_window(hwnd, rect):
                log(f"窗口{i}激活到前台失败，继续尝试", "WARN")
            time.sleep(0.5)
            self._click_at(rect, 300, 350, rand_x=10, rand_y=5 if i != 2 else 0)
            time.sleep(0.5)
        # 最后点击 (802, 136)
        context.safe_click(802 + random.randint(-3, 3), 136 + random.randint(-3, 3))
        log("组队完成")

    def disband_team(self):
        """解散队伍：优先找队伍图片 → 找不到再点固定位置 → 点击操作"""
        rect = (0, 0, 870, 692)
        ox, oy = rect[0], rect[1]

        # 队伍按钮固定位置 (右上角)
        team_btn_x, team_btn_y = 755, 130

        # 优先找图片匹配
        if core.find_and_click(core.TPL['duiwu'], yuzhi=0.7, region=rect):
            log("图片匹配成功，点击队伍")
        else:
            # 图片匹配失败，点击固定位置
            log("未找到队伍按钮，点击固定位置")
            context.safe_click(ox + team_btn_x + random.randint(-5, 5), oy + team_btn_y + random.randint(-5, 5))
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
        """启动任务；单任务互斥 + 双击防重复（rounds 可指定轮数）。

        一次只跑一个手动任务：启动新任务前自动停止其它任务；
        同一任务已在运行时再次点击直接忽略，避免误触反复开关。
        手动单独跑的师门不受「跳过师门」影响（跳过仅在一一条龙生效）。
        """
        btn = self.task_buttons.get(name)
        if btn:
            btn.config(state=tk.DISABLED)
            self.root.after(300, lambda: btn.config(state=tk.NORMAL))

        # 双击防重复：同一任务已运行，忽略本次点击
        if self.task_running.get(name):
            log(f"{name} 正在运行中，请勿重复点击（需要时可用『停止』结束）", "WARN")
            return

        # 互斥：一次只跑一个手动任务，先把其它正在运行的任务停掉
        for other, running in list(self.task_running.items()):
            if other != name and running:
                ev = self.task_stop_events.get(other)
                if ev:
                    ev.set()
                self.task_running[other] = False
                self.task_windows.pop(other, None)
                self._set_btn_idle(other)
                log(f"停止{other}（开启{name}）")

        # 启动
        self.task_running[name] = True
        stop_event = threading.Event()
        self.task_stop_events[name] = stop_event
        func = TASK_FUNCS.get(name)
        if func:
            self._set_btn_running(name)
            threading.Thread(target=self._dispatch_task, args=(name, func, stop_event, rounds), daemon=True).start()
        log(f"启动{name}")

    def _dispatch_task(self, name, func, stop_event, rounds=None):
        """根据任务类型调度。当前所有任务均为"组队型/全屏截图型"：
        只执行一次，用窗口1的上下文"""
        all_windows = self._get_game_windows()
        if not all_windows:
            log("未找到游戏窗口", "WARN")
            self.task_running[name] = False
            self.root.after(0, lambda: self._set_btn_idle(name))
            return

        # 所有任务统一：在窗口1上全屏处理（任务内部已按 REGIONS 遍历5个窗口）
        hwnd, rect = all_windows[0]
        self.task_windows[name] = {hwnd}
        log(f"── 执行 {name} ──")
        self._run_single_task(hwnd, rect, func, stop_event, rounds)

        self.task_running[name] = False
        self.task_windows.pop(name, None)
        self.task_stop_events.pop(name, None)
        self.root.after(0, lambda: self._set_btn_idle(name))
        log(f"{name}完成")

    def _run_single_task(self, hwnd, rect, func, stop_event, rounds=None):
        """单个窗口的任务线程：设置上下文，执行任务"""
        try:
            context.set_window_context(hwnd, rect)
            if not context.activate_window(hwnd, rect):
                # 激活失败（前台锁定限制）不中止任务：继续用矩形坐标点击，
                # 后续识别不到按钮时任务自身会重试/跳过
                log("窗口激活到前台失败，继续尝试执行", "WARN")
            time.sleep(0.5)
            if rounds is not None:
                func(stop_event, rounds=rounds)
            else:
                func(stop_event)
        except Exception as e:
            log(f"窗口执行出错: {e}", "ERR")
            stop_event.set()

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
        """一条龙当前执行按钮"""
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=f"▶ {text}", bg=C_TASK_HIGHLIGHT, activebackground=C_TASK_HIGHLIGHT)
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')

    def _set_btn_done(self, name):
        """一条龙已完成按钮"""
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
        """弹出任务选择窗口（可单独执行或从中途继续一条龙）"""
        self._open_midway_picker()

    def _open_midway_picker(self):
        """创建任务选择弹窗：点击某个任务即从该任务开始一条龙并关闭弹窗"""
        if getattr(self, '_midway_picker', None) and self._midway_picker.winfo_exists():
            self._midway_picker.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("从中途继续")
        win.configure(bg=C_BG)
        win.attributes('-topmost', True)
        win.resizable(False, False)
        self._midway_picker = win

        frame = tk.Frame(win, bg=C_BG)
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        tk.Label(frame, text="选择从中途继续的任务", fg=C_TEXT, bg=C_BG,
                 font=("Microsoft YaHei", 10, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 6))

        def pick(name):
            win.destroy()
            if name in self.task_stop_events and name != 'all_in_one':
                self.task_stop_events.pop(name, None)
            self._start_all_in_one_from(name)

        for i, (name, text, *_r) in enumerate(self.TASK_DEFS):
            row, col = 1 + i // 3, i % 3
            # 加大字号与内边距，按钮更好点击，弹窗随之变大
            self._make_btn(frame, text, lambda n=name: pick(n),
                           font_size=12, pad_x=20, pad_y=12).grid(
                row=row, column=col, padx=4, pady=5, sticky='ew')

        # 内容构建完成后，用实际需求尺寸定位：居中于主窗口，且不超出主窗口/屏幕边界
        win.update_idletasks()
        try:
            pw = win.winfo_reqwidth()
            ph = win.winfo_reqheight()
            mx = self.root.winfo_rootx()
            my = self.root.winfo_rooty()
            mw = self.root.winfo_width()
            mh = self.root.winfo_height()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            # 居中于主窗口
            px = mx + (mw - pw) // 2
            py = my + (mh - ph) // 2
            # 夹紧：弹窗整体保持在主窗口内
            px = max(mx, min(px, mx + mw - pw))
            py = max(my, min(py, my + mh - ph))
            # 兜底：再保证不超出屏幕
            px = max(0, min(px, sw - pw))
            py = max(0, min(py, sh - ph))
            win.geometry(f"+{px}+{py}")
        except Exception:
            pass

    def _dec_zhuogui_rounds(self):
        """捉鬼轮数减1（下限1）"""
        cur = self.zhuogui_rounds_var.get()
        self.zhuogui_rounds_var.set(max(1, cur - 1))
        self._save_gui_prefs()

    def _inc_zhuogui_rounds(self):
        """捉鬼轮数加1（上限99）"""
        cur = self.zhuogui_rounds_var.get()
        self.zhuogui_rounds_var.set(min(99, cur + 1))
        self._save_gui_prefs()

    def _save_gui_prefs(self):
        """保存捉鬼轮数/是否跳过师门到配置"""
        self.cfg['zhuogui_rounds'] = int(self.zhuogui_rounds_var.get())
        self.cfg['skip_shimen'] = bool(self.skip_shimen_var.get())
        self._save_cfg()

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
        # 防止重复启动
        if 'all_in_one' in self.task_stop_events:
            log("一条龙已在运行，请勿重复点击")
            return

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

    # 一条龙步骤顺序：由 _TASK_ORDER 派生（副本跑两次）。改顺序只改 _TASK_ORDER 即可。
    _ALL_IN_ONE_STEPS = [
        (name, text, None, 'func')
        for name, text in _TASK_ORDER
        for _ in (range(2) if name == 'fuben' else range(1))
    ]

    def _all_in_one_thread(self, windows, stop_event, start_from=None):
        """一条龙：按 _ALL_IN_ONE_STEPS 顺序执行所有步骤"""
        started = start_from is None
        hwnd, rect = windows[0]
        last_task = None

        for task_name, display, rounds, step_type in self._ALL_IN_ONE_STEPS:
            if not started:
                if task_name == start_from:
                    started = True
                else:
                    last_task = task_name
                    continue
            if stop_event.is_set():
                return

            # 跳过师门（勾选后整个一条龙不执行师门）
            if task_name == 'shimen' and self.skip_shimen_var.get():
                log("── 师门 已跳过 ──")
                last_task = task_name
                continue

            # 捉鬼轮数从配置控件读取（默认5）
            if task_name == 'zhuogui':
                try:
                    rounds = int(self.zhuogui_rounds_var.get())
                except (TypeError, ValueError):
                    rounds = int((self.cfg or {}).get('zhuogui_rounds') or 5)
                log(f"捉鬼轮数: {rounds}")

            # 两个副本之间加3-5秒延时
            if last_task == 'fuben' and task_name == 'fuben':
                delay = random.randint(3, 5)
                log(f"副本间隔等待{delay}秒...")
                time.sleep(delay)
                if stop_event.is_set():
                    return

            log(f"── {display} 开始 ──")
            self.root.after(0, lambda n=task_name: self._set_btn_current(n))

            task_stop = threading.Event()
            self.task_stop_events['all_in_one_current'] = task_stop
            func = TASK_FUNCS.get(task_name)
            if func:
                self._run_single_task(hwnd, rect, func, task_stop, rounds=rounds)

            if stop_event.is_set():
                return
            self.root.after(0, lambda n=task_name: self._set_btn_done(n))
            last_task = task_name

        log("一条龙任务完成")
        notify.send_feishu_msg("✅ 一条龙任务完成")
        # 重置副本进入按钮计数
        from tasks.fuben import _jinru_index as fuben_jinru_idx
        import tasks.fuben as fuben_mod
        fuben_mod._jinru_index = 0
        self.task_stop_events.pop('all_in_one', None)
        self.root.after(0, self._reset_all_task_btns)
        log("一条龙全部完成")

    def stop_all_tasks(self):
        """停止所有任务"""
        stopped = 0
        for name, stop_event in list(self.task_stop_events.items()):
            stop_event.set()
            stopped += 1
        for name in list(self.task_running.keys()):
            self.task_running[name] = False
        self.task_windows.clear()
        self.task_stop_events.clear()
        # 停止后立即恢复所有任务按钮原色（否则颜色会停留在执行中/高亮/已完成状态）
        self._reset_all_task_btns()
        log(f"停止完成，已停止{stopped}个任务")

    def _start_button_update_timer(self):
        """启动定时器，每分钟更新一次按钮显示状态"""
        self.root.after(60000, self._start_button_update_timer)

    def close_all_games(self):
        """停止所有任务并关闭所有游戏窗口（发关闭消息后自动点确认框确定）。
        参考 mhxy_code 的 close_game_windows：先停任务，发 WM_CLOSE，等待确认框出现后逐个点确定。"""
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return
        self.stop_all_tasks()
        threading.Thread(target=self._close_game_windows_thread, args=(windows,), daemon=True).start()

    def _close_game_windows_thread(self, windows):
        """发关闭消息给所有窗口，等待确认框出现后逐个点击确定按钮"""
        count = 0
        for hwnd, rect in windows:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                count += 1
                time.sleep(0.3)
            except Exception as e:
                log(f"关闭窗口出错: {e}", "ERR")

        if count:
            # 等待各窗口退出确认框弹出后，逐个点确定（相对窗口坐标 582,489）
            time.sleep(2)
            for i, (hwnd, rect) in enumerate(windows, 1):
                try:
                    x = rect[0] + 582
                    y = rect[1] + 489
                    context.safe_click(x, y)
                    log(f"窗口{i} 点击关闭确认 ({x},{y})")
                    time.sleep(0.3)
                except Exception as e:
                    log(f"窗口{i}点击确认出错: {e}", "ERR")

        log(f"已关闭 {count} 个游戏窗口")


if __name__ == "__main__":
    # 启动时隐藏控制台日志窗口（不再显示黑色命令行）
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        HWND = kernel32.GetConsoleWindow()
        if HWND:
            user32.ShowWindow(HWND, 0)  # SW_HIDE
    except Exception:
        pass

    root = tk.Tk()
    app = GameLauncherApp(root)
    root.bind('<F12>', lambda e: app.stop_all_tasks())
    root.mainloop()
