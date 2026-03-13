#!/bin/bash
# Stock API 启动脚本 - 性能优化版

# 配置
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8002}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-"info"}

# 环境变量检查
if [ -z "$JWT_SECRET_KEY" ]; then
    echo "错误: 需要设置 JWT_SECRET_KEY 环境变量"
    echo "用法: JWT_SECRET_KEY=your-secret-key CORS_ORIGINS='http://localhost:3000' ./start.sh"
    exit 1
fi

if [ -z "$CORS_ORIGINS" ]; then
    echo "错误: 需要设置 CORS_ORIGINS 环境变量"
    echo "用法: JWT_SECRET_KEY=your-secret-key CORS_ORIGINS='http://localhost:3000' ./start.sh"
    exit 1
fi

# 导出环境变量
export JWT_SECRET_KEY
export CORS_ORIGINS

# SQLite优化
echo "正在优化SQLite..."
python3 -c "
import sqlite3
import os
db_path = os.path.expanduser('~/.openclaw/data/stock.db')
conn = sqlite3.connect(db_path)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA cache_size=10000')
conn.execute('PRAGMA temp_store=MEMORY')
print('SQLite优化完成:', conn.execute('PRAGMA journal_mode').fetchone()[0])
conn.close()
"

echo "启动 Stock API (workers: $WORKERS)..."
echo "JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:10}..."
echo "CORS_ORIGINS: $CORS_ORIGINS"

# 启动uvicorn with workers
cd "$(dirname "$0")"
PYTHONPATH=$(pwd) uvicorn app.main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL \
    --proxy-headers \
    --forwarded-allow-ips='*'
