#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从OpenAPI数据生成测试用例的独立工具
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from utils.read_files_tools.swagger_for_yaml import SwaggerForYaml
    from utils.read_files_tools.case_automatic_control import TestCaseAutomaticGeneration
except ImportError:
    try:
        from read_files_tools.swagger_for_yaml import SwaggerForYaml
        from read_files_tools.case_automatic_control import TestCaseAutomaticGeneration
    except ImportError:
        print("无法导入必要的模块，请检查项目结构")
        sys.exit(1)


class OpenAPIToTestCase:
    """从OpenAPI数据生成测试用例的类"""
    
    def __init__(self):
        """初始化OpenAPI测试用例生成器"""
        pass
    
    def generate_from_openapi_data(self, openapi_data: Dict[str, Any], output_dir: Optional[str] = None) -> List[str]:
        """
        从OpenAPI数据生成测试用例
        
        Args:
            openapi_data: OpenAPI格式的数据
            output_dir: 输出目录，如果为None则使用默认目录
            
        Returns:
            生成的测试用例文件路径列表
        """
        # 如果未指定输出目录，使用默认目录
        if output_dir is None:
            output_dir = "interfacetest"
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建临时文件存储OpenAPI数据
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_file:
            yaml.dump(openapi_data, temp_file, default_flow_style=False, allow_unicode=True)
            temp_path = temp_file.name
        
        try:
            # 使用临时文件路径初始化SwaggerForYaml
            swagger = SwaggerForYaml(Path(temp_path))
            
            # 设置输出文件路径
            yaml_out = Path(output_dir) / "test_cases.yaml"
            
            # 生成YAML测试用例
            swagger.write_yaml_handler()
            
            # 生成pytest测试用例
            generator = TestCaseAutomaticGeneration()
            generator.get_case_automatic()
            
            # 返回生成的文件路径
            return [str(yaml_out)]
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def generate_from_openapi_file(self, openapi_file: str, output_dir: Optional[str] = None) -> List[str]:
        """
        从OpenAPI文件生成测试用例
        
        Args:
            openapi_file: OpenAPI文件路径
            output_dir: 输出目录，如果为None则使用默认目录
            
        Returns:
            生成的测试用例文件路径列表
        """
        # 读取OpenAPI文件
        with open(openapi_file, 'r', encoding='utf-8') as f:
            openapi_data = yaml.safe_load(f)
        
        # 生成测试用例
        return self.generate_from_openapi_data(openapi_data, output_dir)


def main():
    """主函数，用于命令行调用"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='从OpenAPI数据生成测试用例')
    parser.add_argument('--file', help='OpenAPI文件路径')
    parser.add_argument('--output', help='输出目录', default='interfacetest')
    
    args = parser.parse_args()
    
    if not args.file:
        print("请提供OpenAPI文件路径")
        parser.print_help()
        return
    
    # 创建测试用例生成器
    generator = OpenAPIToTestCase()
    
    # 生成测试用例
    try:
        output_files = generator.generate_from_openapi_file(args.file, args.output)
        print(f"测试用例生成成功，输出文件: {output_files}")
    except Exception as e:
        print(f"生成测试用例失败: {e}")


if __name__ == "__main__":
    main()