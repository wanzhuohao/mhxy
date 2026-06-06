"""任务模块，导出所有任务函数"""

from tasks.shimen import shimen_start
from tasks.baotu import baotu_start
from tasks.watu import watu_start
from tasks.mijing import mijing_start
from tasks.yabiao import yabiao_start
from tasks.fuben import fuben_start
from tasks.dati import dati_start
from tasks.zhuogui import zhuogui_start

# 独立型任务：每个窗口各跑各的
INDEPENDENT_TASKS = {'shimen', 'baotu', 'watu', 'mijing', 'yabiao', 'dati'}

# 组队型任务：只在窗口 1（队长）执行
TEAM_TASKS = {'fuben', 'zhuogui'}

TASK_FUNCS = {
    'shimen': shimen_start,
    'baotu': baotu_start,
    'watu': watu_start,
    'mijing': mijing_start,
    'yabiao': yabiao_start,
    'fuben': fuben_start,
    'dati': dati_start,
    'zhuogui': zhuogui_start,
}
