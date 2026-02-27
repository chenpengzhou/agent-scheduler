# Agent监控任务管理实现

## 🎯 任务目标

实现agent监控系统的任务管理功能，包括待办事项显示、任务优先级调整、直接操控agent功能。

## 📋 实现任务

### 1. 后端API开发

#### 任务管理API
- `/api/tasks/agent/{agent_id}`：获取agent待办事项
- `/api/tasks/<task_id>/priority`：更新任务优先级
- `/api/agents/{agent_id}/control`：控制agent操作

#### API实现
```python
# /home/robin/.openclaw/api/task_management.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models import db, Task, Agent

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/robin/.openclaw/agent_monitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route("/api/tasks/agent/<agent_id>")
def get_agent_tasks(agent_id):
    """获取agent待办事项"""
    tasks = Task.query.filter(
        Task.agent_id == agent_id,
        Task.status != "completed"
    ).order_by(Task.priority_order, Task.created_at).all()
    
    return jsonify({
        "agent": agent_id,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
            for task in tasks
        ],
        "total": len(tasks),
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/tasks/<task_id>/priority", methods=["PUT"])
def update_task_priority(task_id):
    """更新任务优先级"""
    priority = request.json.get("priority")
    
    task = Task.query.get(task_id)
    
    if not task:
        return jsonify({"success": False, "error": "任务不存在"}), 404
        
    task.priority = priority
    task.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({"success": True})

@app.route("/api/agents/<agent_id>/control", methods=["POST"])
def control_agent(agent_id):
    """控制agent操作"""
    action = request.json.get("action")
    
    agent = Agent.query.get(agent_id)
    
    if not agent:
        return jsonify({"success": False, "error": "Agent不存在"}), 404
        
    if action == "pause":
        agent.status = "pause"
    elif action == "resume":
        agent.status = "running"
    elif action == "restart":
        agent.status = "restarting"
        
    agent.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({"success": True})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8001, debug=True)
```

### 2. 前端开发

#### 任务管理组件
```javascript
// /home/robin/.openclaw/static/task_management.js
class TaskManagement extends React.Component {
    state = {
        selectedAgent: null,
        tasks: [],
        priorities: ["高", "中", "低"],
        agents: []
    }

    componentDidMount() {
        this.fetchAgents()
        this.fetchTasks()
    }

    fetchAgents() {
        fetch("/api/agents")
            .then(response => response.json())
            .then(data => this.setState({ agents: data.agents }))
    }

    fetchTasks(agentId) {
        fetch(`/api/tasks/agent/${agentId}`)
            .then(response => response.json())
            .then(data => this.setState({ tasks: data.tasks }))
    }

    updatePriority(taskId, priority) {
        fetch(`/api/tasks/${taskId}/priority`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ priority })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.fetchTasks(this.state.selectedAgent)
            }
        })
    }

    controlAgent(agentId, action) {
        fetch(`/api/agents/${agentId}/control`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ action })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.fetchAgents()
            }
        })
    }

    handleAgentSelect(agent) {
        this.setState({ selectedAgent: agent.id })
        this.fetchTasks(agent.id)
    }

    render() {
        return (
            <div className="task-management">
                {/* Agent列表 */}
                <div className="agent-list">
                    {this.state.agents.map(agent => (
                        <div 
                            key={agent.id}
                            className={`agent-item ${agent.id === this.state.selectedAgent ? 'active' : ''}`}
                            onClick={() => this.handleAgentSelect(agent)}
                        >
                            <h4>{agent.name}</h4>
                            <p>任务数: {agent.task_count}</p>
                        </div>
                    ))}
                </div>
                
                {/* 待办事项 */}
                <div className="task-list">
                    {this.state.tasks.map(task => (
                        <div key={task.id} className="task-item">
                            <div className="task-header">
                                <h4>{task.title}</h4>
                                <select 
                                    value={task.priority}
                                    onChange={(e) => this.updatePriority(task.id, e.target.value)}
                                >
                                    {this.state.priorities.map(p => (
                                        <option key={p} value={p}>{p}</option>
                                    ))}
                                </select>
                            </div>
                            <p>{task.description}</p>
                            <div className="task-meta">
                                <span className={`status-${task.status}`}>{task.status}</span>
                            </div>
                        </div>
                    ))}
                </div>
                
                {/* 控制按钮 */}
                {this.state.selectedAgent && (
                    <div className="control-panel">
                        <button 
                            onClick={() => this.controlAgent(this.state.selectedAgent, "pause")}
                            className="btn-pause"
                        >
                            ⏸️ 暂停
                        </button>
                        <button 
                            onClick={() => this.controlAgent(this.state.selectedAgent, "resume")}
                            className="btn-resume"
                        >
                            🚀 启动
                        </button>
                        <button 
                            onClick={() => this.controlAgent(this.state.selectedAgent, "restart")}
                            className="btn-restart"
                        >
                            🔄 重启
                        </button>
                    </div>
                )}
            </div>
        )
    }
}

// 渲染组件
ReactDOM.render(
    <TaskManagement />,
    document.getElementById("task-management-container")
)
```

### 3. 数据库设计

#### 数据模型
```python
# /home/robin/.openclaw/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Task(db.Model):
    __tablename__ = "tasks"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    agent_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="pending")
    priority = db.Column(db.String(10), default="中")
    priority_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class Agent(db.Model):
    __tablename__ = "agents"
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="running")
    task_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 🎯 验收标准

### 功能验收

#### 待办事项显示
- ✅ 显示每个agent的待办事项
- ✅ 支持分页和搜索
- ✅ 显示任务状态和优先级

#### 任务优先级调整
- ✅ 支持高/中/低优先级调整
- ✅ 任务拖拽排序
- ✅ 实时更新任务状态

#### Agent控制
- ✅ 支持暂停/启动/重启
- ✅ 任务执行控制
- ✅ 实时状态反馈

### 性能验收
- ✅ API响应时间 < 0.5秒
- ✅ 并发处理 > 100请求/秒
- ✅ 数据库查询优化

## 📅 开发计划

### 阶段1：API开发（1天）
- 待办事项API
- 任务优先级API  
- Agent控制API

### 阶段2：前端开发（2天）
- 待办事项列表
- 任务优先级调整
- Agent控制界面

### 阶段3：后端开发（2天）
- 任务管理功能
- Agent状态管理
- 事件通知系统

### 阶段4：测试优化（1天）
- 功能测试
- 性能优化
- 错误处理

---
**任务创建时间**：2026-02-23
**任务负责人**：开发工程师
**优先级**：高
