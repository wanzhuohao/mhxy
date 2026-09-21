# 梦幻西游辅助工具

梦幻西游游戏辅助脚本，基于 Python + pyautogui 实现自动化操作。

## 技术栈

- Python 3.x
- pyautogui（键鼠自动化）
- tkinter（GUI 界面）
- OpenCV（图像匹配）
- lark-cli（飞书消息通知，可选）

## 项目结构

```
mhxy/
├── src/            # 源代码
│   ├── mhxy.py     # 主程序 GUI
│   ├── core.py     # 截图、模板匹配、重试
│   ├── context.py  # 窗口上下文、点击锁
│   ├── notify.py   # 飞书通知
│   ├── tasks/      # 任务模块
│   └── config.json # 配置文件（不提交）
├── templates/      # 模板图片
├── progress.md     # 开发进度
├── CLAUDE.md       # 项目说明
└── window.json    # 窗口位置配置
```

## 功能模块

| 功能 | 说明 |
|------|------|
| 组队/解散 | 组队（邀请4个好友）、解散队伍 |
| 副本 | 自动刷副本（连打、失败回城） |
| 领双/捉鬼 | 领双倍、无限捉鬼 |
| 师门任务 | 自动完成师门任务循环 |
| 宝图/挖图 | 宝图任务、挖宝图 |
| 秘境 | 自动刷秘境 |
| 押镖 | 自动押镖 |
| 三界/科举 | 三界答题、科举答题 |
| 领奖 | 领取奖励 |
| 刮刮乐 | 刮刮乐刮奖（含福利入口） |
| 帮派 | 打开帮派界面操作 |
| 回家 | 回长安城 |
| 出售 | 卖东西（商会出售） |
| 打工 | 打工加分 |
| 窗口管理 | 多窗口并行、位置记忆 |
| 飞书通知 | 任务开始/完成时发送飞书消息 |

> 任务按钮顺序以 `mhxy.py` 类属性 `_TASK_ORDER` 为唯一来源（按钮/一条龙/中途继续共用）。

## 安装依赖

```bash
pip install pyautogui opencv-python numpy
```

## 飞书通知配置（可选）

如需任务完成时接收飞书消息，需安装 lark-cli：

```bash
npm install -g @anthropic-ai/lark-cli
```

然后创建 `src/config.json`：

```json
{
  "feishu_chat_id": "你的飞书会话ID（oc_开头）",
  "lark_cli_path": "lark-cli 的完整路径"
}
```

## 注意事项

- 窗口标题都一样，排序用句柄不用标题

## 使用方式

运行 `src/mhxy.py` 启动 GUI 界面，选择功能后自动执行。

## 注意事项（Claude Code）

- **启动新 GUI 前必须先杀掉旧进程**：每次运行 `python mhxy.py` 之前，先执行以下命令杀掉旧进程（taskkill 在 bash 中不生效，必须用 wmic）：
  ```
  wmic process where "name='python.exe' and commandline like '%mhxy%'" call terminate
  ```
