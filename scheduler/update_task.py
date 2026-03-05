#!/usr/bin/env python3
"""
Agent 更新任务状态工具
用法：python3 update_task.py <task_id> <action> [feedback]
动作：
  - complete: 完成当前步骤，提交审核
  - pass: 审核通过
  - reject: 审核不通过，需要重做
  - done: 任务全部完成
示例：
  python3 update_task.py <id> complete
  python3 update_task.py <id> reject "代码有bug"
  python3 update_task.py <id> done
"""
import sys
import json

sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from db import db


def update_task(task_id: str, action: str, feedback: str = "") -> str:
    """更新任务状态"""
    
    task = db.get_task(task_id)
    if not task:
        return f"❌ 任务不存在: {task_id}"
    
    steps = task["steps"]
    current_step = task["current_step"]
    
    if action == "complete":
        # 完成当前步骤，待审核
        db.update_task_status(task_id, "待审核", action="完成处理")
        return f"✅ 已完成 {task['step']}，提交审核"
    
    elif action == "pass":
        # 审核通过，进入下一步
        if current_step < len(steps) - 1:
            next_step = steps[current_step + 1]
            db.update_step(task_id, next_step, current_step + 1)
            db.update_task_status(task_id, "待处理", action="审核通过")
            return f"✅ 审核通过 → 下一步: {next_step}"
        else:
            # 最后一步完成
            db.update_task_status(task_id, "已完成", action="审核通过")
            return f"✅ 全部步骤完成，任务已验收"
    
    elif action == "reject":
        # 审核不通过，回退
        db.update_task_status(task_id, "审核不通过", feedback=feedback, action="审核不通过")
        return f"❌ 审核不通过: {feedback}\n→ 将回退到上一步"
    
    elif action == "done":
        # CEO 验收完成
        db.update_task_status(task_id, "已验收", action="CEO验收")
        return f"✅ 任务已验收完成"
    
    else:
        return f"❌ 未知动作: {action}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    task_id = sys.argv[1]
    action = sys.argv[2]
    feedback = sys.argv[3] if len(sys.argv) > 3 else ""
    
    result = update_task(task_id, action, feedback)
    print(result)
