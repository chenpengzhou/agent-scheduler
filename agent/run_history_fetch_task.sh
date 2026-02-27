#!/bin/bash

# 股票历史数据获取任务调度脚本

LOG_DIR="/home/robin/.openclaw/workspace-dev/logs"
PID_FILE="/home/robin/.openclaw/workspace-dev/agent/history_fetch.pid"
LOG_FILE="$LOG_DIR/history_fetch.log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 检查任务是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    
    if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
        echo "✅ 任务正在运行 (PID: $PID)"
        echo "📊 任务信息:"
        echo "   - 日志文件: $LOG_FILE"
        echo "   - 运行时间: $(ps -p $PID -o etime=)"
        
        # 显示任务状态
        if [ -f "$LOG_FILE" ]; then
            echo "📋 最后10条日志:"
            tail -10 "$LOG_FILE"
        fi
        
        exit 0
    else
        echo "⚠️ 任务已停止，清除过时的PID文件"
        rm -f "$PID_FILE"
    fi
fi

# 开始新的任务
echo "🚀 启动股票历史数据获取任务..."
echo "📊 任务配置:"
echo "   - 运行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "   - Tushare API: https://api.tushare.pro"
echo "   - 数据库位置: /home/robin/.openclaw/data/stock.db"
echo "   - 日志文件: $LOG_FILE"

# 启动Python程序
nohup python3 /home/robin/.openclaw/workspace-dev/agent/fetch_stock_history.py > "$LOG_FILE" 2>&1 &
PYTHON_PID=$!

if [ $? -eq 0 ]; then
    echo "$PYTHON_PID" > "$PID_FILE"
    echo "✅ 任务启动成功 (PID: $PYTHON_PID)"
    
    # 显示任务初始化过程
    echo "⏳ 初始化中..."
    sleep 2
    
    if [ -f "$LOG_FILE" ]; then
        echo "📋 任务输出:"
        cat "$LOG_FILE"
    fi
else
    echo "❌ 任务启动失败"
    exit 1
fi

# 验证任务运行状态
echo "🔍 验证任务运行状态..."

for i in {1..5}; do
    if ps -p $PYTHON_PID -o pid= > /dev/null; then
        echo "✅ 任务正在运行"
        break
    fi
    
    echo "⏳ 等待任务启动..."
    sleep 1
    
    if [ $i -eq 5 ]; then
        echo "❌ 任务启动超时"
        if [ -f "$LOG_FILE" ]; then
            echo "📊 错误信息:"
            cat "$LOG_FILE"
        fi
        rm -f "$PID_FILE"
        exit 1
    fi
done

echo "✅ 任务调度完成！"
echo "📋 查看任务状态: $0 status"
echo "📊 查看任务日志: tail -f $LOG_FILE"
echo "🚫 停止任务: $0 stop"
