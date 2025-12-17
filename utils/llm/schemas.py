# utils/llm/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GenerateArgs(BaseModel):
    base_name: str = Field(..., description="接口/操作标识")
    force_regenerate: bool = Field(False, description="是否强制重新生成")
    file_path: str = Field(..., description="传递给内部函数的文件地址变量")
    files: Optional[Dict[str, str]] = Field(default=None, description="相关文件内容，如 openapi.yaml 等")


class ExecuteArgs(BaseModel):
    base_name: Optional[str] = Field(default=None, description="接口/操作标识（可选）")
    file_path: Optional[str] = Field(default=None, description="直接指定测试文件路径（可选）")
    timeout_sec: int = Field(600, description="pytest 执行超时时间（秒）")

class GenExecArgs(BaseModel):
    base_name: str
    force_regenerate: bool = False
    file_path: str = Field(..., description="传递给内部函数的文件地址变量")
    timeout_sec: int = 600
    files: Optional[Dict[str, str]] = None
