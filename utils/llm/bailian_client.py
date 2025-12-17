# utils/llm/bailian_client.py
from __future__ import annotations

from typing import Optional
from openai import OpenAI

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()
ACCESS_KEY = os.getenv("DASHSCOPE_API_KEY")
BAILIAN_API_URL = os.getenv("BAILIAN_API_URL")
BAILIAN_MODEL = os.getenv("BAILIAN_MODEL")

def call_bailian_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    ACCESS_KEY: str,
    BAILIAN_API_URL: str,
    BAILIAN_MODEL: str,
) -> Optional[str]:
    """调用阿里云百炼API，通用封装（保留你原实现，便于工具内部直接用）"""
    try:
        client = OpenAI(api_key=ACCESS_KEY, base_url=BAILIAN_API_URL)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=BAILIAN_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=4096,
        )
        content = completion.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```yaml", "").replace("```", "").strip()
        return content
    except Exception as e:
        print(f"调用百炼API错误：{e}")
        print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
        return None


def build_bailian_chat_llm(
    *,
    ACCESS_KEY: str,
    BAILIAN_API_URL: str,
    BAILIAN_MODEL: str,
):
    """
    LangChain Tool Calling 需要可解析 tool_calls 的 ChatModel。
    百炼是 OpenAI compatible，因此直接用 ChatOpenAI。
    """
    return ChatOpenAI(
        api_key=ACCESS_KEY,
        base_url=BAILIAN_API_URL,
        model=BAILIAN_MODEL,
        temperature=0.1,
        max_tokens=4096,
    )
