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

    def test_web_tool_descriptions_encourage_search_then_read_workflow(self) -> None:
        markdown_description = web_tools.fetch_markdown_tool.get_schema().description
        self.assertIn("先用搜索工具发现候选来源", markdown_description)
        self.assertIn("交叉验证多个来源", markdown_description)

        check_link_description = web_tools.check_link_tool.get_schema().description
        self.assertIn("不能替代正文阅读", check_link_description)


if __name__ == "__main__":
    unittest.main()
