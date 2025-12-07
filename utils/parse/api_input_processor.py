"""
统一的API输入处理器
支持飞书URL、JSON文件和直接OpenAPI文档输入
"""

import os
import json
import yaml
import requests
from urllib.parse import quote
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

# 导入现有的feishu_parse和ai模块
from feishu_parse import transform_feishu_url, download_json
from ai import (
    generate_openapi_yaml, 
    generate_api_relation_file, 
    generate_business_scene_file,
    generate_file_fingerprint,
    get_output_path,
    should_regenerate
)


class APIInputProcessor:
    """统一的API输入处理器"""
    
    def __init__(self, output_dir: str = "../../openApi"):
        """
        初始化API输入处理器
        
        Args:
            output_dir: 输出目录，默认为../../openApi
        """
        self.output_dir = output_dir
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process_feishu_url(self, feishu_url: str) -> Tuple[str, str]:
        """
        处理飞书URL，下载并保存API JSON
        
        Args:
            feishu_url: 飞书文档URL
            
        Returns:
            Tuple[str, str]: (保存的JSON文件路径, 文档路径)
        """
        # 转换URL并获取路径
        api_url, path = transform_feishu_url(feishu_url)
        print(f"原始URL: {feishu_url}")
        print(f"转换后的API URL: {api_url}")
        
        # 生成文件名：将路径中的 / 替换为 _
        # 保存到api目录下
        api_dir = os.path.join(os.path.dirname(__file__), '../../api')
        os.makedirs(api_dir, exist_ok=True)
        filename = os.path.join(api_dir, path.replace('/', '_') + '.json')
        print(f"生成的文件名: {filename}")
        
        # 下载JSON并保存
        data = download_json(api_url, filename)
        if not data:
            raise Exception(f"从飞书URL下载JSON失败: {feishu_url}")
            
        return filename, path
    
    def process_json_file(self, json_file_path: str) -> str:
        """
        处理JSON文件，验证格式并返回路径
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            str: 验证后的JSON文件路径
        """
        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON文件不存在: {json_file_path}")
            
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"JSON文件验证成功: {json_file_path}")
            return json_file_path
        except json.JSONDecodeError as e:
            raise Exception(f"JSON文件格式错误: {e}")
    
    def process_openapi_document(self, openapi_content: str, save_path: Optional[str] = None) -> str:
        """
        处理OpenAPI文档内容，保存为文件
        
        Args:
            openapi_content: OpenAPI文档内容（YAML或JSON格式）
            save_path: 可选的保存路径，如果不提供则自动生成
            
        Returns:
            str: 保存的OpenAPI文件路径
        """
        if not save_path:
            # 生成唯一文件名
            import hashlib
            content_hash = hashlib.md5(openapi_content.encode()).hexdigest()[:8]
            save_path = os.path.join(self.output_dir, f"direct_openapi_{content_hash}.yaml")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 验证内容格式并保存
        try:
            # 尝试解析为YAML
            yaml.safe_load(openapi_content)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(openapi_content)
        except yaml.YAMLError:
            try:
                # 尝试解析为JSON
                json.loads(openapi_content)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(openapi_content)
            except json.JSONDecodeError:
                raise Exception("OpenAPI文档格式错误，既不是有效的YAML也不是有效的JSON")
        
        print(f"OpenAPI文档已保存: {save_path}")
        return save_path
    
    def process_business_scenes(self, scenes_content: str, save_path: Optional[str] = None) -> str:
        """
        处理业务场景内容，验证并保存为文件
        
        Args:
            scenes_content: 业务场景内容（JSON格式）
            save_path: 可选的保存路径，如果不提供则自动生成
            
        Returns:
            str: 保存的业务场景文件路径
        """
        if not save_path:
            # 生成唯一文件名
            import hashlib
            content_hash = hashlib.md5(scenes_content.encode()).hexdigest()[:8]
            save_path = os.path.join(self.output_dir, f"direct_business_scene_{content_hash}.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 验证内容格式并保存
        try:
            scenes_data = json.loads(scenes_content)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(scenes_data, f, ensure_ascii=False, indent=2)
            print(f"业务场景文件已保存: {save_path}")
            return save_path
        except json.JSONDecodeError as e:
            raise Exception(f"业务场景JSON格式错误: {e}")
    
    def process_api_relations(self, relations_content: str, save_path: Optional[str] = None) -> str:
        """
        处理接口关联关系内容，验证并保存为文件
        
        Args:
            relations_content: 接口关联关系内容（JSON格式）
            save_path: 可选的保存路径，如果不提供则自动生成
            
        Returns:
            str: 保存的接口关联关系文件路径
        """
        if not save_path:
            # 生成唯一文件名
            import hashlib
            content_hash = hashlib.md5(relations_content.encode()).hexdigest()[:8]
            save_path = os.path.join(self.output_dir, f"direct_api_relation_{content_hash}.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 验证内容格式并保存
        try:
            relations_data = json.loads(relations_content)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(relations_data, f, ensure_ascii=False, indent=2)
            print(f"接口关联关系文件已保存: {save_path}")
            return save_path
        except json.JSONDecodeError as e:
            raise Exception(f"接口关联关系JSON格式错误: {e}")
    
    def generate_from_json_files(self, json_paths: List[str]) -> Dict[str, str]:
        """
        从JSON文件生成OpenAPI文档、接口关联关系和业务场景
        
        Args:
            json_paths: JSON文件路径列表
            
        Returns:
            Dict[str, str]: 生成的文件路径映射
        """
        # 验证所有JSON文件
        validated_paths = []
        for path in json_paths:
            validated_paths.append(self.process_json_file(path))
        
        # 生成指纹
        fingerprint = generate_file_fingerprint(validated_paths)
        
        # 定义输出路径
        openapi_output_path = get_output_path(validated_paths, fingerprint, self.output_dir, "openapi")
        relation_output_path = get_output_path(validated_paths, fingerprint, self.output_dir, "api_relation")
        scene_output_path = get_output_path(validated_paths, fingerprint, self.output_dir, "business_scene")
        
        result = {
            "openapi": openapi_output_path,
            "api_relation": relation_output_path,
            "business_scene": scene_output_path
        }
        
        # 生成OpenAPI YAML文件
        if should_regenerate(validated_paths, openapi_output_path):
            try:
                generate_openapi_yaml(validated_paths, openapi_output_path)
            except Exception as e:
                print(f"生成OpenAPI文件失败：{str(e)}")
                result["openapi"] = None
        else:
            print("跳过OpenAPI文件生成，使用现有文件")
        
        # 生成接口关联关系文件
        if should_regenerate(validated_paths, relation_output_path):
            try:
                generate_api_relation_file(validated_paths, relation_output_path)
            except Exception as e:
                print(f"生成接口关联关系文件失败：{str(e)}")
                result["api_relation"] = None
        else:
            print("跳过接口关联关系文件生成，使用现有文件")
        
        # 生成业务场景文件
        if should_regenerate(validated_paths, scene_output_path):
            try:
                generate_business_scene_file(validated_paths, scene_output_path)
            except Exception as e:
                print(f"生成业务场景文件失败：{str(e)}")
                result["business_scene"] = None
        else:
            print("跳过业务场景文件生成，使用现有文件")
        
        return result
    
    def process_feishu_url_and_generate(self, feishu_url: str) -> Dict[str, str]:
        """
        处理飞书URL并生成OpenAPI文档、接口关联关系和业务场景
        
        Args:
            feishu_url: 飞书文档URL
            
        Returns:
            Dict[str, str]: 生成的文件路径映射
        """
        # 处理飞书URL，下载JSON
        json_file_path, _ = self.process_feishu_url(feishu_url)
        
        # 从JSON文件生成
        return self.generate_from_json_files([json_file_path])
    
    def process_input(self, 
                     feishu_url: Optional[str] = None,
                     json_files: Optional[List[str]] = None,
                     openapi_doc: Optional[str] = None,
                     business_scenes: Optional[str] = None,
                     api_relations: Optional[str] = None) -> Dict[str, str]:
        """
        统一处理各种输入
        
        Args:
            feishu_url: 飞书URL
            json_files: JSON文件路径列表
            openapi_doc: OpenAPI文档内容
            business_scenes: 业务场景内容
            api_relations: 接口关联关系内容
            
        Returns:
            Dict[str, str]: 生成的文件路径映射
        """
        result = {
            "openapi": None,
            "api_relation": None,
            "business_scene": None
        }
        
        # 处理飞书URL
        if feishu_url:
            print(f"处理飞书URL: {feishu_url}")
            feishu_result = self.process_feishu_url_and_generate(feishu_url)
            # 只更新非None的值
            for key, value in feishu_result.items():
                if value is not None:
                    result[key] = value
            return result
        
        # 处理JSON文件
        if json_files:
            print(f"处理JSON文件: {json_files}")
            json_result = self.generate_from_json_files(json_files)
            # 只更新非None的值
            for key, value in json_result.items():
                if value is not None:
                    result[key] = value
            return result
        
        # 处理直接输入的OpenAPI文档
        if openapi_doc:
            print("处理直接输入的OpenAPI文档")
            result["openapi"] = self.process_openapi_document(openapi_doc)
        
        # 处理直接输入的业务场景
        if business_scenes:
            print("处理直接输入的业务场景")
            result["business_scene"] = self.process_business_scenes(business_scenes)
        
        # 处理直接输入的接口关联关系
        if api_relations:
            print("处理直接输入的接口关联关系")
            result["api_relation"] = self.process_api_relations(api_relations)
        
        return result


# 使用示例
if __name__ == "__main__":
    processor = APIInputProcessor()
    
    # 示例1: 处理飞书URL
    # feishu_url = "https://open.feishu.cn/document/server-docs/contact-v3/user/create"
    # result = processor.process_input(feishu_url=feishu_url)
    # print("处理结果:", result)
    
    # 示例2: 处理JSON文件
    # json_files = ["../../api/server-docs_im-v1_message_create.json"]
    # result = processor.process_input(json_files=json_files)
    # print("处理结果:", result)
    
    # 示例3: 处理直接输入的OpenAPI文档
    # openapi_doc = """
    # openapi: 3.0.0
    # info:
    #   title: 示例API
    #   version: 1.0.0
    # paths:
    #   /hello:
    #     get:
    #       summary: 获取问候
    #       responses:
    #         '200':
    #           description: 成功响应
    # """
    # result = processor.process_input(openapi_doc=openapi_doc)
    # print("处理结果:", result)