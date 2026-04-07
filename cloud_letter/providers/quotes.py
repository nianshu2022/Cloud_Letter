"""
聚合信息池网络访问提供者 (Quotes & External API Providers)
抽象隔离出针对名言、每日一句及二次元头图获取抓取的调用源调度代理类。
"""
import re
import random
from typing import Optional, Dict, List
from cloud_letter.config import config
from cloud_letter.core.utils import get_session, logger

class QuoteService:
    """数据源网络聚合调用执行器容器"""
    
    def __init__(self) -> None:
        self.tian_api_key: str = config.get("tian")
        self.pic_styles: List[str] = config.get_list("pictype")

    def fetch_rainbow_fart(self) -> Optional[str]:
        """天行数据接口: 解析抓取彩虹屁数据层"""
        if not self.tian_api_key:
            return None
        try:
            url = f"http://apis.tianapi.com/caihongpi/index?key={self.tian_api_key}"
            with get_session() as session:
                resp = session.get(url, timeout=10).json()
            return f"🌈 {resp['result']['content']}"
        except Exception as e:
            logger.warning(f"天行 API 拒接并下钻断路: {e}")
            return None

    def fetch_random_pic(self) -> Optional[str]:
        """搏天 API 壁纸下发流转，响应抽离一层随机算法以分担并发。"""
        mode = random.choice(self.pic_styles) if self.pic_styles else "suiji"
        try:
            url = f"https://api.btstu.cn/sjbz/api.php?format=json&lx={mode}"
            with get_session() as session:
                return session.get(url, timeout=10).json().get("imgurl")
        except Exception as e:
            logger.error(f"图片壁纸远端断连报错: {e}")
            return None

    def fetch_bing_wallpaper(self) -> Optional[Dict[str, str]]:
        """逆解截录官网必应当期首张轮播图返回信息结构。"""
        try:
            url = "https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1"
            with get_session() as session:
                resp = session.get(url, timeout=10).json()
            img_meta = resp["images"][0]
            clean_copyright = re.sub(r"\(.*?\)", "", img_meta["copyright"])
            return {
                "pic_url": "https://cn.bing.com/" + img_meta["url"],
                "tip_text": f"{img_meta['title']}——{clean_copyright}"
            }
        except Exception as e:
            logger.warning(f"Bing 壁纸提取流发生格式解构错误: {e}")
            return None

    def fetch_iciba_daily(self) -> Optional[Dict[str, str]]:
        """独立挂载从金山词霸抽取每日提点的一句中英短释功能。"""
        try:
            url = "http://open.iciba.com/dsapi/"
            with get_session() as session:
                resp = session.get(url, timeout=10).json()
            return {
                "tip_text": f"🔤 {resp['content']}\n🀄️ {resp['note']}",
                "pic_url": resp['fenxiang_img']
            }
        except Exception as e:
            logger.warning(f"词霸每日热词无响应，挂起: {e}")
            return None
