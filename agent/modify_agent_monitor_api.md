# 待执行
**最后更新时间:** 2026-02-23 12:44:13

**执行时间:** 2026-02-23 11:21:45

# 开发任务 - Agent Monitor API接口修改

## 🎯 任务目标

根据产品经理的重新设计需求，修改 `/api/stats` 接口，返回所有已配置的Agent信息，包括活动和空闲状态的Agent，以及任务队列信息。

## 📋 功能需求

### 1. API接口修改需求

#### 1.1 接口输出格式
当前接口只返回活动会话的Agent信息，需要扩展为：
```json
{
  "total_agents": 9,
  "active_agents": 1,
  "idle_agents": 8,
  "total_tasks": 0,
  "completed_tasks": 0,
  "pending_tasks": 0,
  "agents": [
    {
      "key": "agent:main:main",
      "name": "Main Agent",
      "type": "main",
      "status": "active",
      "session_active": true,
      "session_duration": "3m",
      "current_task": {
        "title": "与用户交互",
        "status": "running",
        "progress": 100,
        "duration": "3m"
      },
      "task_queue": [],
      "resource_usage": {
        "cpu": 0.1,
        "memory": 0.2
      }
    },
    {
      "key": "agent:trader:1",
      "name": "交易员",
      "type": "trader",
      "status": "idle",
      "session_active": false,
      "session_duration": "0m",
      "current_task": null,
      "task_queue": [],
      "resource_usage": {
        "cpu": 0,
        "memory": 0
      }
    },
    ...
  ]
}
```

#### 1.2 Agent信息字段
- **agent_key**: Agent的唯一标识符
- **agent_name**: Agent显示名称
- **agent_type**: Agent类型（main、trader、sre-engineer等）
- **status**: 状态（active/idle）
- **session_active**: 是否有活动会话
- **session_duration**: 会话持续时间
- **current_task**: 当前处理的任务信息
- **task_queue**: 任务队列
- **resource_usage**: 资源使用情况（CPU、内存）

### 2. 数据获取方法

#### 2.1 获取所有已配置的Agent
从配置文件 `/home/robin/.openclaw/openclaw.json` 的 `agents.list` 中获取所有Agent信息

#### 2.2 获取活动会话信息
从 `openclaw sessions list --json` 中获取会话信息，并与配置的Agent进行匹配

#### 2.3 任务信息获取
从任务管理系统中获取每个Agent的任务信息

### 3. 服务器端实现

#### 3.1 修改 `/api/stats` 接口
```python
# 在 server.py 中添加新的 API 接口
def handle_api_stats():
    # 获取所有配置的Agent
    all_agents = get_all_configured_agents()
    
    # 获取当前会话信息
    active_sessions = get_active_sessions()
    
    # 构建返回数据
    result = {
        "total_agents": len(all_agents),
        "active_agents": len(active_sessions),
        "idle_agents": len(all_agents) - len(active_sessions),
        "total_tasks": 0,
        "completed_tasks": 0,
        "pending_tasks": 0,
        "agents": []
    }
    
    for agent_config in all_agents:
        # 查找对应的会话信息
        session_info = find_session_info(agent_config, active_sessions)
        
        # 获取任务信息
        tasks_info = get_agent_tasks(agent_config['key'])
        
        # 构建Agent信息
        agent_data = {
            "key": agent_config['id'],
            "name": get_agent_name(agent_config['id']),
            "type": agent_config['id'],
            "status": "active" if session_info else "idle",
            "session_active": session_info is not None,
            "session_duration": get_duration(session_info),
            "current_task": tasks_info['current'],
            "task_queue": tasks_info['queue'],
            "resource_usage": get_resource_usage()
        }
        
        result['agents'].append(agent_data)
        
    return json.dumps(result)
```

#### 3.2 辅助函数
```python
def get_all_configured_agents():
    """从配置文件获取所有Agent配置"""
    config_file = '/home/robin/.openclaw/openclaw.json'
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    return config.get('agents', {}).get('list', [])

def get_active_sessions():
    """获取当前活跃的会话信息"""
    result = subprocess.run(
        ['openclaw', 'sessions', 'list', '--json'],
        capture_output=True, text=True, timeout=10
    )
    return json.loads(result.stdout) if result.returncode == 0 else []

def get_agent_tasks(agent_key):
    """获取Agent的任务信息"""
    # 目前任务信息从会话中推断
    return {
        "current": None,
        "queue": []
    }

def get_resource_usage():
    """获取资源使用情况"""
    return {
        "cpu": 0,
        "memory": 0
    }

def get_agent_name(agent_key):
    """获取Agent显示名称"""
    name_map = {
        "main": "Main Agent",
        "trader": "交易员",
        "sre-engineer": "SRE工程师",
        "strategy-expert": "策略专家",
        "product-manager": "产品经理",
        "dev-engineer": "开发工程师",
        "architect": "架构师",
        "qa-tester": "测试工程师",
        "marketing": "营销经理"
    }
    
    type_part = agent_key.split(':')[1]
    return name_map.get(type_part, type_part)
```

### 4. 错误处理

- 配置文件读取失败
- 会话信息获取失败
- 任务信息获取失败
- 资源使用信息获取失败

## 📅 开发时间表

### 阶段1：API接口修改（1天）
- 获取所有配置的Agent信息
- 匹配活动会话和Agent配置
- 完善Agent信息展示

### 阶段2：任务信息集成（1天）
- 任务管理系统集成
- 任务队列信息获取
- 任务状态展示

### 阶段3：性能优化（0.5天）
- 缓存机制优化
- 异步处理
- 接口响应时间优化

### 阶段4：测试验证（0.5天）
- 接口功能测试
- 数据一致性验证
- 性能测试

## 📄 文件修改位置

**主要修改文件：**
- `/home/robin/github/agent-monitor/server.py` - 服务器端API接口
- `/home/robin/github/agent-monitor/index.html` - 前端页面（需要配合产品经理的设计）

**辅助文件：**
- `/home/robin/.openclaw/workspace-dev/agent/task_creation_notification.md` - 任务通知
- `/home/robin/.openclaw/workspace-dev/agent/test_api.py` - 测试脚本

## 🎯 验收标准

### 功能验收
- [ ] API返回所有9个已配置的Agent信息
- [ ] 正确区分活动和空闲Agent
- [ ] 显示当前任务和任务队列信息
- [ ] 包含资源使用情况信息

### 性能验收
- [ ] 接口响应时间 < 2秒
- [ ] 资源使用率 < 0.1%
- [ ] 并发处理能力 > 100次/秒

### 测试验收
- [ ] 接口功能测试通过
- [ ] 数据一致性验证通过
- [ ] 边界条件测试通过

## 📋 下一步

1. 开始修改 `/api/stats` 接口
2. 实现Agent信息获取和匹配
3. 集成任务管理系统
4. 优化接口性能
5. 测试验证

---

**任务创建时间：** 2026-02-23  
**任务负责人：** 开发工程师  
**优先级：** 高
