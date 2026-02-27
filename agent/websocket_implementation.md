# WebSocket实时更新功能实现

## 🎯 任务目标

实现WebSocket实时数据推送功能，避免agent监控页面整体刷新，实现增量更新机制。

## 📋 功能需求

### WebSocket服务器实现

#### 核心功能
- ✅ 建立WebSocket连接
- ✅ 处理连接管理
- ✅ 实现消息分发
- ✅ 添加心跳检测
- ✅ 断线重连机制

#### 服务器端代码
```python
# /home/robin/github/agent-monitor/server.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json
import asyncio
import random
import time
from datetime import datetime

app = FastAPI()

class WebSocketManager:
    def __init__(self):
        self.active_connections = []
        self.subscriptions = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        del self.subscriptions[websocket]
        
    async def subscribe(self, websocket: WebSocket, channel: str):
        self.subscriptions[websocket].add(channel)
        
    async def unsubscribe(self, websocket: WebSocket, channel: str):
        self.subscriptions[websocket].remove(channel)
        
    async def send_message(self, message: dict, channel: str):
        for websocket in self.active_connections:
            if channel in self.subscriptions[websocket]:
                await websocket.send_text(json.dumps(message))

manager = WebSocketManager()

@app.websocket("/ws/agent_monitor")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'subscribe':
                for channel in message['channels']:
                    await manager.subscribe(websocket, channel)
                    print(f"✅ 订阅成功: {channel}")
                    
            elif message['type'] == 'unsubscribe':
                for channel in message['channels']:
                    await manager.unsubscribe(websocket, channel)
                    print(f"✅ 取消订阅: {channel}")
                    
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")
    finally:
        manager.disconnect(websocket)
```

### WebSocket客户端实现

#### 前端代码
```javascript
// /home/robin/github/agent-monitor/static/js/websocket.js
class AgentMonitorWebSocket {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.callbacks = {};
        
        this.connect();
    }
    
    connect() {
        try {
            this.socket = new WebSocket(this.url);
            
            this.socket.onopen = () => {
                console.log('✅ WebSocket连接成功');
                this.reconnectAttempts = 0;
                this.subscribeToUpdates();
            };
            
            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleDataUpdate(data);
            };
            
            this.socket.onerror = (error) => {
                console.error('❌ WebSocket错误:', error);
                this.attemptReconnect();
            };
            
            this.socket.onclose = () => {
                console.log('🔌 WebSocket连接关闭');
                this.attemptReconnect();
            };
            
        } catch (error) {
            console.error('❌ 无法连接到服务器:', error);
            this.attemptReconnect();
        }
    }
    
    subscribeToUpdates() {
        const subscription = {
            type: 'subscribe',
            channels: ['agent_status', 'task_updates', 'system_stats']
        };
        this.send(subscription);
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }
    
    handleDataUpdate(data) {
        switch(data.type) {
            case 'agent_status_update':
                this.updateAgentStatus(data.payload);
                break;
            case 'task_status_update':
                this.updateTaskStatus(data.payload);
                break;
            case 'system_stats':
                this.updateSystemStats(data.payload);
                break;
        }
    }
    
    updateAgentStatus(agentData) {
        const agentElement = document.querySelector(`[data-agent-id="${agentData.id}"]`);
        if (agentElement) {
            agentElement.querySelector('.agent-status').textContent = agentData.status;
            agentElement.querySelector('.agent-status').className = `agent-status status-${agentData.status}`;
            agentElement.querySelector('.task-count').textContent = agentData.taskCount;
            
            agentElement.classList.add('updated');
            setTimeout(() => {
                agentElement.classList.remove('updated');
            }, 500);
        }
    }
    
    updateTaskStatus(taskData) {
        const taskElement = document.querySelector(`[data-task-id="${taskData.id}"]`);
        if (taskElement) {
            taskElement.querySelector('.task-status').textContent = taskData.status;
            taskElement.querySelector('.task-status').className = `task-status status-${taskData.status}`;
            
            const progressElement = taskElement.querySelector('.task-progress');
            if (progressElement && taskData.progress) {
                progressElement.style.width = `${taskData.progress}%`;
                progressElement.textContent = `${taskData.progress}%`;
            }
        }
    }
    
    updateSystemStats(stats) {
        document.querySelector('#total-agents').textContent = stats.total;
        document.querySelector('#online-agents').textContent = stats.online;
        document.querySelector('#active-agents').textContent = stats.active;
        document.querySelector('#idle-agents').textContent = stats.idle;
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('❌ 重连失败，停止尝试');
        }
    }
}
```

### 实时数据生成器

#### 数据生成器代码
```python
# /home/robin/github/agent-monitor/realtime_data.py
import asyncio
import random
import json
from datetime import datetime

class RealTimeDataGenerator:
    def __init__(self, manager):
        self.manager = manager
        self.running = False
        
    async def generate_data(self):
        while self.running:
            agent_data = {
                "type": "agent_status_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "id": f"agent_{random.randint(1, 9)}",
                    "name": f"Agent {random.randint(1, 9)}",
                    "status": random.choice(["running", "idle", "paused"]),
                    "taskCount": random.randint(0, 5),
                    "taskProgress": random.randint(0, 100)
                }
            }
            
            await self.manager.send_message(agent_data, "agent_status")
            
            task_data = {
                "type": "task_status_update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "id": f"task_{random.randint(1, 20)}",
                    "title": f"Task {random.randint(1, 20)}",
                    "status": random.choice(["pending", "running", "completed"]),
                    "priority": random.choice(["高", "中", "低"]),
                    "progress": random.randint(0, 100)
                }
            }
            
            await self.manager.send_message(task_data, "task_updates")
            
            await asyncio.sleep(random.uniform(1, 5))
            
    async def start(self):
        self.running = True
        await self.generate_data()
        
    async def stop(self):
        self.running = False
```

## 🎯 实施计划

### 阶段1：基础架构（1天）
- 建立WebSocket连接
- 实现连接管理
- 添加心跳机制

### 阶段2：数据分发（1天）
- 实时数据生成
- 增量更新算法
- 状态比较实现

### 阶段3：前端优化（1天）
- 增量更新管理器
- 动画过渡效果
- 响应式设计优化

### 阶段4：性能优化（0.5天）
- 防抖和缓冲
- 渲染优化
- 内存泄漏检测

## 📊 验收标准

### 功能验收

#### WebSocket连接
- ✅ 成功建立连接
- ✅ 断线重连机制
- ✅ 心跳检测

#### 实时更新
- ✅ 数据增量更新
- ✅ DOM操作优化
- ✅ 动画过渡效果

#### 响应式设计
- ✅ 支持移动端
- ✅ 布局自适应
- ✅ 触摸优化

### 性能验收

#### 渲染性能
- ✅ 避免不必要的重排重绘
- ✅ 虚拟DOM优化
- ✅ 动画流畅度

#### 内存使用
- ✅ 无内存泄漏
- ✅ 资源及时释放
- ✅ GC优化

#### 网络性能
- ✅ 最小化数据传输
- ✅ 增量数据压缩
- ✅ 重连机制优化

---
**任务创建时间**：2026-02-23
**任务负责人**：开发工程师
**优先级**：高
