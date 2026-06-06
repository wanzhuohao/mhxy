"""师门任务（独立型，每窗口各跑各的）"""

import threading
from core import log, find_pic, find_and_click, TPL, _wait, _retry
from notify import send_feishu_msg


def shimen_start(stop_event: threading.Event):
    """师门：循环找任务图标 → 去完成 → 等待完成，最多 20 轮"""
    log("师门任务开始")
    send_feishu_msg("🎮 师门任务开始")
    max_tasks = 20
    completed = 0
    try:
        # 先尝试 3 次找到任务图标
        first_found = False
        for attempt in range(3):
            if stop_event.is_set():
                return
            if _retry(lambda: find_and_click(TPL['shimenrenwu'], yuzhi=0.85, dx=50, dy=10),
                      max_retries=1, label=f"师门图标{attempt+1}"):
                first_found = True
                break
            log(f"师门任务：第 {attempt+1} 次未找到任务图标")
            if _wait(2, stop_event):
                return

        if not first_found:
            log("师门任务：3次未找到，等待完成判断")
            send_feishu_msg("⏳ 师门任务3次未找到，进入等待完成判断")
            _wait_completion(stop_event, 0)
            send_feishu_msg("✅ 师门任务完成")
            return

        completed = 1
        log("── 师门任务 1 开始 ──")

        # 点击"去完成"
        if not _retry(lambda: find_and_click(TPL['quwancheng'], yuzhi=0.95), label="师门去完成"):
            log("师门任务：未找到去完成按钮")
            send_feishu_msg("✅ 师门任务完成（无任务）")
            return

        # 等待完成
        if not _wait_completion(stop_event, 1):
            send_feishu_msg("✅ 师门任务完成")
            return
        log("师门任务 1 完成 ✓")

        for task_num in range(2, max_tasks + 1):
            if stop_event.is_set():
                break

            log(f"── 师门任务 {task_num} 开始 ──")

            # 点击任务图标
            if not _retry(lambda: find_and_click(TPL['shimenrenwu'], yuzhi=0.85, dx=50, dy=10), label="师门图标"):
                log(f"师门任务结束，共完成 {completed} 个")
                send_feishu_msg(f"✅ 师门任务完成，共 {completed} 个")
                return

            # 点击"去完成"
            if not _retry(lambda: find_and_click(TPL['quwancheng'], yuzhi=0.95), label="师门去完成"):
                log("师门任务：未找到去完成按钮")
                return

            # 等待完成
            if not _wait_completion(stop_event, task_num):
                return

            completed += 1
            log(f"师门任务 {task_num} 完成 ✓")
            if _wait(3, stop_event):
                break

        log(f"师门任务全部完成，共 {completed} 个")
        send_feishu_msg(f"✅ 师门任务完成，共 {completed} 个")
    except Exception as e:
        log(f"师门任务异常: {e}", "ERR")
        send_feishu_msg(f"❌ 师门任务异常: {e}")


def _wait_completion(stop_event, task_num):
    """等待师门任务完成，最长 2 分钟"""
    log(f"等待师门任务 {task_num} 完成...")
    timeout = 120
    import time
    start = time.time()
    while not stop_event.is_set():
        if time.time() - start > timeout:
            log(f"师门任务 {task_num} 等待超时", "WARN")
            return False
        if find_pic(TPL['shimen_complete'], yuzhi=0.85):
            log(f"检测到师门任务完成")
            _retry(lambda: find_and_click(TPL['shimen_confirm'], yuzhi=0.85), label="师门确认")
            if _wait(1, stop_event):
                return False
            _retry(lambda: find_and_click(TPL['shimen_x'], yuzhi=0.85), label="师门关闭")
            return True
        if _wait(5, stop_event):
            return False
    return False
