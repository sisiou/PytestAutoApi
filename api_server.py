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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import traceback

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
CORS(app)  # 启用跨域支持

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB最大文件大小
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MULTI_UPLOAD_FOLDER'] = 'multiuploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['TEST_CASES_FOLDER'] = 'test_cases'

# 确保必要的目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEST_CASES_FOLDER'], exist_ok=True)

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

def save_result(task_id: str, result: Dict[str, Any]):
    """保存任务结果"""
    result_path = os.path.join(app.config['RESULTS_FOLDER'], f"{task_id}.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
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
        save_result(file_id, api_docs[file_id])
        
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
        save_result(f"test_cases_{file_id}", test_cases[file_id])
        
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
        save_result(f"coverage_{file_id}", coverage_reports[file_id])
        
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
        save_result(f"suggestions_{file_id}", suggestions[file_id])
        
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
            save_result(f"test_cases_{file_id}", test_cases[file_id])
        
        if 'execution_results' in workflow_results:
            coverage_reports[file_id] = {
                'file_id': file_id,
                'execution_results': workflow_results['execution_results'],
                'created_at': datetime.now().isoformat()
            }
            save_result(f"coverage_{file_id}", coverage_reports[file_id])
        
        if 'analysis_results' in workflow_results:
            suggestions[file_id] = {
                'file_id': file_id,
                'analysis_results': workflow_results['analysis_results'],
                'created_at': datetime.now().isoformat()
            }
            save_result(f"suggestions_{file_id}", suggestions[file_id])
        
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
            import yaml
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
                return jsonify({
                    'success': False,
                    'error': '无效的JSON格式',
                    'message': str(e)
                }), 400
        elif file_extension in ['.yaml', '.yml']:
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                return jsonify({
                    'success': False,
                    'error': '无效的YAML格式',
                    'message': str(e)
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
def generate_test_cases():
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
        save_result(task_id, result)
        
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
        save_result(task_id, result)
        
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
        
        # 保存执行结果
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
        
        # ========== 修改：启动 Allure 报告服务器（后台运行） ==========
        allure_url = None
        allure_process = None
        
        # 检查多个可能的Allure结果目录
        possible_allure_dirs = [
            project_root / "allure-results",
            project_root / "report" / "tmp",
            project_root / "reports" / "allure-results",
            project_root / "test-results" / "allure",
            project_root / folder_path / "allure-results"  # 特定文件夹下的结果
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
            logger.warning(f"未找到Allure测试结果目录，检查了: {possible_allure_dirs}")
        # ========== 修改代码结束 ==========
        
        # 返回完整输出（限制长度避免响应过大）
        max_output_length = 5000  # 增加到5000字符
        
        response_data = {
            'task_id': task_id,
            'folder': folder_name,
            'folder_path': folder_path,
            'return_code': return_code,
            'stdout': stdout[-max_output_length:] if len(stdout) > max_output_length else stdout,
            'stderr': stderr[-max_output_length:] if len(stderr) > max_output_length else stderr,
            'stdout_length': len(stdout),
            'stderr_length': len(stderr)
        }
        
        # ========== 修改：添加 Allure 报告信息 ==========
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
        # ========== 修改代码结束 ==========
        
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
        logger.error(f"执行 run_feishu_generator_and_tests.py 失败: {str(e)}")
        return jsonify({
            'error': '执行脚本失败',
            'message': str(e)
        }), 500

@app.route('/api/feishu/generate-ai-test-cases', methods=['POST'])
def generate_ai_test_cases():
    """执行 universal_ai_test_generator.py 脚本，生成AI测试用例"""
    try:
        # 获取请求参数
        data = request.json or {}
        base_name = data.get('base_name', '')
        
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
        
        # 构建命令参数（第一步：生成 YAML 用例）
        base_dir = "uploads"
        output_dir = "tests"
        cmd_args_yaml = [
            sys.executable,
            str(script_path),
            '--base-name', base_name,
            '--base-dir', base_dir,
            '--output-dir', output_dir,
            '--output-format', 'yaml'
        ]
        
        logger.info(f"开始生成YAML用例: {' '.join(cmd_args_yaml)}")
        
        # 设置环境变量，强制使用 UTF-8 编码（解决 Windows GBK 编码问题）
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'  # 强制 Python 使用 UTF-8 编码
        env['PYTHONUTF8'] = '1'  # Python 3.7+ 支持，强制 UTF-8
        env['NON_INTERACTIVE'] = '1'  # 标记为非交互式模式
        
        def run_proc(cmd_args):
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
        
        return_code, stdout, stderr = run_proc(cmd_args_yaml)
        if return_code != 0:
            return jsonify({
                'task_id': task_id,
                'error': '执行脚本失败',
                'message': '生成 YAML 用例失败',
                'return_code': return_code,
                'base_name': base_name,
                'stdout': stdout[-2000:] if stdout else '',
                'stderr': stderr[-2000:] if stderr else ''
            }), 500
        
        # 第二步：将 YAML 转换为 pytest 脚本（不调用大模型）
        yaml_file_path = project_root / output_dir / f"cases_{base_name}.yaml"
        if not yaml_file_path.exists():
            # 兜底：尝试最近的 cases_*.yaml
            candidates = list((project_root / output_dir).glob("cases_*.yaml"))
            if candidates:
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                yaml_file_path = candidates[0]
        
        cmd_args_convert = [
            sys.executable,
            str(script_path),
            '--base-name', base_name,
            '--base-dir', base_dir,
            '--output-dir', output_dir,
            '--yaml-to-py',
            '--yaml-path', str(yaml_file_path)
        ]
        logger.info(f"YAML 转换为 pytest: {' '.join(cmd_args_convert)}")
        convert_return_code, convert_stdout, convert_stderr = run_proc(cmd_args_convert)
        if convert_return_code != 0:
            return jsonify({
                'task_id': task_id,
                'error': '转换失败',
                'message': 'YAML 转 pytest 失败',
                'return_code': convert_return_code,
                'base_name': base_name,
                'stdout': convert_stdout[-2000:] if convert_stdout else '',
                'stderr': convert_stderr[-2000:] if convert_stderr else ''
            }), 500
        
        # 保存执行结果
        result = {
            'task_id': task_id,
            'script': str(script_path),
            'base_name': base_name,
            'base_dir': base_dir,
            'output_dir': output_dir,
            'return_code': convert_return_code,
            'stdout': convert_stdout,
            'stderr': convert_stderr,
            'yaml_return_code': return_code,
            'yaml_stdout': stdout,
            'yaml_stderr': stderr,
            'created_at': datetime.now().isoformat()
        }
        save_result(task_id, result)
        
        # 检查生成的测试文件
        # 首先尝试从 stdout 中解析生成的文件名
        test_file_path = None
        import re
        if convert_stdout:
            # 匹配格式: [OK] 生成测试文件: tests\test_xxx_normal_exception.py
            # 或: [OK] 生成测试文件: tests/test_xxx_normal_exception.py
            match = re.search(r'生成测试文件:\s*(?:tests[/\\])?test_([\w-]+)_normal_exception\.py', convert_stdout)
            if match:
                operation_id = match.group(1)
                test_file_path = project_root / output_dir / f"test_{operation_id}_normal_exception.py"
            else:
                # 尝试匹配完整路径
                match = re.search(r'生成测试文件:\s*([^\s]+test_[\w-]+_normal_exception\.py)', convert_stdout)
                if match:
                    file_path_str = match.group(1).replace('\\', '/')
                    # 如果是相对路径，从项目根目录开始
                    if not os.path.isabs(file_path_str):
                        test_file_path = project_root / file_path_str
                    else:
                        test_file_path = Path(file_path_str)
        
        # 如果从 stdout 中没找到，尝试搜索最近生成的测试文件
        if test_file_path is None or not test_file_path.exists():
            tests_dir = project_root / output_dir
            if tests_dir.exists():
                # 查找所有 test_*_normal_exception.py 文件
                test_files = list(tests_dir.glob("test_*_normal_exception.py"))
                if test_files:
                    # 按修改时间排序，取最新的
                    test_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    test_file_path = test_files[0]
                    logger.info(f"从目录中找到测试文件: {test_file_path}")
        
        # 如果还是没找到，尝试使用 base_name（虽然可能不匹配，但作为最后的尝试）
        if test_file_path is None or not test_file_path.exists():
            test_file_path = project_root / output_dir / f"test_{base_name}_normal_exception.py"
        
        config_file_path = project_root / output_dir / f"conftest.py"
        
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
            'config_file_path': str(config_file_path) if config_file_exists else None
        }
        
        # 如果生成失败，添加错误信息摘要
        if return_code != 0:
            response_data['error'] = '测试用例生成失败'
            response_data['message'] = f'脚本返回码: {return_code}（0表示成功，非0表示有错误或警告）'
            
            # 尝试从输出中提取关键错误信息
            if stderr:
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed', 'ERROR']
                error_lines = [line for line in stderr.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    response_data['error_summary'] = error_lines[-10:]  # 最后10行错误信息
            
            # 也从 stdout 中查找错误信息（有些错误可能输出到 stdout）
            if stdout:
                error_keywords = ['错误', 'Error', 'Exception', 'Traceback', '失败', 'Failed', 'ERROR']
                error_lines = [line for line in stdout.split('\n') 
                             if any(keyword in line for keyword in error_keywords)]
                if error_lines:
                    if 'error_summary' not in response_data:
                        response_data['error_summary'] = []
                    response_data['error_summary'].extend(error_lines[-10:])
            
            # 限制输出长度，避免响应过大
            max_output_length = 3000
            if len(stdout) > max_output_length:
                response_data['generation_stdout'] = stdout[-max_output_length:]
                response_data['generation_stdout_length'] = len(stdout)
            else:
                response_data['generation_stdout'] = stdout
            
            if len(stderr) > max_output_length:
                response_data['generation_stderr'] = stderr[-max_output_length:]
                response_data['generation_stderr_length'] = len(stderr)
            else:
                response_data['generation_stderr'] = stderr
            
            return jsonify(response_data)
        
        # 如果生成成功，继续执行测试用例
        response_data['message'] = 'AI测试用例生成成功'
        if test_file_exists:
            response_data['message'] += f'，测试文件已生成: {test_file_path.name}'
        
        # ========== 执行生成的测试用例 ==========
        if test_file_exists:
            logger.info(f"开始执行测试用例: {test_file_path}")
            
            # 对该接口禁用 Allure（防止与其它接口报告混淆）
            use_allure = False
            allure_results_dir = None
            allure_report_dir = None
            
            pytest_cmd = [
                sys.executable, '-m', 'pytest',
                str(test_file_path),
                '-v',
                '--tb=short',
            ]
            
            if use_allure:
                allure_results_dir = project_root / "allure-results" / task_id
                allure_results_dir.mkdir(parents=True, exist_ok=True)
                allure_report_dir = project_root / "report" / "html" / task_id
                allure_report_dir.parent.mkdir(parents=True, exist_ok=True)
                pytest_cmd.append(f'--alluredir={allure_results_dir}')
                pytest_cmd.append('--clean-alluredir')
            
            logger.info(f"执行pytest命令: {' '.join(pytest_cmd)}")
            
            # 执行pytest
            test_process = subprocess.Popen(
                pytest_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                cwd=str(project_root),
                encoding='utf-8',
                errors='replace',
                env=env
            )
            
            test_stdout = ''
            test_stderr = ''
            test_return_code = -1
            
            try:
                test_stdout, test_stderr = test_process.communicate(timeout=600)  # 10分钟超时
                test_return_code = test_process.returncode
            except subprocess.TimeoutExpired:
                test_process.kill()
                try:
                    test_stdout, test_stderr = test_process.communicate()
                except Exception as e:
                    logger.error(f"获取测试超时后的输出失败: {e}")
                    test_stdout = f"测试执行超时，无法获取完整输出: {str(e)}"
                    test_stderr = ""
                test_return_code = -1
                response_data['test_error'] = '测试执行超时'
                response_data['test_message'] = '测试执行超过10分钟，已终止'
            except Exception as e:
                logger.error(f"执行测试时出错: {e}")
                try:
                    test_process.kill()
                except:
                    pass
                test_return_code = -1
                response_data['test_error'] = '执行测试时出错'
                response_data['test_message'] = str(e)
            
            # 保存测试执行结果
            response_data['test_return_code'] = test_return_code
            response_data['test_success'] = test_return_code == 0 or test_return_code == 1  # pytest返回1表示有测试失败，但执行成功

            # 将测试输出写到控制台便于排查（截断避免过长）
            log_tail = 2000
            if test_stdout:
                logger.info(f"pytest stdout (tail {log_tail}):\n{test_stdout[-log_tail:]}")
            if test_stderr:
                logger.error(f"pytest stderr (tail {log_tail}):\n{test_stderr[-log_tail:]}")
            
            # 限制测试输出长度
            max_output_length = 3000
            if len(test_stdout) > max_output_length:
                response_data['test_stdout'] = test_stdout[-max_output_length:]
                response_data['test_stdout_length'] = len(test_stdout)
            else:
                response_data['test_stdout'] = test_stdout
            
            if len(test_stderr) > max_output_length:
                response_data['test_stderr'] = test_stderr[-max_output_length:]
                response_data['test_stderr_length'] = len(test_stderr)
            else:
                response_data['test_stderr'] = test_stderr
            
            # ========== 提取指标：只用 pytest 输出，避免引用其他任务的 Allure 数据 ==========
            metrics = _parse_pytest_output(test_stdout)
            if metrics:
                response_data['metrics'] = metrics
                response_data['message'] += f'，测试执行完成。通过: {metrics.get("passed", 0)}/{metrics.get("total", 0)}'
                logger.info(f"从 pytest 输出解析到指标: {metrics}")
            else:
                response_data['metrics'] = None
                logger.warning("无法从 pytest 输出中解析测试结果")
            
            # 如果仍然没有指标，设置默认值
            if not response_data.get('metrics'):
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
            
            # 如果测试执行失败，添加错误信息摘要
            if test_return_code not in [0, 1]:  # 0=成功, 1=有失败但执行成功
                if 'test_error' not in response_data:
                    response_data['test_error'] = '测试执行失败'
                    response_data['test_message'] = f'测试返回码: {test_return_code}'
                
                # 提取测试错误信息
                if test_stderr:
                    error_keywords = ['FAILED', 'ERROR', '失败', 'Error', 'Exception']
                    error_lines = [line for line in test_stderr.split('\n') 
                                 if any(keyword in line for keyword in error_keywords)]
                    if error_lines:
                        if 'test_error_summary' not in response_data:
                            response_data['test_error_summary'] = []
                        response_data['test_error_summary'].extend(error_lines[-10:])
        else:
            response_data['test_message'] = '测试文件不存在，跳过测试执行'
            response_data['metrics'] = None
        
        # 限制生成脚本的输出长度
        max_output_length = 2000
        if len(stdout) > max_output_length:
            response_data['generation_stdout'] = stdout[-max_output_length:]
            response_data['generation_stdout_length'] = len(stdout)
        else:
            response_data['generation_stdout'] = stdout
        
        if len(stderr) > max_output_length:
            response_data['generation_stderr'] = stderr[-max_output_length:]
            response_data['generation_stderr_length'] = len(stderr)
        else:
            response_data['generation_stderr'] = stderr
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"执行 universal_ai_test_generator.py 失败: {str(e)}")
        return jsonify({
            'error': '执行脚本失败',
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
        
        # 从配置中获取授权令牌和基础URL
        authorization = feishu_config.get_authorization()
        base_url = feishu_config.get_base_url()
        
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

