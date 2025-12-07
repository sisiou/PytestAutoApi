#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL到测试用例的整合工具
将飞书URL通过feishu_parse.py生成JSON，再通过ai.py生成API文档和场景，
最后通过feishu_message_send_generator_v2.py生成测试用例，并与前端交互
"""

import os
import sys
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入所需模块
try:
    from utils.parse.feishu_parse import transform_feishu_url, download_json
    from utils.parse.ai import process_url_with_ai
    from utils.other_tools.openapi_to_testcase import OpenAPIToTestCase
    from utils.other_tools.feishu_test_generator import FeishuTestGenerator
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("尝试使用相对路径导入...")
    
    # 尝试使用相对路径导入
    try:
        from parse.feishu_parse import transform_feishu_url, download_json
        from parse.ai import process_url_with_ai
        from other_tools.openapi_to_testcase import OpenAPIToTestCase
        from other_tools.feishu_test_generator import FeishuTestGenerator
    except ImportError as e2:
        print(f"相对路径导入也失败: {e2}")
        print("请确保所有依赖模块都在正确的路径下")
        sys.exit(1)


class UrlToTestCaseIntegration:
    """URL到测试用例的整合类"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化整合工具
        
        Args:
            output_dir: 输出目录，如果为None则使用默认目录
        """
        # 设置默认输出目录
        if output_dir is None:
            self.output_dir = os.path.join(project_root, "integration_output")
        else:
            self.output_dir = output_dir
            
        # 创建输出目录结构
        self.temp_dir = os.path.join(self.output_dir, "temp")
        self.openapi_dir = os.path.join(self.output_dir, "openapi")
        self.relation_dir = os.path.join(self.output_dir, "relation")
        self.scene_dir = os.path.join(self.output_dir, "scene")
        self.testcase_dir = os.path.join(self.output_dir, "testcase")
        
        # 确保所有目录存在
        for dir_path in [self.output_dir, self.temp_dir, self.openapi_dir, 
                         self.relation_dir, self.scene_dir, self.testcase_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def process_url(self, url: str) -> Dict[str, Any]:
        """
        处理URL并生成测试用例
        
        Args:
            url: 要处理的飞书URL
            
        Returns:
            包含处理结果的字典
        """
        try:
            print(f"\n开始处理URL: {url}")
            print("=" * 60)
            
            # 步骤1: 使用feishu_parse.py转换URL并下载JSON
            print("\n步骤1: 转换URL并下载JSON文件")
            api_url, path = transform_feishu_url(url)
            print(f"转换后的API URL: {api_url}")
            print(f"路径: {path}")
            
            # 生成URL的哈希值作为唯一标识
            url_hash = hashlib.md5(url.encode()).hexdigest()
            temp_filename = f"feishu_parse_{int(time.time())}_{url_hash}.json"
            temp_filepath = os.path.join(self.temp_dir, temp_filename)
            
            # 下载JSON文件
            download_json(api_url, temp_filepath)
            print(f"JSON文件已下载到: {temp_filepath}")
            
            # 步骤2: 使用ai.py生成API文档、关联关系和业务场景
            print("\n步骤2: 使用AI生成API文档和场景")
            ai_result = process_url_with_ai(url, self.output_dir)
            
            if not ai_result.get('success', False):
                return {
                    'success': False,
                    'error': ai_result.get('error', '未知错误'),
                    'message': 'AI处理失败'
                }
            
            print("✓ API文档生成完成")
            print(f"  OpenAPI文件: {ai_result.get('openapi_file')}")
            print(f"  关联关系文件: {ai_result.get('relation_file')}")
            print(f"  业务场景文件: {ai_result.get('scene_file')}")
            
            # 步骤3: 使用openapi_to_testcase.py生成测试用例
            print("\n步骤3: 生成测试用例")
            generator = OpenAPIToTestCase()
            
            # 读取OpenAPI数据
            openapi_data = ai_result.get('openapi_data', {})
            
            # 生成测试用例
            testcase_files = generator.generate_from_openapi_data(
                openapi_data, 
                output_dir=self.testcase_dir
            )
            
            print("✓ 测试用例生成完成")
            for file_path in testcase_files:
                print(f"  测试用例文件: {file_path}")
            
            # 返回成功结果
            return {
                'success': True,
                'url': url,
                'url_hash': url_hash,
                'api_url': api_url,
                'path': path,
                'temp_json_file': temp_filepath,
                'openapi_file': ai_result.get('openapi_file'),
                'relation_file': ai_result.get('relation_file'),
                'scene_file': ai_result.get('scene_file'),
                'testcase_files': testcase_files,
                'message': 'URL处理完成，测试用例已生成'
            }
            
        except Exception as e:
            error_msg = f"处理URL时出错: {str(e)}"
            print(f"\n✗ {error_msg}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': error_msg,
                'message': 'URL处理失败'
            }
    
    def batch_process_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理URL列表
        
        Args:
            urls: 要处理的URL列表
            
        Returns:
            包含每个URL处理结果的字典列表
        """
        results = []
        
        print(f"\n开始批量处理 {len(urls)} 个URL")
        print("=" * 60)
        
        for i, url in enumerate(urls, 1):
            print(f"\n处理第 {i}/{len(urls)} 个URL")
            result = self.process_url(url)
            results.append(result)
            
            # 添加分隔符
            if i < len(urls):
                print("\n" + "-" * 60)
        
        # 统计结果
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"\n批量处理完成: {success_count}/{len(urls)} 个URL处理成功")
        
        return results
    
    def create_frontend_api(self, host: str = "127.0.0.1", port: int = 8080):
        """
        创建前端交互API服务
        
        Args:
            host: 服务主机地址
            port: 服务端口
        """
        try:
            from flask import Flask, request, jsonify, render_template_string
            
            app = Flask(__name__)
            
            # 简单的前端界面
            frontend_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>飞书URL测试用例生成器</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #333;
            margin-top: 0;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        textarea {
            width: 100%;
            height: 100px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: monospace;
            resize: vertical;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
        }
        .success {
            background-color: #dff0d8;
            border: 1px solid #d6e9c6;
            color: #3c763d;
        }
        .error {
            background-color: #f2dede;
            border: 1px solid #ebccd1;
            color: #a94442;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>飞书URL测试用例生成器</h1>
        <p>输入飞书API文档URL，自动生成测试用例</p>
        
        <div class="form-group">
            <label for="urls">飞书URL (每行一个):</label>
            <textarea id="urls" placeholder="https://open.feishu.cn/open-apis/docx/v1/documents..."></textarea>
        </div>
        
        <button onclick="processUrls()">生成测试用例</button>
        
        <div class="loading" id="loading">
            <p>正在处理中，请稍候...</p>
        </div>
        
        <div id="result"></div>
    </div>

    <script>
        function processUrls() {
            const urlsTextarea = document.getElementById('urls');
            const resultDiv = document.getElementById('result');
            const loadingDiv = document.getElementById('loading');
            
            const urls = urlsTextarea.value.trim().split('\\n').filter(url => url.trim());
            
            if (urls.length === 0) {
                alert('请输入至少一个URL');
                return;
            }
            
            loadingDiv.style.display = 'block';
            resultDiv.innerHTML = '';
            resultDiv.className = 'result';
            
            fetch('/api/process_urls', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ urls: urls })
            })
            .then(response => response.json())
            .then(data => {
                loadingDiv.style.display = 'none';
                
                if (data.success) {
                    resultDiv.className = 'result success';
                    let resultText = `处理完成: ${data.success_count}/${data.total_count} 个URL处理成功\\n\\n`;
                    
                    data.results.forEach((result, index) => {
                        resultText += `URL ${index + 1}: ${result.url}\\n`;
                        resultText += `状态: ${result.success ? '成功' : '失败'}\\n`;
                        
                        if (result.success) {
                            resultText += `OpenAPI文件: ${result.openapi_file || '无'}\\n`;
                            resultText += `测试用例文件: ${result.testcase_files ? result.testcase_files.join(', ') : '无'}\\n`;
                        } else {
                            resultText += `错误: ${result.error || '未知错误'}\\n`;
                        }
                        
                        resultText += '\\n' + '-'.repeat(50) + '\\n\\n';
                    });
                    
                    resultDiv.textContent = resultText;
                } else {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `处理失败: ${data.error || '未知错误'}`;
                }
            })
            .catch(error => {
                loadingDiv.style.display = 'none';
                resultDiv.className = 'result error';
                resultDiv.textContent = `请求失败: ${error.message}`;
            });
        }
    </script>
