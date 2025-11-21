#!/bin/bash

# 华为云ECS直接部署脚本（不使用Docker）
# 适用于华为云ECS服务器直接部署PytestAutoApi项目

set -e

# 配置变量 - 请根据实际情况修改
ECS_USER="root"                           # ECS服务器用户名
ECS_HOST="your_ecs_ip_address"            # ECS服务器IP地址
ECS_PORT="22"                             # SSH端口
PROJECT_NAME="PytestAutoApi"              # 项目名称
DEPLOY_PATH="/opt/${PROJECT_NAME}"        # 部署路径
PYTHON_VERSION="python3"                  # Python版本
VENV_NAME="venv"                          # 虚拟环境名称
SERVICE_NAME="pytest-auto-api"            # 系统服务名称

echo "=========================================="
echo "    华为云ECS直接部署脚本"
echo "=========================================="

# 检查本地是否有项目文件
if [ ! -f "api_server.py" ]; then
    echo "错误: 未找到api_server.py文件，请确保在项目根目录执行此脚本"
    exit 1
fi

# 打包项目文件
echo "正在打包项目文件..."
tar -czf ${PROJECT_NAME}.tar.gz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' --exclude='*.log' .

# 上传到ECS服务器
echo "正在上传项目文件到ECS服务器..."
scp -P ${ECS_PORT} ${PROJECT_NAME}.tar.gz ${ECS_USER}@${ECS_HOST}:/tmp/

# 在ECS服务器上执行部署命令
echo "正在ECS服务器上执行部署..."
ssh -p ${ECS_PORT} ${ECS_USER}@${ECS_HOST} << EOF
    # 创建部署目录
    mkdir -p ${DEPLOY_PATH}
    cd ${DEPLOY_PATH}
    
    # 解压项目文件
    tar -xzf /tmp/${PROJECT_NAME}.tar.gz -C .
    
    # 安装系统依赖
    apt-get update
    apt-get install -y ${PYTHON_VERSION} ${PYTHON_VERSION}-pip ${PYTHON_VERSION}-venv nginx supervisor
    
    # 创建虚拟环境
    ${PYTHON_VERSION} -m venv ${VENV_NAME}
    source ${VENV_NAME}/bin/activate
    
    # 安装Python依赖
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # 创建必要的目录
    mkdir -p uploads results test_cases
    
    # 创建systemd服务文件
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOL
[Unit]
Description=PytestAutoApi Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${DEPLOY_PATH}
Environment=PATH=${DEPLOY_PATH}/${VENV_NAME}/bin
ExecStart=${DEPLOY_PATH}/${VENV_NAME}/bin/python api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

    # 配置Nginx反向代理
    cat > /etc/nginx/sites-available/${SERVICE_NAME} << EOL
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static {
        alias ${DEPLOY_PATH}/frontend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOL

    # 启用Nginx站点
    ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # 启动并启用服务
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}
    systemctl start ${SERVICE_NAME}
    systemctl restart nginx
    
    # 清理临时文件
    rm -f /tmp/${PROJECT_NAME}.tar.gz
    
    echo "部署完成！"
    echo "服务状态: systemctl status ${SERVICE_NAME}"
    echo "Nginx状态: systemctl status nginx"
EOF

# 清理本地临时文件
rm -f ${PROJECT_NAME}.tar.gz

echo "=========================================="
echo "    部署完成"
echo "=========================================="
echo "访问地址: http://${ECS_HOST}"
echo "API地址: http://${ECS_HOST}/api/health"
echo ""
echo "如需查看服务状态，请登录ECS服务器执行:"
echo "systemctl status ${SERVICE_NAME}"
echo "=========================================="