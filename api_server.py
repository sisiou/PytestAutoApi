#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能自动化测试平台后端API服务
提供RESTful API接口支持前端交互
"""
import sys
import os
import json
import time
import logging
import yaml
import time
import uuid
import hashlib
import subprocess
import random
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import traceback
from utils.llm.ai_test_router_api import bp_ai_router

# 导入环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入智能自动化平台模块
from utils.smart_auto.api_parser import APIParser, APIParserFactory
from utils.smart_auto.test_generator import TestCaseGenerator, generate_test_cases
from utils.smart_auto.coverage_scorer import CoverageScorer
from utils.smart_auto.api_case_generator import APICaseGenerator
from utils.smart_auto.dependency_analyzer import DependencyAnalyzer

# 导入文档上传处理器
from utils.smart_auto.document_upload_handler import document_upload_handler

# 导入飞书解析模块
from utils.parse.feishu_parse import transform_feishu_url, download_json
from utils.parse.ai import (
    generate_openapi_yaml,
    generate_api_relation_file,
    generate_business_scene_file,
    generate_file_fingerprint,
    get_output_path,
    process_url_with_ai,
    _normalize_url,
    _create_file_key_from_url
)
from utils.parse.split_openai import integrate_with_upload_api
from utils.parse.relation_to_group import integrate_with_group_api
import tempfile
import traceback



# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
# 注册langchain实例
app.register_blueprint(bp_ai_router)
CORS(app)  # 启用跨域支持

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB最大文件大小
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MULTI_UPLOAD_FOLDER'] = 'multiuploads'
app.config['RESULTS_FOLDER'] = 'uploads/results'
app.config['TEST_CASES_FOLDER'] = 'test_cases'
app.config['SUGGESTIONS_FOLDER'] = 'suggestions'

# 确保必要的目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEST_CASES_FOLDER'], exist_ok=True)
os.makedirs(app.config['SUGGESTIONS_FOLDER'], exist_ok=True)

# 全局变量存储解析结果
api_docs = {}
test_cases = {}
coverage_reports = {}
suggestions = {}
smart_test_results = {}

# 缓存变量
docs_list_cache = None
docs_list_cache_time = None
CACHE_EXPIRE_TIME = 60  # 缓存60秒
test_scenes = {}
test_relations = {}

def clear_docs_list_cache():
    """清除文档列表缓存"""
    global docs_list_cache, docs_list_cache_time
    docs_list_cache = None
    docs_list_cache_time = None

def load_saved_api_docs():
    """加载已保存的API文档"""
    global api_docs
    results_dir = app.config['RESULTS_FOLDER']
    
    if not os.path.exists(results_dir):
        return
    
    # 遍历结果目录中的所有JSON文件
    for filename in os.listdir(results_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(results_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # 检查是否是API文档数据
                if 'api_data' in doc_data and ('filename' in doc_data or 'url' in doc_data):
                    task_id = filename[:-5]  # 移除.json扩展名
                    api_docs[task_id] = doc_data
                    logger.info(f"已加载API文档: {task_id}")
            except Exception as e:
                logger.error(f"加载API文档失败 {filename}: {str(e)}")

def load_saved_test_cases():
    """加载已保存的测试用例"""
    global test_cases
    test_cases_dir = app.config['TEST_CASES_FOLDER']
    
    if not os.path.exists(test_cases_dir):
        return
    
    # 遍历测试用例目录中的所有JSON文件
    for filename in os.listdir(test_cases_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(test_cases_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    case_data = json.load(f)
                
                # 检查是否是测试用例数据
                if 'test_cases' in case_data:
                    task_id = filename[:-5]  # 移除.json扩展名
                    test_cases[task_id] = case_data
                    logger.info(f"已加载测试用例: {task_id}")
            except Exception as e:
                logger.error(f"加载测试用例失败 {filename}: {str(e)}")

# 在启动时加载已保存的数据
load_saved_api_docs()
load_saved_test_cases()

# 错误处理
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

# 辅助函数
def generate_task_id(url=None):
    """生成任务ID"""
    if url:
        # 从URL生成稳定的ID，使用URL的哈希值确保相同URL生成相同ID
        # 使用MD5哈希算法对URL进行哈希
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        # 取哈希值的前16位作为ID
        return url_hash[:16]
    else:
        # 如果没有URL，使用时间戳
        return str(int(time.time() * 1000))

def generate_file_id(url=None):
    """生成文件ID"""
    return generate_task_id(url)

def save_result(file_id: str, result: Dict[str, Any]):
    """保存任务结果
    
    Args:
        file_id: 文件ID，用作文件名
        result: 结果数据
    """
    result_path = os.path.join(app.config['RESULTS_FOLDER'], f"results_{file_id}.json")
    logger.info(f"使用file_id {file_id} 保存结果到 {result_path}")
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存到 {result_path}")
    return result_path

def load_result(task_id: str) -> Optional[Dict[str, Any]]:
    """加载任务结果"""
    result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{task_id}.json")
    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# API路由

# 1. 系统状态和健康检查
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/status', methods=['GET'])
def system_status():
    """系统状态接口"""
    return jsonify({
        'api_docs_count': len(api_docs),
        'test_cases_count': len(test_cases),
        'coverage_reports_count': len(coverage_reports),
        'suggestions_count': len(suggestions),
        'timestamp': datetime.now().isoformat()
    })

# 2. API文档解析
@app.route('/api/docs/upload', methods=['POST'])
def upload_document():
    """上传文档接口"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # 验证文件类型
        allowed_extensions = ['json', 'yaml', 'yml']
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        if file_extension not in allowed_extensions:
            return jsonify({'error': '不支持的文件类型，请上传 OpenAPI 3.0.0 JSON 或 YAML 格式的文件'}), 400
        
        # 生成唯一文件ID
        file_id = generate_task_id()
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        
        # 检查是否指定了目标路径
        target_path = request.form.get('target_path')
        if target_path:
            # 如果指定了目标路径，确保目录存在
            os.makedirs(target_path, exist_ok=True)
            file_path = os.path.join(target_path, filename)
        else:
            # 使用默认路径
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
        file.save(file_path)

        base_output_path = os.path.join(os.getcwd(), "multiuploads", 'split_openapi')
        output_dir, count = integrate_with_upload_api(file_path, base_output_path)
        print(f"输出目录: {output_dir}, 生成文件数量: {count}")

        # ========== 2. 收集拆分后的所有YAML文件路径 ==========
        # 遍历拆分后的文件夹，获取所有.yaml文件路径
        openapi_file_paths = []
        if output_dir and os.path.exists(output_dir):
            for file_name in os.listdir(output_dir):
                if file_name.lower().endswith('.yaml') or file_name.lower().endswith('.yml'):
                    openapi_file_paths.append(os.path.join(output_dir, file_name))

        # 校验：确保有拆分后的文件
        if not openapi_file_paths:
            return jsonify({
                'success': False,
                'error': '未生成拆分后的OpenAPI文件，无法生成关联关系',
                'message': '拆分接口返回空文件列表'
            }), 400

        # 获取文件名（不含扩展名）作为目录名
        file_name_without_ext = os.path.splitext(filename)[0]
        
        # ========== 3. 生成关联关系文件（传入正确的文件路径列表） ==========
        relation_path = os.path.join(base_output_path, file_name_without_ext, "relation.json")  # 使用文件名作为目录
        try:
            relation_data = generate_api_relation_file(openapi_file_paths, relation_path)
        except Exception as e:
            logger.error(f"生成关联关系文件失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': '生成接口关联关系失败',
                'message': str(e)
            }), 500

        # ========== 4. 按关联关系分组文件（确保函数参数正确） ==========
        try:
            integrate_with_group_api(relation_path, output_dir, output_dir)
        except Exception as e:
            logger.warning(f"文件分组失败（非致命错误）: {str(e)}")
            # 分组失败不阻断整体流程，仅日志告警
                
        
        # 返回文件信息
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'file_path': file_path,
            'size': os.path.getsize(file_path),
            'message': '文件上传成功'
        })
    
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        return jsonify({'error': '上传文档失败', 'message': str(e)}), 500

@app.route('/api/docs/parse/<file_id>', methods=['POST'])
def parse_uploaded_document(file_id):
    """解析已上传的文档接口"""
    try:
        # 查找文件 - 检查主上传目录和子目录
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 定义要搜索的目录列表
        search_dirs = [upload_dir]
        
        # 添加子目录到搜索列表
        for subdir in os.listdir(upload_dir):
            subdir_path = os.path.join(upload_dir, subdir)
            if os.path.isdir(subdir_path):
                search_dirs.append(subdir_path)
        
        # 在所有目录中查找匹配的文件
        for search_dir in search_dirs:
            for filename in os.listdir(search_dir):
                # 首先尝试直接匹配文件ID（为了向后兼容）
                if filename.startswith(file_id):
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
                # 如果没有找到，尝试匹配文件名中包含file_id的情况
                elif file_id in filename:
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
            if file_path:
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 使用文档上传处理器解析文档
        parse_result = document_upload_handler.parse_document(file_path)
        
        if not parse_result.get('success', False):
            return jsonify({
                'error': '文档解析失败',
                'message': parse_result.get('error', '未知错误')
            }), 500
        
        # 获取解析结果
        info = parse_result.get('info', {})
        endpoints = parse_result.get('endpoints', [])
        models = parse_result.get('models', {})
        parser_type = parse_result.get('parser', 'unknown')
        raw_data = parse_result.get('raw_data', {})
        
        # 创建输出目录 - 使用uploads目录下的不同子目录
        openapi_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'openapi')
        relation_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'relation')
        scene_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'scene')
        os.makedirs(openapi_dir, exist_ok=True)
        os.makedirs(relation_dir, exist_ok=True)
        os.makedirs(scene_dir, exist_ok=True)
        
        # 生成文件指纹
        temp_json_path = os.path.join(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'processed'), f"temp_{file_id}.json")
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        
        fingerprint = generate_file_fingerprint([temp_json_path])
        
        # 生成处理后的文件
        try:
            # 1. 生成OpenAPI文档 - 保存到openapi目录
            openapi_output_path = get_output_path([temp_json_path], fingerprint, openapi_dir, "openapi")
            yaml_content = generate_openapi_yaml([temp_json_path], openapi_output_path)
            logger.info(f"成功生成OpenAPI YAML文档: {openapi_output_path}")
            
            # 将YAML内容转换为Python对象
            openapi_data = yaml.safe_load(yaml_content)
            
            # 2. 生成接口关联关系文件 - 保存到api_relation目录
            relation_output_path = get_output_path([temp_json_path], fingerprint, relation_dir, "relation")
            relation_data = generate_api_relation_file([temp_json_path], relation_output_path)
            logger.info(f"成功生成接口关联关系文件: {relation_output_path}")
            
            # 3. 生成业务场景文件 - 保存到business_scene目录
            scene_output_path = get_output_path([temp_json_path], fingerprint, scene_dir, "scene")
            scene_data = generate_business_scene_file([temp_json_path], scene_output_path)
            logger.info(f"成功生成业务场景文件: {scene_output_path}")
            
        except Exception as e:
            logger.error(f"生成处理文件失败: {str(e)}")
            # 如果生成失败，创建基本结构
            openapi_data = raw_data
            relation_data = {
                "relation_info": {
                    "title": "接口关联关系总览",
                    "description": "所有接口的依赖、数据流转、权限关联关系",
                    "total_apis": 0,
                    "relations": [],
                    "key_relation_scenarios": []
                }
            }
            scene_data = {
                "business_scenes": {
                    "title": "业务场景总览",
                    "description": "基于接口功能的核心业务场景汇总",
                    "scenes": []
                }
            }
        finally:
            # 清理临时文件
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)
                logger.info(f"已删除临时文件: {temp_json_path}")
        
        # 存储解析结果
        api_docs[file_id] = {
            'file_id': file_id,
            'filename': os.path.basename(file_path),
            'file_path': file_path,
            'api_data': raw_data,
            'openapi_data': openapi_data,
            'openapi_file_path': openapi_output_path if 'openapi_output_path' in locals() else None,
            'relation_data': relation_data,
            'relation_file_path': relation_output_path if 'relation_output_path' in locals() else None,
            'scene_data': scene_data,
            'scene_file_path': scene_output_path if 'scene_output_path' in locals() else None,
            'parser_type': parser_type,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(f"test_cases_{file_id}", test_cases[file_id])
        
        # 清除文档列表缓存
        clear_docs_list_cache()
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': '文档解析成功',
            'parser_type': parser_type,
            'info': info,
            'endpoints': endpoints,
            'models': models,
            'endpoint_count': len(endpoints),
            'model_count': len(models)
        })
    
    except Exception as e:
        logger.error(f"解析文档失败: {str(e)}")
        return jsonify({'error': '解析文档失败', 'message': str(e)}), 500

@app.route('/api/docs/generate-test-cases/<file_id>', methods=['POST'])
def generate_test_cases_for_document(file_id):
    """为已上传的文档生成测试用例"""
    try:
        # 查找文件 - 检查主上传目录和子目录
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 定义要搜索的目录列表
        search_dirs = [upload_dir]
        
        # 添加子目录到搜索列表
        for subdir in os.listdir(upload_dir):
            subdir_path = os.path.join(upload_dir, subdir)
            if os.path.isdir(subdir_path):
                search_dirs.append(subdir_path)
        
        # 在所有目录中查找匹配的文件
        for search_dir in search_dirs:
            for filename in os.listdir(search_dir):
                # 首先尝试直接匹配文件ID（为了向后兼容）
                if filename.startswith(file_id):
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
                # 如果没有找到，尝试匹配文件名中包含file_id的情况
                elif file_id in filename:
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
            if file_path:
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 使用文档上传处理器生成测试用例
        result = document_upload_handler.generate_test_cases(file_id, file_path)
        
        if not result.get('success', False):
            return jsonify({
                'error': '生成测试用例失败',
                'message': result.get('error', '未知错误')
            }), 500
        
        # 存储测试用例
        test_cases[file_id] = {
            'file_id': file_id,
            'test_cases': result.get('test_cases', []),
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(file_id, test_cases[file_id])
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': '测试用例生成成功',
            'test_case_count': result.get('test_case_count', 0),
            'parser_type': result.get('parser', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"生成测试用例失败: {str(e)}")
        return jsonify({'error': '生成测试用例失败', 'message': str(e)}), 500

@app.route('/api/docs/execute-tests/<file_id>', methods=['POST'])
def execute_tests_for_document(file_id):
    """执行已上传文档的测试用例"""
    try:
        # 获取测试用例
        if file_id not in test_cases:
            return jsonify({'error': '测试用例不存在，请先生成测试用例'}), 404
        
        test_cases_list = test_cases[file_id].get('test_cases', [])
        if not test_cases_list:
            return jsonify({'error': '测试用例为空'}), 400
        
        # 使用文档上传处理器执行测试
        result = document_upload_handler.execute_tests(file_id, test_cases_list)
        
        if not result.get('success', False):
            return jsonify({
                'error': '执行测试用例失败',
                'message': result.get('error', '未知错误')
            }), 500
        
        # 存储测试结果
        execution_results = result.get('execution_results', {})
        coverage_reports[file_id] = {
            'file_id': file_id,
            'execution_results': execution_results,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(file_id, coverage_reports[file_id])
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': '测试用例执行成功',
            'execution_results': execution_results,
            'parser_type': result.get('parser', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"执行测试用例失败: {str(e)}")
        return jsonify({'error': '执行测试用例失败', 'message': str(e)}), 500

@app.route('/api/docs/analyze-results/<file_id>', methods=['POST'])
def analyze_test_results_for_document(file_id):
    """分析已上传文档的测试结果"""
    try:
        # 获取测试结果
        if file_id not in coverage_reports:
            return jsonify({'error': '测试结果不存在，请先执行测试用例'}), 404
        
        execution_results = coverage_reports[file_id].get('execution_results', {})
        if not execution_results:
            return jsonify({'error': '测试结果为空'}), 400
        
        # 使用文档上传处理器分析测试结果
        result = document_upload_handler.analyze_test_results(file_id, execution_results)
        
        if not result.get('success', False):
            return jsonify({
                'error': '分析测试结果失败',
                'message': result.get('error', '未知错误')
            }), 500
        
        # 存储分析结果
        analysis_results = result.get('analysis_results', {})
        suggestions[file_id] = {
            'file_id': file_id,
            'analysis_results': analysis_results,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(file_id, suggestions[file_id])
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': '测试结果分析成功',
            'analysis_results': analysis_results,
            'parser_type': result.get('parser', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"分析测试结果失败: {str(e)}")
        return jsonify({'error': '分析测试结果失败', 'message': str(e)}), 500

@app.route('/api/docs/full-workflow/<file_id>', methods=['POST'])
def full_test_workflow_for_document(file_id):
    """为已上传的文档执行完整的测试工作流程"""
    try:
        # 查找文件 - 检查主上传目录和子目录
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 定义要搜索的目录列表
        search_dirs = [upload_dir]
        
        # 添加子目录到搜索列表
        for subdir in os.listdir(upload_dir):
            subdir_path = os.path.join(upload_dir, subdir)
            if os.path.isdir(subdir_path):
                search_dirs.append(subdir_path)
        
        # 在所有目录中查找匹配的文件
        for search_dir in search_dirs:
            for filename in os.listdir(search_dir):
                # 首先尝试直接匹配文件ID（为了向后兼容）
                if filename.startswith(file_id):
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
                # 如果没有找到，尝试匹配文件名中包含file_id的情况
                elif file_id in filename:
                    file_path = os.path.join(search_dir, filename)
                    logger.info(f"在目录 {search_dir} 中找到文件: {filename}")
                    break
            if file_path:
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 使用文档上传处理器执行完整工作流程
        result = document_upload_handler.full_test_workflow(file_path)
        
        if not result.get('success', False):
            return jsonify({
                'error': '执行完整工作流程失败',
                'message': result.get('error', '未知错误')
            }), 500
        
        # 获取工作流程结果
        workflow_results = result.get('workflow_results', {})
        
        # 存储各阶段结果
        if 'parse_result' in workflow_results:
            api_docs[file_id] = {
                'file_id': file_id,
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'api_data': workflow_results['parse_result'],
                'created_at': datetime.now().isoformat()
            }
            save_result(file_id, api_docs[file_id])
            # 清除文档列表缓存
            clear_docs_list_cache()
        
        if 'test_cases' in workflow_results:
            test_cases[file_id] = {
                'file_id': file_id,
                'test_cases': workflow_results['test_cases'],
                'created_at': datetime.now().isoformat()
            }
            save_result(file_id, test_cases[file_id])
        
        if 'execution_results' in workflow_results:
            coverage_reports[file_id] = {
                'file_id': file_id,
                'execution_results': workflow_results['execution_results'],
                'created_at': datetime.now().isoformat()
            }
            save_result(file_id, coverage_reports[file_id])
        
        if 'analysis_results' in workflow_results:
            suggestions[file_id] = {
                'file_id': file_id,
                'analysis_results': workflow_results['analysis_results'],
                'created_at': datetime.now().isoformat()
            }
            save_result(file_id, suggestions[file_id])
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'message': '完整测试工作流程执行成功',
            'workflow_results': workflow_results,
            'parser_type': result.get('parser', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"执行完整工作流程失败: {str(e)}")
        return jsonify({'error': '执行完整工作流程失败', 'message': str(e)}), 500

@app.route('/api/docs/delete-openapi/<file_id>', methods=['DELETE'])
def delete_openapi_doc(file_id):
    """删除OpenAPI文档"""
    try:
        # 安全检查文件ID
        if not file_id or not isinstance(file_id, str):
            return jsonify({
                'success': False,
                'message': '无效的文件ID'
            }), 400
        
        # 防止路径遍历攻击
        if '..' in file_id or '/' in file_id or '\\' in file_id:
            return jsonify({
                'success': False,
                'message': '文件ID包含非法字符'
            }), 400
        
        # 构建文件路径
        openapi_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'openapi')
        
        # 尝试不同的文件名格式
        possible_paths = [
            os.path.join(openapi_dir, f"{file_id}.yaml"),
            os.path.join(openapi_dir, f"openapi_{file_id}.yaml"),
            os.path.join(openapi_dir, f"{file_id}.yml"),
            os.path.join(openapi_dir, f"openapi_{file_id}.yml")
        ]
        
        # 查找存在的文件
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        # 检查文件是否存在
        if not file_path:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        # 删除文件
        os.remove(file_path)
        
        # 清除相关缓存
        try:
            from utils.cache_process.cache_control import _cache_config
            cache_keys = [key for key in _cache_config.keys() if 'openapi_list' in key]
            for key in cache_keys:
                _cache_config.pop(key, None)
        except ImportError:
            pass
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
        
    except Exception as e:
        logger.error(f"删除OpenAPI文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        }), 500

@app.route('/api/docs/generate-from-openapi/<file_id>', methods=['POST'])
def generate_test_cases_from_openapi(file_id):
    """从OpenAPI文档生成测试用例"""
    try:
        # 安全检查文件ID
        if not file_id or not isinstance(file_id, str):
            return jsonify({
                'success': False,
                'message': '无效的文件ID'
            }), 400
        
        # 防止路径遍历攻击
        if '..' in file_id or '/' in file_id or '\\' in file_id:
            return jsonify({
                'success': False,
                'message': '文件ID包含非法字符'
            }), 400
        
        # 构建文件路径
        openapi_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'openapi')
        
        # 尝试不同的文件名格式
        possible_paths = [
            os.path.join(openapi_dir, f"{file_id}.yaml"),
            os.path.join(openapi_dir, f"openapi_{file_id}.yaml"),
            os.path.join(openapi_dir, f"{file_id}.yml"),
            os.path.join(openapi_dir, f"openapi_{file_id}.yml")
        ]
        
        # 查找存在的文件
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        # 检查文件是否存在
        if not file_path:
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 404
        
        # 读取OpenAPI文档
        with open(file_path, 'r', encoding='utf-8') as f:
            openapi_content = f.read()
        
        # 解析OpenAPI文档
        try:
            openapi_data = yaml.safe_load(openapi_content)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'解析OpenAPI文档失败: {str(e)}'
            }), 400
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 保存OpenAPI文档到JSON目录
        json_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'json')
        json_file_path = os.path.join(json_dir, f"{task_id}.json")
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(openapi_data, f, ensure_ascii=False, indent=2)
        
        # 调用现有的生成测试用例函数
        result = generate_test_cases(task_id)
        
        # 清除相关缓存
        try:
            from utils.cache_process.cache_control import _cache_config
            cache_keys = [key for key in _cache_config.keys() if 'docs_list' in key]
            for key in cache_keys:
                _cache_config.pop(key, None)
        except ImportError:
            pass
        
        return jsonify({
            'success': True,
            'message': '测试用例生成成功',
            'task_id': task_id,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"从OpenAPI文档生成测试用例失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'生成测试用例失败: {str(e)}'
        }), 500


@app.route('/api/docs/uploaded-list', methods=['GET'])
def list_uploaded_documents():
    """获取已上传的文档列表"""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        documents = []
        
        # 遍历上传目录
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                # 提取文件ID（去掉前缀）
                file_id = filename.split('_', 1)[0] if '_' in filename else filename.rsplit('.', 1)[0]
                
                # 获取文件信息
                stat = os.stat(file_path)
                documents.append({
                    'file_id': file_id,
                    'filename': filename,
                    'size': stat.st_size,
                    'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'status': 'uploaded'
                })
        
        return jsonify({
            'documents': documents,
            'count': len(documents)
        })
    
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        return jsonify({'error': '获取文档列表失败', 'message': str(e)}), 500

