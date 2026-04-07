"""
历法编组辅助计算包 (Date Utilities)
消除以往依赖面向过程产生的繁杂日期，引入 datetime 操作化改写公历以及借用 zhdate 做农历算法集成。
"""
from datetime import datetime, date, timedelta
from typing import Tuple, List, Optional, Dict
from zhdate import ZhDate
import random
from cloud_letter.config import config
from cloud_letter.core.utils import logger

class DateCalculator:
    """集中式管理有关纪念日和历法计算引擎的纯静态封装"""

    def __init__(self) -> None:
        # 硬绑定东八区规避计算抖动时延
        self.now_dt: datetime = datetime.utcnow() + timedelta(hours=8)
        self.today: date = self.now_dt.date()
        self.call: str = config.get("call")

    def get_anniversary(self, target_day_str: str, target_name: str) -> Tuple[str, int]:
        """核心逆解某特定年份的纪念日。"""
        this_year = self.now_dt.year
        parts = target_day_str.split("-")
        is_lunar = parts[0].startswith("n")
        
        try:
            if is_lunar:
                lunar_month, lunar_day = int(parts[1]), int(parts[2])
                last_date = ZhDate(this_year - 1, lunar_month, lunar_day).to_datetime().date()
                this_date = ZhDate(this_year, lunar_month, lunar_day).to_datetime().date()
                this_date = last_date if self.today <= last_date else this_date
            else:
                this_date = date(this_year, int(parts[1]), int(parts[2]))
        except Exception:
            logger.error(f"日期文本被破坏解析不合法: {target_day_str}")
            return ("", 9999)

        if self.today == this_date:
            return (f"🎂 {target_name}就是今天啦！", 0)
            
        if self.today > this_date:
            if is_lunar:
                next_lunar = ZhDate(this_year + 1, int(parts[1]), int(parts[2])).to_datetime().date()
                next_date = date(next_lunar.year, next_lunar.month, next_lunar.day)
            else:
                next_date = date(this_year + 1, int(parts[1]), int(parts[2]))
            days_remain = (next_date - self.today).days
        else:
            days_remain = (this_date - self.today).days
            
        return (f"🎂 距离{target_name}还有 {days_remain} 天", days_remain)

    def get_duration(self, begin_day_str: str, begin_name: str) -> Tuple[str, int]:
        """针对里程碑计算在一起流逝的天数"""
        parts = begin_day_str.split("-")
        is_lunar = parts[0].startswith("n")
        
        if is_lunar:
            begin_date = ZhDate(int(parts[0][1:]), int(parts[1]), int(parts[2])).to_datetime().date()
        else:
            begin_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            
        if self.today == begin_date:
            return (f"💓 {begin_name}就是今天啦！", 0)
        elif self.today > begin_date:
            return (f"💓 {begin_name}已经 {(self.today - begin_date).days} 天", (self.today - begin_date).days)
        else:
            return (f"💓 距离{begin_name}还有 {(begin_date - self.today).days} 天", (begin_date - self.today).days)

    def extract_all_days(self) -> Optional[str]:
        """提取聚合系统内填报全部被挂载的相关独立日程。"""
        t_days, t_names = config.get_list("targetday"), config.get_list("targetname")
        b_days, b_names = config.get_list("beginday"), config.get_list("beginname")
        results = []
        
        if t_days and t_names and len(t_days) == len(t_names):
            results.extend([self.get_anniversary(d, n) for d, n in zip(t_days, t_names)])
            
        if b_days and b_names and len(b_days) == len(b_names):
            results.extend([self.get_duration(d, n) for d, n in zip(b_days, b_names)])
            
        if results:
            results.sort(key=lambda x: x[1])
            return "\n".join(r[0] for r in results)
        return None

    def get_today_greeting(self) -> Dict[str, str]:
        """按照早晚自动计算打招呼的礼节性标语与颜文字"""
        date_str = self.now_dt.strftime("今天是 %Y年%m月%d日")
        weekday = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"][int(self.now_dt.strftime("%w"))]
        today_date = f"{date_str} {weekday} "
        
        hour = self.now_dt.hour
        if 0 <= hour < 6: greeting = "凌晨好"
        elif 6 <= hour < 9: greeting = "早上好"
        elif 9 <= hour < 12: greeting = "上午好"
        elif 12 <= hour < 14: greeting = "中午好"
        elif 14 <= hour < 18: greeting = "下午好"
        else: greeting = "晚上好"
        
        emoticons = ["(￣▽￣)~*", "(～￣▽￣)～", "ヾ(✿ﾟ▽ﾟ)ノ", "٩(๑❛ᴗ❛๑)۶", "(´▽`)ﾉ"]
        greeting_text = f"{greeting} ~ {random.choice(emoticons)}"
        
        return {
            "today_date": today_date,
            "today_tip": f"{self.call}{greeting_text}" if self.call else greeting_text
        }
