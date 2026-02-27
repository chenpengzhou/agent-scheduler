#!/bin/bash

PID_FILE="/home/robin/.openclaw/workspace-dev/agent/history_fetch.pid"
LOG_FILE="/home/robin/.openclaw/workspace-dev/logs/history_fetch.log"

if [ "$1" = "status" ] || [ "$1" = "log" ] || [ "$1" = "stop" ]; then
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ 任务未运行"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE" 2>/dev/null)
    
    case "$1" in
        "status")
            if kill -0 $PID 2>/dev/null; then
                echo "✅ 任务正在运行 (PID: $PID)"
                echo "📊 运行时间: $(ps -p $PID -o etime=)"
                
                if [ -f "$LOG_FILE" ]; then
                    echo "📋 最后10条日志:"
                    tail -10 "$LOG_FILE"
                fi
            else
                echo "❌ 任务已停止"
                rm -f "$PID_FILE"
            fi
            ;;
            
        "log")
            if [ -f "$LOG_FILE" ]; then
                echo "📊 任务日志 ($LOG_FILE):"
                cat "$LOG_FILE"
            else
                echo "❌ 日志文件不存在"
            fi
            ;;
            
        "stop")
            if kill -0 $PID 2>/dev/null; then
                echo "🚫 停止任务 (PID: $PID)"
                kill $PID
                
                # 等待任务结束
                for i in {1..5}; do
                    if ! kill -0 $PID 2>/dev/null; then
                        echo "✅ 任务已停止"
                        rm -f "$PID_FILE"
                        exit 0
                    fi
                    sleep 1
                done
                
                # 强制杀死
                echo "⚠️ 强制停止任务"
                kill -9 $PID
                rm -f "$PID_FILE"
            else
                echo "❌ 任务已停止"
                rm -f "$PID_FILE"
            fi
            ;;
    esac
else
    echo "用法: $0 [status|log|stop]"
    echo "  status - 显示任务运行状态"
    echo "  log - 显示任务完整日志"
    echo "  stop - 停止任务"
fi
