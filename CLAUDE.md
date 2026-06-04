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
├── src/           # 源代码
│   ├── mhxy.py    # 主程序 GUI
│   ├── business.py # 业务逻辑
│   └── config.json # 配置文件（不提交）
├── templates/     # 模板图片
├── tool/          # 可复用脚本
└── window.json    # 窗口位置配置
```

## 功能模块

| 功能 | 说明 |
|------|------|
| 师门任务 | 自动完成师门任务循环 |
| 宝图任务 | 自动挖宝图 |
| 押镖/秘境/副本等 | 多种任务自动化 |
| 窗口管理 | 多窗口并行、位置记忆 |
| 飞书通知 | 任务开始/完成时发送飞书消息 |

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

## 使用方式

运行 `src/mhxy.py` 启动 GUI 界面，选择功能后自动执行。
