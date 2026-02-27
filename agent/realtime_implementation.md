# 开发工程师任务 - 实时刷新机制实现

## 🎯 任务目标

根据架构师的方案设计，实现实时刷新机制的具体代码。

## 📋 实现内容

### 1. 服务器端实现

#### 1.1 WebSocket服务器
**文件位置**：`/home/robin/github/agent-monitor/server.py`

**实现方案**：
```python
import asyncio
import websockets
import json
import time
import os

class WebSocketServer:
    def __init__(self, port=8001):
        self.port = port
        self.clients = set()
        self.lock = asyncio.Lock()
        
    async def handle_connection(self, websocket, path):
        self.clients.add(websocket)
        
        try:
            # 发送初始数据
            initial_data = await self.get_initial_data()
            await websocket.send(json.dumps({
                "type": "initial",
                "data": initial_data
            }))
            
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
            
        finally:
            self.clients.remove(websocket)
            
    async def send_data_updates(self):
        while True:
            try:
                updates = await self.get_data_updates()
                
                if updates:
                    data = {
                        "type": "update",
                        "timestamp": int(time.time() * 1000),
                        "data": updates
                    }
                    
                    for client in list(self.clients):
                        try:
                            await client.send(json.dumps(data))
                        except:
                            self.clients.remove(client)
                            
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Data update error: {e}")
                await asyncio.sleep(1)
                
    async def start_server(self):
        server = await websockets.serve(
            self.handle_connection, '0.0.0.0', self.port
        )
        
        asyncio.create_task(self.send_data_updates())
        return server
```

#### 1.2 数据更新检测
**文件位置**：`/home/robin/github/agent-monitor/utils.py`

**实现方案**：
```python
def detect_changes(current_data, previous_data):
    """检测数据变化"""
    changes = {
        'agents': [],
        'stats': None
    }
    
    # 统计变化
    if current_data['total'] != previous_data['total']:
        changes['stats'] = {
            'total': current_data['total'],
            'online': current_data['online'],
            'offline': current_data['offline']
        }
        
    # 检测Agent状态变化
    current_agents = {agent['key']: agent for agent in current_data['agents']}
    previous_agents = {agent['key']: agent for agent in previous_data['agents']}
    
    # 检查新增Agent
    for key, agent in current_agents.items():
        if key not in previous_agents:
            changes['agents'].append({
                'key': key,
                'operation': 'add',
                'data': agent
            })
            
    # 检查删除Agent
    for key, agent in previous_agents.items():
        if key not in current_agents:
            changes['agents'].append({
                'key': key,
                'operation': 'remove'
            })
            
    # 检查Agent信息变化
    for key, current in current_agents.items():
        if key in previous_agents:
            previous = previous_agents[key]
            
            if current['online'] != previous['online']:
                changes['agents'].append({
                    'key': key,
                    'operation': 'update',
                    'data': {
                        'key': key,
                        'online': current['online'],
                        'status': current['status']
                    }
                })
                
    return changes
```

### 2. 前端实现

#### 2.1 实时刷新模块
**文件位置**：`/home/robin/github/agent-monitor/realtime.js`

**实现方案**：
```javascript
class RealTimeMonitor {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
        this.reconnectDelay = 2000;
        this.cache = new DataCache();
        this.renderer = new RealTimeRenderer();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const port = 8001;
        const url = `${protocol}://${window.location.hostname}:${port}/updates`;
        
        this.socket = new WebSocket(url);
        
        this.socket.onopen = () => {
            console.log('WebSocket连接成功');
            this.reconnectAttempts = 0;
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket连接关闭');
            this.reconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'initial':
                this.renderer.update(data.data);
                break;
                
            case 'update':
                this.renderer.update(data.data);
                break;
                
            case 'error':
                console.error('服务器错误:', data.message);
                break;
        }
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnects) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnects})`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('重连次数已达上限');
        }
    }
}
```

#### 2.2 增量更新渲染
**文件位置**：`/home/robin/github/agent-monitor/realtime.js`

