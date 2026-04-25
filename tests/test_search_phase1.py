import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import vnag.skill as skill_module
from vnag.skill import SkillManager
from vnag.tools import search_tools, web_tools


class SearchPhase1TestCase(unittest.TestCase):
    def test_skill_manager_loads_repo_skills_from_working_dir(self) -> None:
        repo_root: Path = Path(__file__).resolve().parents[1]
        expected_skills = {
            "search-then-read",
            "answer-with-sources",
            "clarify-before-action",
            "plan-and-track",
            "environment-tool-check",
            "mcp-tool-routing",
        }

        with TemporaryDirectory() as temp_dir:
            fallback_working_dir = Path(temp_dir)
            manager = SkillManager()

            with patch.object(skill_module, "WORKING_DIR", repo_root):
                manager.load_skills()

        self.assertTrue(expected_skills.issubset(set(manager.list_skills())))

        skill = manager.get_skill("search-then-read")
        self.assertIsNotNone(skill)
        assert skill is not None
        self.assertIn("search-tools_search-web", skill.content)
        self.assertIn("search-tools_search-and-read", skill.content)
        self.assertIn("web-tools_fetch-markdown", skill.content)
        self.assertIn("挑选 2 到 3 个高相关", skill.content)

        catalog = manager.get_skill_catalog()
        for skill_name in expected_skills:
            self.assertIn(skill_name, catalog)
        self.assertIn("先搜索候选来源，再阅读正文并交叉验证", catalog)
        self.assertIn("证据来源", catalog)

        with patch.object(skill_module, "WORKING_DIR", fallback_working_dir):
            manager_without_skills = SkillManager()
            manager_without_skills.load_skills()

        self.assertEqual(manager_without_skills.list_skills(), [])

    def test_search_tool_descriptions_encourage_reading_full_sources(self) -> None:
        search_description = search_tools.serper_search_tool.get_schema().description
        self.assertIn("候选来源", search_description)
        self.assertIn("snippet", search_description)

        jina_description = search_tools.jina_search_tool.get_schema().description
        self.assertIn("web-tools_fetch-markdown", jina_description)
        self.assertIn("交叉验证", jina_description)

        unified_description = search_tools.search_web_tool.get_schema().description
        self.assertIn("结构化", unified_description)
        self.assertIn("候选来源", unified_description)
        self.assertIn("默认搜索入口", unified_description)

    def test_web_tool_descriptions_encourage_search_then_read_workflow(self) -> None:
        markdown_description = web_tools.fetch_markdown_tool.get_schema().description
        self.assertIn("先用搜索工具发现候选来源", markdown_description)
        self.assertIn("交叉验证多个来源", markdown_description)

        check_link_description = web_tools.check_link_tool.get_schema().description
        self.assertIn("不能替代正文阅读", check_link_description)

    def test_search_web_uses_serper_for_auto_provider(self) -> None:
        raw_result = {
            "organic": [
                {
                    "title": "Cursor Docs",
                    "link": "https://cursor.com/docs",
                    "snippet": "Official documentation.",
                    "date": "2026-04-25",
                },
                {
                    "title": "Cursor Blog",
                    "link": "https://cursor.com/blog",
                    "snippet": "Product updates.",
                },
            ]
        }

        with (
            patch.dict(
                search_tools.setting,
                {"serper_key": "enabled", "bocha_key": "", "tavily_key": "", "jina_key": ""},
            ),
            patch.object(search_tools, "serper_search", return_value=raw_result) as mocked,
        ):
            result = search_tools.search_web("cursor docs", count=2)

        mocked.assert_called_once_with(query="cursor docs", num=2)
        self.assertEqual(result["query"], "cursor docs")
        self.assertEqual(result["provider"], "serper")
        self.assertEqual(result["attempted_providers"], ["serper"])
        self.assertEqual(
            result["results"],
            [
                {
                    "title": "Cursor Docs",
                    "url": "https://cursor.com/docs",
                    "snippet": "Official documentation.",
                    "source": "serper",
                    "rank": 1,
                },
                {
                    "title": "Cursor Blog",
                    "url": "https://cursor.com/blog",
                    "snippet": "Product updates.",
                    "source": "serper",
                    "rank": 2,
                },
            ],
        )

    def test_search_web_auto_falls_back_to_configured_provider(self) -> None:
        raw_result = {
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "Bocha Result",
                            "url": "https://example.com/bocha",
                            "summary": "Fallback result.",
                        }
                    ]
                }
            }
        }

        with (
            patch.dict(
                search_tools.setting,
                {"serper_key": "", "bocha_key": "enabled", "tavily_key": "", "jina_key": ""},
            ),
            patch.object(search_tools, "bocha_search", return_value=raw_result) as mocked_bocha,
        ):
            result = search_tools.search_web("fallback case", provider="auto", count=2)

        mocked_bocha.assert_called_once_with(
            query="fallback case",
            count=2,
            summary=True,
            freshness="noLimit",
        )
        self.assertEqual(result["provider"], "bocha")
        self.assertEqual(result["attempted_providers"], ["bocha"])
        self.assertEqual(result["results"][0]["source"], "bocha")

    def test_search_web_auto_falls_back_after_provider_error(self) -> None:
        serper_error = {"error": "Serper 搜索请求失败: timeout"}
        tavily_result = {
            "results": [
                {
                    "title": "Tavily Result",
                    "url": "https://example.com/tavily",
                    "content": "Recovered after fallback.",
                }
            ]
        }

        with (
            patch.dict(
                search_tools.setting,
                {
                    "serper_key": "enabled",
                    "bocha_key": "",
                    "tavily_key": "enabled",
                    "jina_key": "",
                },
            ),
            patch.object(search_tools, "serper_search", return_value=serper_error) as mocked_serper,
            patch.object(search_tools, "tavily_search", return_value=tavily_result) as mocked_tavily,
        ):
            result = search_tools.search_web("recover search", provider="auto", count=2)

        mocked_serper.assert_called_once_with(query="recover search", num=2)
        mocked_tavily.assert_called_once_with(query="recover search", max_results=2)
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(result["attempted_providers"], ["serper", "tavily"])
        self.assertEqual(result["results"][0]["source"], "tavily")

    def test_search_web_auto_falls_back_after_empty_results(self) -> None:
        empty_serper = {"organic": []}
        jina_result = {
            "data": [
                {
                    "title": "Jina Result",
                    "url": "https://example.com/jina",
                    "description": "Recovered from empty results.",
                }
            ]
        }

        with (
            patch.dict(
                search_tools.setting,
                {"serper_key": "enabled", "bocha_key": "", "tavily_key": "", "jina_key": ""},
            ),
            patch.object(search_tools, "serper_search", return_value=empty_serper) as mocked_serper,
            patch.object(search_tools, "jina_search", return_value=jina_result) as mocked_jina,
        ):
            result = search_tools.search_web("empty recover", provider="auto", count=2)

        mocked_serper.assert_called_once_with(query="empty recover", num=2)
        mocked_jina.assert_called_once_with(query="empty recover", with_content=False)
        self.assertEqual(result["provider"], "jina")
        self.assertEqual(result["attempted_providers"], ["serper", "jina"])
        self.assertEqual(result["results"][0]["source"], "jina")

    def test_search_web_auto_prefers_bocha_when_freshness_is_set(self) -> None:
        bocha_result = {
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "Fresh Result",
                            "url": "https://example.com/fresh",
                            "summary": "Freshness aware result.",
                        }
                    ]
                }
            }
        }

        with (
            patch.dict(
                search_tools.setting,
                {
                    "serper_key": "enabled",
                    "bocha_key": "enabled",
                    "tavily_key": "",
                    "jina_key": "",
                },
            ),
            patch.object(search_tools, "bocha_search", return_value=bocha_result) as mocked_bocha,
            patch.object(search_tools, "serper_search") as mocked_serper,
        ):
            result = search_tools.search_web(
                "fresh news",
                provider="auto",
                count=2,
                freshness="oneWeek",
            )

        mocked_bocha.assert_called_once_with(
            query="fresh news",
            count=2,
            summary=True,
            freshness="oneWeek",
        )
        mocked_serper.assert_not_called()
        self.assertEqual(result["provider"], "bocha")
        self.assertEqual(result["attempted_providers"], ["bocha"])

    def test_search_web_normalizes_tavily_results(self) -> None:
        raw_result = {
            "results": [
                {
                    "title": "Release Notes",
                    "url": "https://example.com/release",
                    "content": "Latest release details.",
                    "score": 0.98,
                },
                {
                    "title": "Discard Me",
                    "url": "",
                    "content": "Missing URL should be ignored.",
                },
            ]
        }

        with patch.object(search_tools, "tavily_search", return_value=raw_result) as mocked:
            result = search_tools.search_web("release", provider="tavily", count=3)

        mocked.assert_called_once_with(query="release", max_results=3)
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(
            result["results"],
            [
                {
                    "title": "Release Notes",
                    "url": "https://example.com/release",
                    "snippet": "Latest release details.",
                    "source": "tavily",
                    "rank": 1,
                }
            ],
        )

    def test_search_web_returns_structured_error_for_provider_failures(self) -> None:
        with patch.object(
            search_tools,
            "serper_search",
            return_value={"error": "Serper 搜索请求失败: timeout"},
        ):
            result = search_tools.search_web("timeout case", provider="serper")

        self.assertEqual(result["query"], "timeout case")
        self.assertEqual(result["provider"], "serper")
        self.assertEqual(result["results"], [])
        self.assertIn("timeout", result["error"])

    def test_search_web_rejects_unknown_provider(self) -> None:
        result = search_tools.search_web("cursor", provider="unknown")

        self.assertEqual(result["query"], "cursor")
        self.assertEqual(result["provider"], "unknown")
        self.assertEqual(result["results"], [])
        self.assertIn("不支持的 provider", result["error"])

    def test_search_and_read_fetches_top_k_markdown_documents(self) -> None:
        search_result = {
            "query": "python packaging",
            "provider": "serper",
            "results": [
                {
                    "title": "PEP 621",
                    "url": "https://example.com/pep-621",
                    "snippet": "Metadata for Python projects.",
                    "source": "serper",
                    "rank": 1,
                },
                {
                    "title": "PyPA Guide",
                    "url": "https://example.com/pypa-guide",
                    "snippet": "Packaging tutorial.",
                    "source": "serper",
                    "rank": 2,
                },
                {
                    "title": "Ignored",
                    "url": "https://example.com/ignored",
                    "snippet": "Should not be fetched.",
                    "source": "serper",
                    "rank": 3,
                },
            ],
        }

        with (
            patch.object(search_tools, "search_web", return_value=search_result) as mocked_search,
            patch.object(
                search_tools,
                "fetch_markdown",
                side_effect=["# PEP 621", "# PyPA Guide"],
            ) as mocked_fetch,
        ):
            result = search_tools.search_and_read(
                "python packaging",
                top_k=2,
                provider="auto",
            )

        mocked_search.assert_called_once_with(
            query="python packaging",
            count=2,
            provider="auto",
        )
        self.assertEqual(mocked_fetch.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in mocked_fetch.call_args_list],
            [
                "https://example.com/pep-621",
                "https://example.com/pypa-guide",
            ],
        )
        self.assertEqual(result["query"], "python packaging")
        self.assertEqual(result["provider"], "serper")
        self.assertEqual(len(result["search_results"]), 3)
        self.assertEqual(
            result["documents"],
            [
                {
                    "title": "PEP 621",
                    "url": "https://example.com/pep-621",
                    "snippet": "Metadata for Python projects.",
                    "markdown": "# PEP 621",
                },
                {
                    "title": "PyPA Guide",
                    "url": "https://example.com/pypa-guide",
                    "snippet": "Packaging tutorial.",
                    "markdown": "# PyPA Guide",
                },
            ],
        )

    def test_search_and_read_returns_structured_error_when_search_fails(self) -> None:
        with patch.object(
            search_tools,
            "search_web",
            return_value={
                "query": "bad case",
                "provider": "serper",
                "results": [],
                "error": "Serper 搜索请求失败: timeout",
            },
        ):
            result = search_tools.search_and_read("bad case")

        self.assertEqual(result["query"], "bad case")
        self.assertEqual(result["provider"], "serper")
        self.assertEqual(result["search_results"], [])
        self.assertEqual(result["documents"], [])
        self.assertIn("timeout", result["error"])

    def test_profile_tutorial_documents_research_profiles(self) -> None:
        repo_root: Path = Path(__file__).resolve().parents[1]
        profile_doc = repo_root.joinpath("docs/source/tutorial/profile.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("联网研究助手", profile_doc)
        self.assertIn("联网研究助手-调试", profile_doc)
        self.assertIn("search-tools_search-web", profile_doc)
        self.assertIn("search-tools_search-and-read", profile_doc)
        self.assertIn("web-tools_fetch-markdown", profile_doc)
        self.assertIn("search-tools_serper-search", profile_doc)
        self.assertIn("use_skills=True", profile_doc)


if __name__ == "__main__":
    unittest.main()