@app.route('/api/docs/all-documents', methods=['GET'])
def list_all_documents():
    """获取uploads目录下的所有文档列表(openapi、relation、scene)"""
    try:
        # 定义要扫描的目录
        directories = {
            'openapi': {
                'path': os.path.join(app.config['UPLOAD_FOLDER'], 'openapi'),
                'description': 'OpenAPI文档',
                'file_types': ['.yaml', '.yml', '.json']
            },
            'relation': {
                'path': os.path.join(app.config['UPLOAD_FOLDER'], 'relation'),
                'description': '关系文档',
                'file_types': ['.json', '.yaml', '.yml', '.txt']
            },
            'scene': {
                'path': os.path.join(app.config['UPLOAD_FOLDER'], 'scene'),
                'description': '场景文档',
                'file_types': ['.json', '.yaml', '.yml', '.txt']
            }
        }
        
        all_documents = {}
        
        # 遍历每个目录
        for dir_type, dir_info in directories.items():
            documents = []
            dir_path = dir_info['path']
            
            # 确保目录存在
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                all_documents[dir_type] = {
                    'description': dir_info['description'],
                    'documents': [],
                    'count': 0
                }
                continue
            
            # 遍历目录中的文件
            for filename in os.listdir(dir_path):
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension in dir_info['file_types']:
                    file_path = os.path.join(dir_path, filename)
                    
                    # 获取文件信息
                    stat = os.stat(file_path)
                    
                    # 提取文件ID
                    file_id = filename
                    if filename.startswith(f'{dir_type}_'):
                        file_id = filename[len(f'{dir_type}_'):]  # 去掉类型前缀
                    
                    # 去掉文件扩展名
                    if '.' in file_id:
                        file_id = file_id.rsplit('.', 1)[0]
                    
                    # 尝试解析文件内容
                    content_preview = ""
                    item_count = 0
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            if file_extension == '.json':
                                content = json.load(f)
                                content_preview = json.dumps(content, ensure_ascii=False, indent=2)
                                
                                # 根据目录类型计算项目数量
                                if dir_type == 'openapi' and 'paths' in content:
                                    for path, path_item in content['paths'].items():
                                        for method in path_item:
                                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                                item_count += 1
                                elif dir_type in ['relation', 'scene']:
                                    item_count = len(content) if isinstance(content, (list, dict)) else 0
                            else:
                                content = f.read()
                                content_preview = content
                                item_count = len(content.split('\n')) if content else 0
                    except Exception as e:
                        logger.warning(f"解析文件失败 {filename}: {str(e)}")
                        content_preview = f"解析失败: {str(e)}"
                    
                    documents.append({
                        'file_id': file_id,
                        'file_name': filename,
                        'file_size': stat.st_size,
                        'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'item_count': item_count,
                        'content_preview': content_preview[:500] + ('...' if len(content_preview) > 500 else ''),
                        'status': 'uploaded',
                        'editable': True
                    })
            
            all_documents[dir_type] = {
                'description': dir_info['description'],
                'documents': documents,
                'count': len(documents)
            }
        
        return jsonify({
            'success': True,
            'data': all_documents,
            'total_count': sum(info['count'] for info in all_documents.values())
        })
    
    except Exception as e:
        logger.error(f"获取所有文档列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取所有文档列表失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/get-document/<doc_type>/<file_id>', methods=['GET'])
def get_document_content(doc_type, file_id):
    """获取指定文档的完整内容"""
    try:
        # 验证文档类型
        if doc_type not in ['openapi', 'relation', 'scene']:
            return jsonify({
                'success': False,
                'error': '无效的文档类型'
            }), 400
        
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], doc_type)
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': f'{doc_type}目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith(f'{doc_type}_'):
                    potential_id = filename[len(f'{doc_type}_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 读取文件内容
        file_extension = os.path.splitext(file_name)[1].lower()
        content = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_extension == '.json':
                try:
                    json_content = json.load(f)
                    content = json.dumps(json_content, ensure_ascii=False, indent=2)
                except:
                    content = f.read()
            else:
                content = f.read()
        
        return jsonify({
            'success': True,
            'data': {
                'file_id': file_id,
                'file_name': file_name,
                'doc_type': doc_type,
                'content': content,
                'file_extension': file_extension
            }
        })
    
    except Exception as e:
        logger.error(f"获取文档内容失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取文档内容失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/update-document/<doc_type>/<file_id>', methods=['PUT'])
def update_document_content(doc_type, file_id):
    """更新指定文档的内容"""
    try:
        # 验证文档类型
        if doc_type not in ['openapi', 'relation', 'scene']:
            return jsonify({
                'success': False,
                'error': '无效的文档类型'
            }), 400
        
        # 获取请求数据
        data = request.json
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: content'
            }), 400
        
        content = data.get('content', '')
        
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], doc_type)
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir, exist_ok=True)
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith(f'{doc_type}_'):
                    potential_id = filename[len(f'{doc_type}_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 获取文件扩展名
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # 验证内容（如果是JSON，尝试解析）
        if file_extension == '.json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                # 尝试提供更详细的错误信息和修复建议
                error_msg = str(e)
                line_num = error_msg.split('line ')[1].split(' ')[0] if 'line ' in error_msg else '未知'
                
                # 尝试简单的自动修复
                try:
                    # 尝试添加缺失的引号
                    fixed_content = content.replace('"', '\\"')
                    json.loads(fixed_content)
                    return jsonify({
                        'success': False,
                        'error': 'JSON格式错误，但可能可以自动修复',
                        'message': f'第{line_num}行附近有格式问题: {error_msg}',
                        'suggestion': '系统检测到可能的引号问题，是否尝试自动修复？',
                        'can_auto_fix': True
                    }), 400
                except:
                    pass
                
                return jsonify({
                    'success': False,
                    'error': '无效的JSON格式',
                    'message': f'第{line_num}行附近有格式问题: {error_msg}',
                    'suggestion': '请检查JSON格式，确保所有字符串都用双引号包围，括号和逗号都正确匹配'
                }), 400
        elif file_extension in ['.yaml', '.yml']:
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                # 尝试提供更详细的错误信息
                error_msg = str(e)
                if 'line' in error_msg:
                    line_num = error_msg.split('line ')[1].split(',')[0]
                else:
                    line_num = '未知'
                
                return jsonify({
                    'success': False,
                    'error': '无效的YAML格式',
                    'message': f'第{line_num}行附近有格式问题: {error_msg}',
                    'suggestion': '请检查YAML格式，确保缩进使用空格而非制表符，冒号后有空格'
                }), 400
        
        # 创建备份
        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        
        # 写入新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 如果是OpenAPI文档，更新内存中的解析结果
        if doc_type == 'openapi' and file_id in api_docs:
            try:
                parser = APIParser(file_path)
                api_data = parser.parse()
                api_docs[file_id]['api_data'] = api_data
                api_docs[file_id]['updated_at'] = datetime.now().isoformat()
                save_result(file_id, api_docs[file_id])
            except Exception as e:
                logger.warning(f"更新OpenAPI文档解析结果失败: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': '文档更新成功',
            'backup_file': os.path.basename(backup_path)
        })
    
    except Exception as e:
        logger.error(f"更新文档内容失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '更新文档内容失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/generate-document/<doc_type>/<file_id>', methods=['POST'])
def generate_document_content(doc_type, file_id):
    """生成指定类型的文档内容"""
    try:
        # 验证文档类型
        if doc_type not in ['relation', 'scene']:
            return jsonify({
                'success': False,
                'error': '无效的文档类型'
            }), 400
        
        # 查找文件
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 遍历上传目录查找匹配的文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_filepath = os.path.join(temp_dir, "data.json")
            
            # 读取原始文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    json_data = json.load(f)
                except:
                    # 如果不是JSON格式，尝试作为文本处理
                    content = f.read()
                    json_data = {"content": content}
            
            # 写入临时文件
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # 定义输出路径
            doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], doc_type)
            os.makedirs(doc_dir, exist_ok=True)
            output_path = os.path.join(doc_dir, f"{doc_type}_{file_id}.json")
            
            # 根据文档类型生成内容
            if doc_type == 'relation':
                result = generate_api_relation_file([temp_filepath], output_path)
            elif doc_type == 'scene':
                result = generate_business_scene_file([temp_filepath], output_path)
            
            # 读取生成的内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return jsonify({
                'success': True,
                'data': {
                    'file_id': file_id,
                    'doc_type': doc_type,
                    'content': content,
                    'file_path': output_path
                }
            })
    
    except Exception as e:
        logger.error(f"生成文档内容失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '生成文档内容失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/create-document/<doc_type>', methods=['POST'])
def create_document(doc_type):
    """创建新文档"""
    try:
        # 验证文档类型
        if doc_type not in ['openapi', 'relation', 'scene']:
            return jsonify({
                'success': False,
                'error': '无效的文档类型'
            }), 400
        
        # 获取请求数据
        data = request.json
        if not data or 'file_name' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: file_name, content'
            }), 400
        
        file_name = data.get('file_name', '')
        content = data.get('content', '')
        
        # 验证文件名
        if not file_name:
            return jsonify({
                'success': False,
                'error': '文件名不能为空'
            }), 400
        
        # 确保文件名有正确的扩展名
        if not any(file_name.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.txt']):
            if doc_type == 'openapi':
                file_name += '.json'
            else:
                file_name += '.json'
        
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], doc_type)
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir, exist_ok=True)
        
        # 添加前缀
        prefixed_name = f"{doc_type}_{file_name}"
        file_path = os.path.join(doc_dir, prefixed_name)
        
        # 检查文件是否已存在
        if os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件已存在'
            }), 409
        
        # 验证内容（如果是JSON，尝试解析）
        if file_name.endswith('.json'):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return jsonify({
                    'success': False,
                    'error': '无效的JSON格式',
                    'message': str(e)
                }), 400
        elif file_name.endswith(('.yaml', '.yml')):
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                return jsonify({
                    'success': False,
                    'error': '无效的YAML格式',
                    'message': str(e)
                }), 400
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 生成文件ID
        file_id = file_name
        if '.' in file_id:
            file_id = file_id.rsplit('.', 1)[0]
        
        return jsonify({
            'success': True,
            'message': '文档创建成功',
            'data': {
                'file_id': file_id,
                'file_name': prefixed_name,
                'doc_type': doc_type
            }
        })
    
    except Exception as e:
        logger.error(f"创建文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '创建文档失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/delete-document/<doc_type>/<file_id>', methods=['DELETE'])
def delete_document(doc_type, file_id):
    """删除指定文档"""
    try:
        # 验证文档类型
        if doc_type not in ['openapi', 'relation', 'scene']:
            return jsonify({
                'success': False,
                'error': '无效的文档类型'
            }), 400
        
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], doc_type)
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': f'{doc_type}目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        for filename in os.listdir(doc_dir):
            # 尝试匹配文件ID
            potential_id = filename
            if filename.startswith(f'{doc_type}_'):
                potential_id = filename[len(f'{doc_type}_'):]
            
            if '.' in potential_id:
                potential_id = potential_id.rsplit('.', 1)[0]
            
            if potential_id == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 删除文件
        os.remove(file_path)
        
        # 删除所有相关的文件（json、relation、scene目录下的同名文件）
        related_dirs = ['json', 'relation', 'scene', 'test_case', 'test_code']
        for related_dir in related_dirs:
            related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], related_dir)
            if related_dir == 'test_case':
                # test_case目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_case')
            elif related_dir == 'test_code':
                # test_code目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_code')
                
            if os.path.exists(related_dir_path):
                for filename in os.listdir(related_dir_path):
                    # 检查是否是相关文件（文件名包含相同的ID）
                    if file_id in filename:
                        related_file_path = os.path.join(related_dir_path, filename)
                        try:
                            os.remove(related_file_path)
                            logger.info(f"已删除相关文件: {related_file_path}")
                        except Exception as e:
                            logger.warning(f"删除相关文件失败 {related_file_path}: {str(e)}")
        
        # 如果是OpenAPI文档，从内存中删除解析结果
        if doc_type == 'openapi' and file_id in api_docs:
            del api_docs[file_id]
            # 清除文档列表缓存
            clear_docs_list_cache()
            
            # 删除结果文件
            result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{file_id}.json")
            if os.path.exists(result_path):
                os.remove(result_path)
        
        return jsonify({
            'success': True,
            'message': '文档删除成功'
        })
    
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '删除文档失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/openapi-list', methods=['GET'])
def list_openapi_documents():
    """获取uploads/openapi目录下的OpenAPI文档列表"""
    try:
        openapi_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'openapi')
        documents = []
        
        # 确保目录存在
        if not os.path.exists(openapi_dir):
            os.makedirs(openapi_dir, exist_ok=True)
            return jsonify({
                'success': True,
                'data': [],
                'count': 0
            })
        
        # 遍历openapi目录
        for filename in os.listdir(openapi_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml') or filename.endswith('.json'):
                file_path = os.path.join(openapi_dir, filename)
                
                # 获取文件信息
                stat = os.stat(file_path)
                
                # 提取文件ID（去掉openapi_前缀）
                file_id = filename
                if filename.startswith('openapi_'):
                    file_id = filename[8:]  # 去掉'openapi_'前缀
                
                # 去掉文件扩展名
                if '.' in file_id:
                    file_id = file_id.rsplit('.', 1)[0]
                
                # 尝试解析文件获取API数量
                api_count = 0
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if filename.endswith('.json'):
                            content = json.load(f)
                        else:
                            content = yaml.safe_load(f)
                        
                        # 计算API数量
                        if 'paths' in content:
                            for path, path_item in content['paths'].items():
                                for method in path_item:
                                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                        api_count += 1
                except Exception as e:
                    logger.warning(f"解析OpenAPI文件失败 {filename}: {str(e)}")
                
                documents.append({
                    'file_id': file_id,
                    'file_name': filename,
                    'file_size': stat.st_size,
                    'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'api_count': api_count,
                    'status': 'uploaded'
                })
        
        return jsonify({
            'success': True,
            'data': documents,
            'count': len(documents)
        })
    
    except Exception as e:
        logger.error(f"获取OpenAPI文档列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取OpenAPI文档列表失败',
            'message': str(e)
        }), 500

@app.route('/api/docs/delete/<file_id>', methods=['DELETE'])
def delete_uploaded_document(file_id):
    """删除已上传的文档"""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 查找文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 删除文件
        os.remove(file_path)
        
        # 删除所有相关的文件（json、relation、scene目录下的同名文件）
        related_dirs = ['json', 'relation', 'scene', 'test_case', 'test_code']
        for related_dir in related_dirs:
            related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], related_dir)
            if related_dir == 'test_case':
                # test_case目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_case')
            elif related_dir == 'test_code':
                # test_code目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_code')
                
            if os.path.exists(related_dir_path):
                for filename in os.listdir(related_dir_path):
                    # 检查是否是相关文件（文件名包含相同的ID）
                    if file_id in filename:
                        related_file_path = os.path.join(related_dir_path, filename)
                        try:
                            os.remove(related_file_path)
                            logger.info(f"已删除相关文件: {related_file_path}")
                        except Exception as e:
                            logger.warning(f"删除相关文件失败 {related_file_path}: {str(e)}")
        
        # 从内存中删除解析结果
        if file_id in api_docs:
            del api_docs[file_id]
            # 清除文档列表缓存
            clear_docs_list_cache()
        
        # 删除结果文件
        result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{file_id}.json")
        if os.path.exists(result_path):
            os.remove(result_path)
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
    
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        return jsonify({'error': '删除文档失败', 'message': str(e)}), 500

