"""
聚合独立化定制引擎模块 (Custom Content Provider)
负责处理所有源自本地配置文件手操映射过来的字符串和图文引用源。
"""
import random
from typing import Optional
from cloud_letter.config import config
from cloud_letter.providers.quotes import QuoteService
from cloud_letter.core.date_utils import DateCalculator

class CustomContentService:
    """内部映射并处理用户在 env 层面留下的自主文案组合池"""
    
    def __init__(self) -> None:
        self.quote_service = QuoteService()
        self.date_calc = DateCalculator()
        self.title_conf = config.get("title")
        self.content_conf = config.get("content")
        self.pic_conf = config.get("pic")

    def get_custom_title(self) -> Optional[str]:
        """获取或生成顶层推送主题约束"""
        return self.title_conf if self.title_conf else None

    def get_aggregated_content(self) -> str:
        """合成系统问候面板，动态缝合当天的早安、彩虹屁等至同一段落呈现"""
        pieces = []
        today_data = self.date_calc.get_today_greeting()
        pieces.append(today_data["today_tip"])
        
        if self.content_conf:
            pieces.append(self.content_conf)
            
        rainbow = self.quote_service.fetch_rainbow_fart()
        if rainbow:
            pieces.append(rainbow)
            
        return "\n\n".join(pieces)

    def get_custom_pic(self) -> Optional[str]:
        """按权重拆分抓取本地自留图像直链列表"""
        if not self.pic_conf:
            return None
            
        if "&&" in self.pic_conf:
            valid_pics = [p.strip() for p in self.pic_conf.split("&&") if p.strip()]
            return random.choice(valid_pics) if valid_pics else None
            
        return self.pic_conf.strip() if self.pic_conf.strip() else None
