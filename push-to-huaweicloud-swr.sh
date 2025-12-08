#!/bin/bash

# 华为云SWR容器镜像仓库推送脚本
# 使用前请确保已安装并配置好华为云CLI工具和Docker

set -e

# 配置变量 - 请根据实际情况修改
REGION="cn-north-4"                    # 华为云区域
PROJECT_ID="your_project_id"            # 华为云项目ID
SWR_ORGANIZATION="your_organization"    # SWR组织名称
IMAGE_NAME="pytest-auto-api"            # 镜像名称
IMAGE_TAG="latest"                       # 镜像标签
ACCESS_KEY="your_access_key"            # 华为云访问密钥
SECRET_KEY="your_secret_key"            # 华为云秘密密钥

# 构建镜像仓库地址
SWR_REGISTRY="${REGION}.swr.myhuaweicloud.com"
FULL_IMAGE_NAME="${SWR_REGISTRY}/${SWR_ORGANIZATION}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=========================================="
echo "    华为云SWR容器镜像推送脚本"
echo "=========================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到Docker，请先安装Docker"
    exit 1
fi

# 检查华为云CLI是否安装
if ! command -v hcloud &> /dev/null; then
    echo "错误: 未找到华为云CLI工具，请先安装"
    echo "安装文档: https://support.huaweicloud.com/cli-hcloud/hcloud_01_0001.html"
    exit 1
fi

# 配置华为云CLI
echo "正在配置华为云CLI..."
hcloud configure set \
    --cli-region=${REGION} \
    --cli-project-id=${PROJECT_ID} \
    --cli-access-key=${ACCESS_KEY} \
    --cli-secret-key=${SECRET_KEY}

# 登录SWR镜像仓库
echo "正在登录SWR镜像仓库..."
docker login -u ${REGION}@${PROJECT_ID} -p $(hcloud SWR ShowTempAuth --cli-region=${REGION}) ${SWR_REGISTRY}

# 构建Docker镜像
echo "正在构建Docker镜像..."
docker build -t ${FULL_IMAGE_NAME} .

# 推送镜像到SWR
echo "正在推送镜像到SWR..."
docker push ${FULL_IMAGE_NAME}

echo "=========================================="
echo "    镜像推送完成"
echo "=========================================="
echo "镜像地址: ${FULL_IMAGE_NAME}"
echo ""
echo "您可以在华为云CCE集群中使用以下命令部署:"
echo "kubectl apply -f huaweicloud-deployment.yaml"
echo "=========================================="