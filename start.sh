#!/bin/bash

# 启动 Flask 应用的脚本
# 需要 Redis 服务先运行

# 激活虚拟环境
source venv/bin/activate

# 检查 Redis 是否运行
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis 未运行，正在启动 Redis..."
    # macOS 上使用 brew services 启动 Redis
    brew services start redis
    sleep 2
fi

# 启动 Celery Worker（后台运行）
echo "启动 Celery Worker..."
celery -A app.celery worker --loglevel=info --pidfile=celery.pid &
CELERY_PID=$!
echo "Celery Worker 已启动 (PID: $CELERY_PID)"

# 等待 Celery 启动
sleep 2

# 启动 Flask 应用
echo "启动 Flask 应用 (http://0.0.0.0:5002)..."
python app.py
