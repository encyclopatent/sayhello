#!/bin/bash
# SAYHELLO Flask应用和Celery启动脚本
# 在8080端口启动服务

echo "========================================="
echo "  SAYHELLO 应用启动脚本"
echo "========================================="

# 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=production
export PORT=8080
export HOST=0.0.0.0

# 检查Redis是否运行
echo ""
echo "检查Redis状态..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis正在运行"
else
    echo "✗ Redis未运行，请先启动Redis："
    echo "  macOS: brew services start redis"
    echo "  Linux: sudo systemctl start redis"
    exit 1
fi

# 进入项目目录
cd "/Users/zhaoyongjiang/Downloads/SAYHELLO"

# 停止已存在的进程
echo ""
echo "检查并停止已存在的进程..."
pkill -f "celery worker" 2>/dev/null && echo "  停止旧的Celery Worker" || echo "  无旧Celery Worker进程"
pkill -f "celery beat" 2>/dev/null && echo "  停止旧的Celery Beat" || echo "  无旧Celery Beat进程"

# 等待进程完全停止
sleep 2

# 创建必要的目录
echo ""
echo "创建必要的目录..."
mkdir -p logs
mkdir -p static/uploads
mkdir -p static/outputs
echo "✓ 目录创建完成"

# 启动Celery Worker
echo ""
echo "启动Celery Worker..."
celery -A app.celery worker \
    --loglevel=info \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid \
    --detach

if [ $? -eq 0 ]; then
    echo "✓ Celery Worker已在后台启动"
    echo "  日志文件: logs/celery_worker.log"
else
    echo "✗ Celery Worker启动失败"
    exit 1
fi

# 启动Celery Beat（定时任务调度器，可选）
echo ""
echo "启动Celery Beat..."
celery -A app.celery beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=logs/celery_beat.pid \
    --detach

if [ $? -eq 0 ]; then
    echo "✓ Celery Beat已在后台启动"
    echo "  日志文件: logs/celery_beat.log"
else
    echo "✗ Celery Beat启动失败（非必需，继续运行）"
fi

# 启动Flask应用
echo ""
echo "启动Flask应用 (端口8080)..."
python3 app.py 8080 > logs/flask.log 2>&1 &
FLASK_PID=$!

if [ $? -eq 0 ]; then
    echo "✓ Flask应用已在后台启动"
    echo "  PID: $FLASK_PID"
    echo "  日志文件: logs/flask.log"
    echo ""
    echo "========================================="
    echo "  所有服务已成功启动！"
    echo "========================================="
    echo ""
    echo "访问地址："
    echo "  主页: http://localhost:8080"
    echo "  ST26工具: http://localhost:8080/st26"
    echo "  siRNA工具: http://localhost:8080/sirna"
    echo ""
    echo "查看日志："
    echo "  Flask: tail -f logs/flask.log"
    echo "  Celery Worker: tail -f logs/celery_worker.log"
    echo "  Celery Beat: tail -f logs/celery_beat.log"
    echo ""
    echo "停止服务："
    echo "  ./stop.sh"
    echo ""
    echo "========================================="

    # 保存PID到文件
    echo $FLASK_PID > logs/flask.pid
    echo "Flask PID已保存到 logs/flask.pid"

else
    echo "✗ Flask应用启动失败"
    exit 1
fi