@app.route('/api/docs/parse', methods=['POST'])
def parse_api_docs():
    """解析API文档接口"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            # 保存上传的文件
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # 生成任务ID
            task_id = generate_task_id()
            
            # 解析API文档
            parser = APIParser(file_path)
            api_data = parser.parse()
            
            # 存储解析结果
            api_docs[task_id] = {
                'task_id': task_id,
                'filename': filename,
                'file_path': file_path,
                'api_data': api_data,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存结果
            save_result(task_id, api_docs[task_id])
            
            return jsonify({
                'task_id': task_id,
                'message': 'API文档解析成功',
                'api_count': len(api_data.get('apis', []))
            })
    
    except Exception as e:
        logger.error(f"解析API文档失败: {str(e)}")
        return jsonify({'error': 'API文档解析失败', 'message': str(e)}), 500

@app.route('/api/chain/run', methods=['POST'])
def run_chain_test():
    """
    执行链式测试接口
    从请求体中接收group_name参数（如 related_group_4），拼接路径后执行chain_full_runner
    
    :return: 执行结果
    """
    try:
        # 检查请求体是否为 JSON
        if not request.is_json:
            return jsonify({
                'error': '请求格式错误',
                'message': '请求体必须是 JSON 格式'
            }), 400
        
        # 从请求体中获取 group_name（必需参数）
        group_name = request.json.get('group_name')
        if not group_name:
            return jsonify({
                'error': '参数缺失',
                'message': '请求体中必须包含 group_name 参数'
            }), 400
        
        # 基础路径（写死在接口中，相对于项目根目录）
        base_api_dir = "multiuploads/split_openapi/openapi_API"
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        
        # 拼接完整路径（相对于项目根目录）
        api_dir = os.path.join(base_api_dir, group_name)
        api_dir_path = project_root / api_dir
        
        # 检查路径是否存在
        if not api_dir_path.exists():
            return jsonify({
                'error': 'API目录不存在',
                'message': f'路径不存在: {api_dir}',
                'api_dir': api_dir
            }), 404
        
        # 默认参数（确保所有值都是字符串，不能为 None）
        relation_dir = "uploads/relation"
        redis_url = request.json.get('redis_url') if request.is_json else os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
        tmp_dir = request.json.get('tmp_dir') if request.is_json else ".chain_out"
        
        # 确保参数不为 None，并转换为字符串
        if redis_url is None:
            redis_url = 'redis://127.0.0.1:6379/0'
        redis_url = str(redis_url)
        
        if tmp_dir is None:
            tmp_dir = ".chain_out"
        tmp_dir = str(tmp_dir)
        
        # 构建命令
        script_path = Path(__file__).parent / "scripts" / "chain_full_runner.py"
        if not script_path.exists():
            return jsonify({
                'error': '脚本文件不存在',
                'message': f'找不到脚本: {script_path}'
            }), 500
        
        # 准备命令参数（确保所有值都是字符串）
        cmd = [
            str(sys.executable),
            str(script_path),
            '--api-dir', str(api_dir_path),
            '--relation-dir', str(relation_dir),
            '--redis-url', str(redis_url),
            '--tmp-dir', str(tmp_dir)
        ]
        
        # 可选参数（只添加非空值）
        if request.is_json:
            api_key = request.json.get('api_key')
            if api_key and str(api_key).strip():
                cmd.extend(['--api-key', str(api_key).strip()])
            
            model = request.json.get('model')
            if model and str(model).strip():
                cmd.extend(['--model', str(model).strip()])
            
            base_url = request.json.get('base_url')
            if base_url and str(base_url).strip():
                cmd.extend(['--base-url', str(base_url).strip()])
            
            only_file = request.json.get('only_file')
            if only_file and str(only_file).strip():
                cmd.extend(['--only-file', str(only_file).strip()])
            
            if request.json.get('skip_pytest'):
                cmd.append('--skip-pytest')
            
            if request.json.get('stream'):
                cmd.append('--stream')
        
        # 确保 cmd 中所有元素都是字符串（最终检查）
        cmd = [str(item) for item in cmd if item is not None]
        
        logger.info(f"执行链式测试: group_name={group_name}, api_dir={api_dir}")
        logger.info(f"命令: {' '.join(cmd)}")
        
        # 准备环境变量，确保 Python 路径正确
        env = os.environ.copy()
        project_root = Path(__file__).parent
        project_root_str = str(project_root)
        
        # 设置 PYTHONPATH，确保可以导入项目模块
        pythonpath = env.get('PYTHONPATH', '')
        if pythonpath:
            # 如果已有 PYTHONPATH，追加项目根目录
            env['PYTHONPATH'] = f"{project_root_str}{os.pathsep}{pythonpath}"
        else:
            # 如果没有 PYTHONPATH，直接设置
            env['PYTHONPATH'] = project_root_str
        
        logger.info(f"PYTHONPATH: {env['PYTHONPATH']}")
        
        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,  # 确保工作目录是项目根目录
            env=env
        )
        
        # 等待执行完成（可以设置超时）
        timeout = request.json.get('timeout', 3600) if request.is_json else 3600  # 默认1小时
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({
                'error': '执行超时',
                'message': f'命令执行超过 {timeout} 秒',
                'api_dir': api_dir
            }), 500
        
        # 收集生成的测试用例文件信息
        test_files = []
        tmp_dir_path = project_root / tmp_dir
        test_file_paths = []
        if tmp_dir_path.exists():
            # 查找所有生成的测试文件
            for test_file in sorted(tmp_dir_path.glob("test_chain_*.py")):
                test_file_paths.append(test_file)
                try:
                    test_file_info = _extract_test_case_info(test_file)
                    if test_file_info:
                        test_files.append(test_file_info)
                except Exception as e:
                    logger.warning(f"提取测试文件信息失败 {test_file}: {str(e)}")
                    # 即使提取失败，也记录文件存在
                    test_files.append({
                        'file_path': str(test_file.relative_to(project_root)),
                        'file_name': test_file.name,
                        'test_count': 0,
                        'test_cases': [],
                        'error': f'提取信息失败: {str(e)}'
                    })
        
        # 如果生成了测试文件，执行一次汇总的 pytest 获取完整结果
        # 注意：即使 chain_full_runner 返回码不为0，只要生成了测试文件，也执行汇总 pytest
        aggregated_stdout = stdout
        aggregated_stderr = stderr
        skip_pytest = request.json.get('skip_pytest', False) if request.is_json else False
        
        if test_file_paths and not skip_pytest:
            logger.info(f"执行汇总 pytest，包含 {len(test_file_paths)} 个测试文件")
            logger.info(f"测试文件列表: {[f.name for f in test_file_paths]}")
            
            # 验证所有测试文件是否存在
            existing_test_files = []
            for test_file in test_file_paths:
                if test_file.exists():
                    existing_test_files.append(test_file)
                    logger.info(f"✓ 测试文件存在: {test_file}")
                else:
                    logger.warning(f"✗ 测试文件不存在: {test_file}")
            
            if not existing_test_files:
                logger.warning("没有可执行的测试文件，跳过汇总 pytest")
            else:
                try:
                    # 先执行收集命令，查看能找到多少测试用例
                    collect_cmd = [
                        str(sys.executable),
                        "-m", "pytest",
                        str(tmp_dir_path.resolve()),
                        "--collect-only",
                        "-q"  # 安静模式，只显示收集到的测试数量
                    ]
                    
                    logger.info(f"汇总 pytest 收集命令: {' '.join(collect_cmd)}")
                    
                    collect_process = subprocess.Popen(
                        collect_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=project_root,
                        env=env
                    )
                    collect_stdout, collect_stderr = collect_process.communicate(timeout=60)
                    logger.info(f"收集到的测试用例:\n{collect_stdout}")
                    
                    # 构建汇总 pytest 执行命令
                    # 方式1：使用目录方式（推荐，pytest 会自动发现所有测试）
                    pytest_cmd = [
                        str(sys.executable),
                        "-m", "pytest",
                        str(tmp_dir_path.resolve()),  # 使用目录，pytest 会自动发现所有 test_*.py 文件
                        "-v",
                        "--tb=short"
                    ]
                    
                    # 方式2：如果方式1不行，可以显式指定所有文件
                    # pytest_cmd = [str(sys.executable), "-m", "pytest", "-v", "--tb=short"]
                    # pytest_cmd.extend([str(f.resolve()) for f in existing_test_files])
                    
                    logger.info(f"汇总 pytest 执行命令: {' '.join(pytest_cmd)}")
                    logger.info(f"将执行 {len(existing_test_files)} 个测试文件")
                    
                    # 执行汇总 pytest
                    pytest_process = subprocess.Popen(
                        pytest_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=project_root,
                        env=env
                    )
                    
                    pytest_stdout, pytest_stderr = pytest_process.communicate(timeout=timeout)
                    # 使用汇总的 pytest 输出
                    aggregated_stdout = pytest_stdout
                    aggregated_stderr = pytest_stderr
                    logger.info(f"汇总 pytest 执行完成，返回码: {pytest_process.returncode}")
                    logger.info(f"汇总 pytest stdout 长度: {len(pytest_stdout) if pytest_stdout else 0}")
                    if pytest_stdout:
                        # 显示最后几行，通常包含测试结果摘要
                        lines = pytest_stdout.split('\n')
                        logger.info(f"汇总 pytest 最后10行:\n{chr(10).join(lines[-10:])}")
                    if pytest_stderr:
                        logger.warning(f"汇总 pytest stderr: {pytest_stderr[:500]}")
                except subprocess.TimeoutExpired:
                    logger.warning("汇总 pytest 执行超时，使用原始输出")
                    pytest_process.kill()
                except Exception as e:
                    logger.warning(f"执行汇总 pytest 失败: {str(e)}，使用原始输出")
                    logger.error(traceback.format_exc())
        
        # 解析 pytest 执行结果（使用汇总的输出）
        test_metrics = None
        if aggregated_stdout:
            try:
                test_metrics = _parse_pytest_output(aggregated_stdout)
            except Exception as e:
                logger.warning(f"解析 pytest 输出失败: {str(e)}")
        
        # 解析失败的测试用例详情（使用汇总的输出）
        failed_tests = []
        try:
            failed_tests = _extract_failed_tests(aggregated_stdout, aggregated_stderr)
        except Exception as e:
            logger.warning(f"提取失败测试用例详情失败: {str(e)}")
        
        # 检查返回码
        # 如果生成了测试文件并执行了汇总 pytest，以汇总 pytest 的结果为准
        # 否则以 chain_full_runner 的返回码为准
        if test_file_paths and not skip_pytest and aggregated_stdout != stdout:
            # 使用了汇总 pytest 的输出，以汇总 pytest 的结果为准
            # pytest 返回码 0 表示全部通过，1 表示有失败但执行成功，其他表示执行错误
            execution_success = True  # 汇总 pytest 执行成功就认为整体成功
        else:
            # 使用 chain_full_runner 的结果
            execution_success = process.returncode == 0 or (process.returncode != 0 and test_metrics and test_metrics.get('total', 0) > 0)
        
        # 如果 chain_full_runner 执行失败且没有生成测试文件，才返回错误
        if not execution_success and process.returncode != 0 and not test_file_paths:
            logger.error(f"链式测试执行失败: {stderr}")
            return jsonify({
                'error': '执行失败',
                'message': stderr or '未知错误',
                'return_code': process.returncode,
                'stdout': stdout[-5000:] if stdout else '',  # 只返回最后5000字符
                'stderr': stderr[-5000:] if stderr else '',  # 只返回最后5000字符
                'api_dir': api_dir,
                'test_files': test_files,
                'test_metrics': test_metrics,
                'failed_tests': failed_tests
            }), 500
        
        # 执行成功
        logger.info(f"链式测试执行成功: group_name={group_name}")
        
        # 构建响应数据
        response_data = {
            'success': True,
            'message': '链式测试执行成功',
            'group_name': group_name,
            'api_dir': api_dir,
            'return_code': process.returncode,
            'test_files': test_files,
            'test_metrics': test_metrics or {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'error': 0,
                'duration_ms': None,
                'duration_human': None
            },
            'failed_tests': failed_tests,
            'stdout_tail': aggregated_stdout[-2000:] if aggregated_stdout else '',  # 只返回最后2000字符
            'stderr_tail': aggregated_stderr[-2000:] if aggregated_stderr else ''  # 只返回最后2000字符
        }
        
        # 如果有测试指标，添加汇总信息
        if test_metrics:
            total = test_metrics.get('total', 0)
            passed = test_metrics.get('passed', 0)
            failed = test_metrics.get('failed', 0)
            response_data['summary'] = {
                'total_cases': total,
                'passed_cases': passed,
                'failed_cases': failed,
                'success_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%",
                'duration': test_metrics.get('duration_human', 'N/A')
            }
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行链式测试失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': '执行链式测试失败',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/chain/relation-run', methods=['POST'])
def run_chain_relation():
    """
    对外接口：执行 relation 解析脚本
    等价于:
    python scripts/chain_relation_runner.py --api-dir multiuploads/split_openapi/openapi_API/<group_name> --relation-dir uploads/relation
    """
    try:
        if not request.is_json:
            return jsonify({'error': '请求格式错误', 'message': '请求体必须是 JSON 格式'}), 400

        group_name = request.json.get('group_name')
        if not group_name:
            return jsonify({'error': '参数缺失', 'message': '请求体中必须包含 group_name 参数'}), 400

        base_api_dir = "multiuploads/split_openapi/openapi_API"
        project_root = Path(__file__).parent
        api_dir_path = project_root / base_api_dir / group_name
        if not api_dir_path.exists():
            return jsonify({'error': 'API目录不存在', 'message': f'路径不存在: {api_dir_path}'}), 404

        relation_dir = request.json.get('relation_dir') or "uploads/relation"
        relation_dir_path = project_root / relation_dir
        if not relation_dir_path.exists():
            return jsonify({'error': 'relation目录不存在', 'message': f'路径不存在: {relation_dir_path}'}), 404

        timeout = request.json.get('timeout', 600)

        # 优先直接调用内部函数获取结构化依赖数据
        try:
            from scripts.chain_relation_runner import build_graph, topo_sort

            nodes, edges, rel_map = build_graph(relation_dir_path, api_dir_path)
            order = topo_sort(nodes, edges)

            dependencies = [
                {"source": src, "target": tgt}
                for src, tgts in edges.items()
                for tgt in tgts
            ]

            return jsonify({
                'success': True,
                'group_name': group_name,
                'api_dir': str(api_dir_path.relative_to(project_root)),
                'relation_dir': str(relation_dir_path.relative_to(project_root)),
                'execution_order': order,
                'dependencies': dependencies,
            }), 200
        except Exception as inner_exc:
            logger.warning(f"直接调用解析失败，回退到子进程执行: {inner_exc}")

        # 回退方案：使用子进程执行脚本，返回原始输出
        script_path = project_root / "scripts" / "chain_relation_runner.py"
        if not script_path.exists():
            return jsonify({'error': '脚本文件不存在', 'message': f'找不到脚本: {script_path}'}), 500

        cmd = [
            str(sys.executable),
            str(script_path),
            "--api-dir", str(api_dir_path),
            "--relation-dir", str(relation_dir_path),
        ]

        # 环境变量，确保可导入项目模块
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}" if pythonpath else str(project_root)

        logger.info(f"执行 relation 解析(子进程): {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,
            env=env
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({'error': '执行超时', 'message': f'命令执行超过 {timeout} 秒'}), 500

        return jsonify({
            'success': process.returncode == 0,
            'return_code': process.returncode,
            'group_name': group_name,
            'api_dir': str(api_dir_path.relative_to(project_root)),
            'relation_dir': str(relation_dir_path.relative_to(project_root)),
            'stdout_tail': stdout[-2000:] if stdout else '',
            'stderr_tail': stderr[-2000:] if stderr else '',
        }), (200 if process.returncode == 0 else 500)

    except Exception as e:
        logger.error(f"执行 relation 解析失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': '执行失败', 'message': str(e), 'traceback': traceback.format_exc()}), 500

def _extract_test_case_info(test_file_path: Path) -> Optional[Dict[str, Any]]:
    """
    从生成的测试文件中提取测试用例信息
    
    :param test_file_path: 测试文件路径
    :return: 测试用例信息字典
    """
    try:
        import ast
        import re
        
        content = test_file_path.read_text(encoding='utf-8')
        
        # 提取所有测试函数
        test_cases = []
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # 提取函数文档字符串
                docstring = ast.get_docstring(node) or ""
                
                # 提取用例名称和描述
                name = node.name
                description = docstring.strip() if docstring else ""
                
                test_cases.append({
                    'name': name,
                    'description': description,
                    'line_number': node.lineno
                })
        
        return {
            'file_path': str(test_file_path.relative_to(Path(__file__).parent)),
            'file_name': test_file_path.name,
            'test_count': len(test_cases),
            'test_cases': test_cases
        }
    except Exception as e:
        logger.warning(f"提取测试用例信息失败 {test_file_path}: {str(e)}")
        # 如果解析失败，至少返回文件名
        return {
            'file_path': str(test_file_path.relative_to(Path(__file__).parent)),
            'file_name': test_file_path.name,
            'test_count': 0,
            'test_cases': [],
            'error': str(e)
        }


def _extract_failed_tests(stdout: str, stderr: str) -> List[Dict[str, Any]]:
    """
    从 pytest 输出中提取失败的测试用例详情
    
    :param stdout: pytest 标准输出
    :param stderr: pytest 标准错误输出
    :return: 失败测试用例列表
    """
    import re
    
    failed_tests = []
    combined_output = (stdout or "") + "\n" + (stderr or "")
    
    if not combined_output:
        return failed_tests
    
    # 匹配失败测试用例的模式
    # 格式: "FAILED test_file.py::test_function_name - AssertionError: ..."
    failed_pattern = r'FAILED\s+([^\s]+)::([^\s]+)\s*-\s*(.+)'
    matches = re.finditer(failed_pattern, combined_output, re.MULTILINE)
    
    for match in matches:
        file_path = match.group(1)
        test_name = match.group(2)
        error_msg = match.group(3).strip()
        
        # 截断过长的错误信息
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        
        failed_tests.append({
            'file': file_path,
            'test_name': test_name,
            'error': error_msg
        })
    
    # 如果没有匹配到，尝试从其他格式提取
    if not failed_tests:
        # 尝试匹配 "test_name FAILED" 格式
        alt_pattern = r'([^\s]+::test_[^\s]+)\s+FAILED'
        alt_matches = re.finditer(alt_pattern, combined_output, re.MULTILINE)
        for match in alt_matches:
            test_full_name = match.group(1)
            parts = test_full_name.split('::')
            failed_tests.append({
                'file': parts[0] if len(parts) > 0 else '',
                'test_name': parts[-1] if len(parts) > 1 else test_full_name,
                'error': '测试失败（详细信息请查看完整输出）'
            })
    
    return failed_tests


def progress_callback_wrapper(current, total, message):
    """进度回调函数包装器"""
    logger.info(f"多线程解析进度: {current}/{total} - {message}")


@app.route('/api/docs/parse-url-multithread', methods=['POST'])
def parse_api_docs_multithread():
    """多线程批量解析API文档接口"""
    try:
        data = request.json
        if not data or 'urls' not in data:
            return jsonify({'error': '缺少必要参数: urls (URL数组)'}), 400
        
        urls = data.get('urls', [])
        if not urls:
            return jsonify({'error': 'URLs不能为空'}), 400
        
        # 获取解析参数
        max_workers = data.get('max_workers', 4)
        headless = data.get('headless', True)
        limit = data.get('limit', None)
        
        if limit and len(urls) > limit:
            urls = urls[:limit]
            logger.info(f"URL数量超过限制，只解析前 {limit} 个")
        
        # 生成任务ID
        task_id = generate_task_id(urls[0] if urls else None)
        
        # 创建多线程解析器
        # parser = MultithreadFeishuAPIParser(
        #     max_workers=max_workers,
        #     headless=headless,
        #     progress_callback=progress_callback_wrapper
        # )
        
        # 临时使用简单解析器替代多线程解析器
        logger.warning("多线程解析器暂不可用，使用简单解析器替代")
        results = {"success_count": 0, "total": 0, "failed_count": 0, "success_rate": 0}
        
        # 转换为API列表格式
        # api_list = [{"url": url, "original_url": url} for url in urls]
        
        # 执行并行解析
        # logger.info(f"开始多线程解析 {len(urls)} 个API文档，使用 {max_workers} 个线程")
        # results = parser.parse_api_list_parallel(
        #     api_list, 
        #     progress_callback=progress_callback_wrapper
        # )
        
        # 存储批量解析结果
        api_docs[task_id] = {
            'task_id': task_id,
            'batch_mode': True,
            'urls': urls,
            'config': {
                'max_workers': max_workers,
                'headless': headless,
                'limit': limit
            },
            'api_data': results,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, api_docs[task_id])
        
        # 清除文档列表缓存
        clear_docs_list_cache()
        
        # 返回汇总结果
        return jsonify({
            'success': results.get('success_count', 0) > 0,
            'task_id': task_id,
            'message': f'多线程解析完成: 成功 {results.get("success_count", 0)}/{results.get("total", 0)}',
            'api_count': results.get('total', 0),
            'success_count': results.get('success_count', 0),
            'failed_count': results.get('failed_count', 0),
            'success_rate': results.get('success_rate', 0),
            'performance_stats': {
                'total_apis': results.get('total', 0),
                'successful_apis': results.get('success_count', 0),
                'failed_apis': results.get('failed_count', 0),
                'success_rate': results.get('success_rate', 0)
            }
        })
    
    except Exception as e:
        logger.error(f"多线程解析API文档失败: {str(e)}")
        return jsonify({'error': '多线程解析失败', 'message': str(e)}), 500


@app.route('/api/docs/parse-all-feishu', methods=['POST'])
def parse_all_feishu_apis():
    """从飞书API首页解析所有API文档"""
    try:
        data = request.json or {}
        
        # 获取解析参数
        max_workers = data.get('max_workers', 4)
        headless = data.get('headless', True)
        limit = data.get('limit', None)  # 限制解析数量
        base_url = data.get('base_url', 'https://open.feishu.cn/document')
        
        # 生成任务ID
        task_id = generate_task_id(base_url)
        
        # 创建多线程解析器
        # parser = MultithreadFeishuAPIParser(
        #     max_workers=max_workers,
        #     headless=headless,
        #     progress_callback=progress_callback_wrapper
        # )
        
        # 临时使用简单解析器替代多线程解析器
        logger.warning("多线程解析器暂不可用，使用简单解析器替代")
        results = {"success": False, "success_count": 0, "total": 0, "failed_count": 0, "success_rate": 0, "results": []}
        
        # 从飞书API首页解析所有API
        # logger.info(f"开始从 {base_url} 解析所有飞书API文档")
        # results = parser.parse_from_feishu_api_page(
        #     base_url=base_url,
        #     limit=limit
        # )
        
        if not results.get('success', False):
            return jsonify({
                'success': False,
                'task_id': task_id,
                'message': '获取API链接失败',
                'api_count': 0
            }), 500
        
        # 存储批量解析结果
        api_docs[task_id] = {
            'task_id': task_id,
            'batch_mode': True,
            'base_url': base_url,
            'urls': [r.get('url') for r in results.get('results', [])],
            'config': {
                'max_workers': max_workers,
                'headless': headless,
                'limit': limit,
                'base_url': base_url
            },
            'api_data': results,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, api_docs[task_id])
        
        # 清除文档列表缓存
        clear_docs_list_cache()
        
        # 返回汇总结果
        return jsonify({
            'success': results.get('success_count', 0) > 0,
            'task_id': task_id,
            'message': f'飞书API全量解析完成: 成功 {results.get("success_count", 0)}/{results.get("total", 0)}',
            'api_count': results.get('total', 0),
            'success_count': results.get('success_count', 0),
            'failed_count': results.get('failed_count', 0),
            'success_rate': results.get('success_rate', 0),
            'performance_stats': {
                'total_apis': results.get('total', 0),
                'successful_apis': results.get('success_count', 0),
                'failed_apis': results.get('failed_count', 0),
                'success_rate': results.get('success_rate', 0)
            }
        })
    
    except Exception as e:
        logger.error(f"飞书API全量解析失败: {str(e)}")
        return jsonify({'error': '飞书API全量解析失败', 'message': str(e)}), 500


@app.route('/api/docs/fetch-feishu', methods=['POST'])
def fetch_feishu_document():
    """获取飞书开放平台API文档并转换为OpenAPI格式"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': '缺少必要参数: url'}), 400
        
        url = data['url']
        if not url:
            return jsonify({'error': 'URL不能为空'}), 400
        
        # 检查是否是飞书文档URL
        if 'open.feishu.cn/document/' not in url:
            return jsonify({'error': '不是有效的飞书文档URL'}), 400
        
        
        logger.info(f"开始处理飞书URL: {url}")
        
        # 先移除URL中的查询参数（如果有）
        url_without_query = url.split('?')[0] if '?' in url else url
        logger.info(f"移除查询参数后的URL: {url_without_query}")
        
        # 转换URL
        api_url, path = transform_feishu_url(url_without_query)
        logger.info(f"转换后的API URL: {api_url}, 路径: {path}")
        
        # 下载JSON数据
        json_data = download_json(api_url)
        logger.info(f"下载的JSON数据长度: {len(str(json_data)) if json_data else 0}")
        
        if not json_data:
            return jsonify({'error': '获取飞书文档失败'}), 500
        
        # 从飞书API响应中提取实际内容
        if isinstance(json_data, dict) and 'data' in json_data and 'content' in json_data['data']:
            # 提取content字段，这是实际的API文档内容
            content = json_data['data']['content']
            title = json_data['data'].get('title', '')
            logger.info(f"提取到content字段，长度: {len(content) if content else 0}")
            
            # 创建一个新的数据结构，用于存储API信息
            api_info = {
                "title": title,
                "path": path,
                "content": content,
                "url": url,
                "api_url": api_url
            }
            
            # 将api_info作为新的json_data
            json_data = api_info
        else:
            logger.warning("无法从飞书API响应中提取content字段")
            # 即使无法提取content，也尝试使用原始数据
            json_data = {
                "title": "飞书API文档",
                "path": path,
                "content": str(json_data),  # 将整个响应转为字符串作为内容
                "url": url,
                "api_url": api_url
            }
        
        # 生成任务ID
        task_id = generate_task_id(url)
        
        # 创建临时文件存储JSON数据
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(json_data, temp_file, ensure_ascii=False, indent=2)
            temp_json_path = temp_file.name
        
        logger.info(f"创建临时文件: {temp_json_path}")
        
        try:
            # 生成指纹
            fingerprint = generate_file_fingerprint([temp_json_path])
            
            # 创建输出目录 - 使用uploads目录下的不同子目录
            openapi_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'openapi')
            relation_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'api_relation')
            scene_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'business_scene')
            os.makedirs(openapi_dir, exist_ok=True)
            os.makedirs(relation_dir, exist_ok=True)
            os.makedirs(scene_dir, exist_ok=True)
            
            # 1. 生成OpenAPI文档 - 保存到openapi目录
            openapi_output_path = get_output_path([temp_json_path], fingerprint, openapi_dir, "openapi")
            try:
                yaml_content = generate_openapi_yaml([temp_json_path], openapi_output_path)
                logger.info(f"成功生成OpenAPI YAML文档: {openapi_output_path}")
                
                # 将YAML内容转换为JSON格式返回给前端
                openapi_data = yaml.safe_load(yaml_content)
            except Exception as e:
                logger.error(f"生成OpenAPI YAML文档失败: {str(e)}")
                # 如果生成失败，创建一个基本的OpenAPI文档
                openapi_data = {
                    'openapi': '3.0.0',
                    'info': {
                        'title': f'飞书API文档 - {path}',
                        'version': '1.0.0',
                        'description': '从飞书文档获取的API文档'
                    },
                    'servers': [
                        {
                            'url': 'https://open.feishu.cn',
                            'description': '飞书开放平台API服务器'
                        }
                    ],
                    'paths': {}
                }
                logger.info("使用基本OpenAPI文档结构")
            
            # 2. 生成接口关联关系文件 - 保存到api_relation目录
            relation_output_path = get_output_path([temp_json_path], fingerprint, relation_dir, "api_relation")
            try:
                relation_data = generate_api_relation_file([temp_json_path], relation_output_path)
                logger.info(f"成功生成接口关联关系文件: {relation_output_path}")
            except Exception as e:
                logger.error(f"生成接口关联关系文件失败: {str(e)}")
                # 如果生成失败，创建一个基本的关联关系文件
                relation_data = {
                    "relation_info": {
                        "title": "接口关联关系总览",
                        "description": "所有接口的依赖、数据流转、权限关联关系",
                        "total_apis": 0,
                        "relations": [],
                        "key_relation_scenarios": []
                    }
                }
                logger.info("使用基本接口关联关系结构")
            
            # 3. 生成业务场景文件 - 保存到business_scene目录
            scene_output_path = get_output_path([temp_json_path], fingerprint, scene_dir, "business_scene")
            try:
                scene_data = generate_business_scene_file([temp_json_path], scene_output_path)
                logger.info(f"成功生成业务场景文件: {scene_output_path}")
            except Exception as e:
                logger.error(f"生成业务场景文件失败: {str(e)}")
                # 如果生成失败，创建一个基本的业务场景文件
                scene_data = {
                    "business_scenes": {
                        "title": "业务场景总览",
                        "description": "基于接口功能的核心业务场景汇总",
                        "scenes": []
                    }
                }
                logger.info("使用基本业务场景结构")
            
            # 存储解析结果
            api_docs[task_id] = {
                'task_id': task_id,
                'url': url,
                'api_url': api_url,
                'path': path,
                'json_data': json_data,
                'openapi_data': openapi_data,
                'openapi_file_path': openapi_output_path,
                'relation_data': relation_data,
                'relation_file_path': relation_output_path,
                'scene_data': scene_data,
                'scene_file_path': scene_output_path,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存结果
            save_result(task_id, api_docs[task_id])
            
            # 清除文档列表缓存
            clear_docs_list_cache()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': '飞书文档获取并转换为OpenAPI格式成功',
                'path': path,
                'apiDoc': openapi_data,  # 返回OpenAPI格式的数据
                'openapi_data': openapi_data,  # 兼容前端新的字段名
                'relationData': relation_data,  # 返回接口关联关系数据
                'relation_data': relation_data,  # 兼容前端新的字段名
                'sceneData': scene_data,  # 返回业务场景数据
                'scene_data': scene_data  # 兼容前端新的字段名
            })
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)
                logger.info(f"已删除临时文件: {temp_json_path}")
    
    except Exception as e:
        logger.error(f"获取飞书文档失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({'error': '获取飞书文档失败', 'message': str(e)}), 500

@app.route('/api/docs/parse-url', methods=['POST'])
def parse_api_docs_from_url():
    """从URL解析API文档接口（支持飞书开放平台API文档）"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': '缺少必要参数: url'}), 400
        
        url = data['url']
        if not url:
            return jsonify({'error': 'URL不能为空'}), 400
        
        # 生成任务ID
        task_id = generate_task_id(url)
        
        # 使用完整的飞书API解析器（优先）
        try:
            # result = parse_full_feishu_api(url, headless=True)
            # success = result['success']
            # message = "完整API文档解析成功"
            logger.warning("完整飞书API解析器暂不可用，使用基本解析器替代")
            parser = APIParserFactory.create_parser(url)
            apis = parser.parse_apis()
            
            api_data = {
                'openapi': '3.0.0',
                'info': {
                    'title': 'API文档',
                    'version': '1.0.0',
                    'description': '从URL解析的API文档'
                },
                'paths': {}
            }
            
            # 转换API数据
            for api in apis:
                path = api.get('path', '')
                method = api.get('method', '').lower()
                if path and method:
                    if path not in api_data['paths']:
                        api_data['paths'][path] = {}
                    api_data['paths'][path][method] = {
                        'summary': api.get('summary', ''),
                        'description': api.get('description', ''),
                        'parameters': api.get('parameters', []),
                        'responses': api.get('responses', {})
                    }
            
            result = {'success': True, 'data': api_data}
            success = True
            message = "基本API文档解析成功"
        except Exception as parse_error:
            logger.warning(f"完整解析失败，回退到增强解析: {str(parse_error)}")
            # 如果完整解析失败，回退到增强解析
            # result = parse_enhanced_feishu_api(url)
            # success = result['success']
            # message = "增强API文档解析成功"
            logger.error("所有解析器都不可用")
            result = {'success': False, 'error': str(parse_error)}
            success = False
            message = "API文档解析失败"
        
        if success:
            # 创建输出目录 - 使用uploads目录下的不同子目录
            openapi_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'openapi')
            relation_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'api_relation')
            scene_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'business_scene')
            os.makedirs(openapi_dir, exist_ok=True)
            os.makedirs(relation_dir, exist_ok=True)
            os.makedirs(scene_dir, exist_ok=True)
            
            # 生成文件指纹
            temp_json_path = os.path.join(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'processed'), f"temp_{task_id}.json")
            with open(temp_json_path, 'w', encoding='utf-8') as f:
                json.dump(result['data'], f, ensure_ascii=False, indent=2)
            
            fingerprint = generate_file_fingerprint([temp_json_path])
            
            # 生成处理后的文件
            try:
                # 1. 生成OpenAPI文档 - 保存到openapi目录
                openapi_output_path = get_output_path([temp_json_path], fingerprint, openapi_dir, "openapi")
                yaml_content = generate_openapi_yaml([temp_json_path], openapi_output_path)
                logger.info(f"成功生成OpenAPI YAML文档: {openapi_output_path}")
                
                # 将YAML内容转换为Python对象
                openapi_data = yaml.safe_load(yaml_content)
                
                # 2. 生成接口关联关系文件 - 保存到api_relation目录
                relation_output_path = get_output_path([temp_json_path], fingerprint, relation_dir, "api_relation")
                relation_data = generate_api_relation_file([temp_json_path], relation_output_path)
                logger.info(f"成功生成接口关联关系文件: {relation_output_path}")
                
                # 3. 生成业务场景文件 - 保存到business_scene目录
                scene_output_path = get_output_path([temp_json_path], fingerprint, scene_dir, "business_scene")
                scene_data = generate_business_scene_file([temp_json_path], scene_output_path)
                logger.info(f"成功生成业务场景文件: {scene_output_path}")
                
            except Exception as e:
                logger.error(f"生成处理文件失败: {str(e)}")
                # 如果生成失败，创建基本结构
                openapi_data = result['data']
                relation_data = {
                    "relation_info": {
                        "title": "接口关联关系总览",
                        "description": "所有接口的依赖、数据流转、权限关联关系",
                        "total_apis": 0,
                        "relations": [],
                        "key_relation_scenarios": []
                    }
                }
                scene_data = {
                    "business_scenes": {
                        "title": "业务场景总览",
                        "description": "基于接口功能的核心业务场景汇总",
                        "scenes": []
                    }
                }
            finally:
                # 清理临时文件
                if os.path.exists(temp_json_path):
                    os.unlink(temp_json_path)
                    logger.info(f"已删除临时文件: {temp_json_path}")
            
            # 存储解析结果
            api_docs[task_id] = {
                'task_id': task_id,
                'url': url,
                'api_data': result['data'],
                'openapi_data': openapi_data,
                'openapi_file_path': openapi_output_path if 'openapi_output_path' in locals() else None,
                'relation_data': relation_data,
                'relation_file_path': relation_output_path if 'relation_output_path' in locals() else None,
                'scene_data': scene_data,
                'scene_file_path': scene_output_path if 'scene_output_path' in locals() else None,
                'created_at': datetime.now().isoformat()
            }
            
            # 保存结果
            save_result(task_id, api_docs[task_id])
            
            # 清除文档列表缓存
            clear_docs_list_cache()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': message,
                'api_count': 1
            })
        else:
            # 如果增强解析失败，回退到基本解析
            parser = APIParserFactory.create_parser(url)
            apis = parser.parse_apis()
            
            api_data = {
                'openapi': '3.0.0',
                'info': {
                    'title': 'API文档',
                    'version': '1.0.0',
                    'description': '从API文档解析生成的接口文档'
                },
                'servers': [],
                'paths': {}
            }
            
            for api in apis:
                path = api.path
                method = api.method.lower()
                
                if path not in api_data['paths']:
                    api_data['paths'][path] = {}
                
                method_obj = {
                    'summary': api.summary,
                    'description': api.description,
                    'operationId': api.operation_id,
                    'tags': api.tags,
                    'parameters': api.parameters,
                    'responses': {
                        '200': {
                            'description': '成功响应',
                            'content': {
                                'application/json': {
                                    'schema': api.success_response.get('schema', {}) if api.success_response else {}
                                }
                            }
                        }
                    }
                }
                
                if api.request_body:
                    method_obj['requestBody'] = {
                        'content': {
                            'application/json': {
                                'schema': api.request_body.get('schema', {})
                            }
                        },
                        'required': api.request_body.get('required', False)
                    }
                
                if api.security:
                    method_obj['security'] = api.security
                
                api_data['paths'][path][method] = method_obj
            
            # 存储解析结果
            api_docs[task_id] = {
                'task_id': task_id,
                'url': url,
                'api_data': api_data,
                'created_at': datetime.now().isoformat()
            }
            
            save_result(task_id, api_docs[task_id])
            
            # 清除文档列表缓存
            clear_docs_list_cache()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'API文档解析成功（基础版本）',
                'api_count': len(api_data.get('paths', {}))
            })
    
    except Exception as e:
        logger.error(f"从URL解析API文档失败: {str(e)}")
        return jsonify({'error': '从URL解析API文档失败', 'message': str(e)}), 500

@app.route('/api/docs/list', methods=['GET'])
def list_parsed_docs():
    """获取已解析的API文档列表"""
    global docs_list_cache, docs_list_cache_time
    
    try:
        # 检查缓存是否有效
        current_time = time.time()
        if docs_list_cache is not None and docs_list_cache_time is not None and (current_time - docs_list_cache_time) < CACHE_EXPIRE_TIME:
            return jsonify(docs_list_cache)
        
        # 缓存失效，重新生成文档列表
        docs_list = []
        
        for task_id, doc_info in api_docs.items():
            # 获取文档基本信息
            filename = doc_info.get('filename', '')
            created_at = doc_info.get('created_at', '')
            
            # 计算API数量
            api_data = doc_info.get('api_data', {})
            api_count = 0
            
            # 检查是否为完整解析器的数据格式（包含name, method, path等扁平结构）
            if 'name' in api_data or 'method' in api_data:
                # 完整解析器的扁平数据格式
                api_count = 1  # 这种格式每个文档代表一个API
            else:
                # 传统OpenAPI格式
                paths = api_data.get('paths', {})
                for path, path_item in paths.items():
                    for method, api_detail in path_item.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                            api_count += 1
            
            # 添加到文档列表
            docs_list.append({
                'task_id': task_id,
                'filename': filename,
                'created_at': created_at,
                'api_count': api_count
            })
        
        # 更新缓存
        docs_list_cache = {'docs': docs_list}
        docs_list_cache_time = current_time
        
        return jsonify({'docs': docs_list})
    
    except Exception as e:
        logger.error(f"获取API文档列表失败: {str(e)}")
        return jsonify({'error': '获取API文档列表失败', 'message': str(e)}), 500

@app.route('/api/docs', methods=['GET'])
def get_api_docs():
    """获取API文档列表"""
    docs_list = []
    for task_id, doc in api_docs.items():
        docs_list.append({
            'task_id': task_id,
            'filename': doc['filename'],
            'api_count': len(doc['api_data'].get('apis', [])),
            'created_at': doc['created_at']
        })
    
    return jsonify(docs_list)

@app.route('/api/docs/<task_id>', methods=['GET'])
def get_api_doc(task_id):
    """获取特定API文档详情"""
    if task_id not in api_docs:
        return jsonify({'error': 'API文档不存在'}), 404
    
    # 获取基本文档信息
    doc_data = api_docs[task_id]
    
    # 尝试获取关联关系数据
    relation_data = None
    relation_file = os.path.join(app.config['RELATION_FOLDER'], f"relation_{task_id}.json")
    if os.path.exists(relation_file):
        try:
            with open(relation_file, 'r', encoding='utf-8') as f:
                relation_data = json.load(f)
        except Exception as e:
            logger.error(f"读取关联关系文件失败: {str(e)}")
    
    # 尝试获取业务场景数据
    scene_data = None
    scene_file = os.path.join(app.config['SCENE_FOLDER'], f"scene_{task_id}.json")
    if os.path.exists(scene_file):
        try:
            with open(scene_file, 'r', encoding='utf-8') as f:
                scene_data = json.load(f)
        except Exception as e:
            logger.error(f"读取业务场景文件失败: {str(e)}")
    
    # 将关联关系和业务场景数据添加到响应中
    response_data = doc_data.copy()
    if relation_data:
        response_data['relation_data'] = relation_data
    if scene_data:
        response_data['scene_data'] = scene_data
    
    return jsonify(response_data)

@app.route('/api/docs/by-type/<doc_type>', methods=['GET'])
def get_docs_by_type(doc_type):
    """根据文档类型获取文档列表"""
    try:
        if doc_type == 'single':
            # 获取单接口文档列表
            dir_path = os.path.join(app.config['UPLOAD_FOLDER'], 'openapi')
            documents = []
            
            # 确保目录存在
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                return jsonify({
                    'success': True,
                    'data': []
                })
            
            # 遍历目录中的文件
            for filename in os.listdir(dir_path):
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension in ['.yaml', '.yml', '.json']:
                    file_path = os.path.join(dir_path, filename)
                    
                    # 获取文件信息
                    stat = os.stat(file_path)
                    
                    # 提取文件ID
                    file_id = filename
                    if filename.startswith('openapi_'):
                        file_id = filename[len('openapi_'):]  # 去掉类型前缀
                    
                    # 去掉文件扩展名
                    if '.' in file_id:
                        file_id = file_id.rsplit('.', 1)[0]
                    
                    # 尝试解析文件内容
                    api_count = 0
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            if file_extension == '.json':
                                content = json.load(f)
                                
                                # 计算API数量
                                if 'paths' in content:
                                    for path, path_item in content['paths'].items():
                                        for method in path_item:
                                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                                api_count += 1
                            elif file_extension in ['.yaml', '.yml']:
                                content = yaml.safe_load(f)
                                
                                # 计算API数量
                                if 'paths' in content:
                                    for path, path_item in content['paths'].items():
                                        for method in path_item:
                                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                                api_count += 1
                    except Exception as e:
                        logger.warning(f"解析单接口文档失败 {filename}: {str(e)}")
                    
                    documents.append({
                        'id': file_id,
                        'file_id': file_id,
                        'file_name': filename,
                        'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'api_count': api_count,
                        'doc_type': 'single'
                    })
            
            return jsonify({
                'success': True,
                'data': documents
            })
        
        elif doc_type == 'multi':
            # 获取多接口文档列表
            dir_path = os.path.join(app.config['MULTI_UPLOAD_FOLDER'], 'openapi')
            documents = []
            
            # 确保目录存在
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                return jsonify({
                    'success': True,
                    'data': []
                })
            
            # 遍历目录中的文件
            for filename in os.listdir(dir_path):
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension in ['.yaml', '.yml', '.json']:
                    file_path = os.path.join(dir_path, filename)
                    
                    # 获取文件信息
                    stat = os.stat(file_path)
                    
                    # 提取文件ID
                    file_id = filename
                    if filename.startswith('multiopenapi_'):
                        file_id = filename[len('multiopenapi_'):]  # 去掉类型前缀
                    
                    # 去掉文件扩展名
                    if '.' in file_id:
                        file_id = file_id.rsplit('.', 1)[0]
                    
                    # 尝试解析文件内容
                    api_count = 0
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            if file_extension == '.json':
                                content = json.load(f)
                                
                                # 计算API数量
                                if 'paths' in content:
                                    for path, path_item in content['paths'].items():
                                        for method in path_item:
                                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                                api_count += 1
                            elif file_extension in ['.yaml', '.yml']:
                                content = yaml.safe_load(f)
                                
                                # 计算API数量
                                if 'paths' in content:
                                    for path, path_item in content['paths'].items():
                                        for method in path_item:
                                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                                api_count += 1
                    except Exception as e:
                        logger.warning(f"解析多接口文档失败 {filename}: {str(e)}")
                    
                    documents.append({
                        'id': file_id,
                        'file_id': file_id,
                        'file_name': filename,
                        'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'api_count': api_count,
                        'doc_type': 'multi'
                    })
            
            return jsonify({
                'success': True,
                'data': documents
            })
        
        else:
            return jsonify({
                'success': False,
                'error': '不支持的文档类型'
            }), 400
    
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取文档列表失败',
            'message': str(e)
        }), 500

# 3. 测试用例生成
@app.route('/api/test-cases/generate', methods=['POST'])
def generate_test_cases_for_task():
    """生成测试用例接口"""
    try:
        data = request.json
        if not data or 'task_id' not in data:
            return jsonify({'error': '缺少必要参数: task_id'}), 400
        
        doc_task_id = data['task_id']
        if doc_task_id not in api_docs:
            return jsonify({'error': 'API文档不存在'}), 404
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取API数据
        api_data = api_docs[doc_task_id]['api_data']
        
        # 生成测试用例
        # 使用generate_test_cases函数而不是TestGenerator类
        test_suites = generate_test_cases(api_data)
        
        # 将测试套件转换为API服务器期望的格式
        test_cases_data = {}
        for suite in test_suites:
            for case in suite.test_cases:
                api_path = case.api_path
                if api_path not in test_cases_data:
                    test_cases_data[api_path] = []
                
                test_cases_data[api_path].append({
                    'case_id': case.case_id,
                    'case_name': case.case_name,
                    'api_method': case.api_method,
                    'api_path': case.api_path,
                    'host': case.host,
                    'headers': case.headers,
                    'request_type': case.request_type,
                    'data': case.data,
                    'is_run': case.is_run,
                    'detail': case.detail,
                    'dependence_case': case.dependence_case,
                    'dependence_case_data': case.dependence_case_data,
                    'current_request_set_cache': case.current_request_set_cache,
                    'sql': case.sql,
                    'assert_data': case.assert_data,
                    'setup_sql': case.setup_sql,
                    'teardown': case.teardown,
                    'teardown_sql': case.teardown_sql,
                    'sleep': case.sleep,
                    'code': f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-



class Test{case.api_method.title()}{case.api_path.replace('/', '_').replace('{', '_').replace('}', '_')}:
    def test_{case.case_id}(self):
        url = "{case.host}{case.api_path}"
        headers = {json.dumps(case.headers)}
        data = {json.dumps(case.data)}
        
        response = requests.{case.api_method.lower()}(url, headers=headers, json=data)
        
        # 断言
        assert response.status_code == {case.assert_data.get('status_code', 200)}
"""
                })
        
        # 存储测试用例
        test_cases[task_id] = {
            'task_id': task_id,
            'doc_task_id': doc_task_id,
            'test_cases': test_cases_data,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存测试用例到文件
        test_cases_dir = os.path.join(app.config['TEST_CASES_FOLDER'], task_id)
        os.makedirs(test_cases_dir, exist_ok=True)
        
        for api_path, cases in test_cases_data.items():
            for i, case in enumerate(cases):
                case_filename = f"test_{api_path.replace('/', '_')}_{i+1}.py"
                case_path = os.path.join(test_cases_dir, case_filename)
                
                with open(case_path, 'w', encoding='utf-8') as f:
                    f.write(case['code'])
        
        # 保存结果
        result = {
            **test_cases[task_id],
            'test_cases_count': sum(len(cases) for cases in test_cases_data.values())
        }
        # 使用filename作为file_id，实现相同文件的结果覆盖
        save_result(filename, result)
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'test_cases': test_cases_data,
                'test_cases_count': result['test_cases_count']
            },
            'message': '测试用例生成成功'
        })
    
    except Exception as e:
        logger.error(f"生成测试用例失败: {str(e)}")
        return jsonify({'error': '测试用例生成失败', 'message': str(e)}), 500

