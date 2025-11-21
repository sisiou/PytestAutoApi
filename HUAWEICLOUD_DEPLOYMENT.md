# PytestAutoApi 华为云部署指南

本文档提供了将PytestAutoApi项目部署到华为云的详细指南，包括多种不使用Docker的部署方案。

## 目录

1. [部署方案概述](#部署方案概述)
2. [方案一：华为云ECS直接部署](#方案一华为云ecs直接部署)
3. [方案二：华为云FunctionGraph函数部署](#方案二华为云functiongraph函数部署)
4. [方案三：华为云SFS+CodeArts部署](#方案三华为云sfscodearts部署)
5. [常见问题解答](#常见问题解答)

## 部署方案概述

PytestAutoApi项目是一个基于Flask的Web应用，包含前端界面和后端API服务。针对您的华为服务器不支持Docker的情况，我们提供以下三种部署方案：

1. **华为云ECS直接部署**：在ECS云服务器上直接安装Python环境并部署应用
2. **华为云FunctionGraph函数部署**：将应用转换为无服务器函数部署
3. **华为云SFS+CodeArts部署**：使用SFS存储代码和CodeArts进行持续部署

## 方案一：华为云ECS直接部署

### 方案概述

在华为云ECS云服务器上直接安装Python环境、配置Nginx反向代理，并将PytestAutoApi项目部署为系统服务。

### 前置条件

1. 已创建华为云ECS实例（推荐配置：2核4GB内存，Ubuntu 20.04）
2. 已配置SSH密钥或密码访问ECS实例
3. 本地已安装SSH客户端

### 部署步骤

1. **修改部署脚本配置**

   编辑 `deploy-to-huaweicloud-ecs.sh` 文件，修改以下配置：

   ```bash
   ECS_USER="root"                           # ECS服务器用户名
   ECS_HOST="your_ecs_ip_address"            # ECS服务器IP地址
   ECS_PORT="22"                             # SSH端口
   ```

2. **执行部署脚本**

   在项目根目录执行：

   ```bash
   chmod +x deploy-to-huaweicloud-ecs.sh
   ./deploy-to-huaweicloud-ecs.sh
   ```

3. **验证部署**

   部署完成后，通过浏览器访问：`http://your_ecs_ip_address`

### 优缺点

**优点：**
- 部署简单，无需容器技术
- 完全控制服务器环境
- 性能稳定，适合长期运行

**缺点：**
- 需要自行管理服务器
- 扩展性有限
- 需要手动处理安全更新

## 方案二：华为云FunctionGraph函数部署

### 方案概述

将PytestAutoApi项目转换为华为云FunctionGraph函数，通过API网关提供HTTP访问接口，实现无服务器部署。

### 前置条件

1. 已注册华为云账号
2. 已安装华为云CLI工具
3. 已配置华为云访问凭证

### 部署步骤

1. **安装华为云CLI**

   参考官方文档：https://support.huaweicloud.com/cli-hcloud/hcloud_01_0001.html

2. **配置华为云CLI**

   ```bash
   hcloud configure set \
       --cli-region=cn-north-4 \
       --cli-project-id=your_project_id \
       --cli-access-key=your_access_key \
       --cli-secret-key=your_secret_key
   ```

3. **修改部署脚本配置**

   编辑 `deploy-to-huaweicloud-functiongraph.sh` 文件，修改以下配置：

   ```bash
   REGION="cn-north-4"                    # 华为云区域
   PROJECT_ID="your_project_id"            # 华为云项目ID
   ACCESS_KEY="your_access_key"            # 华为云访问密钥
   SECRET_KEY="your_secret_key"            # 华为云秘密密钥
   ```

4. **执行部署脚本**

   在项目根目录执行：

   ```bash
   chmod +x deploy-to-huaweicloud-functiongraph.sh
   ./deploy-to-huaweicloud-functiongraph.sh
   ```

5. **验证部署**

   部署完成后，使用脚本输出的API访问地址进行测试。

### 优缺点

**优点：**
- 无需管理服务器
- 自动扩展，按需付费
- 高可用性，内置容错机制

**缺点：**
- 有执行时间限制
- 需要适配函数计算模型
- 冷启动可能导致延迟

## 方案三：华为云SFS+CodeArts部署

### 方案概述

使用华为云SFS（弹性文件服务）存储项目代码，通过CodeArts（软件开发云）进行持续部署。

### 前置条件

1. 已创建华为云SFS文件系统
2. 已创建CodeArts项目
3. 已创建ECS实例并挂载SFS文件系统

### 部署步骤

1. **上传代码到SFS**

   ```bash
   # 将项目代码复制到已挂载的SFS目录
   sudo cp -r /path/to/PytestAutoApi /mnt/sfs/
   ```

2. **配置CodeArts部署流水线**

   在CodeArts控制台创建部署流水线，包含以下步骤：
   - 代码检出
   - 构建环境准备
   - 安装依赖
   - 部署应用

3. **配置ECS自启动脚本**

   在ECS上创建自启动脚本，确保重启后应用自动启动：

   ```bash
   sudo nano /etc/rc.local
   ```

   添加以下内容：

   ```bash
   #!/bin/bash
   cd /mnt/sfs/PytestAutoApi
   source venv/bin/activate
   nohup python api_server.py > /var/log/pytest-auto-api.log 2>&1 &
   exit 0
   ```

4. **设置脚本权限**

   ```bash
   sudo chmod +x /etc/rc.local
   ```

### 优缺点

**优点：**
- 代码与运行环境分离
- 支持持续集成和部署
- 便于多环境管理

**缺点：**
- 配置相对复杂
- 需要多个华为云服务配合
- 可能产生额外费用

## 常见问题解答

### Q1: 如何选择最适合的部署方案？

**A:** 根据您的具体需求选择：
- 如果需要完全控制环境且长期稳定运行，选择ECS直接部署
- 如果希望免运维且流量不稳定，选择FunctionGraph函数部署
- 如果需要持续集成部署，选择SFS+CodeArts部署

### Q2: 部署后如何更新应用？

**A:** 不同方案的更新方式：
- ECS直接部署：重新执行部署脚本或手动更新代码
- FunctionGraph函数部署：重新上传函数代码包
- SFS+CodeArts部署：通过CodeArts触发部署流水线

### Q3: 如何配置HTTPS？

**A:** 
- ECS直接部署：在Nginx配置SSL证书
- FunctionGraph函数部署：在API网关配置SSL证书
- SFS+CodeArts部署：在Nginx或API网关配置SSL证书

### Q4: 如何监控应用运行状态？

**A:**
- ECS直接部署：使用systemctl命令查看服务状态
- FunctionGraph函数部署：使用华为云监控服务查看函数执行情况
- SFS+CodeArts部署：结合华为云监控和日志服务

### Q5: 如何处理数据库连接？

**A:** 
- 建议使用华为云RDS数据库服务
- 在应用配置中使用环境变量存储数据库连接信息
- 确保数据库安全组规则允许应用访问

## 总结

本文档提供了三种不使用Docker的华为云部署方案，您可以根据实际需求和资源情况选择最适合的方案。无论选择哪种方案，都建议：

1. 定期备份应用数据和配置
2. 使用华为云监控服务监控应用状态
3. 定期更新系统和依赖库，确保安全性
4. 配置适当的日志记录，便于问题排查

如有其他问题，请参考华为云官方文档或联系技术支持。