#!/bin/bash

# 智能自动化测试平台启动脚本

echo "=========================================="
echo "    智能自动化测试平台启动脚本"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查Node.js环境（用于前端开发）
if ! command -v node &> /dev/null; then
    echo "警告: 未找到Node.js，前端开发可能受限"
fi

# 安装Python依赖
echo "正在检查并安装Python依赖..."
pip3 install flask flask-cors requests pytest

# 创建必要的目录
mkdir -p uploads results test_cases

# 启动后端API服务器
echo "正在启动后端API服务器..."
python3 api_server.py &
BACKEND_PID=$!

# 等待后端服务器启动
sleep 3

# 检查后端服务器是否启动成功
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "后端API服务器启动成功，地址: http://localhost:5000"
else
    echo "后端API服务器启动失败"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 启动前端服务
echo "正在启动前端服务..."
cd frontend

# 尝试使用Python启动简单的HTTP服务器
if command -v python3 &> /dev/null; then
    python3 -m http.server 8080 &
    FRONTEND_PID=$!
    FRONTEND_URL="http://localhost:8080"
else
    echo "无法启动前端HTTP服务器"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 等待前端服务器启动
sleep 2

echo "=========================================="
echo "    智能自动化测试平台已启动"
echo "=========================================="
echo "前端地址: $FRONTEND_URL"
echo "后端API: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

# 等待用户中断
trap 'echo "正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT
wait