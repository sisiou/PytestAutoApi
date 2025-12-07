"""
AI解析器模块

提供与AI服务交互的客户端，用于生成测试场景和测试用例。
"""

import os
import json
import yaml
import re
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Optional

# 加载环境变量
load_dotenv()
# 使用硅基流动API
API_KEY = os.getenv("API_KEY") or os.getenv("SILICONFLOW_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.siliconflow.cn/v1")
API_MODEL = os.getenv("API_MODEL", "Qwen/Qwen2.5-7B-Instruct")


class AIClient:
    """AI客户端，用于生成测试场景和测试用例"""
    
    def __init__(self):
        """初始化AI客户端"""
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本，如果失败则返回None
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            completion = self.client.chat.completions.create(
                model=API_MODEL,
                messages=messages,
                temperature=0.1,  # 低温度保证输出稳定
                max_tokens=4096
            )

            content = completion.choices[0].message.content.strip()
            # 清洗多余标记
            content = content.replace("```json", "").replace("```yaml", "").replace("```", "").strip()
            return content

        except Exception as e:
            print(f"调用AI API错误：{e}")
            return None