# -*- coding: utf-8 -*-
"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.routers import auth, stocks, admin, admin_extended, positions, account, paper_trade, api_keys
from app.middleware import AuthMiddleware
from app.utils.db import init_db
from app.config import CORS_ORIGINS

# 初始化数据库
init_db()

# 创建应用
app = FastAPI(
    title="股票系统管理后台",
    description="股票数据API服务",
    version="1.0.0"
)

# CORS - 限制域名
origins = CORS_ORIGINS if CORS_ORIGINS else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 认证中间件
app.add_middleware(AuthMiddleware)

# 注册路由 - admin_extended要在admin之前，避免路由冲突
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(admin_extended.router)
app.include_router(admin.router)
app.include_router(positions.router)
app.include_router(account.router)
app.include_router(paper_trade.router)
app.include_router(api_keys.router)

# 静态文件和模板
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)


@app.get("/")
async def root():
    """根路径"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/templates/login.html")


@app.get("/templates/{name}")
async def get_template(name: str):
    """获取模板文件"""
    template_path = os.path.join(templates_dir, name)
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=f.read())
    return {"detail": "Template not found"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# 运行说明
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("股票系统管理后台")
    print("=" * 50)
    print("启动命令: uvicorn app.main:app --host 0.0.0.0 --port 8002")
    print("默认账号: admin / admin123")
    print("=" * 50)
