"""
环境配置管理器 (ConfigManager)
职责: 加载执行时包含在系统环境与 .env 内的秘钥保护参数，并基于对象流供给外界读取。
"""
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

@dataclass
class EnvironmentVariables:
    """内部映射所有支持的环境变量结构实体声明"""
    corpid: str = ""
    corpsecret: str = ""
    agentid: str = ""
    appid: str = ""
    appsecret: str = ""
    userid: str = ""
    templateid: str = ""
    qweather: str = ""
    city: str = ""
    tian: str = ""
    targetname: str = ""
    targetday: str = ""
    beginname: str = ""
    beginday: str = ""
    msgtype: str = "1"
    pic: str = ""
    pictype: str = ""
    title: str = ""
    content: str = ""
    call: str = ""
    link: str = ""

class ConfigManager:
    """配置读取与访问管理单例类"""
    
    def __init__(self) -> None:
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(dotenv_path)
        self.settings = EnvironmentVariables()
        
    def _read_env(self, key: str, default: str) -> str:
        val = os.getenv(key.upper())
        if val is None:
            val = os.getenv(key.lower())
        return val if val is not None else default

    def get(self, key: str) -> str:
        """获取映射到的字符串属性配置"""
        default_val = getattr(self.settings, key.lower(), "")
        return self._read_env(key, str(default_val))
        
    def get_list(self, key: str) -> List[str]:
        """将环境变量按照 && 分割为 Python 纯净的列表格式暴露出去"""
        raw_val = self.get(key)
        return [item for item in raw_val.split("&&") if item.strip()] if raw_val else []

# 对外暴露唯一配置管理单例
config = ConfigManager()
