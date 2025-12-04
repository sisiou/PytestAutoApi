#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书 API 错误码映射表

用于将飞书接口返回的错误码转换为友好的错误信息，便于测试时快速定位问题。
"""
from typing import Tuple

# 飞书错误码映射表
# 格式: {错误码: {"http_status": HTTP状态码, "description": "错误描述", "suggestion": "排查建议"}}
FEISHU_ERROR_CODES = {
    20001: {
        "http_status": 400,
        "description": "必要参数缺失",
        "suggestion": "请检查请求时传入的参数是否有误"
    },
    20002: {
        "http_status": 400,
        "description": "应用认证失败",
        "suggestion": "请检查提供的 client_id 与 client_secret 是否正确"
    },
    20003: {
        "http_status": 400,
        "description": "无效的授权码",
        "suggestion": "请检查授权码是否有效，注意授权码仅能使用一次"
    },
    20004: {
        "http_status": 400,
        "description": "授权码已经过期",
        "suggestion": "请在授权码生成后的 5 分钟内使用"
    },
    20005: {
        "http_status": 400,
        "description": "无效的访问令牌",
        "suggestion": "请检查 access_token 是否有效，是否已过期或被撤销"
    },
    20008: {
        "http_status": 400,
        "description": "用户不存在",
        "suggestion": "请检查发起授权的用户的当前状态"
    },
    20009: {
        "http_status": 400,
        "description": "租户未安装应用",
        "suggestion": "请检查应用状态"
    },
    20010: {
        "http_status": 400,
        "description": "用户无应用使用权限",
        "suggestion": "请检查发起授权的用户是否仍具有应用使用权限"
    },
    20024: {
        "http_status": 400,
        "description": "提供的授权码与 client_id 不匹配",
        "suggestion": "请勿混用不同应用的凭证"
    },
    20036: {
        "http_status": 400,
        "description": "无效的 grant_type",
        "suggestion": "请检查请求体中 grant_type 字段的取值"
    },
    20048: {
        "http_status": 400,
        "description": "应用不存在",
        "suggestion": "请检查应用状态"
    },
    20049: {
        "http_status": 400,
        "description": "PKCE 校验失败",
        "suggestion": "请检查请求体中 code_verifier 字段是否存在且有效"
    },
    20050: {
        "http_status": 500,
        "description": "内部服务错误",
        "suggestion": "请稍后重试，如果持续报错请联系技术支持"
    },
    20063: {
        "http_status": 400,
        "description": "请求格式错误",
        "suggestion": "请求体中缺少必要字段，请根据具体的错误信息补齐字段"
    },
    20065: {
        "http_status": 400,
        "description": "授权码已被使用",
        "suggestion": "授权码仅能使用一次，请检查是否有被重复使用"
    },
    20066: {
        "http_status": 400,
        "description": "用户状态非法",
        "suggestion": "请检查发起授权的用户的当前状态"
    },
    20067: {
        "http_status": 400,
        "description": "无效的 scope 列表（存在重复项）",
        "suggestion": "请确保传入的 scope 列表中没有重复项"
    },
    20068: {
        "http_status": 400,
        "description": "无效的 scope 列表（包含未授权权限）",
        "suggestion": "当前接口 scope 参数传入的权限必须是获取授权码时 scope 参数值的子集"
    },
    20069: {
        "http_status": 400,
        "description": "应用未启用",
        "suggestion": "请检查应用状态"
    },
    20070: {
        "http_status": 400,
        "description": "同时使用了多种身份验证方式",
        "suggestion": "请求时同时使用了 Basic Authentication 和 client_secret 两种身份验证方式。请仅使用 client_id、client_secret 身份验证方式调用本接口"
    },
    20071: {
        "http_status": 400,
        "description": "无效的 redirect_uri",
        "suggestion": "请确保 redirect_uri 与获取授权码时传入的 redirect_uri 保持一致"
    },
    20072: {
        "http_status": 503,
        "description": "服务暂不可用",
        "suggestion": "请稍后重试"
    },
}


def get_error_message(error_code: int, response_msg: str = None) -> str:
    """
    根据错误码获取友好的错误信息

    Args:
        error_code: 飞书返回的错误码
        response_msg: 飞书返回的原始错误消息（可选）

    Returns:
        格式化的错误信息字符串
    """
    error_info = FEISHU_ERROR_CODES.get(error_code)
    
    if error_info:
        message = f"[错误码 {error_code}] {error_info['description']}"
        if error_info['suggestion']:
            message += f"\n排查建议: {error_info['suggestion']}"
        if response_msg:
            message += f"\n原始错误信息: {response_msg}"
        return message
    else:
        # 未知错误码，返回通用信息
        base_msg = f"[错误码 {error_code}] 未知错误"
        if response_msg:
            base_msg += f"\n原始错误信息: {response_msg}"
        return base_msg


def check_feishu_error(response_data: dict) -> Tuple[bool, str]:
    """
    检查飞书接口响应是否包含错误码

    Args:
        response_data: 飞书接口返回的响应数据（字典格式）

    Returns:
        (is_error, error_message) 元组
        - is_error: True 表示有错误，False 表示成功
        - error_message: 错误信息（如果有错误）
    """
    # 飞书接口成功时，code 字段为 0
    code = response_data.get("code", 0)
    
    if code == 0:
        return False, ""
    
    # 有错误码，获取错误信息
    msg = response_data.get("msg", "")
    error_message = get_error_message(code, msg)
    return True, error_message