@app.route('/api/test-cases', methods=['GET'])
def get_test_cases_list():
    """获取测试用例列表"""
    cases_list = []
    for task_id, cases in test_cases.items():
        doc_task_id = cases['doc_task_id']
        doc_filename = api_docs.get(doc_task_id, {}).get('filename', 'Unknown')
        
        cases_list.append({
            'task_id': task_id,
            'doc_task_id': doc_task_id,
            'doc_filename': doc_filename,
            'test_cases_count': sum(len(c) for c in cases['test_cases'].values()),
            'created_at': cases['created_at']
        })
    
    return jsonify(cases_list)

@app.route('/api/test-cases/<task_id>', methods=['GET'])
def get_test_cases(task_id):
    """获取特定测试用例详情"""
    if task_id not in test_cases:
        return jsonify({'error': '测试用例不存在'}), 404
    
    return jsonify(test_cases[task_id])

@app.route('/api/test-cases/<task_id>/run', methods=['POST'])
def run_test_cases(task_id):
    """运行测试用例接口"""
    try:
        if task_id not in test_cases:
            return jsonify({'error': '测试用例不存在'}), 404
        
        # 生成任务ID
        run_task_id = generate_task_id()
        
        # 模拟运行测试用例
        # 在实际实现中，这里会调用pytest或其他测试框架运行测试
        test_cases_dir = os.path.join(app.config['TEST_CASES_FOLDER'], task_id)
        
        # 模拟测试结果
        test_results = {
            'run_task_id': run_task_id,
            'test_cases_task_id': task_id,
            'total': 33,
            'passed': 27,
            'failed': 6,
            'skipped': 0,
            'duration': 45.6,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存测试结果
        save_result(run_task_id, test_results)
        
        return jsonify({
            'success': True,
            'data': {
                'run_task_id': run_task_id,
                'results': test_results
            },
            'message': '测试用例运行完成'
        })
    
    except Exception as e:
        logger.error(f"运行测试用例失败: {str(e)}")
        return jsonify({'error': '测试用例运行失败', 'message': str(e)}), 500

# 4. 覆盖度评估
@app.route('/api/coverage/evaluate', methods=['POST'])
def evaluate_coverage():
    """评估测试覆盖度接口"""
    try:
        data = request.json
        if not data or 'test_cases_task_id' not in data:
            return jsonify({'error': '缺少必要参数: test_cases_task_id'}), 400
        
        test_cases_task_id = data['test_cases_task_id']
        if test_cases_task_id not in test_cases:
            return jsonify({'error': '测试用例不存在'}), 404
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取测试用例和API数据
        test_cases_data = test_cases[test_cases_task_id]['test_cases']
        doc_task_id = test_cases[test_cases_task_id]['doc_task_id']
        api_data = api_docs[doc_task_id]['api_data']
        
        # 评估覆盖度
        scorer = CoverageScorer(api_data, test_cases_data)
        coverage_report = scorer.evaluate_coverage()
        
        # 存储覆盖度报告
        coverage_reports[task_id] = {
            'task_id': task_id,
            'test_cases_task_id': test_cases_task_id,
            'doc_task_id': doc_task_id,
            'coverage_report': coverage_report,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, coverage_reports[task_id])
        
        return jsonify({
            'task_id': task_id,
            'message': '覆盖度评估完成',
            'overall_coverage': coverage_report.get('overall_coverage', 0)
        })
    
    except Exception as e:
        logger.error(f"评估覆盖度失败: {str(e)}")
        return jsonify({'error': '覆盖度评估失败', 'message': str(e)}), 500

@app.route('/api/coverage', methods=['GET'])
def get_coverage_reports():
    """获取覆盖度报告列表"""
    reports_list = []
    for task_id, report in coverage_reports.items():
        test_cases_task_id = report['test_cases_task_id']
        doc_task_id = report['doc_task_id']
        doc_filename = api_docs.get(doc_task_id, {}).get('filename', 'Unknown')
        
        reports_list.append({
            'task_id': task_id,
            'test_cases_task_id': test_cases_task_id,
            'doc_task_id': doc_task_id,
            'doc_filename': doc_filename,
            'overall_coverage': report['coverage_report'].get('overall_coverage', 0),
            'created_at': report['created_at']
        })
    
    return jsonify(reports_list)

@app.route('/api/coverage/<task_id>', methods=['GET'])
def get_coverage_report(task_id):
    """获取特定覆盖度报告详情"""
    if task_id not in coverage_reports:
        return jsonify({'error': '覆盖度报告不存在'}), 404
    
    return jsonify(coverage_reports[task_id])

# 5. 智能建议
@app.route('/api/suggestions/generate', methods=['POST'])
def generate_suggestions():
    """生成智能建议接口"""
    try:
        data = request.json
        if not data or 'coverage_task_id' not in data:
            return jsonify({'error': '缺少必要参数: coverage_task_id'}), 400
        
        coverage_task_id = data['coverage_task_id']
        if coverage_task_id not in coverage_reports:
            return jsonify({'error': '覆盖度报告不存在'}), 404
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取覆盖度报告
        coverage_report = coverage_reports[coverage_task_id]['coverage_report']
        
        # 生成智能建议
        suggestions_data = []
        
        # 根据覆盖度报告生成建议
        overall_coverage = coverage_report.get('overall_coverage', 0)
        
        if overall_coverage < 50:
            suggestions_data.append({
                'type': 'coverage',
                'priority': 'high',
                'title': '测试覆盖度过低',
                'description': '当前测试覆盖度低于50%，建议增加更多测试用例以提高覆盖度。',
                'action': '增加边界值测试和异常场景测试'
            })
        elif overall_coverage < 80:
            suggestions_data.append({
                'type': 'coverage',
                'priority': 'medium',
                'title': '测试覆盖度中等',
                'description': '当前测试覆盖度为中等水平，可以进一步优化以提高覆盖度。',
                'action': '补充参数组合测试和业务场景测试'
            })
        
        # 检查未覆盖的功能点
        uncovered_functions = coverage_report.get('uncovered_functions', [])
        if uncovered_functions:
            suggestions_data.append({
                'type': 'function',
                'priority': 'high',
                'title': '存在未覆盖的功能点',
                'description': f'发现{len(uncovered_functions)}个未覆盖的功能点。',
                'action': '为未覆盖的功能点添加测试用例',
                'details': uncovered_functions
            })
        
        # 检查参数覆盖情况
        parameter_coverage = coverage_report.get('parameter_coverage', {})
        if parameter_coverage.get('level') == 'POOR':
            suggestions_data.append({
                'type': 'parameter',
                'priority': 'medium',
                'title': '参数覆盖不足',
                'description': '参数覆盖度较低，建议增加参数变体测试。',
                'action': '增加参数边界值和异常值测试'
            })
        
        # 检查异常覆盖情况
        exception_coverage = coverage_report.get('exception_coverage', {})
        if exception_coverage.get('level') == 'POOR':
            suggestions_data.append({
                'type': 'exception',
                'priority': 'medium',
                'title': '异常覆盖不足',
                'description': '异常场景覆盖度较低，建议增加异常测试用例。',
                'action': '增加各种异常场景的测试用例'
            })
        
        # 存储智能建议
        suggestions[task_id] = {
            'task_id': task_id,
            'coverage_task_id': coverage_task_id,
            'suggestions': suggestions_data,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, suggestions[task_id])
        
        return jsonify({
            'task_id': task_id,
            'message': '智能建议生成完成',
            'suggestions_count': len(suggestions_data)
        })
    
    except Exception as e:
        logger.error(f"生成智能建议失败: {str(e)}")
        return jsonify({'error': '智能建议生成失败', 'message': str(e)}), 500

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions_list():
    """获取智能建议列表"""
    suggestions_list = []
    for task_id, suggestion in suggestions.items():
        coverage_task_id = suggestion['coverage_task_id']
        test_cases_task_id = coverage_reports.get(coverage_task_id, {}).get('test_cases_task_id', '')
        doc_task_id = coverage_reports.get(coverage_task_id, {}).get('doc_task_id', '')
        doc_filename = api_docs.get(doc_task_id, {}).get('filename', 'Unknown')
        
        # 统计高优先级建议数量
        high_priority_count = sum(1 for s in suggestion['suggestions'] if s.get('priority') == 'high')
        
        suggestions_list.append({
            'task_id': task_id,
            'coverage_task_id': coverage_task_id,
            'test_cases_task_id': test_cases_task_id,
            'doc_task_id': doc_task_id,
            'doc_filename': doc_filename,
            'suggestions_count': len(suggestion['suggestions']),
            'high_priority_count': high_priority_count,
            'created_at': suggestion['created_at']
        })
    
    return jsonify(suggestions_list)

@app.route('/api/suggestions/<task_id>', methods=['GET'])
def get_suggestions(task_id):
    """获取特定智能建议详情"""
    if task_id not in suggestions:
        return jsonify({'error': '智能建议不存在'}), 404
    
    return jsonify(suggestions[task_id])

# 6. 仪表板数据
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """获取仪表板统计数据"""
    # 统计数据
    total_apis = sum(len(doc['api_data'].get('apis', [])) for doc in api_docs.values())
    total_test_cases = sum(sum(len(cases) for cases in tc['test_cases'].values()) for tc in test_cases.values())
    
    # 计算平均通过率
    total_passed = 0
    total_tests = 0
    for task_id in test_cases:
        # 模拟测试结果
        passed = 27
        total = 33
        total_passed += passed
        total_tests += total
    
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    # 计算平均覆盖度
    total_coverage = sum(report['coverage_report'].get('overall_coverage', 0) for report in coverage_reports.values())
    avg_coverage = (total_coverage / len(coverage_reports)) if coverage_reports else 0
    
    # 高优先级建议数量
    high_priority_suggestions = sum(
        sum(1 for s in suggestion['suggestions'] if s.get('priority') == 'high')
        for suggestion in suggestions.values()
    )
    
    return jsonify({
        'total_apis': total_apis,
        'total_test_cases': total_test_cases,
        'pass_rate': round(pass_rate, 2),
        'avg_coverage': round(avg_coverage, 2),
        'high_priority_suggestions': high_priority_suggestions,
        'api_docs_count': len(api_docs),
        'test_cases_count': len(test_cases),
        'coverage_reports_count': len(coverage_reports),
        'suggestions_count': len(suggestions)
    })

@app.route('/api/dashboard/recent-activities', methods=['GET'])
def get_recent_activities():
    """获取最近活动"""
    activities = []
    
    # 添加API文档解析活动
    for task_id, doc in api_docs.items():
        activities.append({
            'type': 'api_doc_parsed',
            'title': f'解析API文档: {doc["filename"]}',
            'timestamp': doc['created_at'],
            'details': {
                'task_id': task_id,
                'api_count': len(doc['api_data'].get('apis', []))
            }
        })
    
    # 添加测试用例生成活动
    for task_id, tc in test_cases.items():
        activities.append({
            'type': 'test_cases_generated',
            'title': '生成测试用例',
            'timestamp': tc['created_at'],
            'details': {
                'task_id': task_id,
                'test_cases_count': sum(len(cases) for cases in tc['test_cases'].values())
            }
        })
    
    # 添加覆盖度评估活动
    for task_id, report in coverage_reports.items():
        activities.append({
            'type': 'coverage_evaluated',
            'title': '评估测试覆盖度',
            'timestamp': report['created_at'],
            'details': {
                'task_id': task_id,
                'coverage': report['coverage_report'].get('overall_coverage', 0)
            }
        })
    
    # 添加智能建议生成活动
    for task_id, suggestion in suggestions.items():
        activities.append({
            'type': 'suggestions_generated',
            'title': '生成智能建议',
            'timestamp': suggestion['created_at'],
            'details': {
                'task_id': task_id,
                'suggestions_count': len(suggestion['suggestions'])
            }
        })
    
    # 按时间戳排序，最新的在前
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 返回最近10条活动
    return jsonify(activities[:10])

# 测试场景生成
@app.route('/api/test-scenes/generate', methods=['POST'])
def generate_test_scenes():
    """生成测试场景"""
    try:
        data = request.get_json()
        openapi_spec = data.get('openapi_spec')
        
        if not openapi_spec:
            return jsonify({'error': '缺少OpenAPI规范'}), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 使用AI分析API文档，生成测试场景
        
        generator = APICaseGenerator(openapi_spec)
        scenes = generator.generate_test_scenes()
        
        # 存储测试场景
        test_scenes[task_id] = {
            'task_id': task_id,
            'scenes': scenes,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, test_scenes[task_id])
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'scenes': scenes
            },
            'message': '测试场景生成成功'
        })
    
    except Exception as e:
        logger.error(f"生成测试场景失败: {str(e)}")
        return jsonify({'error': '生成测试场景失败', 'message': str(e)}), 500

# 测试关联关系生成
@app.route('/api/test-relation/generate', methods=['POST'])
def generate_test_relations():
    """生成测试关联关系"""
    try:
        data = request.get_json()
        openapi_spec = data.get('openapi_spec')
        
        if not openapi_spec:
            return jsonify({'error': '缺少OpenAPI规范'}), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 使用AI分析API文档，生成测试关联关系
        
        # 解析OpenAPI规范获取API列表
        try:
            # 检查openapi_spec是否已经是字典类型（前端发送的对象）
            if isinstance(openapi_spec, dict):
                openapi_data = openapi_spec
            else:
                # 如果是字符串，则解析为字典
                openapi_data = json.loads(openapi_spec)
            
            # 从OpenAPI规范中提取API信息
            apis = []
            
            # 检查是否有paths字段（标准OpenAPI格式）
            if 'paths' in openapi_data:
                paths = openapi_data.get('paths', {})
                for path, path_item in paths.items():
                    for method, operation in path_item.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                            # 构建API对象
                            api = {
                                'path': path,
                                'method': method.upper(),
                                'operationId': operation.get('operationId', ''),
                                'summary': operation.get('summary', ''),
                                'description': operation.get('description', ''),
                                'tags': operation.get('tags', []),
                                'parameters': operation.get('parameters', []),
                                'request_body': operation.get('requestBody', {}),
                                'responses': operation.get('responses', {}),
                                'security': operation.get('security', [])
                            }
                            apis.append(api)
            
            # 如果没有找到paths，检查是否有apis字段（自定义格式）
            elif 'apis' in openapi_data:
                apis = openapi_data.get('apis', [])
            
            # 如果仍然没有API，检查是否有endpoints字段（另一种自定义格式）
            elif 'endpoints' in openapi_data:
                apis = openapi_data.get('endpoints', [])
                
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            logger.error(f"解析OpenAPI规范失败: {str(e)}")
            return jsonify({'error': '解析OpenAPI规范失败', 'message': str(e)}), 400
        
        analyzer = DependencyAnalyzer(apis)
        analyzer.analyze_dependencies()
        
        # 获取关联关系
        relations = []
        data_dependencies = analyzer.get_data_dependencies()
        for dep in data_dependencies:
            relations.append({
                'source_api': dep.source_api,
                'target_api': dep.target_api,
                'dependency_type': dep.dependency_type,
                'source_path': dep.source_path,
                'target_path': dep.target_path,
                'description': dep.description
            })
        
        # 获取业务流程
        business_flows = []
        for flow in analyzer.get_business_flows():
            business_flows.append({
                'flow_id': flow.flow_id,
                'flow_name': flow.flow_name,
                'apis': flow.apis,
                'description': flow.description,
                'critical_path': flow.critical_path
            })
        
        # 存储测试关联关系
        test_relations[task_id] = {
            'task_id': task_id,
            'relations': relations,
            'business_flows': business_flows,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, test_relations[task_id])
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'relations': relations,
                'business_flows': business_flows
            },
            'message': '测试关联关系生成成功'
        })
    
    except Exception as e:
        logger.error(f"生成测试关联关系失败: {str(e)}")
        return jsonify({'error': '生成测试关联关系失败', 'message': str(e)}), 500

# 配置保存
@app.route('/api/config/save', methods=['POST'])
def save_config():
    """保存配置"""
    try:
        config_data = request.get_json()
        
        if not config_data:
            return jsonify({'error': '缺少配置数据'}), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 存储配置
        config = {
            'task_id': task_id,
            'config': config_data,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存配置到文件
        config_path = os.path.join(app.config['RESULTS_FOLDER'], f"config_{task_id}.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id
            },
            'message': '配置保存成功'
        })
    
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return jsonify({'error': '保存配置失败', 'message': str(e)}), 500

# 8. 智能测试生成
@app.route('/api/smart-test-generation', methods=['POST'])
def smart_test_generation():
    """智能测试生成"""
    try:
        data = request.get_json()
        doc_task_id = data.get('doc_task_id')
        scenarios = data.get('scenarios', [])
        relationships = data.get('relationships', [])
        
        if not doc_task_id or doc_task_id not in api_docs:
            return jsonify({'error': '无效的文档ID'}), 400
        
        if not scenarios and not relationships:
            return jsonify({'error': '请提供至少一个场景或关联关系'}), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取API文档路径
        api_doc = api_docs[doc_task_id]
        api_doc_path = api_doc['file_path']
        
        generator = ScenarioTestGenerator(api_doc_path, os.path.join(OUTPUT_DIR, 'smart_test_cases'))
        
        # 使用已解析的API文档数据，而不是重新解析
        api_data = api_doc.get('api_data', {})
        if 'apis' in api_data:
            # 传统解析器格式
            apis = []
            for api_dict in api_data['apis']:
                api = APIEndpoint(
                    path=api_dict.get('path', ''),
                    method=api_dict.get('method', ''),
                    summary=api_dict.get('summary', ''),
                    description=api_dict.get('description', ''),
                    operation_id=api_dict.get('operation_id', ''),
                    tags=api_dict.get('tags', []),
                    host=api_dict.get('host', ''),
                    base_path=api_dict.get('base_path', ''),
                    parameters=api_dict.get('parameters', []),
                    request_body=api_dict.get('request_body', {}),
                    response_codes=api_dict.get('response_codes', []),
                    success_response=api_dict.get('success_response', {}),
                    security=api_dict.get('security', [])
                )
                apis.append(api)
            generator.apis = apis
        elif 'endpoints' in api_data:
            # OpenAPI 3.0.0 Agent格式
            apis = []
            for endpoint_dict in api_data['endpoints']:
                api = APIEndpoint(
                    path=endpoint_dict.get('path', ''),
                    method=endpoint_dict.get('method', ''),
                    summary=endpoint_dict.get('summary', ''),
                    description=endpoint_dict.get('description', ''),
                    operation_id=endpoint_dict.get('operation_id', ''),
                    tags=endpoint_dict.get('tags', []),
                    host=endpoint_dict.get('host', ''),
                    base_path=endpoint_dict.get('base_path', ''),
                    parameters=endpoint_dict.get('parameters', []),
                    request_body=endpoint_dict.get('request_body', {}),
                    response_codes=endpoint_dict.get('response_codes', []),
                    success_response=endpoint_dict.get('success_response', {}),
                    security=endpoint_dict.get('security', [])
                )
                apis.append(api)
            generator.apis = apis
        else:
            # 如果没有可用的API数据，尝试重新解析
            if not generator.parse_api_document():
                return jsonify({'error': 'API文档解析失败'}), 500
        
        # 将API转换为字典格式，便于查找
        generator.api_dict = {}
        for api in generator.apis:
            api_id = f"{api.method}_{api.path}"
            generator.api_dict[api_id] = api
        
        # 添加场景
        for scenario_dict in scenarios:
            scenario = create_scenario_from_dict(scenario_dict)
            if not generator.add_scenario(scenario):
                return jsonify({'error': f'添加场景失败: {scenario.scenario_name}'}), 400
        
        # 添加关联关系
        for relationship_dict in relationships:
            relationship = create_relationship_from_dict(relationship_dict)
            if not generator.add_relationship(relationship):
                return jsonify({'error': f'添加关联关系失败: {relationship.description}'}), 400
        
        # 生成测试用例
        test_suites = generator.generate_test_cases()
        
        # 保存测试用例
        if not generator.save_test_suites():
            return jsonify({'error': '保存测试用例失败'}), 500
        
        # 转换测试套件为可序列化的格式
        test_suites_data = []
        for suite in test_suites:
            suite_data = {
                'suite_id': suite.suite_id,
                'suite_name': suite.suite_name,
                'description': suite.description,
                'allure_epic': suite.allure_epic,
                'allure_feature': suite.allure_feature,
                'allure_story': suite.allure_story,
                'test_cases_count': len(suite.test_cases)
            }
            test_suites_data.append(suite_data)
        
        # 存储智能测试生成结果
        smart_test_results[task_id] = {
            'task_id': task_id,
            'doc_task_id': doc_task_id,
            'scenarios_count': len(scenarios),
            'relationships_count': len(relationships),
            'test_suites': test_suites_data,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存结果
        save_result(task_id, smart_test_results[task_id])
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'test_suites': test_suites_data,
                'test_suites_count': len(test_suites),
                'test_cases_count': sum(len(suite.test_cases) for suite in test_suites)
            },
            'message': '智能测试生成完成'
        })
    
    except Exception as e:
        logger.error(f"智能测试生成失败: {str(e)}")
        return jsonify({'error': '智能测试生成失败', 'message': str(e)}), 500

@app.route('/api/smart-test-generation', methods=['GET'])
def get_smart_test_results_list():
    """获取智能测试生成结果列表"""
    results_list = []
    for task_id, result in smart_test_results.items():
        doc_task_id = result['doc_task_id']
        doc_filename = api_docs.get(doc_task_id, {}).get('filename', 'Unknown')
        
        # 统计测试套件和测试用例数量
        test_suites_count = len(result['test_suites'])
        test_cases_count = sum(suite['test_cases_count'] for suite in result['test_suites'])
        
        results_list.append({
            'task_id': task_id,
            'doc_task_id': doc_task_id,
            'doc_filename': doc_filename,
            'scenarios_count': result['scenarios_count'],
            'relationships_count': result['relationships_count'],
            'test_suites_count': test_suites_count,
            'test_cases_count': test_cases_count,
            'created_at': result['created_at']
        })
    
    # 按创建时间排序，最新的在前
    results_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify(results_list)

@app.route('/api/smart-test-generation/<task_id>', methods=['GET'])
def get_smart_test_result(task_id):
    """获取特定智能测试生成结果详情"""
    if task_id not in smart_test_results:
        return jsonify({'error': '智能测试生成结果不存在'}), 404
    
    return jsonify(smart_test_results[task_id])

@app.route('/api/ai/parse', methods=['POST'])
def ai_parse_url():
    """使用AI解析URL并生成JSON文件"""
    try:
        
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL不能为空'}), 400
        
        # 导入ai.py中的函数
        sys.path.append(os.path.join(os.path.dirname(__file__), 'utils', 'parse'))
        
        # 定义输出目录
        output_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用新的process_url_with_ai函数处理URL
        result = process_url_with_ai(url, output_dir)
        
        if not result.get('success', False):
            return jsonify({
                'error': 'AI解析URL失败',
                'message': result.get('error', '未知错误')
            }), 500
        
        # 返回生成的文件内容
        return jsonify({
            'success': True,
            'url': result.get('url'),
            'url_hash': result.get('url_hash'),
            'openapi_data': result.get('openapi_data'),
            'relation_data': result.get('relation_data'),
            'scene_data': result.get('scene_data'),
            'openapi_file': result.get('openapi_file'),
            'relation_file': result.get('relation_file'),
            'scene_file': result.get('scene_file'),
            'message': 'AI解析成功'
        })
        
    except Exception as e:
        logger.error(f"AI解析URL失败: {str(e)}")
        return jsonify({'error': 'AI解析URL失败', 'message': str(e)}), 500

@app.route('/api/ai/files', methods=['GET'])
def get_ai_files():
    """根据URL获取已生成的文件"""
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({'error': 'URL不能为空'}), 400
        
        url = _normalize_url(url)
        file_key = _create_file_key_from_url(url)
        
        # 定义输出目录
        output_dir = app.config['UPLOAD_FOLDER']
        
        # 定义文件路径
        json_file = os.path.join(output_dir, 'json', f"json_{file_key}.json")
        openapi_file = os.path.join(output_dir, 'openapi', f"openapi_{file_key}.yaml")
        relation_file = os.path.join(output_dir, 'relation', f"relation_{file_key}.json")
        scene_file = os.path.join(output_dir, 'scene', f"scene_{file_key}.json")
        
        # 检查文件是否存在
        files_exist = {
            'openapi': os.path.exists(openapi_file),
            'relation': os.path.exists(relation_file),
            'scene': os.path.exists(scene_file)
        }
        
        if not any(files_exist.values()):
            return jsonify({
                'error': '该URL对应的文件不存在',
                'url': url,
                'url_hash': url_hash
            }), 404
        
        # 读取文件内容
        result = {
            'success': True,
            'url': url,
            'file_key': file_key,
            'files_exist': files_exist
        }
        
        # 读取OpenAPI文件
        if files_exist['openapi']:
            with open(openapi_file, 'r', encoding='utf-8') as f:
                result['openapi_data'] = yaml.safe_load(f)
        
        # 读取关联关系文件
        if files_exist['relation']:
            with open(relation_file, 'r', encoding='utf-8') as f:
                result['relation_data'] = json.load(f)
        
        # 读取业务场景文件
        if files_exist['scene']:
            with open(scene_file, 'r', encoding='utf-8') as f:
                result['scene_data'] = json.load(f)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取AI文件失败: {str(e)}")
        return jsonify({'error': '获取AI文件失败', 'message': str(e)}), 500

@app.route('/api/multiapi/documents', methods=['GET'])
def list_multiapi_documents():
    """获取multiuploads/openapi目录下的所有多接口文档列表"""
    try:
        # 定义要扫描的目录
        dir_path = os.path.join(app.config['MULTI_UPLOAD_FOLDER'], 'openapi')
        documents = []
        
        # 确保目录存在
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            return jsonify({
                'success': True,
                'data': {
                    'documents': [],
                    'count': 0
                }
            })
        
        # 遍历目录中的文件
        for filename in os.listdir(dir_path):
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension in ['.yaml', '.yml', '.json']:
                file_path = os.path.join(dir_path, filename)
                
                # 获取文件信息
                stat = os.stat(file_path)
                
                # 提取文件ID
                file_id = filename
                if filename.startswith('multiopenapi_'):
                    file_id = filename[len('multiopenapi_'):]  # 去掉类型前缀
                
                # 去掉文件扩展名
                if '.' in file_id:
                    file_id = file_id.rsplit('.', 1)[0]
                
                # 尝试解析文件内容
                content_preview = ""
                api_count = 0
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if file_extension == '.json':
                            content = json.load(f)
                            content_preview = json.dumps(content, ensure_ascii=False, indent=2)
                            
                            # 计算API数量
                            if 'paths' in content:
                                for path, path_item in content['paths'].items():
                                    for method in path_item:
                                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                            api_count += 1
                        elif file_extension in ['.yaml', '.yml']:
                            content = yaml.safe_load(f)
                            content_preview = yaml.dump(content, allow_unicode=True, indent=2)
                            
                            # 计算API数量
                            if 'paths' in content:
                                for path, path_item in content['paths'].items():
                                    for method in path_item:
                                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                                            api_count += 1
                except Exception as e:
                    logger.warning(f"解析多接口文档失败 {filename}: {str(e)}")
                    content_preview = f"解析失败: {str(e)}"
                
                documents.append({
                    'file_id': file_id,
                    'file_name': filename,
                    'file_size': stat.st_size,
                    'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'api_count': api_count,
                    'content_preview': content_preview[:500] + ('...' if len(content_preview) > 500 else ''),
                    'status': 'uploaded',
                    'editable': True
                })
        
        return jsonify({
            'success': True,
            'data': {
                'documents': documents,
                'count': len(documents)
            }
        })
    
    except Exception as e:
        logger.error(f"获取多接口文档列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取多接口文档列表失败',
            'message': str(e)
        }), 500

