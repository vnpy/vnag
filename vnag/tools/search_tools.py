from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import requests

from vnag.local import LocalTool
from vnag.tools.web_tools import fetch_markdown
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

    这是 provider 原语工具，适合在需要博查特定能力（如 freshness）
    时直接使用。普通研究场景优先使用 `search-tools_search-web`，
    仅在需要 provider 特性、调试差异或统一入口结果不足时再直接调用本工具。

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

    这是 provider 原语工具，适合在需要 Tavily 特定能力（如 search_depth）
    时直接使用。普通研究场景优先使用 `search-tools_search-web`，
    仅在需要 provider 特性、调试差异或统一入口结果不足时再直接调用本工具。

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

    这是 provider 原语工具，适合在需要 Serper 特定参数（如 gl）
    时直接使用。普通研究场景优先使用 `search-tools_search-web`，
    仅在需要 provider 特性、调试差异或统一入口结果不足时再直接调用本工具。

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

    这是 provider 原语工具，适合在需要 Jina 搜索特性时直接使用。
    普通研究场景优先使用 `search-tools_search-web`，仅在需要 provider
    特性、调试差异或统一入口结果不足时再直接调用本工具。

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


def get_auto_providers(freshness: str) -> list[str]:
    """根据当前配置和查询参数返回 auto 模式下的 provider 顺序。"""
    provider_names: list[str]
    if freshness.strip():
        provider_names = ["bocha", "serper", "tavily", "jina"]
    else:
        provider_names = ["serper", "bocha", "tavily", "jina"]

    available_providers: list[str] = []
    for provider_name in provider_names:
        if provider_name == "serper" and setting["serper_key"]:
            available_providers.append(provider_name)
        elif provider_name == "bocha" and setting["bocha_key"]:
            available_providers.append(provider_name)
        elif provider_name == "tavily" and setting["tavily_key"]:
            available_providers.append(provider_name)
        elif provider_name == "jina":
            available_providers.append(provider_name)

    return available_providers


def run_search_provider(
    query: str,
    count: int,
    provider_name: str,
    freshness: str,
) -> tuple[dict[str, Any], Callable[[dict[str, Any], int], list[dict[str, Any]]]]:
    """执行单个 provider 搜索并返回原始结果与规范化函数。"""
    if provider_name == "serper":
        return serper_search(query=query, num=count), _normalize_serper_results

    if provider_name == "tavily":
        return tavily_search(query=query, max_results=count), _normalize_tavily_results

    if provider_name == "bocha":
        effective_freshness: str = freshness or "noLimit"
        return (
            bocha_search(
                query=query,
                count=count,
                summary=True,
                freshness=effective_freshness,
            ),
            _normalize_bocha_results,
        )

    if provider_name == "jina":
        return jina_search(query=query, with_content=False), _normalize_jina_results

    raise ValueError("不支持的 provider，可选值为 auto、serper、tavily、bocha、jina")


