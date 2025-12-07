#!/bin/bash

# 华为云FunctionGraph函数部署脚本
# 将PytestAutoApi项目部署为华为云FunctionGraph函数

set -e

# 配置变量 - 请根据实际情况修改
REGION="cn-north-4"                    # 华为云区域
PROJECT_ID="your_project_id"            # 华为云项目ID
FUNCTION_NAME="pytest-auto-api"         # 函数名称
FUNCTION_DESCRIPTION="PytestAutoApi智能自动化测试平台"  # 函数描述
FUNCTION_MEMORY="512"                   # 函数内存(MB)
FUNCTION_TIMEOUT="60"                   # 函数超时时间(秒)
FUNCTION_RUNTIME="Python3.6"             # 函数运行时
HANDLER="index.handler"                 # 函数处理程序
ACCESS_KEY="your_access_key"            # 华为云访问密钥
SECRET_KEY="your_secret_key"            # 华为云秘密密钥
APIG_GROUP_NAME="pytest-auto-api"       # API网关分组名称
APIG_DESCRIPTION="PytestAutoApi API Gateway"  # API网关描述

echo "=========================================="
echo "    华为云FunctionGraph函数部署脚本"
echo "=========================================="

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

# 创建函数部署包
echo "正在创建函数部署包..."
python3 functiongraph_handler.py

# 检查部署包是否创建成功
if [ ! -f "pytest-auto-api-function.zip" ]; then
    echo "错误: 函数部署包创建失败"
    exit 1
fi

# 创建函数
echo "正在创建FunctionGraph函数..."
hcloud FunctionGraph CreateFunction \
    --cli-region=${REGION} \
    --function_name=${FUNCTION_NAME} \
    --handler=${HANDLER} \
    --memory_size=${FUNCTION_MEMORY} \
    --runtime=${FUNCTION_RUNTIME} \
    --timeout=${FUNCTION_TIMEOUT} \
    --code_type="zip" \
    --code_url="pytest-auto-api-function.zip" \
    --description="${FUNCTION_DESCRIPTION}" \
    --user_data="{}"

# 等待函数创建完成
echo "等待函数创建完成..."
sleep 10

# 创建API网关分组
echo "正在创建API网关分组..."
APIG_GROUP_ID=$(hcloud APIG CreateApiGroup \
    --cli-region=${REGION} \
    --name=${APIG_GROUP_NAME} \
    --description=${APIG_DESCRIPTION} \
    --query="id" \
    --output="text")

# 获取函数URN
FUNCTION_URN=$(hcloud FunctionGraph ShowFunctionMetadata \
    --cli-region=${REGION} \
    --function_name=${FUNCTION_NAME} \
    --query="func_urn" \
    --output="text")

# 创建API网关
echo "正在创建API网关..."
APIG_API_ID=$(hcloud APIG CreateApi \
    --cli-region=${REGION} \
    --group_id=${APIG_GROUP_ID} \
    --name=${FUNCTION_NAME} \
    --type="public" \
    --req_method="ANY" \
    --req_uri="/" \
    --auth_type="NONE" \
    --match_mode="NORMAL" \
    --backend_type="FUNCTION" \
    --func_info="\"{\\\"func_urn\\\":\\\"${FUNCTION_URN}\\\",\\\"invocation_type\\\":\\\"sync\\\"}\"" \
    --description="PytestAutoApi API Gateway" \
    --query="id" \
    --output="text")

# 发布API到环境
echo "正在发布API到环境..."
hcloud APIG PublishApi \
    --cli-region=${REGION} \
    --group_id=${APIG_GROUP_ID} \
    --api_id=${APIG_API_ID} \
    --env_name="RELEASE" \
    --description="Initial release"

# 获取API网关访问地址
APIG_URL=$(hcloud APIG ShowDetailsOfApiV2 \
    --cli-region=${REGION} \
    --group_id=${APIG_GROUP_ID} \
    --api_id=${APIG_API_ID} \
    --env_id="DEFAULT_ENVIRONMENT_RELEASE_ID" \
    --query="group_remark" \
    --output="text")

# 清理临时文件
rm -f pytest-auto-api-function.zip

echo "=========================================="
echo "    部署完成"
echo "=========================================="
echo "函数名称: ${FUNCTION_NAME}"
echo "API网关分组ID: ${APIG_GROUP_ID}"
echo "API网关API ID: ${APIG_API_ID}"
echo "API访问地址: ${APIG_URL}"
echo ""
echo "您可以通过以下地址访问您的应用:"
echo "http://${APIG_URL}/"
echo ""
echo "如需查看函数详情，请执行:"
echo "hcloud FunctionGraph ShowFunctionMetadata --function_name=${FUNCTION_NAME}"
echo "=========================================="