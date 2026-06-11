"""答题任务（全屏截图，分5区域处理）"""

import time
import datetime
from core import log, _screenshot_gray, TPL, _wait
from context import safe_click
from notify import send_feishu_msg
from core import _match_in_region, _retry_click_activity, REGIONS


def dati_start(stop_event):
    """答题：根据时间判断触发三界答题或科举"""
    now = datetime.datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=周一, 6=周日

    # 周一到周五 且 大于17点 → 科举
    if weekday < 5 and hour >= 17:
        log("答题任务开始（科举模式）")
        _dati_keju(stop_event)
    # 大于11点 → 三界答题
    elif hour >= 11:
        log("答题任务开始（三界答题模式）")
        _dati_sanjie(stop_event)
    else:
        log(f"答题：当前时间 {now.strftime('%H:%M')}，不满足触发条件")
        return


def _dati_keju(stop_event):
    """科举答题：全屏截图 → 点活动 → 点科举右边 → 求助/使用"""
    log("科举答题开始")

    # 第0步：先检查科举按钮是否已经在屏幕上（活动面板已打开）
    shot = _screenshot_gray(full=True)
    found_keju_direct = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['keju'], rect)
        if r:
            found_keju_direct.append((i, r))
    if found_keju_direct:
        log(f"活动面板已打开，直接找科举按钮，找到{len(found_keju_direct)}个")
        # 跳到点击科举右边
        for i, r in found_keju_direct:
            safe_click(r[0] + 130, r[1] + 10)
            log(f"窗口{i+1} [keju] 点击科举右边 ({r[0]+130},{r[1]+10})")
            time.sleep(0.3)
        if _wait(2, stop_event):
            return
    else:
        # 第1步：全屏截图，找活动按钮
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['huodong'], rect)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [huodong] 点击活动 ({r[0]},{r[1]})")
            else:
                missing.append(i)
            time.sleep(0.3)
        if missing:
            send_feishu_msg(f"⚠️ 科举答题：{','.join(f'窗口{i+1}' for i in missing)} 未找到活动按钮")

        if len(missing) == len(REGIONS):
            # 所有窗口都没有活动按钮，直接找求助
            log("所有窗口未找到活动按钮，直接找求助")
            _dati_help_loop(stop_event)
            return

        if _wait(3, stop_event):
            return

    # 第2步：全屏截图，找科举按钮并点击右边
    shot = _screenshot_gray(full=True)
    found_keju = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['keju'], rect)
        if r:
            found_keju.append((i, r))
        else:
            missing.append(i)

    # 未找到的窗口点击重试
    if missing:
        result = _retry_click_activity(missing, stop_event)
        if result is not None:
            shot = result
        still_missing = []
        for i in missing:
            r = _match_in_region(shot, TPL['keju'], REGIONS[i])
            if r:
                found_keju.append((i, r))
            else:
                still_missing.append(i)
        missing = still_missing

    for i, r in found_keju:
        safe_click(r[0] + 130, r[1] + 10)
        log(f"窗口{i+1} [keju] 点击科举右边 ({r[0]+130},{r[1]+10})")
        time.sleep(0.3)

    if missing:
        for i in missing:
            log(f"窗口{i+1}：未找到科举按钮", "WARN")
        send_feishu_msg(f"⚠️ 科举答题：{','.join(f'窗口{i+1}' for i in missing)} 未找到科举按钮")

    if _wait(2, stop_event):
        return

    # 第3步：每个窗口累计点10次求助就停止该窗口，等所有窗口都满10次后统一点X，使用不算次数
    help_count = {i: 0 for i in range(len(REGIONS))}
    done_windows = set()
    while not stop_event.is_set():
        if len(done_windows) == len(REGIONS):
            break
        shot = _screenshot_gray(full=True)

        # 找求助1并点击（偏移 dy=-200）— 求助算1次
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                help_count[i] += 1
                log(f"窗口{i+1} 求助{help_count[i]}/10 [qiuzhu] 点击求助1")
                if help_count[i] >= 10:
                    done_windows.add(i)
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）— 求助算1次
        if len(done_windows) == len(REGIONS):
            break
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                help_count[i] += 1
                log(f"窗口{i+1} 求助{help_count[i]}/10 [qiuzhu2] 点击求助2")
                if help_count[i] >= 10:
                    done_windows.add(i)
                time.sleep(0.3)

        # 找使用并点击 — 使用不算次数
        if len(done_windows) == len(REGIONS):
            break
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [shiyong] 点击使用")
                time.sleep(0.3)

        if _wait(1, stop_event):
            break

    # 所有窗口都满10次，统一找x点X
    log("科举答题所有窗口求助满10次，统一点X")
    shot = _screenshot_gray(full=True)
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['dati_x'], rect)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} [dati_x] 点击关闭 ({r[0]},{r[1]})")
            time.sleep(0.3)

    log("科举答题完成")


