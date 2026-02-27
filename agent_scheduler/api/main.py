"""
Agent调度系统API入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from agent_scheduler.api.routes import agents, roles, demands, tasks

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
