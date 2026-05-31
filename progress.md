# mhxy 开发进度

## 待办

- 无

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