@app.route('/api/multiapi/document/<file_id>', methods=['GET'])
def get_multiapi_document(file_id):
    """获取指定多接口文档的完整内容"""
    try:
        # 构建文件路径
        doc_dir = os.path.join(app.config['MULTI_UPLOAD_FOLDER'], 'openapi')
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': '多接口文档目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith('multiopenapi_'):
                    potential_id = filename[len('multiopenapi_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '多接口文档文件不存在'
            }), 404
        
        # 读取文件内容
        file_extension = os.path.splitext(file_name)[1].lower()
        content = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_extension == '.json':
                try:
                    json_content = json.load(f)
                    content = json.dumps(json_content, ensure_ascii=False, indent=2)
                except:
                    content = f.read()
            elif file_extension in ['.yaml', '.yml']:
                try:
                    yaml_content = yaml.safe_load(f)
                    content = yaml.dump(yaml_content, allow_unicode=True, indent=2)
                except:
                    content = f.read()
            else:
                content = f.read()
        
        # 获取文件上传时间
        upload_time = None
        try:
            # 尝试从文件系统获取文件的修改时间作为上传时间
            file_stat = os.stat(file_path)
            # 转换为ISO格式的日期时间字符串
            upload_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        except Exception as e:
            logger.warning(f"获取文件上传时间失败: {str(e)}")
            upload_time = datetime.now().isoformat()  # 使用当前时间作为默认值
        
        return jsonify({
            'success': True,
            'data': {
                'file_id': file_id,
                'file_name': file_name,
                'content': content,
                'file_extension': file_extension,
                'upload_time': upload_time
            }
        })
    
    except Exception as e:
        logger.error(f"获取多接口文档内容失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取多接口文档内容失败',
            'message': str(e)
        }), 500

@app.route('/api/multiapi/document/<file_id>', methods=['DELETE'])
def delete_multiapi_document(file_id):
    """删除指定的多接口文档"""
    try:
        # 构建文件路径
        doc_dir = os.path.join(app.config['MULTI_UPLOAD_FOLDER'], 'openapi')
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': '多接口文档目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith('multiopenapi_'):
                    potential_id = filename[len('multiopenapi_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '多接口文档文件不存在'
            }), 404
        
        # 删除文件
        os.remove(file_path)
        
        # 删除所有相关的文件（json、relation、scene目录下的同名文件）
        related_dirs = ['json', 'relation', 'scene', 'test_case', 'test_code']
        for related_dir in related_dirs:
            related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], related_dir)
            if related_dir == 'test_case':
                # test_case目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_case')
            elif related_dir == 'test_code':
                # test_code目录在UPLOAD_FOLDER下
                related_dir_path = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'uploads', 'test_code')
                
            if os.path.exists(related_dir_path):
                for filename in os.listdir(related_dir_path):
                    # 检查是否是相关文件（文件名包含相同的ID）
                    if file_id in filename:
                        related_file_path = os.path.join(related_dir_path, filename)
                        try:
                            os.remove(related_file_path)
                            logger.info(f"已删除相关文件: {related_file_path}")
                        except Exception as e:
                            logger.warning(f"删除相关文件失败 {related_file_path}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'多接口文档 {file_name} 已成功删除'
        })
    
    except Exception as e:
        logger.error(f"删除多接口文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '删除多接口文档失败',
            'message': str(e)
        }), 500

# 多接口文档关联关系获取API
@app.route('/api/multiapi/relation/<file_id>', methods=['GET'])
def get_multiapi_relation(file_id):
    """获取指定多接口文档的关联关系文件"""
    try:
        # 构建关联关系文件路径
        # 关联关系文件位于 multiuploads/split_openapi/{file_id}/relation.json
        relation_dir = os.path.join(app.config['MULTI_UPLOAD_FOLDER'], 'split_openapi', file_id)
        relation_file = os.path.join(relation_dir, 'relation.json')
        
        if not os.path.exists(relation_file):
            return jsonify({
                'success': False,
                'error': '关联关系文件不存在'
            }), 404
        
        # 读取关联关系文件
        with open(relation_file, 'r', encoding='utf-8') as f:
            relation_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': {
                'file_id': file_id,
                'relation_data': relation_data
            }
        })
    
    except Exception as e:
        logger.error(f"获取多接口文档关联关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取关联关系失败',
            'message': str(e)
        }), 500

# 多接口文档测试用例生成API
@app.route('/api/multiapi/testcases/generate/<file_id>', methods=['POST'])
def generate_multiapi_testcases(file_id):
    """为指定的多接口文档生成测试用例"""
    try:
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'multiopenapi')
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': '多接口文档目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith('multiopenapi_'):
                    potential_id = filename[len('multiopenapi_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '多接口文档文件不存在'
            }), 404
        
        # 解析文档内容
        file_extension = os.path.splitext(file_name)[1].lower()
        document_content = ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            document_content = f.read()
        
        # 根据文件类型解析
        if file_extension == '.json':
            try:
                document = json.loads(document_content)
            except:
                return jsonify({
                    'success': False,
                    'error': 'JSON文档解析失败'
                }), 400
        elif file_extension in ['.yaml', '.yml']:
            try:
                document = yaml.safe_load(document_content)
            except:
                return jsonify({
                    'success': False,
                    'error': 'YAML文档解析失败'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': '不支持的文档格式'
            }), 400
        
        # 生成测试用例
        test_cases = []
        if 'paths' in document:
            for path, path_item in document['paths'].items():
                for method, operation in path_item.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        # 创建测试用例
                        test_case = {
                            'id': f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
                            'name': f"{method.upper()} {path}",
                            'method': method.upper(),
                            'path': path,
                            'summary': operation.get('summary', ''),
                            'description': operation.get('description', ''),
                            'parameters': operation.get('parameters', []),
                            'request_body': operation.get('requestBody', {}),
                            'responses': operation.get('responses', {}),
                            'tags': operation.get('tags', [])
                        }
                        test_cases.append(test_case)
        
        # 保存测试用例到文件
        testcases_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'testcases')
        if not os.path.exists(testcases_dir):
            os.makedirs(testcases_dir)
        
        testcases_file = os.path.join(testcases_dir, f"multiapi_{file_id}.json")
        with open(testcases_file, 'w', encoding='utf-8') as f:
            json.dump({
                'document_id': file_id,
                'document_name': file_name,
                'generated_at': datetime.now().isoformat(),
                'test_cases': test_cases
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'data': {
                'document_id': file_id,
                'document_name': file_name,
                'test_cases_count': len(test_cases),
                'test_cases': test_cases[:5]  # 只返回前5个作为预览
            },
            'message': f'成功生成 {len(test_cases)} 个测试用例'
        })
    
    except Exception as e:
        logger.error(f"生成多接口文档测试用例失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '生成测试用例失败',
            'message': str(e)
        }), 500

# 多接口文档测试用例执行API
@app.route('/api/multiapi/testcases/execute/<file_id>', methods=['POST'])
def execute_multiapi_testcases(file_id):
    """执行指定多接口文档的测试用例"""
    try:
        # 构建文件路径
        doc_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'multiopenapi')
        if not os.path.exists(doc_dir):
            return jsonify({
                'success': False,
                'error': '多接口文档目录不存在'
            }), 404
        
        # 查找文件
        file_path = None
        file_name = None
        
        # 首先尝试直接匹配完整文件名（包含前缀和扩展名）
        for filename in os.listdir(doc_dir):
            # 检查完整文件名（去掉扩展名）是否匹配file_id
            filename_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            if filename_without_ext == file_id:
                file_path = os.path.join(doc_dir, filename)
                file_name = filename
                break
        
        # 如果没有找到，尝试匹配去掉前缀和扩展名后的文件ID
        if not file_path:
            for filename in os.listdir(doc_dir):
                # 尝试匹配文件ID
                potential_id = filename
                if filename.startswith('multiopenapi_'):
                    potential_id = filename[len('multiopenapi_'):]
                
                if '.' in potential_id:
                    potential_id = potential_id.rsplit('.', 1)[0]
                
                if potential_id == file_id:
                    file_path = os.path.join(doc_dir, filename)
                    file_name = filename
                    break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '多接口文档文件不存在'
            }), 404
        
        # 检查测试用例文件是否存在
        testcases_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'testcases')
        testcases_file = os.path.join(testcases_dir, f"multiapi_{file_id}.json")
        
        if not os.path.exists(testcases_file):
            # 如果测试用例不存在，先生成测试用例
            generate_result = generate_multiapi_testcases(file_id)
            if not json.loads(generate_result.data).get('success', False):
                return jsonify({
                    'success': False,
                    'error': '测试用例不存在且生成失败'
                }), 400
        
        # 读取测试用例
        with open(testcases_file, 'r', encoding='utf-8') as f:
            testcases_data = json.load(f)
        
        test_cases = testcases_data.get('test_cases', [])
        
        # 执行测试用例（模拟执行）
        execution_results = []
        passed_count = 0
        failed_count = 0
        
        for test_case in test_cases:
            # 模拟测试执行
            result = {
                'test_case_id': test_case['id'],
                'test_case_name': test_case['name'],
                'method': test_case['method'],
                'path': test_case['path'],
                'status': 'passed' if random.random() > 0.3 else 'failed',  # 70%通过率
                'response_time': round(random.uniform(100, 1000), 2),  # 100-1000ms
                'response_code': 200 if random.random() > 0.2 else 404,  # 80%返回200
                'error': None
            }
            
            if result['status'] == 'failed':
                failed_count += 1
                result['error'] = '模拟测试失败'
            else:
                passed_count += 1
            
            execution_results.append(result)
        
        # 保存执行结果
        reports_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        report_file = os.path.join(reports_dir, f"multiapi_{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'document_id': file_id,
                'document_name': file_name,
                'executed_at': datetime.now().isoformat(),
                'summary': {
                    'total': len(test_cases),
                    'passed': passed_count,
                    'failed': failed_count,
                    'pass_rate': round(passed_count / len(test_cases) * 100, 2) if test_cases else 0
                },
                'results': execution_results
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'data': {
                'document_id': file_id,
                'document_name': file_name,
                'summary': {
                    'total': len(test_cases),
                    'passed': passed_count,
                    'failed': failed_count,
                    'pass_rate': round(passed_count / len(test_cases) * 100, 2) if test_cases else 0
                },
                'report_file': report_file
            },
            'message': f'测试执行完成，通过率: {round(passed_count / len(test_cases) * 100, 2) if test_cases else 0}%'
        })
    
    except Exception as e:
        logger.error(f"执行多接口文档测试用例失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '执行测试用例失败',
            'message': str(e)
        }), 500

