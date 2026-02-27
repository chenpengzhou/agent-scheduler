# 待执行
**最后更新时间:** 2026-02-23 12:44:13

**执行时间:** 2026-02-23 11:21:45

# API接口修复任务

## 📋 任务信息

**任务名称：** 修复Agent监控API接口问题  
**任务编号：** DM20260223-02  
**创建时间：** 2026-02-23 09:56:00  
**负责人：** 开发工程师Agent

## 🚨 问题分析

### 问题现象
当前`/api/stats`接口可能只返回一个agent信息，导致页面无法显示所有配置的agent。

### 接口问题定位
1. **agent数据获取**：可能未正确获取所有配置的agent列表
2. **状态判断**：可能未正确判断agent是否正在工作
3. **数据格式**：返回格式可能不符合页面期望

## 📋 修复方案

### 1. 检查API接口实现
```python
# 检查当前API接口实现
def handle_api_stats():
    # 当前可能只返回一个agent信息
    agents = [
        {'id': 'main', 'name': 'Main Agent', 'status': 'working'}
    ]
    return jsonify({'agents': agents})
```

### 2. 修复API接口
```python
# 修复后的API接口实现
def handle_api_stats():
    # 获取所有配置的agent列表
    all_agents = get_all_configured_agents()
    
    # 获取活动的会话信息
    active_sessions = get_active_sessions()
    
    # 构建完整的agent信息
    agents = []
    for agent_config in all_agents:
        agent = {
            'id': agent_config['id'],
            'name': agent_config.get('name', agent_config['id']),
            'status': 'working' if is_agent_working(agent_config['id'], active_sessions) else 'idle'
        }
        agents.append(agent)
        
    return jsonify({'agents': agents})
```

### 3. 优化状态判断逻辑
```python
# 优化的agent状态判断
def is_agent_working(agent_id, active_sessions):
    # 检查是否有活动会话
    for session in active_sessions:
        if session['agent_id'] == agent_id:
            return True
    
    # 检查是否有正在执行的任务
    if has_active_tasks(agent_id):
        return True
        
    return False
```

## 📅 开发时间表

| 阶段 | 时间 | 工作内容 |
|------|------|----------|
| 1. 接口分析 | 1小时 | 检查当前API接口实现 |
| 2. 代码修改 | 2小时 | 修改API接口实现 |
| 3. 功能测试 | 1小时 | 测试API接口功能 |
| 4. 性能优化 | 0.5小时 | 优化接口响应速度 |
| 5. 部署上线 | 0.5小时 | 部署到生产环境 |

**总耗时：** 5小时

## 📈 预期结果

### 修复后的API接口
- 返回所有9个配置的agent信息
- 正确区分"working"和"idle"状态
- 包含agent的详细信息（如任务执行状态）
- 支持CORS跨域请求

### 系统响应
- 响应时间 < 500ms
- 返回格式符合JSON标准
- 错误处理和重试机制

## 🔍 测试和验证

### 接口测试
```bash
# 使用curl测试API接口
curl -X GET "http://localhost:3000/api/stats" -H "accept: application/json"
```

### 页面验证
```bash
# 检查页面是否显示所有agent
curl -X GET "http://localhost:3000/" -I
```

## 📞 协作要求

### 需要协调的Agent
- **SRE工程师Agent**：服务器部署和运维
- **测试工程师Agent**：功能测试和性能测试

### 开发环境
- Node.js服务器
- Express框架
- SQLite数据库

---
**任务负责人：** 开发工程师Agent  
**创建时间：** 2026-02-23 09:56:00  
**执行要求：** 请按照上述方案修复API接口问题，完成后及时反馈修复进度。
