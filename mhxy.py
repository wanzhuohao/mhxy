import subprocess
import os
import sys
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
import business


def log(msg, level="INFO"):
    """带时间戳和级别的日志"""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {level:<4} {msg}")


# ========== 颜色主题 ==========
C_BG = "#2b2b2b"           # 主背景
C_FRAME = "#353535"         # 面板背景
C_BTN = "#4a6fa5"           # 普通按钮
C_BTN_HOVER = "#5a8fd5"     # 按钮悬停
C_BTN_STOP = "#c0392b"      # 停止按钮
C_BTN_STOP_HOVER = "#e74c3c"
C_BTN_SPECIAL = "#27ae60"   # 特殊按钮（一条龙等）
C_BTN_SPECIAL_HOVER = "#2ecc71"
C_TEXT = "#ecf0f1"          # 文字
C_LOG_BG = "#1e1e1e"        # 日志背景
C_LOG_FG = "#b0b0b0"        # 日志文字
C_BORDER = "#555555"        # 边框
C_TITLE_BG = "#1a1a2e"      # 标题栏


class TextRedirector:
    """将 stdout/stderr 重定向到 tkinter Text 控件，同时保留原输出"""

    def __init__(self, widget, original):
        self.widget = widget
        self.original = original

    def write(self, text):
        self.original.write(text)
        if text.strip():
            self.widget.after(0, self._append, text)

    def _append(self, text):
        self.widget.configure(state='normal')
        if not text.endswith('\n'):
            text += '\n'
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        line_count = int(self.widget.index('end-1c').split('.')[0])
        if line_count > 500:
            self.widget.delete('1.0', f'{line_count - 400}.0')
        self.widget.configure(state='disabled')

    def flush(self):
        self.original.flush()


