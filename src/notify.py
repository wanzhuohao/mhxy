"""飞书通知"""

import subprocess
import json
import os
import time

_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
_CONFIG = {}
if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
        _CONFIG = json.load(f)

FEISHU_CHAT_ID = _CONFIG.get('feishu_chat_id', '')
LARK_CLI_PATH = _CONFIG.get('lark_cli_path', 'lark-cli')

# 容错参数：最多重试 3 次（含首次），间隔 2 秒，单次超时 30 秒
_MAX_ATTEMPTS = 3
_RETRY_INTERVAL = 2
_TIMEOUT = 30


def _decode(b):
    """安全解码子进程输出，UTF-8 优先，失败回退 GBK+replace 避免二次异常"""
    for enc in ('utf-8', 'gbk'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode('utf-8', errors='replace')


def send_feishu_msg(text):
    """发送飞书消息，未配置时静默跳过。失败重试 3 次，全部失败仅告警不抛异常"""
    if not FEISHU_CHAT_ID:
        return
    cmd = [LARK_CLI_PATH, 'im', '+messages-send',
           '--chat-id', FEISHU_CHAT_ID, '--as', 'bot', '--text', text]
    last_err = ''
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=_TIMEOUT, shell=False)
            if result.returncode == 0:
                return
            last_err = _decode(result.stderr or result.stdout).strip()
            print(f"[WARN] 飞书通知失败(第{attempt}次): {last_err}")
        except subprocess.TimeoutExpired:
            last_err = f"超时({_TIMEOUT}s)"
            print(f"[WARN] 飞书通知{last_err}(第{attempt}次)")
        except FileNotFoundError as e:
            # lark-cli 不在 PATH 或路径错，重试也没用，直接告警退出
            print(f"[WARN] 飞书通知未找到 lark-cli: {e}")
            return
        except Exception as e:
            last_err = str(e)
            print(f"[WARN] 飞书通知异常(第{attempt}次): {e}")
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_RETRY_INTERVAL)
    print(f"[ERROR] 飞书通知全部失败，已放弃: {last_err}")
