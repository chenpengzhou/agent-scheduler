# Agent监控页面实时更新优化

## 🎯 任务目标

实现agent监控页面的实时更新优化，避免页面整体刷新，使用局部更新和WebSocket实时推送数据。

## 📋 功能需求

### 1. 实时数据更新

#### 功能说明
- 使用WebSocket实时推送数据更新
- 支持增量更新，只更新变化的部分
- 避免页面整体刷新

#### 技术实现
```javascript
// WebSocket连接管理
class WebSocketManager {
    constructor(url) {
        this.url = url
        this.socket = null
        this.reconnectAttempts = 0
        this.maxReconnectAttempts = 5
        this.reconnectDelay = 3000
    }
    
    connect() {
        try {
            this.socket = new WebSocket(this.url)
            
            this.socket.onopen = () => {
                console.log('✅ WebSocket连接成功')
                this.reconnectAttempts = 0
                this.subscribeToUpdates()
            }
            
            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data)
                this.handleDataUpdate(data)
            }
            
            this.socket.onerror = (error) => {
                console.error('❌ WebSocket错误:', error)
                this.attemptReconnect()
            }
            
            this.socket.onclose = () => {
                console.log('🔌 WebSocket连接关闭')
                this.attemptReconnect()
            }
            
        } catch (error) {
            console.error('❌ 无法连接到服务器:', error)
            this.attemptReconnect()
        }
    }
    
    subscribeToUpdates() {
        const subscription = {
            type: 'subscribe',
            channels: ['agent_status', 'task_updates', 'system_stats']
        }
        this.send(subscription)
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data))
        }
    }
    
    handleDataUpdate(data) {
        switch(data.type) {
            case 'agent_status_update':
                this.updateAgentStatus(data.payload)
                break
            case 'task_status_update':
                this.updateTaskStatus(data.payload)
                break
            case 'system_stats':
                this.updateSystemStats(data.payload)
                break
        }
    }
    
    updateAgentStatus(agentData) {
        // 局部更新agent状态
        const agentElement = document.querySelector(`[data-agent-id="${agentData.id}"]`)
        if (agentElement) {
            agentElement.querySelector('.agent-status').textContent = agentData.status
            agentElement.querySelector('.agent-status').className = `agent-status status-${agentData.status}`
            agentElement.querySelector('.task-count').textContent = agentData.taskCount
            
            // 添加更新动画
            agentElement.classList.add('updated')
            setTimeout(() => {
                agentElement.classList.remove('updated')
            }, 500)
        }
    }
    
    updateTaskStatus(taskData) {
        // 局部更新任务状态
        const taskElement = document.querySelector(`[data-task-id="${taskData.id}"]`)
        if (taskElement) {
            taskElement.querySelector('.task-status').textContent = taskData.status
            taskElement.querySelector('.task-status').className = `task-status status-${taskData.status}`
            
            // 任务进度更新
            const progressElement = taskElement.querySelector('.task-progress')
            if (progressElement && taskData.progress) {
                progressElement.style.width = `${taskData.progress}%`
                progressElement.textContent = `${taskData.progress}%`
            }
        }
    }
    
    updateSystemStats(stats) {
        // 局部更新系统统计
        document.querySelector('#total-agents').textContent = stats.total
        document.querySelector('#online-agents').textContent = stats.online
        document.querySelector('#active-agents').textContent = stats.active
        document.querySelector('#idle-agents').textContent = stats.idle
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++
            console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
            
            setTimeout(() => {
                this.connect()
            }, this.reconnectDelay)
        } else {
            console.error('❌ 重连失败，停止尝试')
        }
    }
}
```

### 2. 增量更新机制

#### 功能说明
- 只更新变化的数据，避免不必要的DOM操作
- 使用虚拟DOM优化
- 支持动画过渡效果

#### 技术实现
```javascript
// 增量更新管理器
class IncrementalUpdateManager {
    constructor() {
        this.previousState = null
        this.currentState = null
    }
    
    update(newState) {
        this.previousState = this.currentState
        this.currentState = newState
        
        if (!this.previousState) {
            this.renderInitialState(newState)
        } else {
            this.applyIncrementalUpdate(this.previousState, newState)
        }
    }
    
    applyIncrementalUpdate(prev, curr) {
        // 比较并应用增量更新
        const changes = this.compareStates(prev, curr)
        
        this.applyAgentChanges(changes.agentChanges)
        this.applyTaskChanges(changes.taskChanges)
        this.applyStatsChanges(changes.statsChanges)
    }
    
    compareStates(prev, curr) {
        const agentChanges = []
        const taskChanges = []
        const statsChanges = []
        
        // 比较agent状态
        if (JSON.stringify(prev.agents) !== JSON.stringify(curr.agents)) {
            const addedAgents = curr.agents.filter(a => 
                !prev.agents.find(p => p.id === a.id))
            const removedAgents = prev.agents.filter(p => 
                !curr.agents.find(a => a.id === p.id))
            const updatedAgents = curr.agents.filter(a => {
                const prevAgent = prev.agents.find(p => p.id === a.id)
                return prevAgent && JSON.stringify(prevAgent) !== JSON.stringify(a)
            })
            
            agentChanges.push({ added: addedAgents, removed: removedAgents, updated: updatedAgents })
        }
        
        // 比较任务状态
        if (JSON.stringify(prev.tasks) !== JSON.stringify(curr.tasks)) {
            const addedTasks = curr.tasks.filter(t => 
                !prev.tasks.find(p => p.id === t.id))
            const removedTasks = prev.tasks.filter(p => 
                !curr.tasks.find(t => t.id === p.id))
            const updatedTasks = curr.tasks.filter(t => {
                const prevTask = prev.tasks.find(p => p.id === t.id)
                return prevTask && JSON.stringify(prevTask) !== JSON.stringify(t)
            })
            
            taskChanges.push({ added: addedTasks, removed: removedTasks, updated: updatedTasks })
        }
        
        // 比较系统统计
        if (JSON.stringify(prev.stats) !== JSON.stringify(curr.stats)) {
            statsChanges.push({ previous: prev.stats, current: curr.stats })
        }
        
        return { agentChanges, taskChanges, statsChanges }
    }
    
    applyAgentChanges(changes) {
        // 添加新agent
        changes.added.forEach(agent => {
            this.renderAgent(agent)
        })
        
        // 更新agent状态
        changes.updated.forEach(agent => {
            this.updateAgent(agent)
        })
        
        // 移除agent
        changes.removed.forEach(agent => {
            this.removeAgent(agent)
        })
    }
    
    applyTaskChanges(changes) {
        // 添加新任务
        changes.added.forEach(task => {
            this.renderTask(task)
        })
        
        // 更新任务状态
        changes.updated.forEach(task => {
            this.updateTask(task)
        })
        
        // 移除任务
        changes.removed.forEach(task => {
            this.removeTask(task)
        })
    }
    
    applyStatsChanges(changes) {
        // 更新统计数据
        this.updateStats(changes[0].current)
    }
}
```