def get_search_results(
    raw: dict[str, Any],
    count: int,
    normalize: Callable[[dict[str, Any], int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """将 provider 原始结果规范化为统一候选来源列表。"""
    return normalize(raw, count)


def search_web(
    query: str,
    count: int = 5,
    provider: str = "auto",
    freshness: str = "",
) -> dict[str, Any]:
    """
    使用统一入口执行网络搜索，并返回裁剪后的结构化候选来源列表。

    这是普通研究型 Agent 的默认搜索入口。相比 provider 原始 JSON，
    本工具只保留模型最常需要的字段，适合先筛选候选来源，再继续调用
    `web-tools_fetch-markdown` 阅读正文。

    `provider` 通常无需显式指定；在 `auto` 模式下，本工具会优先根据当前
    已配置的 API key 选择可用 provider，并在必要时自动回退到其他可用
    provider。仅在需要 provider 特性、调试差异或统一入口结果不足时，
    才建议显式指定 provider。若问题依赖事实、最新信息或官方文档，
    不应只根据 snippet 直接下结论。

    Args:
        query: 搜索关键词
        count: 返回结果数量上限，默认 5
        provider: 搜索提供方，可选 auto、serper、tavily、bocha、jina
        freshness: 时效性过滤，当前仅在 bocha provider 下生效

    Returns:
        裁剪后的结构化搜索结果
    """
    provider_name: str = provider.strip().lower() or "auto"

    if count <= 0:
        return {
            "query": query,
            "provider": provider_name,
            "results": [],
            "error": "count 必须大于 0",
        }

    # 自动选择搜索 provider
    if provider_name == "auto":
        attempted_providers: list[str] = []
        last_error: str = "未找到可用的搜索 provider"

        for auto_provider in get_auto_providers(freshness):
            attempted_providers.append(auto_provider)
            raw, normalize = run_search_provider(
                query=query,
                count=count,
                provider_name=auto_provider,
                freshness=freshness,
            )
            if "error" in raw:
                last_error = _as_text(raw.get("error"))
                continue

            results: list[dict[str, Any]] = get_search_results(raw, count, normalize)
            if results:
                return {
                    "query": query,
                    "provider": auto_provider,
                    "results": results,
                    "attempted_providers": attempted_providers,
                }

            last_error = f"{auto_provider} 未返回可用结果"

        return {
            "query": query,
            "provider": "auto",
            "results": [],
            "error": last_error,
            "attempted_providers": attempted_providers,
        }

    # 如果 provider 不支持，返回错误
    if provider_name not in {"serper", "tavily", "bocha", "jina"}:
        return {
            "query": query,
            "provider": provider_name,
            "results": [],
            "error": (
                "不支持的 provider，可选值为 auto、serper、tavily、bocha、jina"
            ),
        }

    # 执行特定 provider 的搜索
    raw, normalize = run_search_provider(
        query=query,
        count=count,
        provider_name=provider_name,
        freshness=freshness,
    )

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
        "results": get_search_results(raw, count, normalize),
    }


def _truncate_text(text: str, max_chars: int) -> str:
    """按字符数截断文本，避免组合工具一次返回过长内容。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[内容已截断]"


def search_and_read(
    query: str,
    top_k: int = 3,
    provider: str = "auto",
) -> dict[str, Any]:
    """
    先搜索候选来源，再批量抓取前几个结果的 Markdown 正文。

    适合需要“先搜索再阅读正文”才能回答的问题，可减少模型自行编排多次
    工具调用时的失败率。普通研究场景可优先使用本工具快速拿到候选来源
    与正文；若后续仍需深读某个 URL，可再单独调用 `web-tools_fetch-markdown`。
    返回结果会同时保留搜索摘要与正文内容，便于后续比较多个来源并交叉验证。

    Args:
        query: 搜索关键词
        top_k: 需要继续阅读正文的来源数量，默认 3
        provider: 搜索提供方，可选 auto、serper、tavily、bocha、jina

    Returns:
        包含搜索结果和正文内容的结构化结果
    """
    provider_name: str = provider.strip().lower() or "auto"
    if top_k <= 0:
        return {
            "query": query,
            "provider": provider_name,
            "search_results": [],
            "documents": [],
            "error": "top_k 必须大于 0",
        }

    search_result: dict[str, Any] = search_web(
        query=query,
        count=top_k,
        provider=provider_name,
    )
    documents: list[dict[str, Any]] = []

    if "error" in search_result:
        return {
            "query": query,
            "provider": search_result.get("provider", provider_name),
            "search_results": search_result.get("results", []),
            "documents": documents,
            "error": _as_text(search_result.get("error")),
        }

    for item in _as_list(search_result.get("results"))[:top_k]:
        if not isinstance(item, dict):
            continue

        markdown: str = fetch_markdown(_as_text(item.get("url")))
        documents.append(
            {
                "title": _as_text(item.get("title")),
                "url": _as_text(item.get("url")),
                "snippet": _as_text(item.get("snippet")),
                "markdown": _truncate_text(markdown, max_chars=12000),
            }
        )

    return {
        "query": query,
        "provider": _as_text(search_result.get("provider")),
        "search_results": search_result.get("results", []),
        "documents": documents,
    }


# 注册工具
bocha_search_tool: LocalTool = LocalTool(bocha_search)

tavily_search_tool: LocalTool = LocalTool(tavily_search)

serper_search_tool: LocalTool = LocalTool(serper_search)

jina_search_tool: LocalTool = LocalTool(jina_search)

search_web_tool: LocalTool = LocalTool(search_web)

search_and_read_tool: LocalTool = LocalTool(search_and_read)
