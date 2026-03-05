#!/usr/bin/env python3
"""
Agent 启动脚本 - 自动注册到调度系统
"""
import os
import sys
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.heartbeat_reporter import HeartbeatReporter, get_reporter

def main():
    # 获取 Agent ID
    agent_id = os.environ.get("AGENT_ID", "dev-engineer")
    
    # 创建并启动心跳上报器
    reporter = HeartbeatReporter(agent_id)
    
    # 初始注册
    reporter.report_idle()
    
    # 启动后台心跳
    reporter.start_background()
    
    print(f"✅ Agent {agent_id} 已启动并连接到调度系统")
    print(f"   心跳间隔: 30秒")
    print(f"   按 Ctrl+C 停止...")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        reporter.stop_background()
        print(f"⏹️ Agent {agent_id} 已停止")

if __name__ == "__main__":
    main()
