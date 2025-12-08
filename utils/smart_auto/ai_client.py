"""
AI客户端模块，用于与大语言模型交互
"""
import os
import json
import yaml
from openai import OpenAI
from typing import Optional, Dict, Any
from utils.logging_tool.log_control import INFO, ERROR


class AIClient:
    """AI客户端，用于与大语言模型交互"""
    
    def __init__(self, config_path: str = None):
        """
        初始化AI客户端
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, "configs", "config.yaml")
        
        self.config = self._load_config(config_path)
        
        # 初始化OpenAI客户端（使用硅基流动API）
        ai_config = self.config.get("ai_config", {})
        self.client = OpenAI(
            api_key=ai_config.get("api_key", os.getenv("SILICONFLOW_API_KEY")),
            base_url=ai_config.get("base_url", "https://api.siliconflow.cn/v1")
        )
        
        # 默认模型
        self.model = ai_config.get("model_name", "Qwen/Qwen2.5-7B-Instruct")
        
        INFO.logger.info("AI客户端初始化完成")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            INFO.logger.info(f"成功加载配置文件: {config_path}")
            return config
        except Exception as e:
            ERROR.logger.error(f"加载配置文件失败: {str(e)}")
            return {}
    
    def generate_text(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, max_tokens: int = 4096) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数，控制随机性
            max_tokens: 最大令牌数
            
        Returns:
            生成的文本
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = completion.choices[0].message.content.strip()
            # 清洗多余标记
            content = content.replace("```json", "").replace("```yaml", "").replace("```", "").strip()
            return content
            
        except Exception as e:
            ERROR.logger.error(f"调用AI API错误：{e}")
            return None
    
    def generate_json(self, prompt: str, system_prompt: str = None, temperature: float = 0.1, max_tokens: int = 4096) -> Optional[Dict[str, Any]]:
        """
        生成JSON格式的响应
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数，控制随机性
            max_tokens: 最大令牌数
            
        Returns:
            解析后的JSON字典
        """
        try:
            # 添加JSON格式要求到系统提示
            if system_prompt:
                system_prompt += "\n\n请以JSON格式返回结果，不要包含任何其他文本或代码块标记。"
            else:
                system_prompt = "请以JSON格式返回结果，不要包含任何其他文本或代码块标记。"
            
            content = self.generate_text(prompt, system_prompt, temperature, max_tokens)
            if not content:
                return None
                
            # 尝试解析JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    return json.loads(json_str)
                else:
                    ERROR.logger.error(f"无法从响应中提取JSON: {content}")
                    return None
                    
        except Exception as e:
            ERROR.logger.error(f"生成JSON错误：{e}")
            return None