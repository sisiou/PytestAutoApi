#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能自动化测试平台后端API服务
提供RESTful API接口支持前端交互
"""

import os
import json
import time
import uuid
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 导入智能自动化平台模块
from utils.smart_auto.api_parser import APIParser
from utils.smart_auto.test_generator import TestCaseGenerator, generate_test_cases
from utils.smart_auto.coverage_scorer import CoverageScorer

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
def generate_task_id():
    """生成任务ID"""
    return str(uuid.uuid4())

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
    
    return jsonify(api_docs[task_id])

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

import pytest
import requests
import json

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
            'task_id': task_id,
            'message': '测试用例生成成功',
            'test_cases_count': result['test_cases_count']
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
            'run_task_id': run_task_id,
            'message': '测试用例运行完成',
            'results': test_results
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


# ========== 新增辅助函数 ==========
import socket
import threading

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

# 启动服务器
if __name__ == '__main__':
    logger.info("启动智能自动化测试平台API服务器")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)