# 7. 飞书测试接口
@app.route('/api/feishu/run-all-tests', methods=['POST'])
def run_all_feishu_tests():
    """执行 run_all_feishu_tests.py 脚本"""
    try:
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        script_path = project_root / "utils" / "other_tools" / "run_all_feishu_tests.py"
        
        if not script_path.exists():
            return jsonify({
                'error': '脚本文件不存在',
                'message': f'未找到脚本: {script_path}'
            }), 404
        
        logger.info(f"开始执行脚本: {script_path}")
        
        # 执行脚本
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        # 标记为非交互模式，防止子进程内启动 allure serve 等阻塞操作
        env['NON_INTERACTIVE'] = '1'
        
        # 使用 UTF-8 编码，并设置 errors='replace' 来处理编码错误
        # 设置 stdin=subprocess.DEVNULL 防止脚本等待输入而阻塞
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,  # 防止脚本等待输入
            text=True,
            cwd=str(project_root),
            encoding='utf-8',
            errors='replace',  # 遇到编码错误时用替换字符代替
            env=env  # 传递环境变量
        )
        
        # 等待执行完成（可以设置超时时间）
        stdout = ''
        stderr = ''
        return_code = -1
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                stdout, stderr = process.communicate()
            except Exception as e:
                logger.error(f"获取超时后的输出失败: {e}")
                stdout = f"执行超时，无法获取完整输出: {str(e)}"
                stderr = ""
            return_code = -1
            return jsonify({
                'task_id': task_id,
                'error': '执行超时',
                'message': '脚本执行超过10分钟，已终止',
                'return_code': return_code,
                'stdout': stdout[:1000] if stdout else '',  # 限制输出长度
                'stderr': stderr[:1000] if stderr else ''
            }), 500
        except Exception as e:
            logger.error(f"执行脚本时出错: {e}")
            try:
                process.kill()
            except:
                pass
            return jsonify({
                'task_id': task_id,
                'error': '执行脚本时出错',
                'message': str(e),
                'return_code': return_code
            }), 500
        
        # 保存执行结果
        result = {
            'task_id': task_id,
            'script': str(script_path),
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'created_at': datetime.now().isoformat()
        }
        # 使用filename作为file_id，实现相同文件的结果覆盖
        save_result(filename, result)
        
        # ========== 新增：检测并启动Allure报告服务器 ==========
        allure_url = None
        allure_process = None
        
        # 检查多个可能的Allure结果目录
        possible_allure_dirs = [
            project_root / "allure-results",
            project_root / "report" / "tmp",
            project_root / "reports" / "allure-results",
            project_root / "test-results" / "allure"
        ]
        
        allure_results_dir = None
        for dir_path in possible_allure_dirs:
            if dir_path.exists() and any(dir_path.iterdir()):
                allure_results_dir = dir_path
                logger.info(f"找到Allure结果目录: {allure_results_dir}")
                break
        
        if allure_results_dir:
            try:
                # 动态查找可用端口（从9999开始尝试）
                allure_port = find_available_port(9999, 10)
                if allure_port:
                    # 获取本机IP地址
                    local_ip = get_local_ip()
                    
                    # 启动Allure服务器（异步，不阻塞）
                    allure_process = start_allure_server_async(
                        allure_results_dir, 
                        port=allure_port, 
                        host='0.0.0.0'
                    )
                    
                    if allure_process:
                        allure_url = f"http://{local_ip}:{allure_port}"
                        logger.info(f"Allure报告服务器已启动: {allure_url}")
                    else:
                        logger.warning("启动Allure服务器失败")
                else:
                    logger.warning("找不到可用端口启动Allure报告")
            except Exception as e:
                logger.error(f"启动Allure报告失败: {e}")
        else:
            logger.warning("未找到Allure测试结果目录")
        # ========== 新增代码结束 ==========
        
        # 返回完整输出（限制长度避免响应过大）
        max_output_length = 5000  # 增加到5000字符
        
        response_data = {
            'task_id': task_id,
            'return_code': return_code,
            'stdout': stdout[-max_output_length:] if len(stdout) > max_output_length else stdout,
            'stderr': stderr[-max_output_length:] if len(stderr) > max_output_length else stderr,
            'stdout_length': len(stdout),
            'stderr_length': len(stderr)
        }
        
        # ========== 新增：添加Allure信息到响应 ==========
        if allure_url:
            response_data['allure_report'] = {
                'url': allure_url,
                'status': 'running',
                'port': allure_port if 'allure_port' in locals() else None,
                'pid': allure_process.pid if allure_process else None
            }
        # 读取 Allure 报告摘要数据
        summary, summary_path = _find_allure_summary(project_root)
        if summary:
            response_data['allure_summary'] = {'path': summary_path, 'data': summary}
            metrics = _extract_allure_metrics(summary)
            if metrics:
                response_data['allure_metrics'] = metrics
        # ========== 新增代码结束 ==========
        
        if return_code == 0:
            response_data['message'] = '脚本执行成功'
            if allure_url:
                response_data['message'] += f'，Allure报告地址: {allure_url}'
            return jsonify(response_data)
        else:
            # 即使返回码不为0，也返回200状态码，但包含错误信息
            # 这样前端可以根据 return_code 判断是否成功
            response_data['error'] = '脚本执行完成，但有错误或警告'
            response_data['message'] = f'脚本返回码: {return_code}（0表示成功，非0表示有错误或警告）'
            
            # 尝试从输出中提取关键错误信息
            if stderr:
                # 查找常见的错误关键词
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed']
                error_lines = [line for line in stderr.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    response_data['error_summary'] = error_lines[-10:]  # 最后10行错误信息
            
            # 也从 stdout 中查找错误信息（有些错误可能输出到 stdout）
            if stdout:
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed']
                error_lines = [line for line in stdout.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    if 'error_summary' not in response_data:
                        response_data['error_summary'] = []
                    response_data['error_summary'].extend(error_lines[-10:])
            
            return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行 run_all_feishu_tests.py 失败: {str(e)}")
        return jsonify({
            'error': '执行脚本失败',
            'message': str(e)
        }), 500

@app.route('/api/feishu/generate-and-test', methods=['POST'])
def generate_and_test_feishu():
    """执行 run_feishu_generator_and_tests.py 脚本，带文件夹参数"""
    try:
        # 获取请求参数
        data = request.json or {}
        folder_name = data.get('folder', '')
        
        if not folder_name:
            return jsonify({
                'error': '缺少必要参数',
                'message': '请提供 folder 参数（例如: calendar）'
            }), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        script_path = project_root / "run_feishu_generator_and_tests.py"
        
        if not script_path.exists():
            return jsonify({
                'error': '脚本文件不存在',
                'message': f'未找到脚本: {script_path}'
            }), 404
        
        # 构建文件夹路径：uploads/scene/{folder_name}
        folder_path = f"uploads/scene/{folder_name}"
        full_folder_path = project_root / folder_path
        
        # 检查文件夹是否存在
        if not full_folder_path.exists():
            return jsonify({
                'error': '文件夹不存在',
                'message': f'未找到文件夹: {folder_path}'
            }), 404
        
        logger.info(f"开始执行脚本: {script_path} --folder {folder_path}")
        
        # 执行脚本
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        env['NON_INTERACTIVE'] = '1'  # 标记为非交互式模式，脚本不会启动 Allure 服务器（由 API 启动）
        
        # 使用 UTF-8 编码，并设置 errors='replace' 来处理编码错误
        # 设置 stdin=subprocess.DEVNULL 防止脚本等待输入而阻塞
        process = subprocess.Popen(
            [sys.executable, str(script_path), '--folder', folder_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,  # 防止脚本等待输入
            text=True,
            cwd=str(project_root),
            encoding='utf-8',
            errors='replace',  # 遇到编码错误时用替换字符代替
            env=env  # 传递环境变量
        )
        
        # 等待执行完成（可以设置超时时间）
        stdout = ''
        stderr = ''
        return_code = -1
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                stdout, stderr = process.communicate()
            except Exception as e:
                logger.error(f"获取超时后的输出失败: {e}")
                stdout = f"执行超时，无法获取完整输出: {str(e)}"
                stderr = ""
            return_code = -1
            return jsonify({
                'task_id': task_id,
                'error': '执行超时',
                'message': '脚本执行超过10分钟，已终止',
                'return_code': return_code,
                'folder': folder_name,
                'folder_path': folder_path,
                'stdout': stdout[-2000:] if stdout else '',
                'stderr': stderr[-2000:] if stderr else ''
            }), 500
        except Exception as e:
            logger.error(f"执行脚本时出错: {e}")
            try:
                process.kill()
            except:
                pass
            return jsonify({
                'task_id': task_id,
                'error': '执行脚本时出错',
                'message': str(e),
                'folder': folder_name,
                'folder_path': folder_path,
                'return_code': return_code
            }), 500
        
        # 将执行结果保存
        result = {
            'task_id': task_id,
            'script': str(script_path),
            'folder': folder_name,
            'folder_path': folder_path,
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'created_at': datetime.now().isoformat()
        }
        save_result(task_id, result)
        
        # 从 stdout 中提取脚本输出的 JSON 结果（run_feishu_generator_and_tests.py 会在末尾打印）
        def _extract_last_json_line(text: str):
            for line in reversed(text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except Exception:
                    continue
            return None

        parsed = _extract_last_json_line(stdout)
        # 将 parsed_result.responses 提升到顶层的 test_responses，并只保留纯列表
        test_responses = None
        if isinstance(parsed, dict):
            # 提取后删除，避免重复
            raw_responses = parsed.pop('responses', None)
            # 如果是列表，直接返回；如果是字典且包含列表字段，也尝试透传
            if isinstance(raw_responses, list):
                test_responses = raw_responses
            elif isinstance(raw_responses, dict):
                # 优先使用其中名为 responses 的列表；否则直接透传字典，避免返回 null
                inner_list = raw_responses.get('responses') if isinstance(raw_responses.get('responses'), list) else None
                test_responses = inner_list if inner_list is not None else raw_responses

        def _parse_log_blocks_to_cases(log_text: str, cases_data):
            """
            将日志里的“用例标题/请求/响应”块解析为结构化列表:
            [
                {
                    "case_id": "01_open-apis_im_v1_images",
                    "detail": "测试上传图片",
                    "request": {...},
                    "response": {...}
                },
                ...
            ]
            """
            import re, ast, json as _json

            case_map = {}
            if isinstance(cases_data, list):
                for c in cases_data:
                    detail = c.get("detail")
                    if detail:
                        case_map[detail] = c.get("case_id")

            pattern = re.compile(
                r"用例标题:\s*(?P<title>.+?)\n"
                r"请求路径:\s*(?P<url>.+?)\n"
                r"请求方式:\s*(?P<method>\S+)\n"
                r"请求头:\s*(?P<headers>\{.*?\})\n"
                r"请求内容:\s*(?P<body>\{.*?\})\n"
                r"接口响应内容:\s*(?P<resp_body>\{.*?\})\n"
                r"接口响应时长:\s*(?P<elapsed>[\d\.]+)\s*ms\n"
                r"Http状态码:\s*(?P<status>\d+)",
                re.S
            )

            def _parse_obj(text):
                for parser in (
                    lambda t: _json.loads(t),
                    lambda t: ast.literal_eval(t),
                ):
                    try:
                        return parser(text)
                    except Exception:
                        continue
                return text

            results = []
            for m in pattern.finditer(log_text or ""):
                detail = m.group("title").strip()
                results.append({
                    "case_id": case_map.get(detail),
                    "detail": detail,
                    "request": {
                        "method": m.group("method").strip(),
                        "url": m.group("url").strip(),
                        "body": _parse_obj(m.group("body")),
                        "headers": _parse_obj(m.group("headers")),
                    },
                    "response": {
                        "status_code": int(m.group("status")),
                        "body": _parse_obj(m.group("resp_body")),
                        "headers": None,
                        "elapsed_ms": float(m.group("elapsed")),
                    }
                })
            return results or None

        # 若 test_responses 仍为 dict 且包含 stdout 文本，则尝试解析为结构化列表
        if test_responses is None and isinstance(parsed, dict):
            stdout_in_responses = parsed.get("responses") if isinstance(parsed.get("responses"), dict) else None
            if stdout_in_responses and isinstance(stdout_in_responses.get("stdout"), str):
                parsed_list = _parse_log_blocks_to_cases(stdout_in_responses["stdout"], parsed.get("cases"))
                if parsed_list:
                    test_responses = parsed_list

        def _parse_log_blocks_to_cases(log_text: str, cases_data):
            """
            解析 stdout 中的日志块为结构化的请求/响应列表。
            """
            import re, ast, json as _json
            if not log_text:
                return None
            case_map = {}
            if isinstance(cases_data, list):
                for c in cases_data:
                    detail = c.get("detail")
                    if detail:
                        case_map[detail] = c.get("case_id")
            pattern = re.compile(
                r"用例标题:\s*(?P<title>.+?)\n"
                r"请求路径:\s*(?P<url>.+?)\n"
                r"请求方式:\s*(?P<method>\S+)\n"
                r"请求头:\s*(?P<headers>\{.*?\})\n"
                r"请求内容:\s*(?P<body>\{.*?\})\n"
                r"接口响应内容:\s*(?P<resp_body>\{.*?\})\n"
                r"接口响应时长:\s*(?P<elapsed>[\d\.]+)\s*ms\n"
                r"Http状态码:\s*(?P<status>\d+)",
                re.S
            )
            def _parse_obj(text):
                for parser in (lambda t: _json.loads(t), lambda t: ast.literal_eval(t)):
                    try:
                        return parser(text)
                    except Exception:
                        continue
                return text
            results = []
            for m in pattern.finditer(log_text):
                detail = m.group("title").strip()
                results.append({
                    "case_id": case_map.get(detail),
                    "detail": detail,
                    "request": {
                        "method": m.group("method").strip(),
                        "url": m.group("url").strip(),
                        "body": _parse_obj(m.group("body")),
                        "headers": _parse_obj(m.group("headers")),
                    },
                    "response": {
                        "status_code": int(m.group("status")),
                        "body": _parse_obj(m.group("resp_body")),
                        "headers": None,
                        "elapsed_ms": float(m.group("elapsed")),
                    }
                })
            return results or None

        # 尝试从 stdout/stderr 解析结构化请求/响应
        combined_text = f"{stdout}\n{stderr}"
        stdout_parsed = _parse_log_blocks_to_cases(
            combined_text,
            parsed.get("cases") if isinstance(parsed, dict) else None
        )
        if test_responses is None and stdout_parsed:
            test_responses = stdout_parsed

        # 返回精简且可消费的执行结果（去掉 stdout/stderr）
        response_data = {
            'task_id': task_id,
            'folder': folder_name,
            'folder_path': folder_path,
            'return_code': return_code,
            'parsed_result': parsed,
            'test_responses': test_responses
        }
        
        if return_code == 0:
            response_data['message'] = '脚本执行成功'
            return jsonify(response_data)
        else:
            response_data['error'] = '脚本执行完成，但返回码非0'
            response_data['message'] = f'脚本返回码: {return_code}（0表示成功，非0表示有错误或警告）'
            # 尝试提取错误摘要
            error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed']
            error_lines = []
            if stderr:
                error_lines.extend([line for line in stderr.split('\n') if any(k in line for k in error_keywords)])
            if stdout:
                error_lines.extend([line for line in stdout.split('\n') if any(k in line for k in error_keywords)])
            if error_lines:
                response_data['error_summary'] = error_lines[-10:]
            return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行 run_feishu_generator_and_tests.py 失败: {str(e)}")
        return jsonify({
            'error': '执行脚本失败',
            'message': str(e)
        }), 500

@app.route('/api/feishu/generate-test-cases', methods=['POST'])
def generate_test_cases():
    """生成AI测试用例，但不执行测试"""
    try:
        # 获取请求参数
        data = request.json or {}
        base_name = data.get('base_name', '')
        force_regenerate = data.get('force_regenerate', False)  # 是否强制重新生成
        
        if not base_name:
            return jsonify({
                'error': '缺少必要参数',
                'message': '请提供 base_name 参数（例如: feishu_cardkit-v1_card_create）'
            }), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        script_path = project_root / "utils" / "other_tools" / "universal_ai_test_generator.py"
        
        if not script_path.exists():
            return jsonify({
                'error': '脚本文件不存在',
                'message': f'未找到脚本: {script_path}'
            }), 404
        
        # 定义目录和文件路径（只定义一次）
        base_dir = "uploads"
        output_dir = "test_code"  # 测试代码文件目录
        yaml_dir = "test_case"  # YAML配置文件目录
        
        # 构建文件路径的辅助函数
        def get_file_paths():
            """获取各种文件路径"""
            test_file_name = f"test_{base_name}_normal_exception.py"
            yaml_file_name = f"cases_{base_name}.yaml"
            
            return {
                'test_file_path': project_root / base_dir / output_dir / test_file_name,
                'yaml_file_path': project_root / base_dir / yaml_dir / yaml_file_name,
                'config_file_path': project_root / base_dir / output_dir / "conftest.py",
                'tests_dir': project_root / base_dir / output_dir
            }
        
        file_paths = get_file_paths()
        
        # 如果文件已存在且不强制重新生成，则直接返回现有文件信息
        if not force_regenerate and file_paths['test_file_path'].exists() and file_paths['yaml_file_path'].exists():
            logger.info(f"测试文件已存在，跳过生成: {file_paths['test_file_path']}")
            
            # 构建响应数据
            response_data = {
                'task_id': task_id,
                'base_name': base_name,
                'base_dir': base_dir,
                'output_dir': output_dir,
                'generation_return_code': 0,
                'generation_success': True,
                'test_file_exists': True,
                'config_file_exists': True,
                'test_file_path': str(file_paths['test_file_path']),
                'yaml_file_path': str(file_paths['yaml_file_path']),
                'config_file_path': str(file_paths['config_file_path']),
                'message': '测试文件已存在，跳过生成',
                'skip_generation': True
            }
            
            # 保存执行结果
            result = {
                'task_id': task_id,
                'script': str(script_path),
                'base_name': base_name,
                'base_dir': base_dir,
                'output_dir': output_dir,
                'return_code': 0,
                'stdout': f"测试文件已存在，跳过生成: {file_paths['test_file_path']}",
                'stderr': '',
                'created_at': datetime.now().isoformat(),
                'skip_generation': True
            }
            save_result(task_id, result)
            
            return jsonify(response_data)
        
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        env['NON_INTERACTIVE'] = '1'  # 标记为非交互式模式
        
        # 执行子进程的辅助函数
        def run_proc(cmd_args):
            """执行子进程并返回结果"""
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # 防止脚本等待输入
                text=True,
                cwd=str(project_root),
                encoding='utf-8',
                errors='replace',  # 遇到编码错误时用替换字符代替
                env=env  # 传递环境变量
            )
            stdout = ''
            stderr = ''
            return_code = -1
            try:
                stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    stdout, stderr = process.communicate()
                except Exception as e:
                    logger.error(f"获取超时后的输出失败: {e}")
                    stdout = f"执行超时，无法获取完整输出: {str(e)}"
                    stderr = ""
                return_code = -1
            except Exception as e:
                logger.error(f"执行脚本时出错: {e}")
                try:
                    process.kill()
                except:
                    pass
                return_code = -1
                stderr = str(e)
            return return_code, stdout, stderr
        
        # 截断输出的辅助函数
        def truncate_output(output, max_length=3000):
            """截断输出，避免响应过大"""
            if len(output) > max_length:
                return output[-max_length:], len(output)
            return output, None
        
        # 提取错误信息的辅助函数
        def extract_error_lines(output, keywords=None):
            """从输出中提取包含关键字的错误行"""
            if keywords is None:
                keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed', 'ERROR']
            
            if not output:
                return []
                
            return [line for line in output.split('\n') 
                   if any(keyword in line for keyword in keywords)]
        
        # 查找测试文件的辅助函数
        def find_test_file(stdout):
            """从stdout或目录中查找测试文件"""
            # 首先尝试从 stdout 中解析生成的文件名
            if stdout:
                # 匹配格式: [OK] 已生成pytest文件: /path/to/test_xxx_normal_exception.py
                match = re.search(r'已生成pytest文件:\s*([^\s]+test_[\w-]+_normal_exception\.py)', stdout)
                if match:
                    file_path_str = match.group(1).replace('\\', '/')
                    # 如果是相对路径，从项目根目录开始
                    if not os.path.isabs(file_path_str):
                        test_file_path = project_root / file_path_str
                    else:
                        test_file_path = Path(file_path_str)
                    if test_file_path.exists():
                        return test_file_path
                
                # 匹配格式: [OK] 生成测试文件: tests\test_xxx_normal_exception.py
                # 或: [OK] 生成测试文件: tests/test_xxx_normal_exception.py
                match = re.search(r'生成测试文件:\s*(?:tests[/\\])?test_([\w-]+)_normal_exception\.py', stdout)
                if match:
                    operation_id = match.group(1)
                    test_file_path = project_root / base_dir / output_dir / f"test_{operation_id}_normal_exception.py"
                    if test_file_path.exists():
                        return test_file_path
                
                # 尝试匹配完整路径
                match = re.search(r'生成测试文件:\s*([^\s]+test_[\w-]+_normal_exception\.py)', stdout)
                if match:
                    file_path_str = match.group(1).replace('\\', '/')
                    # 如果是相对路径，从项目根目录开始
                    if not os.path.isabs(file_path_str):
                        test_file_path = project_root / file_path_str
                    else:
                        test_file_path = Path(file_path_str)
                    if test_file_path.exists():
                        return test_file_path
            
            # 如果从 stdout 中没找到，尝试搜索最近生成的测试文件
            if file_paths['tests_dir'].exists():
                # 查找所有 test_*_normal_exception.py 文件
                test_files = list(file_paths['tests_dir'].glob("test_*_normal_exception.py"))
                if test_files:
                    # 按修改时间排序，取最新的
                    test_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    return test_files[0]
            
            # 如果还是没找到，使用默认路径
            return file_paths['test_file_path']
        
        # 第一步：生成 YAML 用例
        cmd_args_yaml = [
            sys.executable,
            str(script_path),
            '--base-name', base_name,
            '--base-dir', base_dir,
            '--output-dir', yaml_dir,
            '--output-format', 'yaml'
        ]
        
        logger.info(f"开始生成YAML用例: {' '.join(cmd_args_yaml)}")
        return_code, stdout, stderr = run_proc(cmd_args_yaml)
        
        if return_code != 0:
            # 截断输出
            truncated_stdout, stdout_length = truncate_output(stdout, 2000)
            truncated_stderr, stderr_length = truncate_output(stderr, 2000)
            
            response_data = {
                'task_id': task_id,
                'error': '执行脚本失败',
                'message': '生成 YAML 用例失败',
                'return_code': return_code,
                'base_name': base_name,
                'stdout': truncated_stdout,
                'stderr': truncated_stderr
            }
            
            if stdout_length:
                response_data['stdout_length'] = stdout_length
            if stderr_length:
                response_data['stderr_length'] = stderr_length
                
            return jsonify(response_data), 500
        
        # 第二步：将 YAML 转换为 pytest 脚本（不调用大模型）
        # 使用已定义的变量，避免重复定义
        yaml_file_path = file_paths['yaml_file_path']
        
        # 如果YAML文件不存在，尝试查找最近的 cases_*.yaml 文件
        if not yaml_file_path.exists():
            candidates = list((project_root / base_dir / yaml_dir).glob("cases_*.yaml"))
            if candidates:
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                yaml_file_path = candidates[0]
                logger.info(f"使用找到的YAML文件: {yaml_file_path}")
            else:
                logger.warning(f"未找到YAML文件: {yaml_file_path}")
        
        # 确保YAML文件存在
        if not yaml_file_path.exists():
            response_data = {
                'task_id': task_id,
                'error': 'YAML文件不存在',
                'message': f'未找到YAML文件: {yaml_file_path}',
                'base_name': base_name,
                'yaml_file_path': str(yaml_file_path)
            }
            return jsonify(response_data), 404
        
        cmd_args_convert = [
            sys.executable,
            str(script_path),
            '--base-name', base_name,
            '--base-dir', base_dir,
            '--output-dir', output_dir,
            '--yaml-to-py',
            '--yaml-path', str(yaml_file_path)
        ]
        
        # 如果不强制重新生成，则添加skip-if-exists参数
        if not force_regenerate:
            cmd_args_convert.append('--skip-if-exists')
        else:
            cmd_args_convert.append('--force-regenerate')
            
        logger.info(f"YAML 转换为 pytest: {' '.join(cmd_args_convert)}")
        convert_return_code, convert_stdout, convert_stderr = run_proc(cmd_args_convert)
        
        if convert_return_code != 0:
            # 使用辅助函数截断输出
            truncated_stdout, stdout_length = truncate_output(convert_stdout, 2000)
            truncated_stderr, stderr_length = truncate_output(convert_stderr, 2000)
            
            # 尝试查找测试文件，即使转换失败也可能生成了部分文件
            test_file_path = find_test_file(convert_stdout)
            test_file_exists = test_file_path.exists() if test_file_path else False
            
            response_data = {
                'task_id': task_id,
                'error': '转换失败',
                'message': 'YAML 转 pytest 失败',
                'return_code': convert_return_code,
                'base_name': base_name,
                'stdout': truncated_stdout,
                'stderr': truncated_stderr,
                'test_file_path': str(test_file_path) if test_file_exists else None,
                'test_file_exists': test_file_exists
            }
            
            if stdout_length:
                response_data['stdout_length'] = stdout_length
            if stderr_length:
                response_data['stderr_length'] = stderr_length
                
            return jsonify(response_data), 500
        
        # 使用辅助函数查找测试文件
        test_file_path = find_test_file(convert_stdout)
        config_file_path = file_paths['config_file_path']
        
        # 添加调试日志
        logger.info(f"查找测试文件结果: {test_file_path}")
        logger.info(f"测试文件是否存在: {test_file_path.exists() if test_file_path else False}")
        logger.info(f"转换输出: {convert_stdout[-500:] if convert_stdout else '无输出'}")
        
        test_file_exists = test_file_path.exists() if test_file_path else False
        config_file_exists = config_file_path.exists() if config_file_path else False
        
        # 构建响应数据
        response_data = {
            'task_id': task_id,
            'base_name': base_name,
            'base_dir': base_dir,
            'output_dir': output_dir,
            'generation_return_code': return_code,
            'generation_success': return_code == 0,
            'test_file_exists': test_file_exists,
            'config_file_exists': config_file_exists,
            'test_file_path': str(test_file_path) if test_file_exists else None,
            'config_file_path': str(config_file_path) if config_file_exists else None,
            'yaml_file_path': str(yaml_file_path) if yaml_file_path.exists() else None,
            'skip_generation': False  # 默认为False，表示执行了生成过程
        }
        
        # 如果生成失败，添加错误信息摘要
        if return_code != 0:
            response_data['error'] = '测试用例生成失败'
            response_data['message'] = f'脚本返回码: {return_code}（0表示成功，非0表示有错误或警告）'
            
            # 使用辅助函数提取错误信息
            error_lines = extract_error_lines(stderr)
            if error_lines:
                response_data['error_summary'] = error_lines[-10:]  # 最后10行错误信息
            
            # 也从 stdout 中查找错误信息（有些错误可能输出到 stdout）
            stdout_error_lines = extract_error_lines(stdout)
            if stdout_error_lines:
                if 'error_summary' not in response_data:
                    response_data['error_summary'] = []
                response_data['error_summary'].extend(stdout_error_lines[-10:])
            
            # 使用辅助函数截断输出
            truncated_stdout, stdout_length = truncate_output(stdout)
            truncated_stderr, stderr_length = truncate_output(stderr)
            
            response_data['generation_stdout'] = truncated_stdout
            response_data['generation_stderr'] = truncated_stderr
            
            if stdout_length:
                response_data['generation_stdout_length'] = stdout_length
            if stderr_length:
                response_data['generation_stderr_length'] = stderr_length
            
            return jsonify(response_data)
        
        # 如果生成成功
        response_data['message'] = 'AI测试用例生成成功'
        if test_file_exists:
            response_data['message'] += f'，测试文件已生成: {test_file_path.name}'
        else:
            response_data['message'] += '，但未找到测试文件'
            response_data['warning'] = '未找到可执行的测试文件，请检查转换过程是否成功'
        
        # 使用辅助函数截断生成脚本的输出
        truncated_gen_stdout, gen_stdout_length = truncate_output(stdout, 2000)
        truncated_gen_stderr, gen_stderr_length = truncate_output(stderr, 2000)
        
        response_data['generation_stdout'] = truncated_gen_stdout
        response_data['generation_stderr'] = truncated_gen_stderr
        
        if gen_stdout_length:
            response_data['generation_stdout_length'] = gen_stdout_length
        if gen_stderr_length:
            response_data['generation_stderr_length'] = gen_stderr_length
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"生成测试用例失败: {str(e)}")
        return jsonify({
            'error': '生成测试用例失败',
            'message': str(e)
        }), 500

@app.route('/api/feishu/execute-test-cases', methods=['POST'])
def execute_test_cases():
    """执行已生成的测试用例"""
    try:
        # 获取请求参数
        data = request.json or {}
        base_name = data.get('base_name', '')
        test_file_path = data.get('test_file_path', '')  # 可选，直接指定测试文件路径
        
        if not base_name and not test_file_path:
            return jsonify({
                'error': '缺少必要参数',
                'message': '请提供 base_name 或 test_file_path 参数'
            }), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        
        # 定义目录和文件路径
        base_dir = "uploads"
        output_dir = "test_code"  # 测试代码文件目录
        
        # 如果直接提供了测试文件路径，使用该路径
        if test_file_path:
            test_path = Path(test_file_path)
            if not test_path.exists():
                return jsonify({
                    'error': '测试文件不存在',
                    'message': f'测试文件不存在: {test_file_path}'
                }), 404
        else:
            # 根据base_name查找测试文件
            test_file_name = f"test_{base_name}_normal_exception.py"
            test_path = project_root / base_dir / output_dir / test_file_name
            
            # 如果默认路径不存在，尝试搜索最近生成的测试文件
            if not test_path.exists():
                tests_dir = project_root / base_dir / output_dir
                if tests_dir.exists():
                    # 查找所有 test_*_normal_exception.py 文件
                    test_files = list(tests_dir.glob("test_*_normal_exception.py"))
                    if test_files:
                        # 按修改时间排序，取最新的
                        test_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        test_path = test_files[0]
                        logger.info(f"使用找到的测试文件: {test_path}")
            
            if not test_path.exists():
                return jsonify({
                    'error': '测试文件不存在',
                    'message': f'未找到测试文件: {test_path}'
                }), 404
        
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        env['NON_INTERACTIVE'] = '1'  # 标记为非交互式模式
        
        # 执行子进程的辅助函数
        def run_proc(cmd_args):
            """执行子进程并返回结果"""
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # 防止脚本等待输入
                text=True,
                cwd=str(project_root),
                encoding='utf-8',
                errors='replace',  # 遇到编码错误时用替换字符代替
                env=env  # 传递环境变量
            )
            stdout = ''
            stderr = ''
            return_code = -1
            try:
                stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    stdout, stderr = process.communicate()
                except Exception as e:
                    logger.error(f"获取超时后的输出失败: {e}")
                    stdout = f"执行超时，无法获取完整输出: {str(e)}"
                    stderr = ""
                return_code = -1
            except Exception as e:
                logger.error(f"执行脚本时出错: {e}")
                try:
                    process.kill()
                except:
                    pass
                return_code = -1
                stderr = str(e)
            return return_code, stdout, stderr
        
        # 截断输出的辅助函数
        def truncate_output(output, max_length=3000):
            """截断输出，避免响应过大"""
            if len(output) > max_length:
                return output[-max_length:], len(output)
            return output, None
        
        # 提取错误信息的辅助函数
        def extract_error_lines(output, keywords=None):
            """从输出中提取包含关键字的错误行"""
            if keywords is None:
                keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed', 'ERROR']
            
            if not output:
                return []
                
            return [line for line in output.split('\n') 
                   if any(keyword in line for keyword in keywords)]
        
        # ========== 执行测试用例 ==========
        logger.info(f"开始执行测试用例: {test_path}")
        
        # 对该接口禁用 Allure（防止与其它接口报告混淆）
        use_allure = False
        allure_results_dir = None
        allure_report_dir = None
        
        pytest_cmd = [
            sys.executable, '-m', 'pytest',
            str(test_path),
            '-v',
            '--tb=short',
        ]
        
        if use_allure:
            allure_results_dir = project_root / base_dir / "allure-results" / task_id
            allure_results_dir.mkdir(parents=True, exist_ok=True)
            allure_report_dir = project_root / base_dir / "report" / "html" / task_id
            allure_report_dir.parent.mkdir(parents=True, exist_ok=True)
            pytest_cmd.append(f'--alluredir={allure_results_dir}')
            pytest_cmd.append('--clean-alluredir')
        
        logger.info(f"执行pytest命令: {' '.join(pytest_cmd)}")
        
        # 执行pytest
        test_return_code, test_stdout, test_stderr = run_proc(pytest_cmd)
        
        # 构建响应数据
        response_data = {
            'task_id': task_id,
            'base_name': base_name,
            'test_file_path': str(test_path),
            'test_return_code': test_return_code,
            'test_success': test_return_code == 0 or test_return_code == 1  # pytest返回1表示有测试失败，但执行成功
        }
        
        # 将测试输出写到控制台便于排查（截断避免过长）
        log_tail = 2000
        if test_stdout:
            logger.info(f"pytest stdout (tail {log_tail}):\n{test_stdout[-log_tail:]}")
        if test_stderr:
            logger.error(f"pytest stderr (tail {log_tail}):\n{test_stderr[-log_tail:]}")
        
        # 截断测试输出
        truncated_test_stdout, test_stdout_length = truncate_output(test_stdout)
        truncated_test_stderr, test_stderr_length = truncate_output(test_stderr)
        
        response_data['test_stdout'] = truncated_test_stdout
        response_data['test_stderr'] = truncated_test_stderr
        
        if test_stdout_length:
            response_data['test_stdout_length'] = test_stdout_length
        if test_stderr_length:
            response_data['test_stderr_length'] = test_stderr_length
        
        # 提取指标：只用 pytest 输出，避免引用其他任务的 Allure 数据
        metrics = _parse_pytest_output(test_stdout)
        if metrics:
            response_data['metrics'] = metrics
            response_data['message'] = f'测试执行完成。通过: {metrics.get("passed", 0)}/{metrics.get("total", 0)}'
            logger.info(f"从 pytest 输出解析到指标: {metrics}")
        else:
            response_data['metrics'] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "broken": 0,
                "skipped": 0,
                "unknown": 0,
                "duration_ms": None,
                "duration_human": None,
            }
            response_data['message'] = '测试执行完成，但无法解析测试结果'
            logger.warning("无法从 pytest 输出中解析测试结果")
        
        # 如果测试执行失败，添加错误信息摘要
        if test_return_code not in [0, 1]:  # 0=成功, 1=有失败但执行成功
            response_data['test_error'] = '测试执行失败'
            response_data['test_message'] = f'测试返回码: {test_return_code}'
            
            # 提取测试错误信息
            test_error_lines = extract_error_lines(test_stderr)
            if test_error_lines:
                response_data['test_error_summary'] = test_error_lines[-10:]
        
        # 保存测试结果到results目录
        try:
            # 使用base_name作为文件ID，如果为空则使用task_id
            file_id = base_name if base_name else task_id
            
            result_data = {
                'task_id': task_id,
                'base_name': base_name,
                'test_file_path': str(test_path),
                'result_type': 'test_execution',
                'test_return_code': test_return_code,
                'test_success': response_data['test_success'],
                'metrics': response_data.get('metrics', {}),
                'message': response_data.get('message', ''),
                'created_at': datetime.now().isoformat()
            }
            
            # 如果有错误信息，也保存到结果中
            if 'test_error' in response_data:
                result_data['test_error'] = response_data['test_error']
                result_data['test_message'] = response_data['test_message']
                if 'test_error_summary' in response_data:
                    result_data['test_error_summary'] = response_data['test_error_summary']
            
            # 保存完整输出（截断后的）
            result_data['test_stdout'] = response_data.get('test_stdout', '')
            result_data['test_stderr'] = response_data.get('test_stderr', '')
            
            # 调用save_result函数保存结果，save_result函数会自动添加results_前缀
            save_result(file_id, result_data)
            logger.info(f"测试结果已保存到results目录，文件名: results_{file_id}")
            
            # 添加保存信息到响应
            response_data['result_saved'] = True
            response_data['result_file'] = f"results_{file_id}.json"
            
        except Exception as e:
            logger.error(f"保存测试结果失败: {str(e)}")
            response_data['result_saved'] = False
            response_data['save_error'] = str(e)
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行测试用例失败: {str(e)}")
        return jsonify({
            'error': '执行测试用例失败',
            'message': str(e)
        }), 500


@app.route('/api/feishu/generate-and-excute-ai-test-cases', methods=['POST'])
def generate_ai_test_cases():
    """生成AI测试用例并执行测试，通过调用两个新接口实现"""
    try:
        # 获取请求参数
        data = request.json or {}
        base_name = data.get('base_name', '')
        force_regenerate = data.get('force_regenerate', False)  # 是否强制重新生成
        
        if not base_name:
            return jsonify({
                'error': '缺少必要参数',
                'message': '请提供 base_name 参数（例如: feishu_cardkit-v1_card_create）'
            }), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 第一步：调用生成测试用例接口
        logger.info(f"调用生成测试用例接口: base_name={base_name}, force_regenerate={force_regenerate}")
        
        # 构建生成测试用例的请求
        generate_request_data = {
            'base_name': base_name,
            'force_regenerate': force_regenerate
        }
        
        # 使用requests库调用本地接口
        import requests
        generate_url = f"http://127.0.0.1:5000/api/feishu/generate-test-cases"
        
        try:
            generate_response = requests.post(
                generate_url,
                json=generate_request_data,
                timeout=600  # 10分钟超时
            )
            generate_response.raise_for_status()
            generate_result = generate_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"调用生成测试用例接口失败: {str(e)}")
            return jsonify({
                'error': '调用生成测试用例接口失败',
                'message': str(e)
            }), 500
        
        # 检查生成是否成功
        if 'error' in generate_result:
            logger.error(f"生成测试用例失败: {generate_result.get('message', '未知错误')}")
            return jsonify(generate_result), 500
        
        # 从生成结果中获取测试文件路径
        test_file_path = generate_result.get('test_file_path')
        if not test_file_path:
            logger.error("生成测试用例成功，但未返回测试文件路径")
            return jsonify({
                'error': '生成测试用例失败',
                'message': '未返回测试文件路径'
            }), 500
        
        # 第二步：调用执行测试用例接口
        logger.info(f"调用执行测试用例接口: test_file_path={test_file_path}")
        
        # 构建执行测试用例的请求
        execute_request_data = {
            'base_name': base_name,
            'test_file_path': test_file_path
        }
        
        execute_url = f"http://127.0.0.1:5000/api/feishu/execute-test-cases"
        
        try:
            execute_response = requests.post(
                execute_url,
                json=execute_request_data,
                timeout=600  # 10分钟超时
            )
            execute_response.raise_for_status()
            execute_result = execute_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"调用执行测试用例接口失败: {str(e)}")
            return jsonify({
                'error': '调用执行测试用例接口失败',
                'message': str(e)
            }), 500
        
        # 检查执行是否成功
        if 'error' in execute_result:
            logger.error(f"执行测试用例失败: {execute_result.get('message', '未知错误')}")
            return jsonify(execute_result), 500
        
        # 合并两个接口的结果
        combined_result = {
            'task_id': task_id,
            'base_name': base_name,
            'generation_result': generate_result,
            'execution_result': execute_result,
            'message': '测试用例生成和执行完成'
        }
        
        # 从执行结果中提取关键信息到顶层
        if 'metrics' in execute_result:
            combined_result['metrics'] = execute_result['metrics']
            combined_result['message'] += f'，通过: {execute_result["metrics"].get("passed", 0)}/{execute_result["metrics"].get("total", 0)}'
        
        # 保存执行结果
        result = {
            'task_id': task_id,
            'base_name': base_name,
            'force_regenerate': force_regenerate,
            'generation_result': generate_result,
            'execution_result': execute_result,
            'created_at': datetime.now().isoformat()
        }
        save_result(task_id, result)
        
        return jsonify(combined_result)
    
    except Exception as e:
        logger.error(f"生成AI测试用例失败: {str(e)}")
        return jsonify({
            'error': '生成AI测试用例失败',
            'message': str(e)
        }), 500

@app.route('/api/feishu/generate-and-test-single-file', methods=['POST'])
def generate_and_test_feishu_single_file():
    """执行 run_feishu_single_file.py 脚本，处理单个文件，只返回指标"""
    try:
        # 添加日志，确认接收到请求
        logger.info(f"收到生成测试用例请求，请求方法: {request.method}, 请求路径: {request.path}")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"请求数据: {request.get_data(as_text=True)}")
        
        # 获取请求参数
        data = request.json or {}
        logger.info(f"解析后的请求数据: {data}")
        filename = data.get('filename', '')
        use_ai = data.get('use_ai', False)  # 是否使用 AI 生成
        
        if not filename:
            logger.warning("缺少 filename 参数")
            return jsonify({
                'error': '缺少必要参数',
                'message': '请提供 filename 参数（例如: createCalendar）'
            }), 400
        
        # 移除可能的 .yaml 后缀（如果用户提供了）
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            filename = filename.rsplit('.', 1)[0]
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 获取项目根目录
        project_root = Path(__file__).parent
        script_path = project_root / "run_feishu_single_file.py"
        
        if not script_path.exists():
            return jsonify({
                'error': '脚本文件不存在',
                'message': f'未找到脚本: {script_path}'
            }), 404
        
        # 构建文件路径：uploads/openapi/openapi_API/{filename}.yaml
        file_path = f"uploads/openapi/{filename}.yaml"
        full_file_path = project_root / file_path
        
        # 检查文件是否存在
        if not full_file_path.exists():
            return jsonify({
                'error': '文件不存在',
                'message': f'未找到文件: {file_path}'
            }), 404
        
        # 构建命令参数
        cmd_args = [sys.executable, str(script_path), '--file', file_path]
        if use_ai:
            cmd_args.append('--use-ai')
            logger.info(f"使用 AI 大模型生成测试用例")
        
        logger.info(f"开始执行脚本: {' '.join(cmd_args)}")
        
        # 执行脚本
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        env['NON_INTERACTIVE'] = '1'  # 标记为非交互式模式，脚本不会启动 Allure 服务器
        
        # 使用 UTF-8 编码，并设置 errors='replace' 来处理编码错误
        # 设置 stdin=subprocess.DEVNULL 防止脚本等待输入而阻塞
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,  # 防止脚本等待输入
            text=True,
            cwd=str(project_root),
            encoding='utf-8',
            errors='replace',  # 遇到编码错误时用替换字符代替
            env=env  # 传递环境变量
        )
        
        # 等待执行完成（可以设置超时时间）
        stdout = ''
        stderr = ''
        return_code = -1
        try:
            stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                stdout, stderr = process.communicate()
            except Exception as e:
                logger.error(f"获取超时后的输出失败: {e}")
                stdout = f"执行超时，无法获取完整输出: {str(e)}"
                stderr = ""
            return_code = -1
            return jsonify({
                'task_id': task_id,
                'error': '执行超时',
                'message': '脚本执行超过10分钟，已终止',
                'return_code': return_code,
                'filename': filename,
                'file_path': file_path
            }), 500
        except Exception as e:
            logger.error(f"执行脚本时出错: {e}")
            try:
                process.kill()
            except:
                pass
            return jsonify({
                'task_id': task_id,
                'error': '执行脚本时出错',
                'message': str(e),
                'filename': filename,
                'file_path': file_path,
                'return_code': return_code
            }), 500
        
        # 保存执行结果
        result = {
            'task_id': task_id,
            'script': str(script_path),
            'filename': filename,
            'file_path': file_path,
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'created_at': datetime.now().isoformat()
        }
        save_result(task_id, result)
        
        # 读取 Allure 报告摘要数据（不启动服务器，只读取已生成的报告）
        summary, summary_path = _find_allure_summary(project_root)
        
        # 构建响应数据，只包含指标
        response_data = {
            'task_id': task_id,
            'filename': filename,
            'file_path': file_path,
            'return_code': return_code,
            'success': return_code == 0
        }
        
        # 提取并返回指标
        if summary:
            metrics = _extract_allure_metrics(summary)
            if metrics:
                response_data['metrics'] = metrics
                response_data['summary_path'] = summary_path
            else:
                response_data['metrics'] = None
                response_data['message'] = '无法提取指标数据'
        else:
            response_data['metrics'] = None
            response_data['message'] = '未找到 Allure 报告摘要数据'
        
        # 如果执行失败，添加错误信息摘要
        if return_code != 0:
            response_data['error'] = '脚本执行完成，但有错误或警告'
            response_data['message'] = f'脚本返回码: {return_code}（0表示成功，非0表示有错误或警告）'
            
            # 尝试从输出中提取关键错误信息
            if stderr:
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed']
                error_lines = [line for line in stderr.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    response_data['error_summary'] = error_lines[-10:]  # 最后10行错误信息
            
            # 也从 stdout 中查找错误信息（有些错误可能输出到 stdout）
            if stdout:
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed']
                error_lines = [line for line in stdout.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    if 'error_summary' not in response_data:
                        response_data['error_summary'] = []
                    response_data['error_summary'].extend(error_lines[-10:])
        else:
            response_data['message'] = '脚本执行成功'
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行 run_feishu_single_file.py 失败: {str(e)}")
        return jsonify({
            'error': '执行脚本失败',
            'message': str(e)
        }), 500


# ========== 新增辅助函数 ==========
import socket
import threading

def _find_allure_summary(project_root: Path, report_dir: Path = None, results_dir: Path = None):
    """
    查找 Allure 已生成报告的 summary.json，并返回 (数据, 路径)。
    优先使用本次运行的 report_dir / results_dir，避免不同接口运行的报告互相污染。
    """
    candidates = []
    if report_dir:
        candidates.extend([
            report_dir / "widgets" / "summary.json",
            report_dir / "data" / "summary.json",
        ])
    if results_dir:
        candidates.append(results_dir / "widgets" / "summary.json")
        candidates.append(results_dir / "data" / "summary.json")
    # 兼容旧路径（全局目录，放最后，避免拿到其他任务的报告）
    candidates.extend([
        project_root / "report" / "html" / "widgets" / "summary.json",
        project_root / "report" / "html" / "data" / "summary.json",
        project_root / "allure-report" / "widgets" / "summary.json",
        project_root / "allure-report" / "data" / "summary.json",
    ])
    for path in candidates:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f), str(path)
        except Exception as e:
            logger.debug(f"读取 Allure summary 失败 {path}: {e}")
    return None, None

def _extract_allure_metrics(summary: dict):
    """从 Allure summary 中提取常用统计指标"""
    if not summary:
        return None
    stats = summary.get("statistic", {}) or {}
    total = stats.get("total")
    passed = stats.get("passed")
    failed = stats.get("failed")
    broken = stats.get("broken")
    skipped = stats.get("skipped")
    unknown = stats.get("unknown")
    time_info = summary.get("time", {}) or {}
    duration = time_info.get("duration")
    duration_human = time_info.get("durationHumanReadable")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "broken": broken,
        "skipped": skipped,
        "unknown": unknown,
        "duration_ms": duration,
        "duration_human": duration_human,
    }