def _dati_help_loop(stop_event):
    """直接找求助/使用按钮循环，无求助则视为结束"""
    log("直接进入求助循环")
    for round_num in range(100):
        if stop_event.is_set():
            return
        shot = _screenshot_gray(full=True)
        found_any = False
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} [qiuzhu] 点击求助1")
                found_any = True
                time.sleep(0.3)
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} [qiuzhu2] 点击求助2")
                found_any = True
                time.sleep(0.3)
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [shiyong] 点击使用")
                found_any = True
                time.sleep(0.3)
        if not found_any:
            log("所有窗口都未找到求助/使用，答题结束")
            break
        if _wait(1, stop_event):
            return

    # 点击5个X关闭
    if _wait(1, stop_event):
        return
    shot = _screenshot_gray(full=True)
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['dati_x'], rect)
        if r:
            safe_click(r[0], r[1])
            log(f"窗口{i+1} [dati_x] 点击关闭 ({r[0]},{r[1]})")
            time.sleep(0.3)

    log("答题任务完成")


def _dati_sanjie(stop_event):
    """三界答题：全屏截图 → 点活动 → 点三界右边 → 求助/使用"""
    log("三界答题开始")

    # 第0步：先检查三界按钮是否已经在屏幕上（活动面板已打开）
    shot = _screenshot_gray(full=True)
    found_sanji_direct = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['sanjie'], rect)
        if r:
            found_sanji_direct.append((i, r))
    if found_sanji_direct:
        log(f"活动面板已打开，直接找三界按钮，找到{len(found_sanji_direct)}个")
        # 跳到点击三界右边
        for i, r in found_sanji_direct:
            safe_click(r[0] + 130, r[1] + 10)
            log(f"窗口{i+1} [sanjie] 点击三界右边 ({r[0]+130},{r[1]+10})")
            time.sleep(0.3)
        if _wait(2, stop_event):
            return
    else:
        # 第1步：全屏截图，找活动按钮
        missing = []
        for i, rect in enumerate(REGIONS):
            r = _match_in_region(shot, TPL['huodong'], rect)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [huodong] 点击活动 ({r[0]},{r[1]})")
            else:
                missing.append(i)
            time.sleep(0.3)
        if missing:
            send_feishu_msg(f"⚠️ 三界答题：{','.join(f'窗口{i+1}' for i in missing)} 未找到活动按钮")

        if len(missing) == len(REGIONS):
            # 所有窗口都没有活动按钮，直接找求助
            log("所有窗口未找到活动按钮，直接找求助")
            _dati_help_loop(stop_event)
            return

        if _wait(3, stop_event):
            return

    # 第2步：全屏截图，找三界按钮并点击右边
    shot = _screenshot_gray(full=True)
    found_sanji = []
    missing = []
    for i, rect in enumerate(REGIONS):
        r = _match_in_region(shot, TPL['sanjie'], rect)
        if r:
            found_sanji.append((i, r))
        else:
            missing.append(i)

    # 未找到的窗口点击重试
    if missing:
        result = _retry_click_activity(missing, stop_event)
        if result is not None:
            shot = result
        still_missing = []
        for i in missing:
            r = _match_in_region(shot, TPL['sanjie'], REGIONS[i])
            if r:
                found_sanji.append((i, r))
            else:
                still_missing.append(i)
        missing = still_missing

    for i, r in found_sanji:
        safe_click(r[0] + 130, r[1] + 10)
        log(f"窗口{i+1} [sanjie] 点击三界右边 ({r[0]+130},{r[1]+10})")
        time.sleep(0.3)

    if missing:
        for i in missing:
            log(f"窗口{i+1}：未找到三界按钮", "WARN")
        send_feishu_msg(f"⚠️ 三界答题：{','.join(f'窗口{i+1}' for i in missing)} 未找到三界按钮")

    if _wait(2, stop_event):
        return

    # 第3步：循环找求助/使用，检测结束标志（三界用jieshu）
    done_windows = set()
    while not stop_event.is_set():
        shot = _screenshot_gray(full=True)

        # 检测结束标志 — 有结束立即点X，优先处理
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['jieshu'], rect, yuzhi=0.7)
            if r:
                log(f"窗口{i+1} 三界答题已完成，点击X关闭")
                xr = _match_in_region(shot, TPL['dati_x'], rect)
                if xr:
                    safe_click(xr[0], xr[1])
                    log(f"窗口{i+1} [dati_x] 点击关闭 ({xr[0]},{xr[1]})")
                done_windows.add(i)

        if len(done_windows) == len(REGIONS):
            log("三界答题全部完成")
            break

        # 找求助1并点击（偏移 dy=-200）
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} [qiuzhu] 点击求助1")
                time.sleep(0.3)

        # 找求助2并点击（偏移 dy=-200）
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['qiuzhu2'], rect)
            if r:
                safe_click(r[0], r[1] - 200)
                log(f"窗口{i+1} [qiuzhu2] 点击求助2")
                time.sleep(0.3)

        # 找使用并点击
        shot = _screenshot_gray(full=True)
        for i, rect in enumerate(REGIONS):
            if i in done_windows:
                continue
            r = _match_in_region(shot, TPL['shiyong'], rect, yuzhi=0.65)
            if r:
                safe_click(r[0], r[1])
                log(f"窗口{i+1} [shiyong] 点击使用")
                time.sleep(0.3)

        if _wait(1, stop_event):
            break

    log("三界答题完成")
