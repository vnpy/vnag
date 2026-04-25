from typing import Any
from urllib.parse import quote

import requests

from vnag.local import LocalTool
from vnag.utility import load_json, save_json


# 配置文件名称
SETTING_NAME: str = "tool_search.json"

# 默认配置
setting: dict[str, str] = {
    "bocha_key": "",
    "tavily_key": "",
    "serper_key": "",
    "jina_key": "",
}

# 从文件加载配置
_setting: dict[str, Any] = load_json(SETTING_NAME)
if _setting:
    setting.update(_setting)
else:
    save_json(SETTING_NAME, setting)


def bocha_search(
    query: str,
    count: int = 10,
    summary: bool = True,
    freshness: str = "noLimit",
) -> dict[str, Any]:
    """
    使用博查 Web Search API 进行网络搜索，返回候选来源列表。

    这些结果主要用于发现后续要阅读的网页，不应直接视为最终证据。
    面对事实性问题时，应优先根据结果挑选高相关来源，再继续调用
    `web-tools_fetch-markdown` 阅读正文，并对重要结论做交叉验证。

    Args:
        query: 搜索关键词
        count: 返回结果数量，默认 10
        summary: 是否返回摘要，默认 True
        freshness: 时效性过滤，可选值: noLimit, oneDay, oneWeek, oneMonth, oneYear

    Returns:
        搜索结果的 JSON 数据
    """
    api_key: str = setting["bocha_key"]
    if not api_key:
        return {"error": "未配置博查 API 密钥，请在 .vnag/tool_search.json 中配置"}

    url: str = "https://api.bochaai.com/v1/web-search"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, str | int | bool] = {
        "query": query,
        "summary": summary,
        "freshness": freshness,
        "count": count,
    }

    try:
        resp: requests.Response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"博查搜索请求失败: {e}"}


def tavily_search(
    query: str,
    max_results: int = 10,
    search_depth: str = "basic",
) -> dict[str, Any]:
    """
    使用 Tavily Search API 进行网络搜索，返回候选来源列表。

    搜索结果适合用于发现候选 URL，而不是直接作为最终答案依据。
    遇到事实核查、最新信息或文档查询时，应继续使用
    `web-tools_fetch-markdown` 阅读正文，必要时比较多个来源。

    Args:
        query: 搜索关键词
        max_results: 返回结果数量，默认 10
        search_depth: 搜索深度，可选值: basic, advanced

    Returns:
        搜索结果的 JSON 数据
    """
    api_key: str = setting["tavily_key"]
    if not api_key:
        return {"error": "未配置 Tavily API 密钥，请在 .vnag/tool_search.json 中配置"}

    url: str = "https://api.tavily.com/search"
    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
    }

    try:
        resp: requests.Response = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"Tavily 搜索请求失败: {e}"}


def serper_search(
    query: str,
    num: int = 10,
    gl: str = "cn",
) -> dict[str, Any]:
    """
    使用 Serper API 进行 Google 搜索，返回候选来源列表。

    搜索结果中的 snippet 只适合帮助筛选来源，不应直接作为最终证据。
    对重要结论，应继续打开候选网页正文进行确认；若结果不足，
    应尝试调整关键词后再次搜索。

    Args:
        query: 搜索关键词
        num: 返回结果数量，默认 10
        gl: 地区代码，默认 cn

    Returns:
        搜索结果的 JSON 数据
    """
    api_key: str = setting["serper_key"]
    if not api_key:
        return {"error": "未配置 Serper API 密钥，请在 .vnag/tool_search.json 中配置"}

    url: str = "https://google.serper.dev/search"
    headers: dict[str, str] = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"q": query, "num": num, "gl": gl}

    try:
        resp: requests.Response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"Serper 搜索请求失败: {e}"}


def jina_search(
    query: str,
    with_content: bool = True,
) -> dict[str, Any]:
    """
    使用 Jina Search API 进行网络搜索，返回候选来源列表。

    即使返回了网页内容，也应优先把它当作候选线索而不是最终证据。
    需要严谨回答时，仍建议针对高相关来源继续调用
    `web-tools_fetch-markdown` 阅读正文，并对关键信息交叉验证。

    Args:
        query: 搜索关键词
        with_content: 是否返回网页正文内容，默认 True

    Returns:
        搜索结果的 JSON 数据
    """
    url: str = f"https://s.jina.ai/{quote(query)}"
    headers: dict[str, str] = {"Accept": "application/json"}

    api_key: str = setting["jina_key"]
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if not with_content:
        headers["X-No-Content"] = "true"

    try:
        resp: requests.Response = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"Jina 搜索请求失败: {e}"}


def _as_text(value: Any) -> str:
    """将任意值转换为去首尾空白的文本。"""
    if value is None:
        return ""
    return str(value).strip()


def _as_list(value: Any) -> list[Any]:
    """尽量把常见容器转换成列表。"""
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _build_result(
    *,
    title: Any,
    url: Any,
    snippet: Any,
    source: str,
    rank: int,
) -> dict[str, Any] | None:
    """构造统一的搜索结果项，缺少 URL 时直接丢弃。"""
    normalized_url: str = _as_text(url)
    if not normalized_url:
        return None

    return {
        "title": _as_text(title),
        "url": normalized_url,
        "snippet": _as_text(snippet),
        "source": source,
        "rank": rank,
    }


