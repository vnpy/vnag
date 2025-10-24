"""
常用的时间函数工具
"""
from datetime import datetime

from vnag.local import LocalTool


def get_current_date() -> str:
    """获取YYYY-MM-DD格式的当前日期字符串。"""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_time() -> str:
    """获取HH:MM:SS格式的当前时间字符串。"""
    return datetime.now().strftime("%H:%M:%S")


def get_current_datetime() -> str:
    """获取YYYY-MM-DD HH:MM:SS格式的当前日期和时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_day_of_week() -> str:
    """获取中文格式的当天星期数（例如：星期一）。"""
    weekday_map = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日",
    }
    weekday = datetime.now().weekday()
    return weekday_map[weekday]


# 注册工具
get_current_date_tool: LocalTool = LocalTool(get_current_date)
get_current_time_tool: LocalTool = LocalTool(get_current_time)
get_current_datetime_tool: LocalTool = LocalTool(get_current_datetime)
get_day_of_week_tool: LocalTool = LocalTool(get_day_of_week)
