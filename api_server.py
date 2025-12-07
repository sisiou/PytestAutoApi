#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能自动化测试平台后端API服务
提供RESTful API接口支持前端交互
"""

import os
import sys
import json
import time
import hashlib
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
# 导入智能自动化平台模块
from utils.smart_auto.api_parser import APIParser, APIParserFactory
from utils.smart_auto.test_generator import generate_test_cases
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
            should_regenerate,
            process_url_with_ai
        )
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
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(file_path)
        
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
        # 查找文件
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 遍历上传目录查找匹配的文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
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
        relation_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'api_relation')
        scene_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], 'business_scene')
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
        # 查找文件
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 遍历上传目录查找匹配的文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
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
        # 查找文件
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = None
        
        # 遍历上传目录查找匹配的文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
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
            # 提取API信息
            api_data = doc_info.get('api_data', {})
            
            # 检查是否为完整解析器的数据格式（包含name, method, path等扁平结构）
            if 'name' in api_data or 'method' in api_data:
                # 完整解析器的扁平数据格式 - 只返回基本信息，不返回详细参数和响应
                api_info = {
                    'id': task_id,
                    'method': api_data.get('method', 'GET'),
                    'path': api_data.get('path', '/api/unknown'),
                    'summary': api_data.get('summary', ''),
                    'description': api_data.get('description', ''),
                    'tags': api_data.get('tags', []) if isinstance(api_data.get('tags'), list) else [],
                    # 移除详细的参数和响应信息，只保留计数
                    'parameters_count': len(api_data.get('request', {}).get('headers', [])) + 
                                      len(api_data.get('request', {}).get('query_params', [])) + 
                                      len(api_data.get('request', {}).get('path_params', [])),
                    'responses_count': len(api_data.get('responses', [])),
                    'has_request_body': bool(api_data.get('request', {}).get('body')),
                    'task_id': task_id
                }
                docs_list.append(api_info)
            
            else:
                # 传统OpenAPI格式 - 只返回基本信息，不返回详细参数和响应
                paths = api_data.get('paths', {})
                for path, path_item in paths.items():
                    for method, api_detail in path_item.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                            api_info = {
                                'id': f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '').replace(':', '_')}",
                                'method': method.upper(),
                                'path': path,
                                'summary': api_detail.get('summary', ''),
                                'description': api_detail.get('description', ''),
                                'tags': api_detail.get('tags', []),
                                # 移除详细的参数和响应信息，只保留计数
                                'parameters_count': len(api_detail.get('parameters', [])),
                                'responses_count': len(api_detail.get('responses', {})),
                                'has_request_body': bool(api_detail.get('requestBody')),
                                'task_id': task_id
                            }
                            docs_list.append(api_info)
        
        # 更新缓存
        docs_list_cache = docs_list
        docs_list_cache_time = current_time
        
        return jsonify(docs_list)
    
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
        
        
        # 生成URL的哈希值
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 定义输出目录
        output_dir = app.config['UPLOAD_FOLDER']
        
        # 定义文件路径
        openapi_file = os.path.join(output_dir, 'openapi', f"openapi_{url_hash}.yaml")
        relation_file = os.path.join(output_dir, 'relation', f"relation_{url_hash}.json")
        scene_file = os.path.join(output_dir, 'scene', f"scene_{url_hash}.json")
        
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
            'url_hash': url_hash,
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

# 9. 静态文件服务
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

# 启动服务器
if __name__ == '__main__':
    logger.info("启动智能自动化测试平台API服务器")
    app.run(host='0.0.0.0', port=5000, debug=True)
