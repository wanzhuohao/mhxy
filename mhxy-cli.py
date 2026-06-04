#!/usr/bin/env python3
"""梦幻西游助手 CLI 启动脚本"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from cli.main import main

if __name__ == '__main__':
    main()