class GameLauncherApp:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "window.json")

    def __init__(self, root):
        self.root = root
        self.root.title("梦幻助手")
        self.root.configure(bg=C_BG)
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        # 不设置 -toolwindow，保任务栏显示

        # 恢复窗口位置和大小
        geo = self._load_geometry()
        self.root.geometry(geo)

        # 关闭时保存位置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.game_launcher_path = r"C:\Program Files\梦幻西游时空\MyLauncher_x64r.exe"

        # 任务配置：(名称, 显示文本, 行, 列, 业务函数名)
        self.TASK_DEFS = [
            ('zhuogui', '捉鬼', 0, 0, None),
            ('fuben',   '副本', 0, 1, 'fuben_start'),
            ('mijing',  '秘境', 1, 0, 'mijing_start'),
            ('yabiao',  '押镖', 1, 1, 'yabiao_start'),
            ('watu',    '挖图', 2, 0, 'watu_start'),
            ('dati',    '答题', 2, 1, 'dati_start'),
        ]

        self.task_running = {}
        self.popup_detection_running = False
        self.popup_detection_thread = None
        self.popup_check_interval = 3

        self._build_ui()
        self._check_launcher()

    def _load_geometry(self):
        """从配置文件读取上次的窗口位置和大小"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                w, h = cfg.get('width', 380), cfg.get('height', 700)
                x, y = cfg.get('x', 1700), cfg.get('y', 200)
                return f"{w}x{h}+{x}+{y}"
        except Exception:
            pass
        return "380x700+1700+200"

    def _save_geometry(self):
        """保存当前窗口位置和大小到配置文件"""
        try:
            geo = self.root.geometry()
            # 格式: "宽x高+x+y"
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

    def _toggle_tool(self):
        """切换工具按钮：抓点 / 查分辨率"""
        if self.tool_mode == 'color':
            self.tool_mode = 'resolution'
            self.tool_btn.config(text="查分辨率")
            self.get_window_resolution()
        else:
            self.tool_mode = 'color'
            self.tool_btn.config(text="抓  点")
            self.get_mouse_position_and_color()

    def _toggle_topmost(self):
        """切换窗口置顶"""
        current = self.root.attributes('-topmost')
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
        # 悬停效果
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

        r = 0  # 当前行号

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

        # 组队 / 全部停止
        self._make_btn(btn_frame, "组  队", self.create_team, C_BTN_SPECIAL).grid(
            row=r, column=0, padx=2, pady=1, sticky='ew')
        self._make_btn(btn_frame, "全部停止", self.stop_all_tasks, C_BTN_STOP, C_BTN_STOP_HOVER).grid(
            row=r, column=1, padx=2, pady=1, sticky='ew')
        r += 1

        # 任务按钮
        self.task_buttons = {}
        for name, text, t_row, t_col, _ in self.TASK_DEFS:
            btn = self._make_btn(btn_frame, text, None)
            btn.grid(row=r + t_row, column=t_col, padx=2, pady=1, sticky='ew')
            self.task_buttons[name] = btn
            self.task_running[name] = False
        r += 3  # 任务占 3 行

        # 捉鬼单独绑定
        self.task_buttons['zhuogui'].config(command=self.toggle_zhuogui)
        for name, _, _, _, _ in self.TASK_DEFS:
            if name != 'zhuogui':
                self.task_buttons[name].config(command=lambda n=name: self.toggle_task(n))

        # 抓点 / 分辨率 / 一条龙
        tool_sub = tk.Frame(btn_frame, bg=C_BG)
        tool_sub.grid(row=r, column=0, padx=2, pady=1, sticky='ew')
        tool_sub.columnconfigure(0, weight=1)
        tool_sub.columnconfigure(1, weight=1)
        self._make_btn(tool_sub, "抓点", self.get_mouse_position_and_color, C_BTN_SPECIAL).grid(
            row=0, column=0, padx=1, pady=0, sticky='ew')
        self._make_btn(tool_sub, "分辨率", self.get_window_resolution, C_BTN_SPECIAL).grid(
            row=0, column=1, padx=1, pady=0, sticky='ew')
        self._make_btn(btn_frame, "一条龙", self.all_in_one, C_BTN_SPECIAL).grid(
            row=r, column=1, padx=2, pady=1, sticky='ew')

        # ---- 日志区域 ----
        log_frame = tk.Frame(main, bg=C_BORDER, bd=1)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        self.log_text = tk.Text(
            log_frame, font=("Consolas", 9), state='disabled',
            bg=C_LOG_BG, fg=C_LOG_FG, insertbackground=C_LOG_FG,
            wrap='word', bd=0, padx=6, pady=4,
            selectbackground='#4a6fa5', selectforeground=C_TEXT
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=C_FRAME)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 重定向
        sys.stdout = TextRedirector(self.log_text, sys.stdout)
        sys.stderr = TextRedirector(self.log_text, sys.stderr)

    def _section_label(self, parent, text):
        """分区小标题"""
        tk.Label(
            parent, text=text, font=("Microsoft YaHei", 9),
            fg='#888888', bg=C_BG, anchor='w'
        ).pack(fill=tk.X, padx=2, pady=(4, 1))

    def _check_launcher(self):
        if not os.path.exists(self.game_launcher_path):
            self._log("[WARN] 未找到游戏启动器")

    def _log(self, text):
        """直接写入日志框（不经过 print）"""
        self.log_text.after(0, self._log_append, text)

    def _log_append(self, text):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, text + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    # ========== 窗口枚举 ==========

    def _get_game_windows(self):
        windows = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if '梦幻西游' in title or 'MyLauncher' in title:
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append((hwnd, rect))
        win32gui.EnumWindows(callback, None)
        return windows

    # ========== 启动游戏 ==========

    def launch_game_once(self):
        self._launch_game(1)

    def launch_game_five_times(self):
        current = len(self._get_game_windows())
        need = max(0, 5 - current)
        if need == 0:
            log("已有5个或更多窗口", "WARN")
            return
        self._launch_game(need)
        time.sleep(5)
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
        if random.choice([True, False]):
            first = random.choice(to_arrange)
            to_arrange.remove(first)
            to_arrange.insert(0, first)

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

        friend_ys = [241, 277, 317, 356]
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
        log("组队完成")

    def _click_at(self, rect, rel_x, rel_y, rand_x=5, rand_y=5):
        x = rect[0] + int(rel_x) + random.randint(-rand_x, rand_x)
        y = rect[1] + int(rel_y) + random.randint(-rand_y, rand_y)
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def _raw_click(self, x, y, rand_x=5, rand_y=5):
        cx = x + random.randint(-rand_x, rand_x)
        cy = y + random.randint(-rand_y, rand_y)
        win32api.SetCursorPos((cx, cy))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    # ========== 任务 toggle ==========

    def toggle_task(self, name):
        if self.task_running[name]:
            setattr(business, f'stop_{name}', True)
            self.task_running[name] = False
            self._set_btn_idle(name)
            log(f"停止{name}")
        else:
            setattr(business, f'stop_{name}', False)
            self.task_running[name] = True
            self._set_btn_running(name)
            func = getattr(business, f'{name}_start', None)
            if func:
                threading.Thread(target=func, daemon=True).start()
            log(f"启动{name}")

    def _set_btn_running(self, name):
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=f"■ {text}", bg=C_BTN_STOP, activebackground=C_BTN_STOP_HOVER)
        btn.unbind('<Enter>')
        btn.unbind('<Leave>')

    def _set_btn_idle(self, name):
        btn = self.task_buttons[name]
        text = self._get_display_name(name)
        btn.config(text=text, bg=C_BTN, activebackground=C_BTN_HOVER)
        btn.bind('<Enter>', lambda e, b=btn: b.config(bg=C_BTN_HOVER))
        btn.bind('<Leave>', lambda e, b=btn: b.config(bg=C_BTN))

    def _get_display_name(self, name):
        for n, text, *_ in self.TASK_DEFS:
            if n == name:
                return text
        return name

    # ========== 捉鬼 ==========

    def toggle_zhuogui(self):
        if self.popup_detection_running:
            self.popup_detection_running = False
            if self.popup_detection_thread and self.popup_detection_thread.is_alive():
                self.popup_detection_thread.join(timeout=1.0)
            self._set_btn_idle('zhuogui')
            log("停止捉鬼")
        else:
            self.popup_detection_running = True
            self._set_btn_running('zhuogui')
            self.popup_detection_thread = threading.Thread(target=self._zhuogui_loop, daemon=True)
            self.popup_detection_thread.start()
            log("开始捉鬼")

    def _zhuogui_loop(self):
        while self.popup_detection_running:
            try:
                self._check_and_click_zhuogui()
            except Exception as e:
                log(f"捉鬼检测出错: {e}", "ERR")
            for _ in range(self.popup_check_interval * 10):
                if not self.popup_detection_running:
                    return
                time.sleep(0.1)

    @staticmethod
    def _check_color_at(x, y, target_rgb, tolerance=8):
        shot = pyautogui.screenshot(region=(x - 2, y - 2, 5, 5))
        for dx in range(5):
            for dy in range(5):
                pixel = shot.getpixel((dx, dy))
                if all(abs(pixel[i] - target_rgb[i]) <= tolerance for i in range(3)):
                    return True, pixel
        return False, None

    def _check_and_click_zhuogui(self):
        p1_ok, _ = self._check_color_at(514, 346, (163, 124, 83))
        p2_ok, _ = self._check_color_at(511, 392, (243, 202, 105))
        if not (p1_ok and p2_ok):
            return

        log("检测到捉鬼弹窗，执行点击流程")
        self._raw_click(511, 392)
        time.sleep(10)
        self._raw_click(707, 242)
        time.sleep(1)
        self._raw_click(767, 206, rand_x=15, rand_y=15)
        time.sleep(1)
        self._raw_click(767, 206, rand_x=10, rand_y=10)
        time.sleep(1)
        log("等待60秒后重新检测...")
        time.sleep(60)

    # ========== 抓点 ==========

    def get_mouse_position_and_color(self):
        try:
            self.task_buttons['zhuogui'].config(state=tk.DISABLED)
            self.temp_window = tk.Toplevel(self.root)
            self.temp_window.attributes('-fullscreen', True)
            self.temp_window.attributes('-alpha', 0.1)
            self.temp_window.attributes('-topmost', True)
            self.temp_window.configure(bg='white')
            self.temp_window.bind('<Button-1>', self._on_screen_click)
            self.temp_window.bind('<Escape>', lambda e: self._cleanup_selection())
        except Exception as e:
            log(f"启动选择模式出错: {e}", "ERR")

    def _on_screen_click(self, event):
        try:
            x, y = event.x_root, event.y_root
            shot = pyautogui.screenshot()
            color = shot.getpixel((x, y))
            log(f"坐标: X={x}, Y={y}  颜色: RGB({color[0]}, {color[1]}, {color[2]})", "抓点")
        finally:
            self._cleanup_selection()

    def _cleanup_selection(self):
        if hasattr(self, 'temp_window') and self.temp_window.winfo_exists():
            self.temp_window.destroy()
        self.task_buttons['zhuogui'].config(state=tk.NORMAL)

    # ========== 其他 ==========

    def get_window_resolution(self):
        windows = self._get_game_windows()
        if not windows:
            log("未找到游戏窗口", "WARN")
            return
        _, rect = windows[0]
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        log(f"窗口分辨率: {w}x{h}")

    def all_in_one(self):
        log("开始一条龙")
        threading.Thread(target=business.all_in_one, daemon=True).start()

    def stop_all_tasks(self):
        log("停止所有任务")
        if self.popup_detection_running:
            self.popup_detection_running = False
            if self.popup_detection_thread and self.popup_detection_thread.is_alive():
                self.popup_detection_thread.join(timeout=1)
            self._set_btn_idle('zhuogui')

        business.stop_all()

        for name in self.task_running:
            self.task_running[name] = False
            if name in self.task_buttons:
                self._set_btn_idle(name)


if __name__ == "__main__":
    root = tk.Tk()
    app = GameLauncherApp(root)
    root.bind('<F12>', lambda e: app.stop_all_tasks())
    root.mainloop()
