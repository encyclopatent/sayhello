#!/bin/bash
# SAYHELLO 停止脚本

echo "========================================="
echo "  SAYHELLO 应用停止脚本"
echo "========================================="

cd "/Users/zhaoyongjiang/Downloads/SAYHELLO"

# 停止Flask应用
echo ""
echo "停止Flask应用..."
if [ -f logs/flask.pid ]; then
    FLASK_PID=$(cat logs/flask.pid)
    if ps -p $FLASK_PID > /dev/null 2>&1; then
        kill $FLASK_PID
        echo "✓ Flask应用已停止 (PID: $FLASK_PID)"
    else
        echo "  Flask进程不存在"
    fi
    rm logs/flask.pid
else
    echo "  未找到Flask PID文件"
fi

# 停止Celery Worker
echo ""
echo "停止Celery Worker..."
if [ -f logs/celery_worker.pid ]; then
    WORKER_PID=$(cat logs/celery_worker.pid)
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        kill $WORKER_PID
        echo "✓ Celery Worker已停止 (PID: $WORKER_PID)"
    else
        echo "  Celery Worker进程不存在"
    fi
    rm logs/celery_worker.pid
else
    pkill -f "celery.*worker" && echo "✓ Celery Worker已通过进程名停止" || echo "  未找到运行中的Celery Worker"
fi

# 停止Celery Beat
echo ""
echo "停止Celery Beat..."
if [ -f logs/celery_beat.pid ]; then
    BEAT_PID=$(cat logs/celery_beat.pid)
    if ps -p $BEAT_PID > /dev/null 2>&1; then
        kill $BEAT_PID
        echo "✓ Celery Beat已停止 (PID: $BEAT_PID)"
    else
        echo "  Celery Beat进程不存在"
    fi
    rm logs/celery_beat.pid
else
    pkill -f "celery.*beat" && echo "✓ Celery Beat已通过进程名停止" || echo "  未找到运行中的Celery Beat"
fi

echo ""
echo "========================================="
echo "  所有服务已停止"
echo "========================================="
