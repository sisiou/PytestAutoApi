"""
飞书配置模块
提供飞书API相关的配置信息
"""

import os
import time
import requests
from typing import Dict, Any, Optional


class FeishuConfig:
    """飞书配置类"""
    
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self.tenant_access_token = os.getenv("FEISHU_TENANT_ACCESS_TOKEN", "")
        self.base_url = os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn")
        
        # 令牌缓存相关
        self.token_cache = None
        self.token_expire_time = 0
        self.feishu_api_timeout = 10
        
    def get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token，支持自动刷新"""
        if requests is None:
            print("[ERROR] 错误: 需要安装 requests 库才能获取 token")
            return None
        
        # 检查缓存
        current_time = time.time()
        if self.token_cache and current_time < self.token_expire_time:
            return self.token_cache
        
        # 如果没有配置app_id和app_secret，尝试使用环境变量中的token
        if not self.app_id or not self.app_secret:
            if self.tenant_access_token:
                return self.tenant_access_token
            print("[ERROR] 未配置FEISHU_APP_ID和FEISHU_APP_SECRET")
            return None
        
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.feishu_api_timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                token = data.get("tenant_access_token")
                expire = data.get("expire", 0)
                # 缓存token（提前5分钟过期）
                self.token_cache = token
                self.token_expire_time = current_time + expire - 300
                print(f"[OK] 成功获取 tenant_access_token (过期时间: {expire} 秒)")
                return token
            print(f"[ERROR] 获取 token 失败: code={data.get('code')} msg={data.get('msg')}")
            return None
        except Exception as exc:
            print(f"[ERROR] 获取 token 出错: {exc}")
            return None
    
    def get_authorization(self) -> str:
        """获取授权头，支持自动刷新令牌"""
        token = self.get_tenant_access_token()
        if token:
            return f"Bearer {token}"
        return ""
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "tenant_access_token": self.tenant_access_token,
            "base_url": self.base_url
        }
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.app_id and self.app_secret)


# 全局配置实例
feishu_config = FeishuConfig()