### 3. 响应式设计优化

#### 功能说明
- 支持移动端和桌面端
- 自适应布局
- 触摸和键盘交互优化

#### 技术实现
```css
/* 响应式布局优化 */
@media (max-width: 768px) {
    .task-management {
        grid-template-columns: 1fr;
    }
    
    .agent-list {
        order: 2;
        margin-top: 20px;
    }
    
    .task-list {
        order: 1;
    }
    
    .control-panel {
        order: 3;
    }
    
    .task-item {
        flex-direction: column;
        padding: 15px;
    }
    
    .task-header {
        margin-bottom: 10px;
    }
    
    .task-meta {
        text-align: center;
    }
}

@media (max-width: 480px) {
    .dashboard {
        padding: 10px;
    }
    
    .task-list {
        margin: 10px;
    }
    
    .task-item {
        padding: 10px;
    }
    
    .task-title {
        font-size: 16px;
    }
    
    .task-description {
        font-size: 12px;
    }
}
```

### 4. 性能优化

#### 功能说明
- 优化渲染性能
- 减少不必要的重排重绘
- 内存泄漏检测

#### 技术实现
```javascript
// 性能优化工具
class PerformanceOptimizer {
    constructor() {
        this.renderTimer = null
        this.bufferedUpdates = []
        this.maxBufferTime = 100 // 毫秒
    }
    
    debounceUpdate(updateFunction) {
        if (this.renderTimer) {
            clearTimeout(this.renderTimer)
        }
        
        this.renderTimer = setTimeout(() => {
            this.applyBufferedUpdates()
        }, this.maxBufferTime)
    }
    
    applyBufferedUpdates() {
        const updates = [...this.bufferedUpdates]
        this.bufferedUpdates = []
        
        // 合并和优化更新
        const mergedUpdates = this.mergeUpdates(updates)
        
        // 执行优化后的更新
        mergedUpdates.forEach(update => {
            this.applyOptimizedUpdate(update)
        })
    }
    
    mergeUpdates(updates) {
        const merged = {}
        
        updates.forEach(update => {
            if (update.type === 'agent') {
                if (!merged.agents) merged.agents = []
                const existing = merged.agents.find(a => a.id === update.data.id)
                if (existing) {
                    // 更新现有agent数据
                    Object.assign(existing, update.data)
                } else {
                    merged.agents.push(update.data)
                }
            } else if (update.type === 'task') {
                if (!merged.tasks) merged.tasks = []
                const existing = merged.tasks.find(t => t.id === update.data.id)
                if (existing) {
                    Object.assign(existing, update.data)
                } else {
                    merged.tasks.push(update.data)
                }
            }
        })
        
        return this.optimizeUpdates(merged)
    }
    
    optimizeUpdates(updates) {
        // 优化更新顺序和合并操作
        const optimized = []
        
        if (updates.agents) {
            updates.agents.forEach(agent => {
                optimized.push({ type: 'agent', data: agent })
            })
        }
        
        if (updates.tasks) {
            updates.tasks.forEach(task => {
                optimized.push({ type: 'task', data: task })
            })
        }
        
        return optimized
    }
}
```

## 🎯 实施计划

### 阶段1：WebSocket集成（1天）
- 建立WebSocket连接
- 实现实时数据推送
- 错误处理和重连机制

### 阶段2：增量更新实现（1天）
- 实现增量更新算法
- 优化DOM操作
- 添加动画过渡效果

### 阶段3：性能优化（0.5天）
- 实施渲染优化
- 内存泄漏检测
- 响应式设计优化

### 阶段4：测试验证（0.5天）
- 功能测试
- 性能测试
- 兼容性测试

## 📊 验收标准

### 功能验收
- ✅ WebSocket连接成功
- ✅ 实时数据推送正常
- ✅ 增量更新效果良好
- ✅ 响应式设计优化

### 性能验收
- ✅ 页面加载时间 < 2秒
- ✅ API响应时间 < 500ms
- ✅ 渲染性能良好
- ✅ 内存使用稳定

### 兼容性验收
- ✅ Chrome浏览器支持
- ✅ Firefox浏览器支持
- ✅ Safari浏览器支持
- ✅ 移动端浏览器支持

---
**任务创建时间**：2026-02-23
**任务负责人**：开发工程师
**优先级**：高
