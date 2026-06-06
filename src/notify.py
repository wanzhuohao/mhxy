"""飞书通知"""

import subprocess
import json
import os

_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
_CONFIG = {}
if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
        _CONFIG = json.load(f)

FEISHU_CHAT_ID = _CONFIG.get('feishu_chat_id', '')
LARK_CLI_PATH = _CONFIG.get('lark_cli_path', 'lark-cli')


def send_feishu_msg(text):
    """发送飞书消息，未配置时静默跳过"""
    if not FEISHU_CHAT_ID:
        return
    try:
        result = subprocess.run(
            [LARK_CLI_PATH, 'im', '+messages-send', '--chat-id', FEISHU_CHAT_ID, '--as', 'bot', '--text', text],
            capture_output=True, timeout=10, shell=True
        )
        if result.returncode != 0:
            print(f"[WARN] 飞书通知失败: {result.stderr.decode()}")
    except Exception as e:
        print(f"[WARN] 飞书通知异常: {e}")