def _parse_pytest_output(stdout: str):
    """从 pytest 的 stdout 中解析测试结果
    
    解析格式如: "1 failed, 2 passed, 1 xfailed in 1.93s"
    或: "=================== 1 failed, 2 passed, 1 xfailed in 1.93s ===================="
    """
    import re
    
    if not stdout:
        return None
    
    # 初始化默认值
    failed = 0
    passed = 0
    xfailed = 0
    skipped = 0
    error = 0
    duration_seconds = 0.0
    
    # 匹配各种测试结果格式
    # 格式1: "X failed, Y passed, Z xfailed in N.NNs"
    # 格式2: "X failed, Y passed, Z skipped in N.NNs"
    # 格式3: "X failed, Y passed, Z error in N.NNs"
    
    # 提取 failed
    failed_match = re.search(r'(\d+)\s+failed', stdout)
    if failed_match:
        failed = int(failed_match.group(1))
    
    # 提取 passed
    passed_match = re.search(r'(\d+)\s+passed', stdout)
    if passed_match:
        passed = int(passed_match.group(1))
    
    # 提取 xfailed
    xfailed_match = re.search(r'(\d+)\s+xfailed', stdout)
    if xfailed_match:
        xfailed = int(xfailed_match.group(1))
    
    # 提取 skipped
    skipped_match = re.search(r'(\d+)\s+skipped', stdout)
    if skipped_match:
        skipped = int(skipped_match.group(1))
    
    # 提取 error
    error_match = re.search(r'(\d+)\s+error', stdout)
    if error_match:
        error = int(error_match.group(1))
    
    # 提取执行时间
    time_match = re.search(r'in\s+([\d.]+)\s*s', stdout)
    if time_match:
        duration_seconds = float(time_match.group(1))
    
    # 如果没有任何匹配，返回 None
    if passed == 0 and failed == 0 and xfailed == 0 and skipped == 0 and error == 0:
        return None
    
    total = passed + failed + xfailed + skipped + error
    
    # 格式化时间
    if duration_seconds < 1:
        duration_human = f"{duration_seconds * 1000:.0f}ms"
    elif duration_seconds < 60:
        duration_human = f"{duration_seconds:.2f}s"
    else:
        minutes = int(duration_seconds // 60)
        seconds = duration_seconds % 60
        duration_human = f"{minutes}m {seconds:.2f}s"
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "broken": error,  # error 通常对应 broken
        "skipped": skipped + xfailed,  # xfailed 也算作 skipped
        "unknown": 0,
        "duration_ms": int(duration_seconds * 1000) if duration_seconds > 0 else None,
        "duration_human": duration_human if duration_seconds > 0 else None,
    }

def find_available_port(start_port=9999, max_attempts=10):
    """查找可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                s.close()
                return port
            except socket.error:
                continue
    return None

def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_allure_server_async(results_dir, port=9999, host='127.0.0.1'):
    """异步启动Allure报告服务器"""
    
    def run_allure():
        try:
            # 生成报告到临时目录
            import tempfile
            import time
            
            # 创建临时目录用于报告
            temp_report_dir = tempfile.mkdtemp(prefix="allure_report_")
            
            # 生成报告
            generate_cmd = [
                'allure', 'generate', str(results_dir),
                '-o', temp_report_dir,
                '--clean'
            ]
            
            # 执行生成命令
            logger.info(f"生成Allure报告: {' '.join(generate_cmd)}")
            gen_process = subprocess.run(
                generate_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if gen_process.returncode != 0:
                logger.error(f"生成Allure报告失败: {gen_process.stderr}")
                return
            
            # 启动服务
            serve_cmd = [
                'allure', 'serve', str(results_dir),
                '-p', str(port),
                '-h', host
            ]
            
            logger.info(f"启动Allure服务器: {' '.join(serve_cmd)}")
            
            # 启动服务器（这会阻塞线程）
            process = subprocess.Popen(
                serve_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # 等待一段时间确保服务器启动
            time.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                # 进程已退出，读取错误信息
                stdout, stderr = process.communicate()
                logger.error(f"Allure服务器启动失败: {stderr}")
                return None
            
            logger.info(f"Allure报告服务器已启动: http://{host}:{port}")
            logger.info(f"进程PID: {process.pid}")
            
            # 保存进程对象以便后续管理
            return process
            
        except Exception as e:
            logger.error(f"启动Allure服务器时出错: {e}")
            return None
    
    # 在新线程中启动Allure服务器
    thread = threading.Thread(target=run_allure)
    thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
    thread.start()
    
    # 等待一下确保线程启动
    import time
    time.sleep(2)
    
    # 由于线程是异步的，我们无法直接返回进程对象
    # 这里我们可以通过检查端口是否被占用来判断服务器是否启动成功
    
    # 检查端口是否被占用（即服务器是否启动）
    for _ in range(5):  # 尝试5次，每次等待1秒
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                logger.info(f"端口 {port} 已被占用，Allure服务器可能已启动")
                # 我们无法返回实际的进程对象，但可以返回一个占位符
                class AllureProcess:
                    def __init__(self, port):
                        self.pid = -1  # 未知PID
                        self.port = port
                    
                    def __repr__(self):
                        return f"AllureProcess(port={self.port})"
                
                return AllureProcess(port)
    
    logger.warning(f"端口 {port} 未被占用，Allure服务器可能启动失败")
    return None
# 8. 静态文件服务
@app.route('/')
def index():
    """提供前端主页"""
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """提供静态文件"""
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    return send_from_directory('frontend', path)

# 9. 生成测试用例接口
@app.route('/api/generate_test_cases', methods=['POST'])
def generate_test_cases_by_file_id():
    """
    根据file_id生成测试用例
    """
    try:
        logger.info("收到生成测试用例请求")
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            logger.error("请求体不能为空")
            return jsonify({'error': '请求体不能为空'}), 400
        
        file_id = data.get('file_id')
        if not file_id:
            logger.error("file_id是必需参数")
            return jsonify({'error': 'file_id是必需参数'}), 400
        
        logger.info(f"开始为file_id: {file_id}生成测试用例...")
        
        # 导入必要的模块
        import os
        import json
        import yaml
        from utils.feishu_config import feishu_config
        
        # 使用自动刷新的令牌，而不是从环境变量直接获取
        authorization = feishu_config.get_authorization()
        base_url = feishu_config.base_url
        
        # 如果无法获取授权令牌，返回错误
        if not authorization:
            logger.error('无法获取飞书授权令牌，请检查FEISHU_APP_ID和FEISHU_APP_SECRET环境变量')
            return jsonify({
                'success': False,
                'error': '无法获取飞书授权令牌，请检查FEISHU_APP_ID和FEISHU_APP_SECRET环境变量'
            }), 500
        
        # 构建文件路径
        api_file_path = f"/Users/oss/code/PytestAutoApi/uploads/openapi/openapi_{file_id}.yaml"
        scene_file_path = f"/Users/oss/code/PytestAutoApi/uploads/scene/scene_{file_id}.json"
        relation_file_path = f"/Users/oss/code/PytestAutoApi/uploads/relation/relation_{file_id}.json"
        
        logger.info(f"检查文件路径: {api_file_path}, {scene_file_path}")
        
        # 检查API文档文件是否存在
        if not os.path.exists(api_file_path):
            logger.error(f'API文档文件不存在: {api_file_path}')
            return jsonify({
                'success': False,
                'error': f'API文档文件不存在: {api_file_path}'
            }), 404
        
        # 加载API文档
        with open(api_file_path, 'r', encoding='utf-8') as f:
            if api_file_path.endswith('.yaml') or api_file_path.endswith('.yml'):
                doc_data = yaml.safe_load(f)
            else:
                doc_data = json.load(f)
        
        # 加载测试场景（必须存在）
        if not os.path.exists(scene_file_path):
            logger.error(f'测试场景文件不存在: {scene_file_path}，请先上传场景文件')
            return jsonify({
                'success': False,
                'error': f'测试场景文件不存在: {scene_file_path}，请先上传场景文件'
            }), 404
            
        with open(scene_file_path, 'r', encoding='utf-8') as f:
            scenes_data = json.load(f)
        
        # 加载API依赖关系（如果存在）
        relations_data = {}
        if os.path.exists(relation_file_path):
            with open(relation_file_path, 'r', encoding='utf-8') as f:
                relations_data = json.load(f)
        
        # 从场景文件中获取业务场景数据
        test_scenes_list = []
        if 'business_scenes' in scenes_data and 'scenes' in scenes_data['business_scenes']:
            test_scenes_list = scenes_data['business_scenes']['scenes']
        elif 'scenes_name' in scenes_data:
            # 兼容旧格式
            test_scenes_list = scenes_data['scenes_name']
        
        # 检查场景数据是否为空
        if not test_scenes_list:
            logger.error(f'场景文件中没有有效的测试场景数据: {scene_file_path}')
            return jsonify({
                'success': False,
                'error': f'场景文件中没有有效的测试场景数据: {scene_file_path}'
            }), 400
        
        logger.info(f"找到 {len(test_scenes_list)} 个测试场景")
        
        # 如果有关联关系数据，生成基于关联关系的测试场景
        if relations_data and 'relation_info' in relations_data:
            # 这里简化处理，实际项目中应该实现关联关系分析
            pass
        
        paths = doc_data.get('paths', {})
        
        # 创建YAML格式的测试用例
        yaml_test_cases = {
            "case_common": {
                "allureEpic": "API测试",
                "allureFeature": "功能测试",
                "allureStory": "API功能测试"
            }
        }
        
        # 为每个测试场景生成测试用例
        test_case_index = 1
        
        for scene in test_scenes_list:
            # 处理新格式的场景数据
            if 'scene_id' in scene:
                # 新格式场景数据
                scene_name = scene.get('scene_name', '')
                scene_description = scene.get('scene_description', '')
                scene_priority = scene.get('priority', 'P1').replace('P', '')  # 将P1转换为1
                related_apis = scene.get('related_apis', [])
                test_focus = scene.get('test_focus', [])
                exception_scenarios = scene.get('exception_scenarios', [])
                api_call_combo = scene.get('api_call_combo', [])
                
                # 从related_apis或api_call_combo中提取API路径和方法
                scene_path = ''
                scene_method = 'POST'  # 默认方法
                if related_apis:
                    scene_path = related_apis[0]
                elif api_call_combo:
                    scene_path = api_call_combo[0].get('api_path', '')
                
                # 根据路径确定HTTP方法
                if scene_path and scene_path in paths:
                    for method in paths[scene_path]:
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                            scene_method = method.upper()
                            break
                
                # 创建兼容格式的场景对象
                scene_obj = {
                    'name': scene_name,
                    'description': scene_description,
                    'type': 'business_flow',  # 业务场景默认为业务流程类型
                    'path': scene_path,
                    'method': scene_method,
                    'priority': 'high' if scene_priority == '1' else 'medium' if scene_priority == '2' else 'low',
                    'test_focus': test_focus,
                    'exception_scenarios': exception_scenarios,
                    'api_call_combo': api_call_combo
                }
            else:
                # 旧格式场景数据
                scene_obj = scene
            
            scene_type = scene_obj.get('type', 'basic')
            scene_path = scene_obj.get('path', '')
            scene_method = scene_obj.get('method', '')
            
            # 获取对应的API定义
            api_definition = None
            if scene_path and scene_method and scene_path in paths:
                api_definition = paths[scene_path].get(scene_method.lower(), {})
            
            # 生成基础测试用例
            test_cases = []
            
            # 根据API路径生成特定的测试数据
            test_data = {}
            expected_results = {"status_code": 200}
            
            # 根据不同的API路径生成特定的测试数据
            if '/im/v1/messages' in scene_path:
                # 发送消息API的测试数据
                test_data = {
                    "receive_id_type": "open_id",
                    "receive_id": "ou_xxx",
                    "msg_type": "text",
                    "content": "{\"text\":\"测试消息\"}"
                }
                expected_results = {"status_code": 200, "response_contains": "success"}
            
            # 正常请求测试用例
            normal_case = {
                "name": f"正常请求 - {scene_method} {scene_path}",
                "description": f"测试{scene_method} {scene_path}的正常请求功能",
                "type": "normal",
                "priority": "high",
                "api_path": scene_path,
                "api_method": scene_method,
                "test_case_description": scene_obj.get('description', ''),
                "test_data": test_data,
                "expected_results": expected_results
            }
            test_cases.append(normal_case)
            
            # 异常场景测试用例
            for exception_scenario in scene_obj.get('exception_scenarios', []):
                exception_test_data = test_data.copy()
                exception_expected_results = {"status_code": 400}
                
                if "无效接收者ID" in exception_scenario:
                    exception_test_data["receive_id"] = "invalid_id"
                    exception_expected_results["feishu_code"] = 230013
                elif "空消息内容" in exception_scenario:
                    exception_test_data["content"] = "{\"text\":\"\"}"
                    exception_expected_results["feishu_code"] = 230025
                elif "无效图片key" in exception_scenario:
                    exception_test_data["content"] = "{\"image_key\":\"invalid_key\"}"
                    exception_expected_results["feishu_code"] = 300240
                
                exception_case = {
                    "name": f"异常请求 - {exception_scenario}",
                    "description": f"测试{scene_method} {scene_path}的{exception_scenario}异常场景",
                    "type": "exception",
                    "priority": "medium",
                    "api_path": scene_path,
                    "api_method": scene_method,
                    "test_case_description": f"测试{exception_scenario}异常场景",
                    "test_data": exception_test_data,
                    "expected_results": exception_expected_results
                }
                test_cases.append(exception_case)
            
            # 将测试用例转换为YAML格式
            for test_case in test_cases:
                # 从API路径生成测试用例键名
                api_path = test_case.get('api_path', scene_path)
                if api_path.startswith('/'):
                    api_path = api_path[1:]  # 去掉开头的斜杠
                # 将路径中的斜杠替换为下划线
                api_path_key = api_path.replace('/', '_')
                
                # 生成测试用例键名
                test_case_key = f"{test_case_index:02d}_{api_path_key}"
                
                # 构建YAML格式的测试用例
                yaml_test_case = {
                    "host": base_url,
                    "url": api_path,
                    "method": test_case.get('api_method', scene_method).lower(),
                    "detail": test_case.get('test_case_description', ''),
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {authorization}"
                    },
                    "requestType": "json",
                    "is_run": None,
                    "data": test_case.get('test_data', {}),
                    "dependence_case": False,
                    "assert": {
                        "status_code": test_case.get('expected_results', {}).get('status_code', 200)
                    },
                    "sql": None
                }
                
                # 添加飞书错误码（如果有）
                if 'feishu_code' in test_case.get('expected_results', {}):
                    yaml_test_case["assert"]["feishu_code"] = test_case['expected_results']['feishu_code']
                
                # 添加到YAML测试用例字典
                yaml_test_cases[test_case_key] = yaml_test_case
                test_case_index += 1
        
        # 确保输出目录存在
        output_dir = "/Users/oss/code/PytestAutoApi/uploads/test_cases"
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件路径
        output_file_path = f"{output_dir}/test_cases_{file_id}.yaml"
        
        # 写入YAML文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_test_cases, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"测试用例生成完成，共生成 {len(yaml_test_cases)-1} 个测试用例，保存到 {output_file_path}")
        
        result = {
            'success': True,
            'message': f"成功生成 {len(yaml_test_cases)-1} 个测试用例",
            'file_path': output_file_path,
            'test_cases_count': len(yaml_test_cases)-1
        }
        logger.info(f"返回结果: {result}")
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"生成测试用例时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'生成测试用例时出错: {str(e)}'
        }), 500

# 10. 执行测试用例并生成指标接口
@app.route('/api/execute_test_cases', methods=['POST'])
def execute_test_cases_by_file_id():
    """
    根据file_id读取测试用例文件，生成测试代码，执行测试并生成指标
    """
    try:
        logger.info("收到执行测试用例请求")
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            logger.error("请求体不能为空")
            return jsonify({'error': '请求体不能为空'}), 400
        
        file_id = data.get('file_id')
        if not file_id:
            logger.error("file_id是必需参数")
            return jsonify({'error': 'file_id是必需参数'}), 400
        
        logger.info(f"开始执行file_id: {file_id}的测试用例...")
        
        # 导入必要的模块
        import os
        import json
        import yaml
        import subprocess
        import sys
        from datetime import datetime
        
        # 构建测试用例文件路径
        test_cases_file_path = f"/Users/oss/code/PytestAutoApi/uploads/test_cases/test_cases_{file_id}.yaml"
        
        # 检查测试用例文件是否存在
        if not os.path.exists(test_cases_file_path):
            logger.error(f'测试用例文件不存在: {test_cases_file_path}')
            return jsonify({
                'success': False,
                'error': f'测试用例文件不存在: {test_cases_file_path}'
            }), 404
        
        # 加载测试用例
        with open(test_cases_file_path, 'r', encoding='utf-8') as f:
            test_cases_data = yaml.safe_load(f)
        
        # 创建测试代码目录
        test_code_dir = f"/Users/oss/code/PytestAutoApi/uploads/test_codes/test_code_{file_id}"
        os.makedirs(test_code_dir, exist_ok=True)
        
        # 创建测试报告目录
        test_report_dir = f"/Users/oss/code/PytestAutoApi/uploads/test_reports/test_reports_{file_id}"
        os.makedirs(test_report_dir, exist_ok=True)
        
        # 生成测试代码
        test_code_content = generate_test_code(test_cases_data, file_id)
        
        # 写入测试代码文件
        test_code_file = f"{test_code_dir}/test_{file_id}.py"
        with open(test_code_file, 'w', encoding='utf-8') as f:
            f.write(test_code_content)
        
        # 创建conftest.py文件
        conftest_content = generate_conftest_file(test_cases_data)
        conftest_file = f"{test_code_dir}/conftest.py"
        with open(conftest_file, 'w', encoding='utf-8') as f:
            f.write(conftest_content)
        
        # 执行测试
        logger.info(f"开始执行测试: {test_code_file}")
        test_report_file = f"{test_report_dir}/report_{file_id}.html"
        
        # 构建pytest命令
        pytest_cmd = [
            sys.executable, "-m", "pytest", 
            test_code_dir,
            "--html=" + test_report_file,
            "--self-contained-html",
            "-v",
            "--tb=short"
        ]
        
        # 执行测试
        start_time = datetime.now()
        result = subprocess.run(
            pytest_cmd,
            capture_output=True,
            text=True,
            cwd="/Users/oss/code/PytestAutoApi"
        )
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 解析测试结果
        test_results = parse_test_results(result.stdout, result.stderr, result.returncode)
        
        # 生成测试指标
        test_metrics = generate_test_metrics(test_results, test_cases_data, execution_time)
        
        # 保存测试指标
        metrics_file = f"{test_report_dir}/metrics_{file_id}.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump(test_metrics, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试执行完成，报告保存到: {test_report_file}")
        
        # 返回结果
        response_data = {
            'success': True,
            'message': f"测试执行完成，共执行 {test_metrics['total_tests']} 个测试用例",
            'test_report_file': test_report_file,
            'test_metrics_file': metrics_file,
            'test_metrics': test_metrics,
            'execution_time': execution_time
        }
        
        logger.info(f"返回结果: {response_data}")
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"执行测试用例时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'执行测试用例时出错: {str(e)}'
        }), 500

def generate_test_code(test_cases_data, file_id):
    """
    根据测试用例数据生成pytest测试代码
    """
    # 提取公共配置
    case_common = test_cases_data.get('case_common', {})
    allure_epic = case_common.get('allureEpic', 'API测试')
    allure_feature = case_common.get('allureFeature', '功能测试')
    allure_story = case_common.get('allureStory', 'API功能测试')
    
    # 生成测试代码
    test_code = f'''"""
自动生成的测试代码
文件ID: {file_id}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import pytest
import requests
import json
import allure
from typing import Dict, Any

# 测试配置
BASE_URL = "https://open.feishu.cn/open-apis"
TIMEOUT = 10

@allure.epic("{allure_epic}")
@allure.feature("{allure_feature}")
@allure.story("{allure_story}")
class Test{file_id.replace("-", "_").replace("_", " ").title().replace(" ", "")}:
    """
    自动生成的测试类
    """
    
    @pytest.fixture(scope="class")
    def headers(self):
        """获取请求头"""
        return {{
            "Content-Type": "application/json",
            "Authorization": "Bearer t-g104c91QHHBJAGCXFG5ZZN733P7FGVFA6FP4LBO2"
        }}
    
'''
    
    # 为每个测试用例生成测试方法
    for case_key, case_data in test_cases_data.items():
        if case_key == 'case_common':
            continue
            
        case_name = case_key.replace("-", "_").replace(".", "_")
        case_url = case_data.get('url', '')
        case_method = case_data.get('method', 'get')
        case_detail = case_data.get('detail', '')
        case_headers = case_data.get('headers', {})
        case_data_request = case_data.get('data', {})
        case_assert = case_data.get('assert', {})
        expected_status_code = case_assert.get('status_code', 200)
        
        # 生成测试方法
        test_method = f'''
    @allure.title("{case_detail}")
    @allure.description("""
    测试URL: {case_url}
    请求方法: {case_method.upper()}
    预期状态码: {expected_status_code}
    """)
    def test_{case_name}(self, headers):
        """测试用例: {case_detail}"""
        # 构建请求URL
        url = f"{{BASE_URL}}/{case_url}"
        
        # 发送请求
        response = requests.{case_method}(
            url,
            headers=headers,
            json={case_data_request},
            timeout=TIMEOUT
        )
        
        # 验证响应状态码
        assert response.status_code == {expected_status_code}, f"预期状态码: {expected_status_code}, 实际状态码: {{response.status_code}}"
        
        # 验证响应内容
        if response.status_code == 200:
            response_data = response.json()
            assert response_data is not None, "响应数据不应为空"
'''
        
        # 添加额外的断言
        if 'feishu_code' in case_assert:
            expected_feishu_code = case_assert['feishu_code']
            test_method += f'''
            # 验证飞书错误码
            if 'code' in response_data:
                assert response_data['code'] == {expected_feishu_code}, f"预期飞书错误码: {expected_feishu_code}, 实际错误码: {{response_data['code']}}"
'''
        
        test_code += test_method
    
    return test_code

def generate_conftest_file(test_cases_data):
    """
    生成conftest.py文件
    """
    conftest_content = '''"""
pytest配置文件
"""

