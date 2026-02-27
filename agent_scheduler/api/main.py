"""
Agent调度系统API入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from agent_scheduler.api.routes import agents, roles, demands, tasks, pipeline, monitor, notifications, messages, queue, workflow
from agent_scheduler.api.routes.demands import demands_db
from agent_scheduler.api.routes.agents import agents_db
from agent_scheduler.api.routes.tasks import tasks_db

# 任务监控模块
from task_monitor.api.routes.task_monitor import router as task_monitor_router

app = FastAPI(
    title="Agent Scheduler API",
    description="Agent调度系统API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agents.router)
app.include_router(roles.router)
app.include_router(demands.router)
app.include_router(tasks.router)
app.include_router(pipeline.router)
app.include_router(monitor.router)
app.include_router(notifications.router)
app.include_router(messages.router)
app.include_router(queue.router)
app.include_router(workflow.router)

# 任务监控路由
from task_monitor.api.routes import task_monitor
app.include_router(task_monitor.router)

# 初始化服务
pipeline.init_services()
monitor.init_services()
notifications.init_service()
messages.init_service()
queue.init_service(tasks_db, agents_db)
workflow.init_service(agents_db, tasks_db)
task_monitor.init_service(tasks_db)


@app.get("/")
async def root():
    return {
        "name": "Agent Scheduler API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
