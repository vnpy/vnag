from typing import Any

import requests

from vnag.local import LocalTool


def fetch_html(url: str) -> str:
    """
    获取并返回指定URL的HTML内容。
    """
    try:
        response: requests.Response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"获取HTML时出错: {e}"


def fetch_json(url: str) -> Any:
    """
    获取并解析来自URL的JSON数据。
    """
    try:
        response: requests.Response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"获取JSON时出错: {e}"
    except ValueError:
        return "解析JSON失败，响应内容可能不是有效的JSON格式。"


def fetch_markdown(url: str) -> str:
    """
    使用 jina.ai Reader API 获取网页内容并转换为 Markdown 格式。

    【推荐优先使用】相比 fetch_html 和 fetch_json，本函数返回的 Markdown 格式
    更适合大模型阅读和理解，具有以下优势：
    - 自动提取网页主要内容，过滤广告和导航等干扰信息
    - 结构化的 Markdown 格式便于语义理解
    - 减少 token 消耗，提高处理效率

    Args:
        url: 要获取内容的网页 URL

    Returns:
        网页内容的 Markdown 格式文本
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response: requests.Response = requests.get(jina_url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"获取Markdown时出错: {e}"


def check_link(url: str) -> str:
    """
    检查链接的HTTP状态。
    """
    try:
        response: requests.Response = requests.head(url, timeout=5, allow_redirects=True)
        return f"状态码: {response.status_code} {response.reason}"
    except requests.exceptions.RequestException as e:
        return f"检查链接时出错: {e}"


# 注册工具
fetch_html_tool: LocalTool = LocalTool(fetch_html)

fetch_json_tool: LocalTool = LocalTool(fetch_json)

fetch_markdown_tool: LocalTool = LocalTool(fetch_markdown)

check_link_tool: LocalTool = LocalTool(check_link)
