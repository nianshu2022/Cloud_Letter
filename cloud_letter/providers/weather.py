"""
和风天气请求引擎 (Weather Provider)
管理与外部气象数据供应接口的连接计算，抽离单一服务类，增强重用与异常接管性。
"""
import re
from typing import Optional, List
from cloud_letter.config import config
from cloud_letter.core.utils import get_session, logger

class WeatherService:
    """和风天气网的 API 请求与结构解析类封装"""
    
    def __init__(self) -> None:
        self.api_key: str = config.get("qweather")
        self.target_cities: List[str] = config.get_list("city")

    def _get_weather_icon(self, description_text: str) -> str:
        """根据气象描述文本匹配对应视觉表情。
        
        Args:
            description_text (str): 天气现象，例如 '晴'，'多云'。
        """
        default_icon = "🌤️"
        icon_mapping = ["☀️", "☁️", "⛅️", "☃️", "⛈️", "🏜️", "🏜️", "🌫️", "🌫️", "🌪️", "🌧️"]
        weather_categories = ["晴", "阴", "云", "雪", "雷", "沙", "尘", "雾", "霾", "风", "雨"]
        
        for idx, condition in enumerate(weather_categories):
            if re.search(condition, description_text):
                return icon_mapping[idx]
        return default_icon

    def _fetch_city_weather(self, full_city_name: str) -> Optional[str]:
        """按特定省市命名法组装抓取格式化气象播报"""
        try:
            parts = full_city_name.split("-")
            city = parts[0]
            county = parts[1] if len(parts) > 1 else parts[0]
            
            geo_url = f"https://geoapi.qweather.com/v2/city/lookup?&adm={city}&key={self.api_key}&location={county}"
            with get_session() as session:
                geo_resp = session.get(geo_url, timeout=10).json()

            if geo_resp.get("code") != "200":
                logger.warning(f"因代码未映射对应地址跳过级联播报, 查询市级地理无响应: {full_city_name}")
                return None
                
            city_id = geo_resp["location"][0]["id"]
            weather_url = f"https://devapi.qweather.com/v7/weather/3d?key={self.api_key}&location={city_id}"
            
            with get_session() as session:
                weather_resp = session.get(weather_url, timeout=10).json()
                
            if weather_resp.get("code") == "200":
                today_data = weather_resp["daily"][0]
                text_day = today_data["textDay"]
                icon = self._get_weather_icon(text_day)
                return f"📍 {city}·{county}, 今日天气: {icon} {text_day}，{today_data['tempMin']}~{today_data['tempMax']} ℃"
                
            return None
        except Exception as e:
            logger.error(f"处理气象网络数据解析触发捕获异常: {e}")
            return None

    def fetch_all_weather(self) -> Optional[str]:
        """批量调度轮询执行所有配置列表气象获取流"""
        if not self.api_key or not self.target_cities:
            logger.debug("气象数据环境缺乏认证凭据信息，忽略天气合成节点。")
            return None
            
        reports = []
        for city in self.target_cities:
            report = self._fetch_city_weather(city)
            if report:
                reports.append(report)
                
        return "\n".join(reports) if reports else None