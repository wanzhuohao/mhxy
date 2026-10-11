"""按自然日记录各游戏窗口的日常任务完成状态（轻量版，供趣闻鉴赏等每日任务跳过已做窗口）。"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

# 存储到项目根目录，与 window.json 同级（运行时数据，不提交 git）
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "daily-progress.json"

_lock = threading.RLock()


class DailyProgressStore:
    """持久化「日期 + 任务 + 窗口」的完成状态。"""

    def __init__(self, path: Path | str = DEFAULT_PATH):
        self.path = Path(path)

    @staticmethod
    def today() -> str:
        return datetime.now().date().isoformat()

    def completed_indices(self, task_id, windows=None, *, day=None):
        """返回已完成窗口的 0 基索引集合；优先用句柄匹配，句柄变化后回退到槽位。"""
        day = day or self.today()
        with _lock:
            records = (
                self._load()
                .get("days", {})
                .get(day, {})
                .get("tasks", {})
                .get(task_id, {})
                .get("windows", {})
            )

        if windows is None:
            return {
                int(slot) - 1
                for slot, record in records.items()
                if str(slot).isdigit() and record.get("status") == "completed"
            }

        ordered_windows = list(windows)
        hwnd_to_index = {
            int(hwnd): index for index, (hwnd, _rect) in enumerate(ordered_windows)
        }
        matched = set()
        for slot, record in records.items():
            if record.get("status") != "completed":
                continue
            hwnd = record.get("hwnd")
            if hwnd is not None and int(hwnd) in hwnd_to_index:
                matched.add(hwnd_to_index[int(hwnd)])
            elif str(slot).isdigit():
                index = int(slot) - 1
                if 0 <= index < len(ordered_windows):
                    matched.add(index)
        return matched

    def mark_completed(self, task_id, index, *, hwnd=None, rect=None, source="detected", day=None):
        day = day or self.today()
        slot = str(int(index) + 1)
        with _lock:
            payload = self._load()
            days = payload.setdefault("days", {})
            task = days.setdefault(day, {}).setdefault("tasks", {}).setdefault(task_id, {})
            windows = task.setdefault("windows", {})
            windows[slot] = {
                "status": "completed",
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "source": source,
                "hwnd": int(hwnd) if hwnd is not None else None,
                "rect": list(map(int, rect)) if rect is not None else None,
            }
            task["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._prune(days)
            self._save(payload)

    def _load(self):
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("daily progress root must be an object")
            payload.setdefault("version", 1)
            payload.setdefault("days", {})
            return payload
        except (OSError, ValueError, TypeError):
            return {"version": 1, "days": {}}

    def _save(self, payload):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    @staticmethod
    def _prune(days, keep=14):
        for old_day in sorted(days)[:-keep]:
            days.pop(old_day, None)


daily_progress = DailyProgressStore()
