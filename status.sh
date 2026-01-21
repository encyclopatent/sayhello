#!/bin/bash
# SAYHELLO 服务状态检查脚本

echo "========================================="
echo "  SAYHELLO 服务状态"
echo "========================================="
echo ""

cd "/Users/zhaoyongjiang/Downloads/SAYHELLO"

# 检查Redis
echo "Redis状态："
if redis-cli ping > /dev/null 2>&1; then
    echo "  ✓ Redis正在运行"
else
    echo "  ✗ Redis未运行"
fi
echo ""

# 检查Flask
echo "Flask应用状态："
if [ -f logs/flask.pid ]; then
    FLASK_PID=$(cat logs/flask.pid)
    if ps -p $FLASK_PID > /dev/null 2>&1; then
        echo "  ✓ Flask正在运行 (PID: $FLASK_PID)"
        echo "    访问地址: http://localhost:8080"
    else
        echo "  ✗ Flask进程不存在（PID文件存在但进程未运行）"
    fi
else
    # 通过进程名查找
    FLASK_PID=$(ps aux | grep "python.*app.py 8080" | grep -v grep | awk '{print $2}')
    if [ -n "$FLASK_PID" ]; then
        echo "  ✓ Flask正在运行 (PID: $FLASK_PID)"
        echo "    访问地址: http://localhost:8080"
    else
        echo "  ✗ Flask未运行"
    fi
fi
echo ""

# 检查Celery Worker
echo "Celery Worker状态："
if [ -f logs/celery_worker.pid ]; then
    WORKER_PID=$(cat logs/celery_worker.pid)
    if ps -p $WORKER_PID > /dev/null 2>&1; then
        echo "  ✓ Celery Worker正在运行 (PID: $WORKER_PID)"
    else
        echo "  ✗ Celery Worker进程不存在"
    fi
else
    WORKER_PID=$(ps aux | grep "celery.*worker" | grep -v grep | awk '{print $2}')
    if [ -n "$WORKER_PID" ]; then
        echo "  ✓ Celery Worker正在运行 (PID: $WORKER_PID)"
    else
        echo "  ✗ Celery Worker未运行"
    fi
fi
echo ""

# 检查Celery Beat
echo "Celery Beat状态："
if [ -f logs/celery_beat.pid ]; then
    BEAT_PID=$(cat logs/celery_beat.pid)
    if ps -p $BEAT_PID > /dev/null 2>&1; then
        echo "  ✓ Celery Beat正在运行 (PID: $BEAT_PID)"
    else
        echo "  ✗ Celery Beat进程不存在"
    fi
else
    BEAT_PID=$(ps aux | grep "celery.*beat" | grep -v grep | awk '{print $2}')
    if [ -n "$BEAT_PID" ]; then
        echo "  ✓ Celery Beat正在运行 (PID: $BEAT_PID)"
    else
        echo "  ✗ Celery Beat未运行"
    fi
fi
echo ""

# 显示最近的日志
echo "========================================="
echo "  最近日志（最后5行）"
echo "========================================="
echo ""

if [ -f logs/flask.log ]; then
    echo "Flask日志："
    tail -5 logs/flask.log | sed 's/^/  /'
    echo ""
fi

if [ -f logs/celery_worker.log ]; then
    echo "Celery Worker日志："
    tail -5 logs/celery_worker.log | sed 's/^/  /'
    echo ""
fi

echo "========================================="