def _normalize_serper_results(raw: dict[str, Any], count: int) -> list[dict[str, Any]]:
    """将 Serper 原始结果转换为统一结构。"""
    normalized: list[dict[str, Any]] = []
    for item in _as_list(raw.get("organic")):
        if not isinstance(item, dict):
            continue
        result: dict[str, Any] | None = _build_result(
            title=item.get("title"),
            url=item.get("link"),
            snippet=item.get("snippet"),
            source="serper",
            rank=len(normalized) + 1,
        )
        if result:
            normalized.append(result)
        if len(normalized) >= count:
            break
    return normalized


def _normalize_tavily_results(raw: dict[str, Any], count: int) -> list[dict[str, Any]]:
    """将 Tavily 原始结果转换为统一结构。"""
    normalized: list[dict[str, Any]] = []
    for item in _as_list(raw.get("results")):
        if not isinstance(item, dict):
            continue
        result: dict[str, Any] | None = _build_result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("content"),
            source="tavily",
            rank=len(normalized) + 1,
        )
        if result:
            normalized.append(result)
        if len(normalized) >= count:
            break
    return normalized


def _normalize_bocha_results(raw: dict[str, Any], count: int) -> list[dict[str, Any]]:
    """将博查原始结果转换为统一结构。"""
    normalized: list[dict[str, Any]] = []
    data: Any = raw.get("data", {})
    candidates: list[Any] = []

    if isinstance(data, dict):
        web_pages: Any = data.get("webPages", {})
        if isinstance(web_pages, dict):
            candidates = _as_list(web_pages.get("value"))
        else:
            candidates = _as_list(web_pages)
    else:
        candidates = _as_list(data)

    for item in candidates:
        if not isinstance(item, dict):
            continue
        result: dict[str, Any] | None = _build_result(
            title=item.get("name") or item.get("title"),
            url=item.get("url") or item.get("link"),
            snippet=item.get("snippet") or item.get("summary"),
            source="bocha",
            rank=len(normalized) + 1,
        )
        if result:
            normalized.append(result)
        if len(normalized) >= count:
            break
    return normalized


def _normalize_jina_results(raw: dict[str, Any], count: int) -> list[dict[str, Any]]:
    """将 Jina 原始结果转换为统一结构。"""
    normalized: list[dict[str, Any]] = []
    candidates: list[Any] = _as_list(raw.get("data"))
    if not candidates:
        candidates = _as_list(raw.get("results"))

    for item in candidates:
        if not isinstance(item, dict):
            continue
        result: dict[str, Any] | None = _build_result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("description") or item.get("content"),
            source="jina",
            rank=len(normalized) + 1,
        )
        if result:
            normalized.append(result)
        if len(normalized) >= count:
            break
    return normalized


def search_web(
    query: str,
    count: int = 5,
    provider: str = "auto",
    freshness: str = "",
) -> dict[str, Any]:
    """
    使用统一入口执行网络搜索，并返回裁剪后的结构化候选来源列表。

    相比 provider 原始 JSON，本工具只保留模型最常需要的字段，适合先筛选
    候选来源，再继续调用 `web-tools_fetch-markdown` 阅读正文。若问题依赖
    事实、最新信息或官方文档，不应只根据 snippet 直接下结论。

    Args:
        query: 搜索关键词
        count: 返回结果数量上限，默认 5
        provider: 搜索提供方，可选 auto、serper、tavily、bocha、jina
        freshness: 时效性过滤，当前仅在 bocha provider 下生效

    Returns:
        裁剪后的结构化搜索结果
    """
    provider_name: str = provider.strip().lower() or "auto"
    if provider_name == "auto":
        provider_name = "serper"

    if count <= 0:
        return {
            "query": query,
            "provider": provider_name,
            "results": [],
            "error": "count 必须大于 0",
        }

    raw: dict[str, Any]
    if provider_name == "serper":
        raw = serper_search(query=query, num=count)
        normalize = _normalize_serper_results
    elif provider_name == "tavily":
        raw = tavily_search(query=query, max_results=count)
        normalize = _normalize_tavily_results
    elif provider_name == "bocha":
        effective_freshness: str = freshness or "noLimit"
        raw = bocha_search(
            query=query,
            count=count,
            summary=True,
            freshness=effective_freshness,
        )
        normalize = _normalize_bocha_results
    elif provider_name == "jina":
        raw = jina_search(query=query, with_content=False)
        normalize = _normalize_jina_results
    else:
        return {
            "query": query,
            "provider": provider_name,
            "results": [],
            "error": (
                "不支持的 provider，可选值为 auto、serper、tavily、bocha、jina"
            ),
        }

    if "error" in raw:
        return {
            "query": query,
            "provider": provider_name,
            "results": [],
            "error": _as_text(raw.get("error")),
        }

    return {
        "query": query,
        "provider": provider_name,
        "results": normalize(raw, count),
    }


# 注册工具
bocha_search_tool: LocalTool = LocalTool(bocha_search)

tavily_search_tool: LocalTool = LocalTool(tavily_search)

serper_search_tool: LocalTool = LocalTool(serper_search)

jina_search_tool: LocalTool = LocalTool(jina_search)

search_web_tool: LocalTool = LocalTool(search_web)
