"""
早安系统全聚合处理中枢 (Report Builder)
基于建造者（Builder）原则，接管了过去 `handle.py` 的重活，安全合拢所有 API 回流的文本串及 UI 卡片逻辑。
"""
import os
from typing import Dict, List, Any, Optional
from cloud_letter.config import config
from cloud_letter.providers.quotes import QuoteService
from cloud_letter.core.date_utils import DateCalculator
from cloud_letter.providers.diy import CustomContentService
from cloud_letter.providers.weather import WeatherService

class DailyReportBuilder:
    """包装数据的实体装配师，负责将离散变量压实成企微或发件引擎可直接吞吐的三大件（Wecom, WeChatTest, HTML）"""
    
    def __init__(self) -> None:
        self.msg_type = config.get("msgtype") or "1"
        self.agent_id = config.get("agentid")
        self.landing_link = config.get("link")
        self.pic_type = config.get("pictype")
        
        self.quotes = QuoteService()
        self.dates = DateCalculator()
        self.diy = CustomContentService()
        self.weather = WeatherService()
        
    def _safe_replace(self, text: Optional[str]) -> Optional[str]:
        if not text: return None
        return text.replace("&", "%26").replace("'", "%27").replace("\n", "\\n")
        
    def _build_multi_card(self, out_title: str, inner_title: str, content: str, pic: Optional[str], custom_link: Optional[str]) -> Optional[Dict[str, str]]:
        if self.msg_type != "2": return None
        if not any([out_title, inner_title, content, pic, custom_link]):
            return None
            
        out_title = out_title or content or inner_title or "查看图片"
        safe_pic = pic or self.quotes.fetch_random_pic()
        safe_inner = self._safe_replace(inner_title)
        safe_content = self._safe_replace(content)
        
        url = custom_link
        if not url and self.landing_link:
            url = f"{self.landing_link}?t={safe_inner}&p={safe_pic}&c={safe_content}"
            if len(url) > 1000: url = url[:1000] + "······"
            
        return {
            "title": out_title,
            "url": url,
            "picurl": safe_pic
        }

    def build_report(self) -> Dict[str, Any]:
        """组装出所有的渲染图文。抛弃过去基于 if..else 的堆栈流，转为直接按需块化捕获。"""
        info_blocks = []
        multi_blocks = []
        
        # 1. 基础配置提取
        diy_pic = self.diy.get_custom_pic()
        diy_title = self.diy.get_custom_title()
        diy_content = self.diy.get_aggregated_content()
        info_blocks.append(diy_content)
        
        today_date = self.dates.get_today_greeting()["today_date"]
        
        # 2. 必应数据介入
        bing_data = self.quotes.fetch_bing_wallpaper()
        bing_flag = 1
        
        art_title = today_date
        art_content = diy_content
        art_pic = self.quotes.fetch_random_pic()
        
        if diy_pic or diy_title or self.pic_type:
            if diy_pic: art_pic = diy_pic
            if diy_title: art_title += "\n" + diy_title
            res = self._build_multi_card(art_title, art_title, art_content, art_pic, None)
            if res: multi_blocks.append(res)
        elif bing_data:
            art_pic = bing_data["pic_url"]
            art_title += "\n" + bing_data["tip_text"]
            res = self._build_multi_card(art_title, art_title, art_content, art_pic, None)
            if res: multi_blocks.append(res)
            bing_flag = 0
            
        if not art_pic and bing_data:
            art_pic = bing_data["pic_url"]
            
        if self.pic_type == "none":
            art_pic = None
            
        # 3. 气象追踪
        weather_text = self.weather.fetch_all_weather()
        if weather_text:
            info_blocks.append(weather_text)
            res = self._build_multi_card(weather_text, "Weather", weather_text, None, None)
            if res: multi_blocks.append(res)
            
        # 4. 历法纪元 (Anniversaries)
        days_text = self.dates.extract_all_days()
        if days_text:
            info_blocks.append(days_text)
            res = self._build_multi_card(days_text, "Days", days_text, None, None)
            if res: multi_blocks.append(res)
            
        # (移除过期逻辑: 疫情数据)
            
        # 5. Bing 图文再整合
        if bing_flag and bing_data:
            res = self._build_multi_card(f"🖼️ {bing_data['tip_text']}", "Bing", f"🖼️ {bing_data['tip_text']}", bing_data["pic_url"], None)
            if res: multi_blocks.append(res)
            
        # 6. 词霸名言
        ciba_data = self.quotes.fetch_iciba_daily()
        if ciba_data:
            info_blocks.append(ciba_data["tip_text"])
            res = self._build_multi_card(ciba_data["tip_text"], "iCiba", ciba_data["tip_text"], ciba_data["pic_url"], None)
            if res: multi_blocks.append(res)

        art_content_str = "\n\n".join(info_blocks)
        html_content = art_content_str.replace("\n", "\\n")
        safe_content = self._safe_replace(art_content_str)
        safe_title = self._safe_replace(art_title)

        beta_url = f"{self.landing_link}?t={safe_title}&p={art_pic}&c={safe_content}" if self.landing_link else None
        if beta_url and len(beta_url) > 9999: beta_url = beta_url[:9999] + "······"

        if self.msg_type == "1":
            article = [{"title": art_title, "description": art_content_str, "url": beta_url, "picurl": art_pic}]
        else:
            article = [b for b in multi_blocks if b]

        return {
            "wecom_data": {
                "touser": "@all",
                "toparty": "",
                "totag": "",
                "msgtype": "news",
                "agentid": self.agent_id,
                "news": {"articles": article},
                "enable_id_trans": 0,
                "enable_duplicate_check": 0,
                "duplicate_check_interval": 1800
            },
            "beta_data": {
                "art_url": beta_url,
                "art_content": art_content_str
            },
            "html_data": {
                "p": art_pic,
                "t": art_title,
                "c": html_content
            }
        }

    def render_html(self, html_data: Dict[str, str]) -> str:
        """加载原生前端模板与变量合并映射"""
        tmpl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "email.html")
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        p, t, c = html_data.get("p"), html_data.get("t"), html_data.get("c")
        if p and p.lower() != "none": html = html.replace('class="pic" style="display:none;', 'class="pic" style="').replace("<&p&>", p)
        if t and t.lower() != "none": html = html.replace('class="title" style="display:none;', 'class="title" style="').replace("<&t&>", t.replace("\\n", "<br/>"))
        if c and c.lower() != "none": html = html.replace('class="content" style="display:none;', 'class="content" style="').replace("<&c&>", c.replace("\\n", "<br/>"))
        
        return html

# 提供给外部通道调用的便捷执行单例入口点
builder = DailyReportBuilder()
def handle_html(d): return builder.render_html(d)
def handle_msg(): return builder.build_report()
