"""
前端接口，处理多种输入方式
提供API接口供前端调用，处理飞书URL、JSON文件和直接OpenAPI文档输入
"""

import os
import json
import yaml
import tempfile
import shutil
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

# 导入自定义模块
from .api_input_processor import APIInputProcessor
from .test_case_generator import TestCaseGenerator


class APIFrontend:
    """前端接口类"""
    
    def __init__(self, upload_dir: str = "../../uploads", output_dir: str = "../../outputs"):
        """
        初始化前端接口
        
        Args:
            upload_dir: 上传文件目录
            output_dir: 输出文件目录
        """
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.processor = APIInputProcessor()
        self.generator = TestCaseGenerator()
        
        # 确保目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.app.config['UPLOAD_FOLDER'] = self.upload_dir
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.route('/api/process', methods=['POST'])
        def process_input():
            """处理输入并生成测试用例"""
            try:
                data = request.get_json()
                
                # 检查输入类型
                feishu_url = data.get('feishu_url')
                openapi_doc = data.get('openapi_doc')
                business_scenes = data.get('business_scenes')
                api_relations = data.get('api_relations')
                use_ai = data.get('use_ai', False)
                
                # 处理输入
                input_result = self.processor.process_input(
                    feishu_url=feishu_url,
                    openapi_doc=openapi_doc,
                    business_scenes=business_scenes,
                    api_relations=api_relations
                )
                
                # 生成测试用例
                test_cases_path = None
                if input_result.get('openapi'):
                    test_cases_path = self.generator.generate_all_test_cases(
                        input_result['openapi'],
                        input_result.get('business_scene'),
                        input_result.get('api_relation'),
                        use_ai_generator=use_ai
                    )
                
                # 返回结果
                result = {
                    'status': 'success',
                    'input_result': input_result,
                    'test_cases_path': test_cases_path
                }
                
                return jsonify(result)
            
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/upload', methods=['POST'])
        def upload_file():
            """上传文件并处理"""
            try:
                # 检查是否有文件
                if 'file' not in request.files:
                    return jsonify({
                        'status': 'error',
                        'message': '没有文件'
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'status': 'error',
                        'message': '没有选择文件'
                    }), 400
                
                if file and self._allowed_file(file.filename):
                    # 保存文件
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    
                    # 获取其他参数
                    openapi_doc = request.form.get('openapi_doc')
                    business_scenes = request.form.get('business_scenes')
                    api_relations = request.form.get('api_relations')
                    use_ai = request.form.get('use_ai', 'false').lower() == 'true'
                    
                    # 处理输入
                    input_result = self.processor.process_input(
                        json_files=[file_path],
                        openapi_doc=openapi_doc,
                        business_scenes=business_scenes,
                        api_relations=api_relations
                    )
                    
                    # 生成测试用例
                    test_cases_path = None
                    if input_result.get('openapi'):
                        test_cases_path = self.generator.generate_all_test_cases(
                            input_result['openapi'],
                            input_result.get('business_scene'),
                            input_result.get('api_relation'),
                            use_ai_generator=use_ai
                        )
                    
                    # 返回结果
                    result = {
                        'status': 'success',
                        'input_result': input_result,
                        'test_cases_path': test_cases_path
                    }
                    
                    return jsonify(result)
                
                return jsonify({
                    'status': 'error',
                    'message': '不支持的文件类型'
                }), 400
            
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/download/<path:filename>', methods=['GET'])
        def download_file(filename):
            """下载生成的文件"""
            try:
                file_path = os.path.join(self.output_dir, filename)
                if os.path.exists(file_path):
                    return send_file(file_path, as_attachment=True)
                else:
                    return jsonify({
                        'status': 'error',
                        'message': '文件不存在'
                    }), 404
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/files', methods=['GET'])
        def list_files():
            """列出所有生成的文件"""
            try:
                files = []
                for root, dirs, filenames in os.walk(self.output_dir):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, self.output_dir)
                        file_size = os.path.getsize(file_path)
                        file_type = 'yaml' if filename.endswith('.yaml') or filename.endswith('.yml') else 'json'
                        
                        files.append({
                            'name': filename,
                            'path': rel_path,
                            'size': file_size,
                            'type': file_type
                        })
                
                return jsonify({
                    'status': 'success',
                    'files': files
                })
            
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/preview/<path:filename>', methods=['GET'])
        def preview_file(filename):
            """预览文件内容"""
            try:
                file_path = os.path.join(self.output_dir, filename)
                if not os.path.exists(file_path):
                    return jsonify({
                        'status': 'error',
                        'message': '文件不存在'
                    }), 404
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    if filename.endswith('.yaml') or filename.endswith('.yml'):
                        content = yaml.safe_load(f)
                    else:
                        content = json.load(f)
                
                return jsonify({
                    'status': 'success',
                    'content': content
                })
            
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 400
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                'status': 'success',
                'message': 'API服务运行正常'
            })
    
    def _allowed_file(self, filename):
        """检查文件类型是否允许"""
        ALLOWED_EXTENSIONS = {'json', 'yaml', 'yml'}
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def run(self, host='127.0.0.1', port=5000, debug=True):
        """运行Flask应用"""
        self.app.run(host=host, port=port, debug=debug)


# 创建前端应用实例
def create_app():
    """创建Flask应用实例"""
    frontend = APIFrontend()
    return frontend.app


# 使用示例
if __name__ == "__main__":
    # 创建并运行前端应用
    frontend = APIFrontend()
    frontend.run(host='127.0.0.1', port=5000, debug=True)