"""
Cloud Letter (云笺) - 引擎主入口主循环 (Application Entry)
基于 OOP 调度重做了所有的模块后，这也是唯一暴露给 Serverless 机器或操作系统计划任务的干净切面。
"""
import warnings
from typing import Dict, Any

# 忽略底层字符编码包可能缺乏而引发的红字报警信息，以保持云端控制台净化
warnings.filterwarnings("ignore", message=".*Unable to find acceptable character detection dependency.*")

from cloud_letter.notifiers import sender
from cloud_letter.core import builder

class CloudLetterApp:
    """系统调度代理包装类，用于解析外界环境传来的命令并路由给底层服务族"""
    
    @staticmethod
    def render_web_view(event: dict) -> dict:
        """解析 API 网关路由发送过来的独立邮件详情 Web 查看请求"""
        show_data = event.get("queryString")
        if not show_data:
            return {}
            
        show_html = builder.handle_html(show_data)
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8"},
            "body": show_html
        }

    @staticmethod
    def run_push_task() -> dict:
        """总任务下发执行钩子，驱动整个图文抓取到分发的完整生命周期"""
        res = sender.send_msg()
        status_code = 200 if res.get("code") else 404
        return {
            "isBase64Encoded": False,
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": res
        }

# =================云厂商/容器化运行触发器声明=================

def main_handler(event: dict, context: dict) -> dict:
    """对接腾讯云等提供 event 与 context 上下文注入机制的框架触发点"""
    if event and event.get("queryString"):
        return CloudLetterApp.render_web_view(event)
    return CloudLetterApp.run_push_task()

def handler(event: dict, context: dict) -> dict:
    """抽象度更高的独立被调方法名"""
    return CloudLetterApp.run_push_task()

def main() -> None:
    """本地原生 CLI 操作环境或通过 Docker 挂起的主方法"""
    CloudLetterApp.run_push_task()

if __name__ == "__main__":
    main()
