"""任务模块，导出所有任务函数"""

from tasks.shimen import shimen_start
from tasks.baotu import baotu_start
from tasks.watu import watu_start
from tasks.mijing import mijing_start
from tasks.yabiao import yabiao_start
from tasks.fuben import fuben_start
from tasks.dati import dati_start
from tasks.zhuogui import zhuogui_start, ling_shuang_start
from tasks.jiesan import jiesan_start
from tasks.zudui import zudui_start
from tasks.sanjie import sanjie_start
from tasks.keju import keju_start
from tasks.lingjiang import lingjiang_start
from tasks.guagua import guagua_start
from tasks.bangpai import bangpai_start
from tasks.huijia import huijia_start
from tasks.maidongxi import maidongxi_start
from tasks.shiyonggongju import shiyonggongju_start

# 组队型任务：全屏截图模式，只执行一次（已包含所有窗口的逻辑）
TEAM_TASKS = {'fuben', 'zhuogui', 'lingshuang', 'shimen', 'baotu', 'watu', 'jiesan', 'zudui', 
              'lingjiang', 'mijing', 'yabiao', 'dati', 'sanjie', 'keju', 'guagua', 'bangpai', 'huijia',
              'maidongxi', 'shiyonggongju'}

TASK_FUNCS = {
    'shimen': shimen_start,
    'baotu': baotu_start,
    'watu': watu_start,
    'mijing': mijing_start,
    'yabiao': yabiao_start,
    'fuben': fuben_start,
    'dati': dati_start,
    'zhuogui': zhuogui_start,
    'lingshuang': ling_shuang_start,
    'jiesan': jiesan_start,
    'zudui': zudui_start,
    'sanjie': sanjie_start,
    'keju': keju_start,
    'lingjiang': lingjiang_start,
    'guagua': guagua_start,
    'bangpai': bangpai_start,
    'huijia': huijia_start,
    'maidongxi': maidongxi_start,
    'shiyonggongju': shiyonggongju_start,
}
