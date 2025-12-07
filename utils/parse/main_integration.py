"""
主集成脚本
整合API输入处理器和测试用例生成器，提供统一的命令行接口
"""

import os
import sys
import argparse
import json
from typing import Dict, List, Optional, Union

# 导入自定义模块
from api_input_processor import APIInputProcessor
from test_case_generator import TestCaseGenerator


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='API测试用例生成工具')
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 处理飞书URL命令
    feishu_parser = subparsers.add_parser('feishu', help='处理飞书URL并生成测试用例')
    feishu_parser.add_argument('url', help='飞书文档URL')
    feishu_parser.add_argument('-o', '--output', help='输出目录', default='../../test_cases')
    feishu_parser.add_argument('--ai', action='store_true', help='使用AI生成测试用例')
    
    # 处理JSON文件命令
    json_parser = subparsers.add_parser('json', help='处理JSON文件并生成测试用例')
    json_parser.add_argument('files', nargs='+', help='JSON文件路径列表')
    json_parser.add_argument('-o', '--output', help='输出目录', default='../../test_cases')
    json_parser.add_argument('--ai', action='store_true', help='使用AI生成测试用例')
    
    # 处理OpenAPI文档命令
    openapi_parser = subparsers.add_parser('openapi', help='处理OpenAPI文档并生成测试用例')
    openapi_parser.add_argument('file', help='OpenAPI文档文件路径')
    openapi_parser.add_argument('-s', '--scenes', help='业务场景文件路径（可选）')
    openapi_parser.add_argument('-r', '--relations', help='接口关联关系文件路径（可选）')
    openapi_parser.add_argument('-o', '--output', help='输出目录', default='../../test_cases')
    openapi_parser.add_argument('--ai', action='store_true', help='使用AI生成测试用例')
    
    # 启动前端服务命令
    frontend_parser = subparsers.add_parser('frontend', help='启动前端服务')
    frontend_parser.add_argument('-H', '--host', default='127.0.0.1', help='主机地址')
    frontend_parser.add_argument('-p', '--port', type=int, default=5000, help='端口号')
    frontend_parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果没有提供命令，显示帮助信息
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 处理飞书URL
        if args.command == 'feishu':
            print(f"处理飞书URL: {args.url}")
            processor = APIInputProcessor()
            result = processor.process_input(feishu_url=args.url)
            
            if result.get('openapi'):
                generator = TestCaseGenerator(args.output)
                use_ai = getattr(args, 'ai', False)
                output_path = generator.generate_all_test_cases(
                    result['openapi'],
                    result.get('business_scene'),
                    result.get('api_relation'),
                    use_ai_generator=use_ai
                )
                print(f"测试用例已生成: {output_path}")
            else:
                print("未能生成OpenAPI文档，无法生成测试用例")
        
        # 处理JSON文件
        elif args.command == 'json':
            print(f"处理JSON文件: {args.files}")
            processor = APIInputProcessor()
            result = processor.process_input(json_files=args.files)
            
            if result.get('openapi'):
                generator = TestCaseGenerator(args.output)
                use_ai = getattr(args, 'ai', False)
                output_path = generator.generate_all_test_cases(
                    result['openapi'],
                    result.get('business_scene'),
                    result.get('api_relation'),
                    use_ai_generator=use_ai
                )
                print(f"测试用例已生成: {output_path}")
            else:
                print("未能生成OpenAPI文档，无法生成测试用例")
        
        # 处理OpenAPI文档
        elif args.command == 'openapi':
            print(f"处理OpenAPI文档: {args.file}")
            generator = TestCaseGenerator(args.output)
            use_ai = getattr(args, 'ai', False)
            output_path = generator.generate_all_test_cases(
                args.file,
                args.scenes,
                args.relations,
                use_ai_generator=use_ai
            )
            print(f"测试用例已生成: {output_path}")
        
        # 启动前端服务
        elif args.command == 'frontend':
            print(f"启动前端服务: http://{args.host}:{args.port}")
            from api_frontend import APIFrontend
            frontend = APIFrontend()
            frontend.run(host=args.host, port=args.port, debug=args.debug)
    
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()