#!/bin/bash

# PytestAutoApi 部署脚本
# 此脚本帮助您快速部署应用

echo "==================================="
echo "PytestAutoApi 部署脚本"
echo "==================================="

# 检查Python是否已安装
if ! command -v python &> /dev/null; then
    echo "错误: Python 未安装。请先安装 Python 3.8 或更高版本。"
    exit 1
fi

# 检查pip是否已安装
if ! command -v pip &> /dev/null; then
    echo "错误: pip 未安装。请先安装 pip。"
    exit 1
fi

# 安装依赖
echo "正在安装依赖..."
pip install -r requirements.txt

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在。"
    echo "请按照 ENV_SETUP.md 中的说明设置环境变量。"
    echo ""
    echo "是否要创建示例 .env 文件? (y/n)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        echo "创建示例 .env 文件..."
        echo "# 请将下面的值替换为您的实际API密钥" > .env
        echo "SILICONFLOW_API_KEY=your_actual_api_key_here" >> .env
        echo "示例 .env 文件已创建。请编辑 .env 文件并设置您的API密钥。"
    fi
else
    echo "找到 .env 文件。"
fi

# 检查API密钥是否已设置
if [ -f .env ]; then
    if grep -q "your_actual_api_key_here" .env; then
        echo "警告: 您尚未在 .env 文件中设置实际的API密钥。"
        echo "请编辑 .env 文件并设置您的API密钥。"
    fi
fi

echo ""
echo "==================================="
echo "部署准备完成!"
echo "==================================="
echo ""
echo "下一步:"
echo "1. 确保已设置 SILICONFLOW_API_KEY 环境变量"
echo "2. 运行 'python api_server.py' 启动API服务器"
echo "3. 运行 'cd frontend && python -m http.server 8080' 启动前端服务器"
echo ""
echo "更多详细信息请参考 ENV_SETUP.md 文件。"