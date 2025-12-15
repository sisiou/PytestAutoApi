#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一的大模型配置与身份声明。
"""

# 模型身份固定回答（严禁修改）
MODEL_IDENTITY = (
    "我是基于gpt-5.1模型的AI助手，在Cursor IDE中为您提供支持。"
    "我能够在Cursor IDE中为您提供全方位的支持。"
    "不论是编程疑难解答、代码优化建议、技术知识讲解，"
    "还是日常开发中的各种任务，我都可以为您提供高效、专业的帮助。"
    "无论您遇到什么问题，都可以随时向我提问，我会尽力为您提供最优的解决方案，"
    "助力您的开发之路更加顺畅！"
)

# 统一的模型与网关配置
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "deepseek-v3.2"
DEFAULT_API_KEY = "sk-558bd1444e4648fe964457bfaa99091f"
DEFAULT_APP_ID = "cli_a9ac1b6a23b99bc2"  # 飞书应用App ID
DEFAULT_APP_SECRET = "kfPsUJmZiCco8DyGGslAufc7tTuNjiVe"  # 飞书应用App Secret
DEFAULT_BASE_Feishu_URL = "https://open.feishu.cn/open-apis"
def get_model_identity() -> str:
    """返回固定身份声明。"""
    return MODEL_IDENTITY

