#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询 Redis 中的 image_key
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from utils.cache_process.redis_control import RedisHandler
    
    def check_image_key():
        """查询 Redis 中的 image_key"""
        try:
            redis_handler = RedisHandler()
            
            # 查询 image_key
            image_key = redis_handler.get_key("image_key")
            
            if image_key:
                print(f"[OK] 找到 image_key: {image_key}")
                return image_key
            else:
                print("[FAIL] Redis 中未找到 image_key")
                return None
                
        except Exception as e:
            print(f"[ERROR] 查询 Redis 失败: {e}")
            print("\n提示：")
            print("1. 请确保 Redis 服务已启动")
            print("2. 检查 Redis 配置（默认: 127.0.0.1:6379）")
            return None
    
    def list_all_keys():
        """列出 Redis 中所有的 key"""
        try:
            redis_handler = RedisHandler()
            keys = redis_handler.redis.keys("*")
            
            if keys:
                print(f"\nRedis 中所有 key (共 {len(keys)} 个):")
                print("-" * 50)
                for key in keys:
                    value = redis_handler.get_key(key)
                    print(f"  {key}: {value}")
            else:
                print("\nRedis 中没有任何 key")
                
        except Exception as e:
            print(f"✗ 查询 Redis 失败: {e}")
    
    if __name__ == "__main__":
        import argparse
        
        parser = argparse.ArgumentParser(description="查询 Redis 中的 image_key")
        parser.add_argument("-a", "--all", action="store_true", help="列出所有 key")
        parser.add_argument("-k", "--key", type=str, help="查询指定的 key")
        
        args = parser.parse_args()
        
        if args.all:
            list_all_keys()
        elif args.key:
            try:
                redis_handler = RedisHandler()
                value = redis_handler.get_key(args.key)
                if value:
                    print(f"[OK] {args.key} = {value}")
                else:
                    print(f"[FAIL] Redis 中未找到 key: {args.key}")
            except Exception as e:
                print(f"[ERROR] 查询失败: {e}")
        else:
            check_image_key()
            
except ImportError as e:
    print(f"[ERROR] 导入模块失败: {e}")
    print("请确保已安装 redis 依赖: pip install redis")

