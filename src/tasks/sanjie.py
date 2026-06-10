"""三界答题任务"""

from tasks.dati import _dati_sanjie


def sanjie_start(stop_event):
    """三界答题"""
    _dati_sanjie(stop_event)
