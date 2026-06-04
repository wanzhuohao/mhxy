"""梦幻西游助手 CLI 入口"""

import argparse
import sys
import os

# 确保能导入同级模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.commands import (
    run_task,
    run_all_in_one,
    arrange_windows,
    launch_game,
    create_team,
    list_tasks,
)


def main():
    parser = argparse.ArgumentParser(
        prog='mhxy',
        description='梦幻西游助手 CLI',
    )
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 任务命令
    task_parser = subparsers.add_parser('run', help='运行指定任务')
    task_parser.add_argument('task', nargs='?', help='任务名称 (shimen/baotu/fuben/mijing/yabiao/watu/dati)')

    # 一条龙
    subparsers.add_parser('all', help='运行一条龙任务 (押镖→秘境)')

    # 窗口管理
    subparsers.add_parser('arrange', help='排列游戏窗口')

    launch_parser = subparsers.add_parser('launch', help='启动游戏客户端')
    launch_parser.add_argument('-n', '--count', type=int, default=1, help='启动数量 (默认 1)')

    subparsers.add_parser('team', help='自动组队')

    # 列出任务
    subparsers.add_parser('list', help='列出所有可用任务')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == 'run':
        if args.task is None:
            list_tasks()
        else:
            run_task(args.task)
    elif args.command == 'all':
        run_all_in_one()
    elif args.command == 'arrange':
        arrange_windows()
    elif args.command == 'launch':
        launch_game(args.count)
    elif args.command == 'team':
        create_team()
    elif args.command == 'list':
        list_tasks()


if __name__ == '__main__':
    main()
