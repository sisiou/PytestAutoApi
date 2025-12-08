"""
飞书API配置管理工具
"""
import os
import yaml
import logging

logger = logging.getLogger(__name__)

class FeishuConfig:
    """飞书配置管理类"""
    
    def __init__(self, config_path=None):
        """
        初始化配置
        :param config_path: 配置文件路径，默认为项目根目录下的config/feishu_config.yaml
        """
        if config_path is None:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config", "feishu_config.yaml")
        
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def get_app_id(self):
        """获取App ID"""
        return self.config.get('feishu', {}).get('app_id', '')
    
    def get_app_secret(self):
        """获取App Secret"""
        return self.config.get('feishu', {}).get('app_secret', '')
    
    def get_authorization(self):
        """获取Authorization令牌"""
        return self.config.get('feishu', {}).get('authorization', '')
    
    def get_base_url(self):
        """获取API基础URL"""
        return self.config.get('api', {}).get('base_url', 'https://open.feishu.cn/open-apis')
    
    def get_timeout(self):
        """获取请求超时时间"""
        return self.config.get('api', {}).get('timeout', 30)
    
    def get_default_receive_id_type(self):
        """获取默认接收者ID类型"""
        return self.config.get('test', {}).get('default_receive_id_type', 'open_id')
    
    def get_default_receive_id(self):
        """获取默认接收者ID"""
        return self.config.get('test', {}).get('default_receive_id', 'ou_xxx')
    
    def get_headers(self):
        """获取默认请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_authorization()}"
        }
    
    def reload(self):
        """重新加载配置文件"""
        self.config = self._load_config()

# 创建全局配置实例
feishu_config = FeishuConfig()