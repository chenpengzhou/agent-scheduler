"""
FastAPI 应用入口
"""
import os
import yaml
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.models import init_db
from api.routes import definitions, instances
from api.services.logging_service import setup_logging, get_logger


# 加载配置
def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8000, "reload": False},
        "database": {"url": "sqlite:///./workflow_engine.db", "echo": False},
        "logging": {"level": "INFO", "format": "json", "file": "logs/workflow_engine.log"}
    }


config = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    db_config = config.get("database", {})
    init_db(db_config.get("url", "sqlite:///./workflow_engine.db"), db_config.get("echo", False))
    
    log_config = config.get("logging", {})
    setup_logging(
        level=log_config.get("level", "INFO"),
        log_file=log_config.get("file"),
        format=log_config.get("format", "json")
    )
    
    logger = get_logger("api")
    logger.info("application_startup", config=config)
    
    yield
    
    # 关闭时
    logger = get_logger("api")
    logger.info("application_shutdown")


# 创建应用
app = FastAPI(
    title="Workflow Engine API",
    description="工作流引擎REST API",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(definitions.router)
app.include_router(instances.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Workflow Engine API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    server_config = config.get("server", {})
    uvicorn.run(
        "api.main:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", False)
    )