</body>
</html>
            """
            
            @app.route('/')
            def index():
                """首页"""
                return render_template_string(frontend_html)
            
            @app.route('/api/process_urls', methods=['POST'])
            def api_process_urls():
                """处理URL的API接口"""
                try:
                    data = request.get_json()
                    urls = data.get('urls', [])
                    
                    if not urls:
                        return jsonify({
                            'success': False,
                            'error': '未提供URL列表'
                        })
                    
                    # 批量处理URL
                    results = self.batch_process_urls(urls)
                    
                    # 统计成功数量
                    success_count = sum(1 for r in results if r.get('success', False))
                    
                    return jsonify({
                        'success': True,
                        'total_count': len(urls),
                        'success_count': success_count,
                        'results': results
                    })
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    })
            
            @app.route('/api/process_url', methods=['POST'])
            def api_process_url():
                """处理单个URL的API接口"""
                try:
                    data = request.get_json()
                    url = data.get('url', '')
                    
                    if not url:
                        return jsonify({
                            'success': False,
                            'error': '未提供URL'
                        })
                    
                    # 处理URL
                    result = self.process_url(url)
                    
                    return jsonify(result)
                    
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': str(e)
                    })
            
            # 启动服务
            print(f"\n启动前端交互服务: http://{host}:{port}")
            print("=" * 60)
            print("使用方法:")
            print("1. 在浏览器中打开上述地址")
            print("2. 输入飞书API文档URL")
            print("3. 点击'生成测试用例'按钮")
            print("4. 等待处理完成并查看结果")
            print("\n按 Ctrl+C 停止服务")
            
            app.run(host=host, port=port, debug=False)
            
        except ImportError:
            print("未安装Flask，无法启动前端交互服务")
            print("请运行: pip install flask")
            return None
        except Exception as e:
            print(f"启动前端服务失败: {str(e)}")
            return None


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='飞书URL测试用例生成器')
    parser.add_argument('--url', help='要处理的单个URL')
    parser.add_argument('--urls', help='包含多个URL的文件路径，每行一个URL')
    parser.add_argument('--output', help='输出目录', default=None)
    parser.add_argument('--server', action='store_true', help='启动前端交互服务')
    parser.add_argument('--host', default='127.0.0.1', help='前端服务主机地址')
    parser.add_argument('--port', type=int, default=8080, help='前端服务端口')
    
    args = parser.parse_args()
    
    # 创建整合工具实例
    integration = UrlToTestCaseIntegration(args.output)
    
    # 启动前端交互服务
    if args.server:
        integration.create_frontend_api(args.host, args.port)
        return
    
    # 处理单个URL
    if args.url:
        result = integration.process_url(args.url)
        if result.get('success', False):
            print("\n处理成功!")
            print(f"OpenAPI文件: {result.get('openapi_file')}")
            print(f"测试用例文件: {', '.join(result.get('testcase_files', []))}")
        else:
            print(f"\n处理失败: {result.get('error')}")
        return
    
    # 处理URL列表文件
    if args.urls:
        try:
            with open(args.urls, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            results = integration.batch_process_urls(urls)
            
            # 输出结果摘要
            success_count = sum(1 for r in results if r.get('success', False))
            print(f"\n处理完成: {success_count}/{len(urls)} 个URL处理成功")
            
            # 保存结果到文件
            results_file = os.path.join(integration.output_dir, "results.json")
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"详细结果已保存到: {results_file}")
            
        except Exception as e:
            print(f"读取URL文件失败: {str(e)}")
        return
    
    # 如果没有提供URL，显示帮助信息
    parser.print_help()


if __name__ == "__main__":
    main()