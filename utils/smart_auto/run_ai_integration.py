#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time   : 2025/01/06 10:30
@Author : Smart Auto Platform
@File   : run_ai_integration.py
@Desc   : 运行AI集成示例脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.smart_auto.ai_integration_simple import AIIntegration
from utils.logging_tool.log_control import INFO, ERROR


def main():
    """主函数"""
    # 示例JSON文件路径
    json_file_paths = [
        "api/server-docs_im-v1_message_create.json",
        "api/server-docs_contact-v3_user_create.json",
        "api/server-docs_calendar-v4_calendar_create.json",
        "api/server-docs_authentication-management_login-state-management_get.json"
    ]
    
    # 检查文件是否存在
    for file_path in json_file_paths:
        if not os.path.exists(file_path):
            ERROR.logger.error(f"文件不存在: {file_path}")
            return False
    
    # 创建AI集成实例
    ai_integration = AIIntegration(json_file_paths)
    
    # 生成所有文件
    if ai_integration.generate_all_files():
        INFO.logger.info("文件生成成功")
        
        # 生成整合摘要
        summary = ai_integration.generate_integration_summary()
        INFO.logger.info("整合摘要:")
        INFO.logger.info(f"文件指纹: {summary.get('fingerprint', '')}")
        INFO.logger.info(f"OpenAPI信息: {summary.get('openapi_info', {})}")
        INFO.logger.info(f"关联关系信息: {summary.get('relation_info', {})}")
        INFO.logger.info(f"业务场景信息: {summary.get('scene_info', {})}")
        
        # 创建整合脚本
        if ai_integration.create_integration_script():
            INFO.logger.info("整合脚本创建成功")
        else:
            ERROR.logger.error("整合脚本创建失败")
            return False
    else:
        ERROR.logger.error("文件生成失败")
        return False
    
    # 获取生成的文件路径
    files = ai_integration.get_generated_files()
    INFO.logger.info("生成的文件:")
    for file_type, file_path in files.items():
        INFO.logger.info(f"{file_type}: {file_path}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)