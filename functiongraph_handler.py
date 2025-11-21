#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
华为云FunctionGraph函数部署处理器
将PytestAutoApi项目适配为华为云FunctionGraph函数
"""

import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime

# 添加项目路径到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入必要的模块
try:
    from api_server import app
    from utils.smart_auto.api_parser import APIParser
    from utils.smart_auto.test_generator import TestCaseGenerator
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

def handler(event, context):
    """
    华为云FunctionGraph函数入口点
    处理HTTP请求并返回响应
    """
    try:
        # 解析事件数据
        if isinstance(event, str):
            event = json.loads(event)
        
        # 提取请求信息
        request_method = event.get('httpMethod', 'GET')
        request_path = event.get('path', '/')
        request_headers = event.get('headers', {})
        request_body = event.get('body', '')
        query_parameters = event.get('queryStringParameters', {})
        
        # 模拟Flask请求环境
        with app.test_request_context(
            path=request_path,
            method=request_method,
            headers=request_headers,
            data=request_body,
            query_string=query_parameters
        ):
            # 处理请求
            response = app.full_dispatch_request()
            response_data = response.get_data(as_text=True)
            
            # 构建FunctionGraph响应格式
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': response_data,
                'isBase64Encoded': False
            }
    
    except Exception as e:
        # 错误处理
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            }),
            'isBase64Encoded': False
        }

def create_function_zip():
    """
    创建FunctionGraph函数部署包
    """
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建函数入口文件
        function_entry = os.path.join(temp_dir, 'index.py')
        with open(function_entry, 'w', encoding='utf-8') as f:
            f.write(open(__file__, 'r', encoding='utf-8').read())
        
        # 复制必要的项目文件
        import shutil
        
        # 复制api_server.py
        shutil.copy('api_server.py', os.path.join(temp_dir, 'api_server.py'))
        
        # 复制utils目录
        if os.path.exists('utils'):
            shutil.copytree('utils', os.path.join(temp_dir, 'utils'))
        
        # 复制common目录
        if os.path.exists('common'):
            shutil.copytree('common', os.path.join(temp_dir, 'common'))
        
        # 创建requirements.txt
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w', encoding='utf-8') as f:
            # 只包含FunctionGraph必要的依赖
            f.write("flask==2.0.3\n")
            f.write("flask-cors==3.0.10\n")
            f.write("requests==2.26.0\n")
            f.write("pyyaml==6.0\n")
            f.write("jsonpath==0.82\n")
        
        # 创建ZIP文件
        zip_path = 'pytest-auto-api-function.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        print(f"FunctionGraph函数部署包已创建: {zip_path}")
        return zip_path

if __name__ == '__main__':
    # 创建函数部署包
    create_function_zip()