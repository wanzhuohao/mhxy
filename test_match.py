import pyautogui
import cv2
import numpy as np

pyautogui.FAILSAFE = False

shot = pyautogui.screenshot()
shot_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)

tpl = cv2.imread(r'c:\claude code\mhxy\templates\dati\kejujieshu.jpg', 0)
w, h = tpl.shape[::-1]

res = cv2.matchTemplate(shot_gray, tpl, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

print(f"kejujieshu 最佳匹配度: {max_val:.3f}")
print(f"位置: {max_loc}")

# 多尺度测试
for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
    new_w = int(w * scale)
    new_h = int(h * scale)
    if new_w < 10 or new_h < 10:
        continue
    tpl_scaled = cv2.resize(tpl, (new_w, new_h), interpolation=cv2.INTER_AREA)
    if tpl_scaled.shape[0] > shot_gray.shape[0] or tpl_scaled.shape[1] > shot_gray.shape[1]:
        continue
    res2 = cv2.matchTemplate(shot_gray, tpl_scaled, cv2.TM_CCOEFF_NORMED)
    _, mv2, _, ml2 = cv2.minMaxLoc(res2)
    print(f"  尺度 {scale}: {mv2:.3f} @ {ml2}")

# jieshu
tpl2 = cv2.imread(r'c:\claude code\mhxy\templates\dati\jieshu.bmp', 0)
w2, h2 = tpl2.shape[::-1]
res3 = cv2.matchTemplate(shot_gray, tpl2, cv2.TM_CCOEFF_NORMED)
_, max_val2, _, max_loc2 = cv2.minMaxLoc(res3)
print(f"\njieshu 最佳匹配度: {max_val2:.3f} @ {max_loc2}")
