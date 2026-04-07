"""
派发引擎策略矩阵 (Notifiers / Senders)
完全颠覆了过往面向过程的分离流，现引入了基于面向对象的策略模式与抽象工厂理念。
保证各种信道之间严密隔离、自成配置体系。
"""
from abc import ABC, abstractmethod
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, List
from cloud_letter.config import config
from cloud_letter.core.utils import get_session, logger
from cloud_letter.core.builder import handle_msg, handle_html

class BaseNotifier(ABC):
    """规范任何下挂推送引擎的行为准则。"""
    
    @abstractmethod
    def send(self, global_payload: Dict[str, Any]) -> bool:
        """主执行派发的方法入口"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """校验自身能否工作的健康检查探针"""
        pass
        
    @property
    def name(self) -> str:
        return self.__class__.__name__

class WeComNotifier(BaseNotifier):
    """腾讯企业微信应用通道策略组"""
    
    def __init__(self) -> None:
        self.corpid = config.get("corpid")
        self.corpsecret = config.get("corpsecret")
        self.agentid = config.get("agentid")
        
    def is_configured(self) -> bool:
        return bool(self.corpid and self.corpsecret and self.agentid)
        
    def _get_token(self) -> str:
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        with get_session() as session:
            resp = session.get(url, params={"corpid": self.corpid, "corpsecret": self.corpsecret}).json()
        if resp.get("errcode") == 0:
            return resp["access_token"]
        logger.error(f"[W/C] 企业微信远端拒接鉴权: {resp}")
        return ""
        
    def send(self, global_payload: Dict[str, Any]) -> bool:
        if not self.is_configured(): return False
        token = self._get_token()
        if not token: return False
        
        wecom_data = global_payload.get("wecom_data", {})
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        try:
            with get_session() as session:
                resp = session.post(url, json=wecom_data).json()
            if resp.get("errcode") == 0:
                logger.info("✅ 企业微信通道执行下推落库成功。")
                return True
            logger.error(f"❌ 企微响应错误阻断代码: {resp}")
            return False
        except Exception as e:
            logger.error(f"[W/C] 企微心跳通信完全丢失: {e}")
            return False

class WeChatTestNotifier(BaseNotifier):
    """个人微信公众号测试回调通道策略组"""
    
    def __init__(self) -> None:
        self.appid = config.get("appid")
        self.appsecret = config.get("appsecret")
        self.templateid = config.get("templateid")
        self.user_ids = config.get_list("userid")
        
    def is_configured(self) -> bool:
        return bool(self.appid and self.appsecret and self.templateid and self.user_ids)
        
    def _get_token(self) -> str:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.appid}&secret={self.appsecret}"
        try:
            with get_session() as session:
                return session.get(url, timeout=10).json().get("access_token", "")
        except Exception as e:
            logger.error(f"[WX] 测服号无法拉取临时票据: {e}")
            return ""
            
    def send(self, global_payload: Dict[str, Any]) -> bool:
        if not self.is_configured(): return False
        token = self._get_token()
        if not token: return False
        
        beta_data = global_payload.get("beta_data", {})
        url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
        has_full_success = True
        
        for uid in self.user_ids:
            payload = {
                "touser": uid,
                "template_id": self.templateid,
                "url": beta_data.get("art_url"),
                "topcolor": "#FF0000",
                "data": {"dailyinfo": {"value": beta_data.get("art_content")}}
            }
            try:
                with get_session() as session:
                    resp = session.post(url, json=payload).json()
                if resp.get("errcode") == 0:
                    logger.info(f"✅ 完成一簇对定点测试号UID的下发: {uid}")
                else:
                    logger.error(f"❌ 挂载给 UID {uid} 的数据由于参数被微信退回: {resp}")
                    has_full_success = False
            except Exception as e:
                logger.error(f"[WX] 向用户灌装数据产生脏断连: {e}")
                has_full_success = False
                
        return has_full_success

class EmailNotifier(BaseNotifier):
    """SMTP 原生网络挂载信道发送协议策略"""
    
    def __init__(self) -> None:
        self.email_from = config.get("emailfrom")
        self.email_token = config.get("emailtoken")
        self.email_to = config.get_list("emailto")
        
    def is_configured(self) -> bool:
        return bool(self.email_from and self.email_token and self.email_to)
        
    def send(self, global_payload: Dict[str, Any]) -> bool:
        if not self.is_configured(): return False
        
        html_data = global_payload.get("html_data", {})
        subject = html_data.get("t", "Cloud Letter 推送")
        
        s_lines = subject.split("\n")
        html_title = s_lines[1] if len(s_lines) == 2 else None
        compiled_html = handle_html({"p": html_data.get("p"), "t": html_title, "c": html_data.get("c")})
        
        msg = MIMEText(compiled_html, 'html', 'utf-8')
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ",".join(self.email_to)
        smtp_domain = f"smtp.{self.email_from.split('@')[1]}"
        
        try:
            with smtplib.SMTP_SSL(smtp_domain, 465) as server:
                server.login(self.email_from, self.email_token)
                server.sendmail(self.email_from, self.email_to, msg.as_string())
            logger.info("✅ SMTP 流式分发队列已清空传送成功。")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"[SMTP] 与服务器认证通信或握手崩塌: {e}")
            return False

class NotificationManager:
    """多路由汇聚及轮询派发管理器"""
    
    def __init__(self) -> None:
        self.strategies: List[BaseNotifier] = [WeComNotifier(), WeChatTestNotifier(), EmailNotifier()]

    def execute_all(self) -> Dict[str, Any]:
        ready_channels = [n for n in self.strategies if n.is_configured()]
        if not ready_channels:
            msg = "⛔️ 架构自检异常：环境中未挂载匹配合法的接收端通信线路。所有动作中断。"
            logger.warning(msg)
            return {"code": 0, "msg": msg}
            
        logger.info(f"系统就绪，检查到已连线 {len(ready_channels)} 条有效发射基带。合成渲染主总线开始...")
        global_payload = handle_msg()
        
        results = []
        has_success = False
        for channel in ready_channels:
            logger.info(f"==> 唤醒调度目标： {channel.name} 策略流")
            res = channel.send(global_payload)
            has_success = has_success or res
            results.append(f"{channel.name}: {'SUCCESS' if res else 'FAIL'}")
            
        return {"code": 1 if has_success else 0, "msg": "; ".join(results)}

# 将全局实例化剥离，保留给外围脚本引用的单一路由出口
def send_msg() -> Dict[str, Any]:
    return NotificationManager().execute_all()
