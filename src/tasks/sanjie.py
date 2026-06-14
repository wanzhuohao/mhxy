"""三界答题任务"""

import datetime
from core import log
from tasks.dati import _dati_sanjie


def sanjie_start(stop_event):
    """三界答题：先判断时间"""
    now = datetime.datetime.now()
    hour = now.hour
    
    # 三界答题时间：11点及以后
    if hour >= 11:
        log(f"三界答题开始（{now.strftime('%H:%M')}）")
        _dati_sanjie(stop_event)
    else:
        log(f"三界答题：当前时间 {now.strftime('%H:%M')}，未到开放时间（需11点后）")
