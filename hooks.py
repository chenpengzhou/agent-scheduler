"""
Agent Hook配置
在Agent启动时自动注册消息处理hook
"""

from .auto_trigger import process as auto_trigger_process

# Agent Hook配置
AGENT_HOOKS = {
    # 当收到消息时自动调用
    "on_message": auto_trigger_process,
}


def register_hooks(agent_name: str):
    """注册Agent的hook"""
    print(f"[Hooks] 为 {agent_name} 注册hook完成")
    return AGENT_HOOKS


def get_hook(name: str):
    """获取指定hook"""
    return AGENT_HOOKS.get(name)


# 示例：在Agent消息处理中使用
def handle_agent_message(agent_name: str, message: str):
    """处理Agent收到的消息"""
    # 自动触发
    result = auto_trigger_process(message, agent_name)
    
    if result:
        print(f"[Hooks] 自动触发成功: {result.get('action')}")
        return result
    
    return None
