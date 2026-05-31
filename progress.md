# mhxy 开发进度

## 待办

- 无

## 2026-05-31 线程安全 + 安全修复

- toggle_task 按钮 300ms 防抖，防止快速双击启动多线程
- launch_game_five_times 移到后台线程，GUI 不再冻结 12 秒
- toggle_zhuogui 按钮防抖 + join 移到后台线程
- FAILSAFE 恢复为 True（鼠标移到左上角触发紧急停止）
- fuben_start 硬编码坐标改为 FUBEN_REGION 偏移
- create_team 添加函数文档说明坐标假设
- .gitignore 补充 screen.png

## 2026-05-31 代码迁移与全面优化

- 从 PycharmProjects/1 迁移到独立文件夹，保留原文件不动
- business.py：4个重复匹配函数统一为 find_pic/find_and_click/find_and_click_offset，模板预加载
- mhxy.py：数据驱动按钮创建，统一 toggle_task 方法，深色主题 UI
- 添加日志框（TextRedirector），日志带时间戳
- 窗口位置/大小记忆（window.json）
- 添加置顶/取消置顶切换按钮
- 抓点+分辨率合并为两个小按钮共占一格
- 按钮顺序调整：捉鬼/副本/秘境/押镖/挖图/答题
- 移除师门/宝图/帮派/跑环（游戏内已自动或不需要）
- 添加 .gitignore，移除 __pycache__ 跟踪
