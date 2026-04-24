from typing import Any

import requests

from vnag.local import LocalTool


def fetch_html(url: str) -> str:
    """
    获取并返回指定 URL 的 HTML 内容。

    仅在需要原始页面结构时使用。对大多数“先搜索再阅读正文”的场景，
    更推荐优先使用 `fetch_markdown`，因为它更适合模型阅读和提取证据。
    """
    try:
        response: requests.Response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"获取HTML时出错: {e}"


def fetch_json(url: str) -> Any:
    """
    获取并解析来自 URL 的 JSON 数据。

    适合目标链接本身就是结构化 JSON 接口的场景。若来源是普通网页，
    应优先使用 `fetch_markdown` 阅读正文，而不是尝试从 HTML 或 snippet
    直接下结论。
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
    - 适合在搜索后继续阅读正文，而不是只依赖 snippet 作答

    推荐工作流：
    1. 先用搜索工具发现候选来源
    2. 选择 2 到 3 个高相关链接调用 `fetch_markdown`
    3. 对重要事实交叉验证多个来源
    4. 若不同来源冲突，明确写出冲突点和更可信的依据

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
    检查链接的 HTTP 状态。

    适合在阅读正文前快速确认链接是否可访问，但它不能替代正文阅读或事实验证。
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
