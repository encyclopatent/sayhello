#!/bin/bash
# restart_services.sh - 重启 sayhello 服务

set -e

echo "=== 清除 Python 缓存 ==="
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "缓存已清除"

echo "=== 停止旧进程 ==="
pkill -f "celery" 2>/dev/null || true
pkill -f "python.*app" 2>/dev/null || true
sleep 2

echo "=== 启动 Celery Worker ==="
source venv/bin/activate
celery -A app.celery worker --loglevel=info &
CELERY_PID=$!
echo "Celery started (PID: $CELERY_PID)"

sleep 2

echo "=== 启动 Flask 应用 ==="
python app.py &
FLASK_PID=$!
echo "Flask started (PID: $FLASK_PID)"

echo "=== 服务已启动 ==="
echo "Flask: http://0.0.0.0:5002"
echo "Celery: running"
