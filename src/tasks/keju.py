"""科举答题任务"""

import datetime
from core import log
from tasks.dati import _dati_keju


def keju_start(stop_event):
    """科举答题：先判断时间"""
    now = datetime.datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=周一, 6=周日
    
    # 科举时间：周一到周五 且 17点后
    if weekday < 5 and hour >= 17:
        log(f"科举答题开始（{now.strftime('%H:%M')}）")
        _dati_keju(stop_event)
    else:
        log(f"科举答题：当前时间 {now.strftime('%H:%M')}，未到开放时间（需周一至周五17点后）")
