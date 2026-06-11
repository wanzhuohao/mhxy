"""颜色检测调试工具：移动鼠标到目标点，按 C 复制坐标+RGB"""

import time
import mss
import cv2
import numpy as np
import win32api
import threading

_sct = mss.mss()


def get_pixel_rgb(x, y):
    """获取屏幕坐标 (x,y) 的 RGB"""
    raw = _sct.grab({"left": x, "top": y, "width": 3, "height": 3})
    arr = np.array(raw, dtype=np.uint8)[:, :, :3]
    b, g, r = arr[1, 1]
    return (int(r), int(g), int(b))


def sample_region(x, y, size=30):
    """对 (x,y) 附近区域采样，返回最常见的几种颜色"""
    raw = _sct.grab({"left": x - size, "top": y - size, "width": size * 2, "height": size * 2})
    arr = np.array(raw, dtype=np.uint8)[:, :, :3]
    center = arr[size - 5:size + 5, size - 5:size + 5]
    b, g, r = cv2.mean(center)[:3]
    return (int(r), int(g), int(b))


def mouse_pos():
    return win32api.GetCursorPos()


print("=== 颜色检测调试工具 ===")
print("操作说明：")
print("  1. 打开游戏，让捉鬼完成界面显示")
print("  2. 鼠标移到要检测的位置（例如金色文字处）")
print("  3. 按 回车 读取当前位置颜色")
print("  4. 按 q 回车 退出")
print("  5. 按 s 回车 扫描窗口1区域的特殊颜色")
print("")

last_c = 0
while True:
    cmd = input("> ").strip().lower()
    if cmd in ('q', 'quit', 'exit'):
        break
    if cmd in ('s', 'scan'):
        print("\n扫描窗口1 (0,0,870,692) 中的关键点...")
        points = [
            (420, 300, "中央"),
            (420, 350, "中下部"),
            (420, 380, "下部"),
            (300, 300, "左中"),
            (500, 300, "右中"),
            (350, 392, "退出按钮"),
            (511, 392, "去接受任务"),
            (707, 242, "确认"),
        ]
        for x, y, name in points:
            try:
                rgb = sample_region(x, y)
                print(f"  ({x:4d},{y:4d}) {name:12s} → RGB={rgb}")
            except Exception as e:
                print(f"  ({x:4d},{y:4d}) {name:12s} → 错误: {e}")
        print("")
        continue
    if cmd in ('c', ''):
        x, y = mouse_pos()
        rgb = sample_region(x, y)
        print(f"  鼠标位置=({x},{y}) → RGB={rgb}  相对窗口1: ({x},{y}) → ZHUOGUI_COMPLETE_POINTS: ({x},{y},{rgb},40)")
    else:
        print("未知命令，可用: 回车/c=当前鼠标颜色, s=扫描关键点, q=退出")

print("已退出")
