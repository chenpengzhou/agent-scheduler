#!/bin/bash

# Stock Updater V1.0 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 虚拟环境路径
VENV_DIR="$SCRIPT_DIR/venv"

# 创建虚拟环境（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 检查依赖
if ! python -c "import akshare" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# 运行应用
case "${1:-}" in
    start)
        echo "Starting Stock Updater..."
        python -m app.main --background
        ;;
    stop)
        echo "Stopping Stock Updater..."
        pkill -f "python -m app.main"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    once)
        echo "Running once..."
        python -m app.main --once
        ;;
    test)
        echo "Testing..."
        python -c "from app import config; print('Config OK')"
        python -c "from app.storage import storage; storage.init_tables(); print('Storage OK')"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|once|test}"
        exit 1
        ;;
esac
