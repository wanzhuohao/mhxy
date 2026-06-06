"""宝图任务"""

import threading
from core import log, find_pic, find_and_click, find_and_click_path, TPL, _wait, _retry
from notify import send_feishu_msg


def _is_baotu_complete():
    """宝图任务完成判断：有 renwu 且没有 renwu_baotu"""
    has_renwu = find_pic(TPL['renwu'], yuzhi=0.8) is not False
    has_baotu = find_pic(TPL['renwu_baotu'], yuzhi=0.8) is not False
    return has_renwu and not has_baotu


def baotu_start(stop_event: threading.Event):
    """宝图：找活动按钮 → 点宝图任务 → 等待完成"""
    log("宝图任务开始")
    send_feishu_msg("🎮 宝图任务开始")
    try:
        # 先尝试 3 次找到活动按钮
        first_found = False
        for attempt in range(3):
            if stop_event.is_set():
                return
            if _retry(lambda: find_and_click(TPL['huodong'], yuzhi=0.85), max_retries=1, label=f"宝图活动{attempt+1}"):
                log("点击活动")
                first_found = True
                break
            log(f"宝图任务：第 {attempt+1} 次未找到活动按钮")
            if _wait(2, stop_event):
                return

        if not first_found:
            log("宝图任务：3次未找到活动按钮，进入等待结束判断")
            send_feishu_msg("⏳ 宝图任务3次未找到，进入等待结束判断")
            while not stop_event.is_set():
                if _is_baotu_complete():
                    log("宝图任务完成")
                    send_feishu_msg("✅ 宝图任务完成")
                    return
                if _wait(30, stop_event):
                    return
            return

        # 点击宝图任务和听听无妨
        if _wait(2, stop_event):
            return
        if _retry(lambda: find_and_click(TPL['baoturenwu'], yuzhi=0.75, dx=130, dy=15), label="宝图任务"):
            log("点击宝图任务")
            if _wait(3, stop_event):
                return
            _retry(lambda: find_and_click(TPL['tingtingwufang'], yuzhi=0.75), label="听听无妨")
            log("点击听听无妨")

        # 循环等待宝图任务完成
        log("等待宝图任务完成...")
        while not stop_event.is_set():
            if _is_baotu_complete():
                log("宝图任务完成")
                send_feishu_msg("✅ 宝图任务完成")
                return
            _retry(lambda: find_and_click(TPL['renwu_baotu'], yuzhi=0.8, dx=50, dy=10), label="宝图追踪")
            if _wait(30, stop_event):
                return
    except Exception as e:
        log(f"宝图任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 宝图任务异常: {e}")
