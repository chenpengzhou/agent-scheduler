# -*- coding: utf-8 -*-
"""
FastAPI 应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import logging
import os

from routers import stocks
from services.stock_service import StockDataService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 启动时间
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时初始化
    db_path = os.environ.get('STOCK_DB_PATH', 'auto')
    logger.info(f"股票API服务启动... 数据库路径: {db_path}")
    
    service = StockDataService()
    logger.info(f"数据库路径: {service.db_path}")
    
    yield
    logger.info("股票API服务关闭...")


# 创建应用
app = FastAPI(
    title="股票数据API",
    description="股票数据查询服务",
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
app.include_router(stocks.router, prefix="/api", tags=["股票数据"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "股票数据API",
        "version": "1.0.0",
        "docs": "/docs"
    }
