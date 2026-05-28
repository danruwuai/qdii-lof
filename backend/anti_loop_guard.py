"""anti_loop_guard.py：防止 Claude 陷入重复操作循环的守护机制

使用方法：
1. 在执行可能重复的操作前，调用 check_and_record() 检查是否重复
2. 如果重复次数超过阈值，抛出异常终止
3. 每次成功操作后调用 record_success() 重置计数器

示例：
    from anti_loop_guard import LoopGuard

    guard = LoopGuard("deploy_worker", max_repeats=3)
    guard.check_and_record()  # 如果重复超过3次，抛出异常
    # ... 执行部署操作 ...
    guard.record_success()  # 操作成功，重置计数器
"""

import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# 确保 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

GUARD_DIR = Path(__file__).parent / ".guard"
GUARD_FILE = GUARD_DIR / "loop_state.json"
DEFAULT_MAX_REPEATS = 3


def _load_state() -> dict:
    """加载守护状态"""
    GUARD_DIR.mkdir(exist_ok=True)
    if GUARD_FILE.exists():
        with open(GUARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    """保存守护状态"""
    GUARD_DIR.mkdir(exist_ok=True)
    with open(GUARD_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _hash_key(operation: str) -> str:
    """生成操作哈希键"""
    return hashlib.md5(operation.encode()).hexdigest()[:12]


class LoopGuard:
    """循环检测守护器"""

    def __init__(self, operation: str, max_repeats: int = DEFAULT_MAX_REPEATS, window_minutes: int = 30):
        """
        Args:
            operation: 操作名称（如 "deploy_worker", "read_file", "git_push"）
            max_repeats: 最大允许重复次数
            window_minutes: 时间窗口（分钟），超过窗口后计数器重置
        """
        self.operation = operation
        self.key = _hash_key(operation)
        self.max_repeats = max_repeats
        self.window = timedelta(minutes=window_minutes)

    def check_and_record(self) -> bool:
        """
        检查是否重复操作，并记录本次尝试。

        Returns:
            True 表示可以继续执行，False 表示应该停止

        Raises:
            RuntimeError: 当重复次数超过阈值时抛出
        """
        state = _load_state()
        now = datetime.now().isoformat()

        entry = state.get(self.key, {})
        last_time = entry.get("last_time")
        count = entry.get("count", 0)

        # 检查时间窗口是否过期
        if last_time:
            elapsed = datetime.now() - datetime.fromisoformat(last_time)
            if elapsed > self.window:
                # 窗口过期，重置计数器
                count = 0

        count += 1

        if count > self.max_repeats:
            msg = (
                f"[LOOP DETECTED] 循环检测触发!\n"
                f"操作: {self.operation}\n"
                f"重复次数: {count} / {self.max_repeats}\n"
                f"时间窗口: {self.window}\n"
                f"建议: 停止当前操作，重新评估策略，或手动清除 .guard/loop_state.json"
            )
            # 记录到文件
            state[self.key] = {
                "last_time": now,
                "count": count,
                "blocked": True,
                "blocked_at": now,
            }
            _save_state(state)
            raise RuntimeError(msg)

        # 记录本次尝试
        state[self.key] = {
            "last_time": now,
            "count": count,
            "blocked": False,
        }
        _save_state(state)

        return True

    def record_success(self):
        """操作成功，重置计数器"""
        state = _load_state()
        state[self.key] = {
            "last_time": datetime.now().isoformat(),
            "count": 0,
            "success": True,
        }
        _save_state(state)

    def status(self) -> dict:
        """获取当前状态"""
        state = _load_state()
        entry = state.get(self.key, {})
        return {
            "operation": self.operation,
            "count": entry.get("count", 0),
            "last_time": entry.get("last_time"),
            "blocked": entry.get("blocked", False),
            "max_repeats": self.max_repeats,
        }


def reset_guard(operation: str = None):
    """重置守护状态

    Args:
        operation: 指定操作名称，None 则重置全部
    """
    state = _load_state()
    if operation:
        key = _hash_key(operation)
        state.pop(key, None)
    else:
        state = {}
    _save_state(state)


def print_guard_status():
    """打印所有守护状态"""
    state = _load_state()
    if not state:
        print("[OK] 无活跃的循环守护记录")
        return

    print("[GUARD] 循环守护状态：")
    print("-" * 60)
    for key, entry in state.items():
        if entry.get("blocked"):
            status = "[X] BLOCKED"
        elif entry.get("success"):
            status = "[OK] SUCCESS"
        else:
            status = "[~] ACTIVE"
        print(f"  {status}  key={key}  count={entry.get('count', 0)}  "
              f"last={entry.get('last_time', 'N/A')}")
    print("-" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print_guard_status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "check":
        op = sys.argv[2] if len(sys.argv) > 2 else "default"
        guard = LoopGuard(op)
        try:
            guard.check_and_record()
            print(f"[OK] 操作 '{op}' 允许执行 (计数: {guard.status()['count']})")
        except RuntimeError as e:
            print(str(e))
            sys.exit(1)

    elif cmd == "success":
        op = sys.argv[2] if len(sys.argv) > 2 else "default"
        guard = LoopGuard(op)
        guard.record_success()
        print(f"[OK] 操作 '{op}' 成功，计数器已重置")

    elif cmd == "reset":
        op = sys.argv[2] if len(sys.argv) > 2 else None
        reset_guard(op)
        if op is None:
            print("[OK] 守护状态已重置全部")
        else:
            print(f"[OK] 守护状态已重置: {op}")

    elif cmd == "status":
        print_guard_status()

    else:
        print(f"未知命令: {cmd}")
        print("用法: python anti_loop_guard.py [check|success|reset|status] [operation_name]")