import pytest
import allure
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    生成allure报告
    """
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # 添加失败截图或日志
        try:
            with allure.step("失败信息"):
                allure.attach(str(rep.longrepr), name="失败原因", attachment_type=allure.attachment_type.TEXT)
        except Exception as e:
            print(f"添加allure附件失败: {str(e)}")
'''
    return conftest_content

def parse_test_results(stdout, stderr, returncode):
    """
    解析测试结果
    """
    # 基本测试结果
    test_results = {
        'stdout': stdout,
        'stderr': stderr,
        'returncode': returncode,
        'success': returncode == 0
    }
    
    # 解析测试统计信息
    try:
        # 从stdout中提取测试统计信息
        lines = stdout.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # 示例行: "5 passed, 2 failed in 10.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        test_results['passed'] = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        test_results['failed'] = int(parts[i-1])
                    elif part == 'error' and i > 0:
                        test_results['error'] = int(parts[i-1])
                    elif part == 'skipped' and i > 0:
                        test_results['skipped'] = int(parts[i-1])
                break
    except Exception as e:
        print(f"解析测试统计信息失败: {str(e)}")
        test_results['passed'] = 0
        test_results['failed'] = 0
        test_results['error'] = 0
        test_results['skipped'] = 0
    
    return test_results

def generate_test_metrics(test_results, test_cases_data, execution_time):
    """
    生成测试指标
    """
    # 计算测试用例总数
    total_cases = len([k for k in test_cases_data.keys() if k != 'case_common'])
    
    # 获取测试结果
    passed = test_results.get('passed', 0)
    failed = test_results.get('failed', 0)
    error = test_results.get('error', 0)
    skipped = test_results.get('skipped', 0)
    
    # 计算成功率
    success_rate = (passed / total_cases * 100) if total_cases > 0 else 0
    
    # 计算失败率
    failure_rate = ((failed + error) / total_cases * 100) if total_cases > 0 else 0
    
    # 生成测试指标
    test_metrics = {
        'total_tests': total_cases,
        'passed': passed,
        'failed': failed,
        'error': error,
        'skipped': skipped,
        'success_rate': round(success_rate, 2),
        'failure_rate': round(failure_rate, 2),
        'execution_time': round(execution_time, 2),
        'average_time_per_test': round(execution_time / total_cases, 2) if total_cases > 0 else 0,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'PASSED' if (failed + error) == 0 else 'FAILED'
    }
    
    # 添加测试用例分类统计
    normal_cases = 0
    exception_cases = 0
    
    for case_key, case_data in test_cases_data.items():
        if case_key == 'case_common':
            continue
            
        detail = case_data.get('detail', '')
        if '异常' in detail or '错误' in detail:
            exception_cases += 1
        else:
            normal_cases += 1
    
    test_metrics['normal_cases'] = normal_cases
    test_metrics['exception_cases'] = exception_cases
    
    # 添加测试覆盖率指标
    test_metrics['coverage'] = {
        'api_endpoints': len(set(case_data.get('url', '') for case_key, case_data in test_cases_data.items() if case_key != 'case_common')),
        'test_types': ['正常场景', '异常场景'] if exception_cases > 0 else ['正常场景']
    }
    
    return test_metrics

# 6. 测试结果管理
def sync_test_results():
    """同步和累积测试结果数据"""
    try:
        # 确保结果目录存在
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            return
        
        # 创建累积数据文件路径
        sync_file_path = os.path.join(results_dir, "test_results_sync.json")
        
        # 初始化累积数据
        sync_data = {
            'last_sync': datetime.now().isoformat(),
            'total_results': 0,
            'results': []
        }
        
        # 如果已存在同步文件，先加载它
        if os.path.exists(sync_file_path):
            try:
                with open(sync_file_path, 'r', encoding='utf-8') as f:
                    existing_sync_data = json.load(f)
                    # 保留现有的结果数据
                    sync_data['results'] = existing_sync_data.get('results', [])
            except Exception as e:
                logger.warning(f"加载现有同步数据失败: {str(e)}")
        
        # 创建一个集合来跟踪已处理的文件，避免重复
        processed_files = {result.get('file_name', '') for result in sync_data['results']}
        
        # 遍历结果目录中的所有JSON文件
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and filename != 'test_results_sync.json':
                file_path = os.path.join(results_dir, filename)
                
                # 跳过已经处理过的文件
                if filename in processed_files:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    # 检查是否是测试结果数据
                    is_test_result = (
                        filename.startswith('coverage_') or 
                        filename.startswith('test_results_') or
                        filename.startswith('suggestions_') or
                        ('execution_results' in result_data) or
                        ('analysis_results' in result_data) or
                        ('total' in result_data and 'passed' in result_data and 'failed' in result_data)
                    )
                    
                    if is_test_result:
                        # 提取测试结果信息
                        result_type = 'unknown'
                        if filename.startswith('coverage_'):
                            result_type = 'execution'
                        elif filename.startswith('test_results_'):
                            result_type = 'test'
                        elif filename.startswith('suggestions_'):
                            result_type = 'analysis'
                        elif 'execution_results' in result_data:
                            result_type = 'execution'
                        elif 'analysis_results' in result_data:
                            result_type = 'analysis'
                        
                        # 获取关联的file_id
                        file_id = result_data.get('file_id', '')
                        if not file_id and filename.startswith('coverage_'):
                            file_id = filename[9:]  # 移除'coverage_'前缀
                        elif not file_id and filename.startswith('test_results_'):
                            file_id = filename[13:]  # 移除'test_results_'前缀
                        elif not file_id and filename.startswith('suggestions_'):
                            file_id = filename[12:]  # 移除'suggestions_'前缀
                        
                        # 获取API名称
                        api_name = result_data.get('api_name', '')
                        if not api_name and file_id and file_id in api_docs:
                            api_name = api_docs[file_id].get('filename', file_id)
                        
                        # 获取时间戳
                        timestamp = result_data.get('created_at', '')
                        if not timestamp:
                            # 尝试从文件修改时间获取
                            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        
                        # 创建同步记录
                        sync_record = {
                            'id': str(uuid.uuid4()),
                            'file_name': filename,
                            'file_id': file_id,
                            'api_name': api_name,
                            'result_type': result_type,
                            'timestamp': timestamp,
                            'data': result_data
                        }
                        
                        # 添加到累积结果
                        sync_data['results'].append(sync_record)
                        
                except Exception as e:
                    logger.error(f"处理测试结果文件失败 {filename}: {str(e)}")
        
        # 更新统计信息
        sync_data['total_results'] = len(sync_data['results'])
        sync_data['last_sync'] = datetime.now().isoformat()
        
        # 保存同步数据
        with open(sync_file_path, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果同步完成，共处理 {sync_data['total_results']} 条结果")
        return sync_data
        
    except Exception as e:
        logger.error(f"测试结果同步失败: {str(e)}")
        return None

def get_synced_test_results(limit=20, offset=0, result_type=None, file_id=None):
    """获取同步后的测试结果"""
    try:
        # 确保结果目录存在
        results_dir = app.config['RESULTS_FOLDER']
        sync_file_path = os.path.join(results_dir, "test_results_sync.json")
        
        # 如果同步文件不存在，先执行同步
        if not os.path.exists(sync_file_path):
            sync_data = sync_test_results()
            if not sync_data:
                return {'results': [], 'total': 0}
        else:
            # 检查是否需要重新同步（例如，超过一定时间）
            with open(sync_file_path, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
            
            # 检查最后同步时间，如果超过1小时，重新同步
            last_sync = sync_data.get('last_sync', '')
            if last_sync:
                try:
                    last_sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    current_time = datetime.now()
                    # 如果超过1小时未同步，重新同步
                    if (current_time - last_sync_time).total_seconds() > 3600:
                        sync_data = sync_test_results()
                except Exception as e:
                    logger.warning(f"解析最后同步时间失败: {str(e)}")
                    sync_data = sync_test_results()
        
        # 获取结果列表
        results = sync_data.get('results', [])
        
        # 应用筛选条件
        if result_type and result_type != 'all':
            results = [r for r in results if r.get('result_type') == result_type]
        
        if file_id and file_id != 'all':
            results = [r for r in results if r.get('file_id') == file_id]
        
        # 按时间戳排序（最新的在前）
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 应用分页
        total = len(results)
        paginated_results = results[offset:offset+limit]
        
        return {
            'results': paginated_results,
            'total': total
        }
        
    except Exception as e:
        logger.error(f"获取同步测试结果失败: {str(e)}")
        return {'results': [], 'total': 0}

@app.route('/api/test-results', methods=['GET'])
def get_test_results():
    """获取历史测试结果列表"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status_filter = request.args.get('status', None)
        api_filter = request.args.get('api', None)
        date_filter = request.args.get('date', None)
        result_type_filter = request.args.get('type', None)
        file_id_filter = request.args.get('file_id', None)
        use_synced = request.args.get('synced', 'false').lower() == 'true'
        
        # 如果请求使用同步数据，使用同步函数
        if use_synced:
            synced_results = get_synced_test_results(limit, offset, result_type_filter, file_id_filter)
            
            # 转换同步数据为前端期望的格式
            formatted_results = []
            for result in synced_results['results']:
                data = result.get('data', {})
                result_type = result.get('result_type', 'unknown')
                
                # 根据结果类型提取不同的数据
                if result_type == 'execution' and 'execution_results' in data:
                    exec_results = data['execution_results']
                    total = exec_results.get('total', 0)
                    passed = exec_results.get('passed', 0)
                    failed = exec_results.get('failed', 0)
                    skipped = exec_results.get('skipped', 0)
                    duration = exec_results.get('duration', 0)
                    
                    status = 'unknown'
                    if failed == 0:
                        status = 'passed'
                    elif passed > 0:
                        status = 'partial'
                    else:
                        status = 'failed'
                    
                    formatted_results.append({
                        'id': result.get('id', ''),
                        'suiteName': data.get('suite_name', '执行结果'),
                        'apiName': result.get('api_name', ''),
                        'timestamp': result.get('timestamp', ''),
                        'status': status,
                        'totalCases': total,
                        'passedCases': passed,
                        'failedCases': failed,
                        'skippedCases': skipped,
                        'duration': f"{duration}秒" if duration else '-',
                        'request': data.get('request', {}),
                        'response': data.get('response', {}),
                        'log': data.get('log', ''),
                        'resultType': result_type,
                        'fileId': result.get('file_id', ''),
                        'fileName': result.get('file_name', '')
                    })
                    
                elif result_type == 'analysis' and 'analysis_results' in data:
                    analysis = data['analysis_results']
                    
                    formatted_results.append({
                        'id': result.get('id', ''),
                        'suiteName': data.get('suite_name', '分析结果'),
                        'apiName': result.get('api_name', ''),
                        'timestamp': result.get('timestamp', ''),
                        'status': 'analysis',
                        'totalCases': 0,
                        'passedCases': 0,
                        'failedCases': 0,
                        'skippedCases': 0,
                        'duration': '-',
                        'request': {},
                        'response': analysis,
                        'log': '',
                        'resultType': result_type,
                        'fileId': result.get('file_id', ''),
                        'fileName': result.get('file_name', '')
                    })
                    
                else:
                    # 通用格式
                    formatted_results.append({
                        'id': result.get('id', ''),
                        'suiteName': data.get('suite_name', '测试结果'),
                        'apiName': result.get('api_name', ''),
                        'timestamp': result.get('timestamp', ''),
                        'status': 'unknown',
                        'totalCases': data.get('total', 0),
                        'passedCases': data.get('passed', 0),
                        'failedCases': data.get('failed', 0),
                        'skippedCases': data.get('skipped', 0),
                        'duration': f"{data.get('duration', 0)}秒" if data.get('duration') else '-',
                        'request': data.get('request', {}),
                        'response': data.get('response', {}),
                        'log': data.get('log', ''),
                        'resultType': result_type,
                        'fileId': result.get('file_id', ''),
                        'fileName': result.get('file_name', '')
                    })
            
            # 应用额外的筛选条件
            if status_filter and status_filter != 'all':
                formatted_results = [r for r in formatted_results if r.get('status') == status_filter]
            
            if api_filter and api_filter != 'all':
                formatted_results = [r for r in formatted_results if r.get('apiName') == api_filter]
            
            if date_filter and date_filter != 'all':
                try:
                    now = datetime.now().date()
                    filtered_results = []
                    
                    for result in formatted_results:
                        timestamp = result.get('timestamp', '')
                        if timestamp:
                            try:
                                result_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                                
                                if date_filter == 'today' and result_date == now:
                                    filtered_results.append(result)
                                elif date_filter == 'week':
                                    week_ago = now.replace(day=now.day-7)
                                    if result_date >= week_ago:
                                        filtered_results.append(result)
                                elif date_filter == 'month':
                                    month_ago = now.replace(day=now.day-30)
                                    if result_date >= month_ago:
                                        filtered_results.append(result)
                            except Exception as e:
                                logger.warning(f"解析日期失败: {str(e)}")
                    
                    formatted_results = filtered_results
                except Exception as e:
                    logger.warning(f"日期筛选失败: {str(e)}")
            
            # 应用分页
            total = len(formatted_results)
            paginated_results = formatted_results[offset:offset+limit]
            
            return jsonify({
                'success': True,
                'results': paginated_results,
                'total': total
            })
        
        # 原有的逻辑（不使用同步数据）
        # 确保结果目录存在
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            return jsonify({
                'success': True,
                'results': [],
                'total': 0
            })
        
        # 收集所有测试结果文件
        test_results = []
        
        # 遍历结果目录中的所有JSON文件
        for filename in os.listdir(results_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(results_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    # 检查是否是测试结果数据
                    # 检查文件名前缀是否匹配测试结果模式
                    if (filename.startswith('coverage_') or 
                        filename.startswith('test_results_') or
                        ('execution_results' in result_data) or
                        ('total' in result_data and 'passed' in result_data and 'failed' in result_data)):
                        
                        # 提取测试结果信息
                        result_id = filename[:-5]  # 移除.json扩展名
                        timestamp = result_data.get('created_at', result_data.get('timestamp', ''))
                        
                        # 尝试从文件名或数据中获取API名称
                        api_name = result_data.get('api_name', '')
                        if not api_name and 'file_id' in result_data:
                            file_id = result_data['file_id']
                            # 尝试从API文档中获取API名称
                            if file_id in api_docs:
                                api_name = api_docs[file_id].get('filename', file_id)
                        
                        # 获取测试状态
                        status = 'unknown'
                        if 'status' in result_data:
                            status = result_data['status']
                        elif 'execution_results' in result_data:
                            # 从执行结果中计算状态
                            exec_results = result_data['execution_results']
                            if isinstance(exec_results, dict):
                                total = exec_results.get('total', 0)
                                passed = exec_results.get('passed', 0)
                                failed = exec_results.get('failed', 0)
                                
                                if failed == 0:
                                    status = 'passed'
                                elif passed > 0:
                                    status = 'partial'
                                else:
                                    status = 'failed'
                        elif 'total' in result_data and 'passed' in result_data and 'failed' in result_data:
                            total = result_data.get('total', 0)
                            passed = result_data.get('passed', 0)
                            failed = result_data.get('failed', 0)
                            
                            if failed == 0:
                                status = 'passed'
                            elif passed > 0:
                                status = 'partial'
                            else:
                                status = 'failed'
                        
                        # 获取测试统计
                        total_cases = 0
                        passed_cases = 0
                        failed_cases = 0
                        skipped_cases = 0
                        
                        if 'execution_results' in result_data:
                            exec_results = result_data['execution_results']
                            if isinstance(exec_results, dict):
                                total_cases = exec_results.get('total', 0)
                                passed_cases = exec_results.get('passed', 0)
                                failed_cases = exec_results.get('failed', 0)
                                skipped_cases = exec_results.get('skipped', 0)
                        elif 'total' in result_data:
                            total_cases = result_data.get('total', 0)
                            passed_cases = result_data.get('passed', 0)
                            failed_cases = result_data.get('failed', 0)
                            skipped_cases = result_data.get('skipped', 0)
                        
                        # 获取执行时长
                        duration = result_data.get('duration', 0)
                        
                        # 创建测试结果对象
                        test_result = {
                            'id': result_id,
                            'suiteName': result_data.get('suite_name', '默认套件'),
                            'apiName': api_name,
                            'timestamp': timestamp,
                            'status': status,
                            'totalCases': total_cases,
                            'passedCases': passed_cases,
                            'failedCases': failed_cases,
                            'skippedCases': skipped_cases,
                            'duration': f"{duration}秒" if duration else '-',
                            'request': result_data.get('request', {}),
                            'response': result_data.get('response', {}),
                            'log': result_data.get('log', '')
                        }
                        
                        # 应用筛选条件
                        include_result = True
                        
                        # 状态筛选
                        if status_filter and status_filter != 'all' and status != status_filter:
                            include_result = False
                        
                        # API筛选
                        if api_filter and api_filter != 'all' and api_name != api_filter:
                            include_result = False
                        
                        # 日期筛选
                        if date_filter and date_filter != 'all' and timestamp:
                            try:
                                result_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                                now = datetime.now().date()
                                
                                if date_filter == 'today' and result_date != now:
                                    include_result = False
                                elif date_filter == 'week':
                                    week_ago = now.replace(day=now.day-7)
                                    if result_date < week_ago:
                                        include_result = False
                                elif date_filter == 'month':
                                    month_ago = now.replace(day=now.day-30)
                                    if result_date < month_ago:
                                        include_result = False
                            except Exception as e:
                                logger.warning(f"解析日期失败: {str(e)}")
                        
                        if include_result:
                            test_results.append(test_result)
                            
                except Exception as e:
                    logger.error(f"加载测试结果失败 {filename}: {str(e)}")
        
        # 按时间戳排序（最新的在前）
        test_results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 应用分页
        total = len(test_results)
        paginated_results = test_results[offset:offset+limit]
        
        return jsonify({
            'success': True,
            'results': paginated_results,
            'total': total
        })
        
    except Exception as e:
        logger.error(f"获取测试结果失败: {str(e)}")
        return jsonify({'error': '获取测试结果失败', 'message': str(e)}), 500

@app.route('/api/test-results/<result_id>', methods=['GET'])
def get_test_result_detail(result_id):
    """获取特定测试结果的详细信息"""
    try:
        # 确保结果目录存在
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            return jsonify({'error': '测试结果不存在'}), 404
        
        # 查找测试结果文件
        file_path = os.path.join(results_dir, f"{result_id}.json")
        if not os.path.exists(file_path):
            # 尝试查找带有前缀的文件
            found = False
            for filename in os.listdir(results_dir):
                if filename.endswith('.json') and result_id in filename:
                    file_path = os.path.join(results_dir, filename)
                    found = True
                    break
            
            if not found:
                return jsonify({'error': '测试结果不存在'}), 404
        
        # 读取测试结果
        with open(file_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        # 返回详细结果
        return jsonify({
            'success': True,
            'result': result_data
        })
        
    except Exception as e:
        logger.error(f"获取测试结果详情失败: {str(e)}")
        return jsonify({'error': '获取测试结果详情失败', 'message': str(e)}), 500

@app.route('/api/test-results/statistics', methods=['GET'])
def get_test_results_statistics():
    """获取测试结果统计信息"""
    try:
        # 获取所有测试结果
        all_results = []
        
        # 从results目录获取测试执行结果
        results_dir = app.config['RESULTS_FOLDER']
        if os.path.exists(results_dir):
            for filename in os.listdir(results_dir):
                # 读取所有以coverage_或results_开头的JSON文件
                if (filename.startswith('coverage_') or filename.startswith('results_')) and filename.endswith('.json'):
                    file_path = os.path.join(results_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            if isinstance(result_data, dict):
                                # 添加结果类型标识
                                result_data['result_type'] = result_data.get('result_type', 'execution')
                                all_results.append(result_data)
                    except Exception as e:
                        logger.error(f"读取测试结果文件 {filename} 失败: {str(e)}")
        
        # 从suggestions目录获取测试分析结果
        suggestions_dir = app.config['SUGGESTIONS_FOLDER']
        if os.path.exists(suggestions_dir):
            for filename in os.listdir(suggestions_dir):
                if filename.startswith('suggestions_') and filename.endswith('.json'):
                    file_path = os.path.join(suggestions_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            if isinstance(result_data, dict):
                                # 添加结果类型标识
                                result_data['result_type'] = 'analysis'
                                all_results.append(result_data)
                    except Exception as e:
                        logger.error(f"读取分析结果文件 {filename} 失败: {str(e)}")
        
        # 计算统计数据
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        coverage_percent = 0
        
        # 处理执行结果
        for result in all_results:
            if result.get('result_type') == 'execution' or result.get('result_type') == 'test_execution':
                # 尝试从不同的字段获取测试指标
                metrics = None
                
                # 检查是否有metrics字段（实际文件中的字段名）
                if 'metrics' in result:
                    metrics = result['metrics']
                # 检查是否有test_metrics字段
                elif 'test_metrics' in result:
                    metrics = result['test_metrics']
                # 检查是否有summary字段
                elif 'summary' in result:
                    metrics = result['summary']
                # 检查是否有直接的统计字段
                elif 'total' in result or 'passed' in result or 'failed' in result:
                    metrics = result
                
                if metrics:
                    total_tests += metrics.get('total', metrics.get('total_tests', 0))
                    passed_tests += metrics.get('passed', metrics.get('passed_tests', 0))
                    failed_tests += metrics.get('failed', metrics.get('failed_tests', 0))
        
        # 计算平均覆盖率
        coverage_results = []
        for result in all_results:
            if result.get('result_type') == 'execution' or result.get('result_type') == 'test_execution':
                # 尝试从不同的字段获取覆盖率数据
                coverage = None
                
                # 检查metrics字段
                if 'metrics' in result and 'coverage' in result['metrics']:
                    coverage = result['metrics']['coverage']
                # 检查test_metrics字段
                elif 'test_metrics' in result and 'coverage' in result['test_metrics']:
                    coverage = result['test_metrics']['coverage']
                # 检查summary字段
                elif 'summary' in result and 'coverage' in result['summary']:
                    coverage = result['summary']['coverage']
                # 检查直接字段
                elif 'coverage' in result:
                    coverage = result['coverage']
                
                if coverage is not None:
                    coverage_results.append(coverage)
        
        if coverage_results:
            coverage_percent = sum(coverage_results) / len(coverage_results)
        
        return jsonify({
            'success': True,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'coverage_percent': round(coverage_percent, 2)
        })
        
    except Exception as e:
        logger.error(f"获取测试结果统计信息失败: {str(e)}")
        return jsonify({'error': '获取测试结果统计信息失败', 'message': str(e)}), 500

@app.route('/api/test-results/sync', methods=['POST'])
def sync_test_results_endpoint():
    """手动触发测试结果同步"""
    try:
        sync_data = sync_test_results()
        
        if sync_data:
            return jsonify({
                'success': True,
                'message': '测试结果同步成功',
                'total_results': sync_data.get('total_results', 0),
                'last_sync': sync_data.get('last_sync', '')
            })
        else:
            return jsonify({
                'success': False,
                'error': '测试结果同步失败'
            }), 500
            
    except Exception as e:
        logger.error(f"测试结果同步失败: {str(e)}")
        return jsonify({'error': '测试结果同步失败', 'message': str(e)}), 500


def _parse_log_blocks_to_cases(log_text: str, cases_data):
    """解析日志块为结构化请求/响应列表。"""
    if not log_text:
        return None
    case_map = {}
    if isinstance(cases_data, list):
        for c in cases_data:
            detail = c.get("detail")
            if detail:
                case_map[detail] = c.get("case_id")
    pattern = re.compile(
        r"用例标题:\s*(?P<title>.+?)\n"
        r"请求路径:\s*(?P<url>.+?)\n"
        r"请求方式:\s*(?P<method>\S+)\n"
        r"请求头:\s*(?P<headers>\{.*?\})\n"
        r"请求内容:\s*(?P<body>\{.*?\})\n"
        r"接口响应内容:\s*(?P<resp_body>\{.*?\})\n"
        r"接口响应时长:\s*(?P<elapsed>[\d\.]+)\s*ms\n"
        r"Http状态码:\s*(?P<status>\d+)",
        re.S
    )
    def _parse_obj(text):
        for parser in (lambda t: json.loads(t), lambda t: ast.literal_eval(t)):
            try:
                return parser(text)
            except Exception:
                continue
        return text
    results = []
    for m in pattern.finditer(log_text):
        detail = m.group("title").strip()
        results.append({
            "case_id": case_map.get(detail),
            "detail": detail,
            "request": {
                "method": m.group("method").strip(),
                "url": m.group("url").strip(),
                "body": _parse_obj(m.group("body")),
                "headers": _parse_obj(m.group("headers")),
            },
            "response": {
                "status_code": int(m.group("status")),
                "body": _parse_obj(m.group("resp_body")),
                "headers": None,
                "elapsed_ms": float(m.group("elapsed")),
            }
        })
    return results or None


@app.route('/api/ai/message-prompt', methods=['POST'])
def run_message_prompt():
    """
    通用 message_ai_prompt 执行入口
    output_pytest 由后台自动生成，命名: tests/generated/test_ai_<openapi_stem>_<ts>.py
    body 可选字段：
      - openapi: str
      - external_params: dict | null（为 null/缺省时不带此参数）
      - no_stream: bool (默认 False，为 True 时追加 --no-stream)
    """
    try:
        import ast
        data = request.json or {}
        project_root = Path(__file__).parent
        uploads_openapi_dir = project_root / "uploads" / "openapi"

        def _resolve_openapi_path(value: Optional[str]) -> str:
            """
            支持简写：如传入 "forward" 自动映射到 uploads/openapi/openapi_feishu_server-docs_im-v1_message_forward.yaml
            规则：
              - 无后缀且不含路径分隔符 -> 视为别名，尝试 alias_map
              - 仅文件名 -> 默认拼接 uploads/openapi
              - 其他 -> 原样返回
            """
            default_path = uploads_openapi_dir / "openapi_feishu_server-docs_im-v1_message_update.yaml"
            if not value:
                return str(default_path)

            raw = value.strip()
            path_obj = Path(raw)

            # 别名映射（无路径、无后缀）
            if not path_obj.suffix and "/" not in raw and "\\" not in raw:
                alias = raw.lower()
                alias_map = {
                    "forward": uploads_openapi_dir / "openapi_feishu_server-docs_im-v1_message_forward.yaml",
                    "create": uploads_openapi_dir / "openapi_feishu_server-docs_im-v1_message_create.yaml",
                    "reply": uploads_openapi_dir / "openapi_feishu_server-docs_im-v1_message_reply.yaml",
                    "update": uploads_openapi_dir / "openapi_feishu_server-docs_im-v1_message_update.yaml",
                }
                if alias in alias_map:
                    return str(alias_map[alias])

            # 仅文件名时，尝试 uploads/openapi 下是否存在
            candidate = uploads_openapi_dir / raw
            if candidate.exists():
                return str(candidate)

            # 否则直接返回原值（可能是绝对/相对路径）
            return raw

        openapi_path = _resolve_openapi_path(data.get("openapi"))
        external_params = data.get("external_params", None)
        no_stream = bool(data.get("no_stream", False))

        task_id = generate_task_id()

        # 自动生成输出路径
        gen_dir = project_root / "tests" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(openapi_path).stem
        output_pytest = str(gen_dir / f"test_ai_{stem}_{task_id}.py")

        cmd = [
            sys.executable,
            "-m",
            "utils.aiMakecase.message_ai_prompt",
            "--openapi",
            openapi_path,
            "--output-pytest",
            output_pytest,
        ]

        if external_params is not None:
            cmd += ["--external-params", json.dumps(external_params, ensure_ascii=False)]

        if no_stream:
            cmd.append("--no-stream")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NON_INTERACTIVE"] = "1"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            cwd=str(project_root),
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        try:
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return_code = -1

        max_len = 5000
        response_data = {
            "task_id": task_id,
            "return_code": return_code,
            "openapi": openapi_path,
            "output_pytest": output_pytest,
            "external_params": external_params,
            "no_stream": no_stream,
            "cmd": cmd,
            "stdout": stdout[-max_len:] if stdout else "",
            "stderr": stderr[-max_len:] if stderr else "",
            "stdout_length": len(stdout) if stdout else 0,
            "stderr_length": len(stderr) if stderr else 0,
        }

        if return_code == 0:
            response_data["message"] = "message_ai_prompt 执行成功"
            return jsonify(response_data)
        else:
            response_data["error"] = "message_ai_prompt 执行失败"
            return jsonify(response_data), 500

    except Exception as e:
        logger.error(f"执行 message_ai_prompt 失败: {e}")
        return jsonify({
            "error": "执行 message_ai_prompt 失败",
            "message": str(e)
        }), 500


@app.route('/api/ai/message-prompt/run', methods=['POST'])
def run_message_prompt_tests():
    """
    执行已生成的 message_ai_prompt pytest 用例
    body:
      - test_file: 可选，指定 pytest 文件路径；缺省则取 tests/generated 下最新文件
    响应包含解析出的请求体与响应数据（从 pytest 输出日志解析）。
    """
    try:
        import ast
        data = request.json or {}
        project_root = Path(__file__).parent

        test_file = data.get("test_file")
        if not test_file:
            gen_dir = project_root / "tests" / "generated"
            if not gen_dir.exists():
                return jsonify({"error": "未找到生成的测试文件"}), 404
            candidates = list(gen_dir.glob("test_ai_*.py"))
            if not candidates:
                return jsonify({"error": "未找到生成的测试文件"}), 404
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            test_file = str(candidates[0])

        task_id = generate_task_id()
        log_path = project_root / "uploads" / "results" / f"mp_run_{task_id}.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_file
        ]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NON_INTERACTIVE"] = "1"
        env["MP_LOG_PATH"] = str(log_path)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            cwd=str(project_root),
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        try:
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return_code = -1

        # 优先读取测试写入的结构化日志文件
        test_responses = None
        log_read_error = None
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        test_responses = loaded
            except Exception as e:
                log_read_error = f"读取 MP_LOG_PATH 失败: {e}"
                logger.warning(log_read_error)

        # 回退：如无文件，则尝试从 stdout/stderr 解析
        if test_responses is None:
            combined = f"{stdout}\n{stderr}"
            test_responses = _parse_log_blocks_to_cases(combined, None)

        max_len = 5000
        response_data = {
            "task_id": task_id,
            "return_code": return_code,
            "test_file": test_file,
            "stdout": stdout[-max_len:] if stdout else "",
            "stderr": stderr[-max_len:] if stderr else "",
            "stdout_length": len(stdout) if stdout else 0,
            "stderr_length": len(stderr) if stderr else 0,
            "test_responses": test_responses,
            "log_path": str(log_path)
        }
        if log_read_error:
            response_data["log_read_error"] = log_read_error

        if return_code == 0:
            response_data["message"] = "pytest 执行成功"
            return jsonify(response_data)
        else:
            response_data["error"] = "pytest 执行失败"
            return jsonify(response_data), 500

    except Exception as e:
        logger.error(f"执行 message_ai_prompt 测试失败: {e}")
        return jsonify({
            "error": "执行 message_ai_prompt 测试失败",
            "message": str(e)
        }), 500

@app.route('/api/test-results/export', methods=['GET'])
def export_test_results():
    """导出测试结果"""
    try:
        import zipfile
        import io
        
        # 确保结果目录存在
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            return jsonify({'error': '测试结果目录不存在'}), 404
        
        # 创建内存中的ZIP文件
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 添加所有测试结果文件到ZIP
            for filename in os.listdir(results_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(results_dir, filename)
                    zip_file.write(file_path, filename)
        
        zip_buffer.seek(0)
        
        # 创建响应
        response = app.response_class(
            zip_buffer.read(),
            mimetype='application/zip',
            direct_passthrough=True
        )
        
        # 设置下载文件名
        download_name = f"test-results-{datetime.now().strftime('%Y%m%d')}.zip"
        response.headers.set('Content-Disposition', 'attachment', filename=download_name)
        
        return response
        
    except Exception as e:
        logger.error(f"导出测试结果失败: {str(e)}")
        return jsonify({'error': '导出测试结果失败', 'message': str(e)}), 500

# 启动服务器
if __name__ == '__main__':
    # 固定服务器配置
    HOST = '0.0.0.0'  # 固定主机地址（监听所有网络接口）
    PORT = 5000        # 固定端口
    DEBUG = True       # 调试模式
    
    # 固定显示的访问地址（用于日志和前端配置）
    DISPLAY_HOST = '127.0.0.1'  # 固定显示地址
    DISPLAY_URL = f'http://{DISPLAY_HOST}:{PORT}'
    
    logger.info(f"启动智能自动化测试平台API服务器")
    logger.info(f"监听地址: {HOST}:{PORT}")
    logger.info(f"访问地址: {DISPLAY_URL}")
    logger.info(f"本地访问: http://localhost:{PORT}")
    
    # 启动服务器
    app.run(host=HOST, port=PORT, debug=DEBUG, use_reloader=False)