**实现方案**：
```javascript
class RealTimeRenderer {
    constructor() {
        this.cache = new DataCache();
    }
    
    update(data) {
        const changes = this.cache.update(data);
        
        if (changes.added) {
            changes.added.forEach(agent => this.renderAgent(agent));
        }
        
        if (changes.updated) {
            changes.updated.forEach(agent => this.updateAgent(agent));
        }
        
        if (changes.removed) {
            changes.removed.forEach(key => this.removeAgent(key));
        }
        
        this.updateStats(data.total, data.online, data.offline);
    }
    
    renderAgent(agent) {
        const container = document.getElementById('agentsGrid');
        const card = this.createAgentCard(agent);
        container.appendChild(card);
    }
    
    updateAgent(agent) {
        const container = document.getElementById(`agent-${agent.key}`);
        
        if (!container) {
            this.renderAgent(agent);
            return;
        }
        
        // 更新状态
        const statusBadge = container.querySelector('.status-badge');
        if (statusBadge) {
            const isOnline = agent.online;
            statusBadge.className = `status-badge ${isOnline ? 'online' : 'offline'}`;
            statusBadge.textContent = isOnline ? '在线' : '离线';
            
            this.animateUpdate(statusBadge);
        }
    }
    
    animateUpdate(element) {
        element.style.transform = 'scale(1.05)';
        element.style.transition = 'all 0.3s ease';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 300);
    }
}
```

### 3. 集成到现有系统

#### 3.1 服务器端集成
**文件位置**：`/home/robin/github/agent-monitor/server.py`

**实现方案**：
```python
# 在现有服务器中集成WebSocket
from websocket_server import WebSocketServer

class AgentHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stats':
            self.send_stats()
        elif self.path == '/':
            self.serve_index()
        else:
            self.send_error(404)

# 启动服务器
if __name__ == "__main__":
    print(f"🚀 Agent Monitor: http://localhost:{PORT}")
    print(f"🚀 WebSocket: ws://localhost:8001")
    
    # 启动WebSocket服务器
    ws_server = WebSocketServer(8001)
    asyncio.create_task(ws_server.start_server())
    
    with socketserver.TCPServer(("", PORT), AgentHandler) as httpd:
        httpd.serve_forever()
```

#### 3.2 前端集成
**文件位置**：`/home/robin/github/agent-monitor/index.html`

**实现方案**：
```javascript
// 在页面加载完成后启动
document.addEventListener('DOMContentLoaded', function() {
    // 启动实时监控
    const realtimeMonitor = new RealTimeMonitor();
    realtimeMonitor.connect();
    
    // 启动传统刷新作为后备方案
    const fallbackRefresh = setInterval(() => {
        if (!realtimeMonitor.socket || realtimeMonitor.socket.readyState !== WebSocket.OPEN) {
            loadData();
        }
    }, 60000); // 60秒作为后备刷新
    
    // 清理资源
    window.addEventListener('beforeunload', () => {
        realtimeMonitor.close();
        clearInterval(fallbackRefresh);
    });
});
```

## 📅 开发时间表

### 阶段1：服务器端实现（2天）
- WebSocket服务器实现
- 数据更新检测算法
- 服务器端集成

### 阶段2：前端实现（2天）  
- 前端实时刷新逻辑
- 增量更新渲染
- 前端集成

### 阶段3：测试和优化（1天）
- 功能测试
- 性能优化
- 边界条件测试

## 📄 文件修改位置

**主要修改文件**：
- `/home/robin/github/agent-monitor/server.py` - 服务器端
- `/home/robin/github/agent-monitor/index.html` - 前端页面
- `/home/robin/github/agent-monitor/realtime.js` - 实时刷新模块
- `/home/robin/github/agent-monitor/utils.py` - 工具函数

**新增文件**：
- `/home/robin/github/agent-monitor/websocket_server.py` - WebSocket服务器
- `/home/robin/github/agent-monitor/realtime.css` - 实时刷新样式

## 🎯 代码质量标准

### 架构设计标准
- 清晰的模块划分
- 低耦合、高内聚原则
- 可扩展性和可维护性
- 错误处理和日志记录

### 代码质量标准
- 命名规范一致性
- 代码可读性和文档化
- 性能优化和内存管理
- 安全性和权限控制

## 📋 验收标准

### 功能验收
- [ ] WebSocket连接成功
- [ ] 实时数据推送正常
- [ ] 局部更新效果良好
- [ ] 离线状态保持稳定

### 性能验收
- [ ] 页面刷新次数减少90%
- [ ] 网络流量减少80%
- [ ] 响应时间 < 1秒
- [ ] 内存使用保持稳定

### 可靠性验收
- [ ] 自动重连功能正常
- [ ] 错误处理和恢复
- [ ] 网络抖动处理

### 安全验收
- [ ] 数据传输加密
- [ ] 连接验证
- [ ] 防止XSS攻击

---

**任务创建时间**：2026-02-23  
**任务负责人**：开发工程师  
**优先级**：高
