#!/bin/bash
# 启动股票API服务

cd /home/robin/.openclaw/workspace-dev/stock_api

# 安装依赖
pip install -r requirements.txt -q

# 启动服务
echo "启动股票API服务在 0.0.0.0:8000 ..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
