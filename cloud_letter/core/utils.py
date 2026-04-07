"""
核心连接网络工具模块 (Network Utilities)
提供统一的带重试机制的隔离网络会话管理与全局日志构建体系。
"""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 初始化基础日志实例，供全局继承
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(name)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("cloud_letter")

def get_session() -> requests.Session:
    """配置并生成带有网络重试和衰减退避机制的 Session，以确保 API 调用高可用性。
    
    Returns:
        requests.Session: 已经注入重试拦截器的连接实例。
    """
    session = requests.Session()
    # 当服务端遇到瞬时负载压力抛出 5xx 时允许重试。
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
