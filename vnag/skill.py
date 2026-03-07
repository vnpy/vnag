import re
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

from .object import ToolSchema
from .utility import WORKING_DIR


@dataclass
class Skill:
    """技能数据模型"""
    name: str
    description: str
    content: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    skill_dir: str = ""

    def to_prompt(self) -> str:
        """将技能转换为提示词格式"""
        return (
            f"# 技能: {self.name}\n\n"
            f"{self.description}\n\n"
            f"工作目录: {self.skill_dir}\n\n"
            f"---\n\n{self.content}"
        )


class SkillManager:
    """技能管理器：负责技能的发现、加载和管理"""

    TOOL_NAME: str = "get_skill"

    def __init__(self) -> None:
        """构造函数"""
        self._skills: dict[str, Skill] = {}

    def load_skills(self) -> None:
        """扫描 skills/ 目录，加载所有 SKILL.md 文件"""
        skills_dir: Path = WORKING_DIR / "skills"

        if not skills_dir.exists():
            return

        for skill_file in skills_dir.rglob("SKILL.md"):
            skill: Skill | None = self._parse_skill_file(skill_file)
            if skill:
                self._skills[skill.name] = skill

    def _parse_skill_file(self, path: Path) -> Skill | None:
        """解析 SKILL.md 文件，提取 YAML frontmatter 和正文"""
        try:
            text: str = path.read_text(encoding="utf-8")

            # 用正则提取 YAML frontmatter
            match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
            if not match:
                print(f"Skill [{path}] missing YAML frontmatter")
                return None

            frontmatter_text: str = match.group(1)
            content: str = match.group(2).strip()

            # 解析 YAML
            try:
                frontmatter: dict = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                print(f"Skill [{path}] YAML parse failed: {e}")
                return None

            # 校验必填字段
            if "name" not in frontmatter or "description" not in frontmatter:
                print(f"Skill [{path}] missing required fields: name or description")
                return None

            # 获取技能目录并处理路径
            skill_dir: Path = path.parent
            processed_content: str = self._process_skill_paths(content, skill_dir)

            return Skill(
                name=frontmatter["name"],
                description=frontmatter["description"],
                content=processed_content,
                metadata=frontmatter.get("metadata", {}),
                skill_dir=str(skill_dir),
            )
        except Exception:
            msg: str = f"Skill [{path}] load failed: {traceback.format_exc()}"
            print(msg)
            return None

    def _process_skill_paths(self, content: str, skill_dir: Path) -> str:
        """将 SKILL.md 正文中的相对路径转换为绝对路径"""
        # 模式1：目录类路径（scripts/, examples/, templates/, reference/）
        def replace_dir_path(match: re.Match) -> str:
            prefix: str = match.group(1)
            rel_path: str = match.group(2)
            abs_path: Path = skill_dir / rel_path
            if abs_path.exists():
                return f"{prefix}{abs_path}"
            return cast(str, match.group(0))

        pattern_dirs: str = r"(python\s+|`)((?:scripts|examples|templates|reference)/[^\s`\)]+)"
        content = re.sub(pattern_dirs, replace_dir_path, content)

        # 模式2：直接文档引用（see reference.md、read forms.md 等）
        def replace_doc_path(match: re.Match) -> str:
            prefix: str = match.group(1)
            filename: str = match.group(2)
            suffix: str = match.group(3)
            abs_path: Path = skill_dir / filename
            if abs_path.exists():
                return f"{prefix}`{abs_path}` (use read_file to access){suffix}"
            return cast(str, match.group(0))

        pattern_docs: str = r"(see|read|refer to|check)\s+([a-zA-Z0-9_-]+\.(?:md|txt|json|yaml))([.,;\s])"
        content = re.sub(pattern_docs, replace_doc_path, content, flags=re.IGNORECASE)

        # 模式3：Markdown 链接
        def replace_markdown_link(match: re.Match) -> str:
            prefix: str = match.group(1) if match.group(1) else ""
            link_text: str = match.group(2)
            filepath: str = match.group(3)
            clean_path: str = filepath[2:] if filepath.startswith("./") else filepath
            abs_path: Path = skill_dir / clean_path
            if abs_path.exists():
                return f"{prefix}[{link_text}](`{abs_path}`) (use read_file to access)"
            return cast(str, match.group(0))

        pattern_markdown: str = (
            r"(?:(Read|See|Check|Refer to|Load|View)\s+)?"
            r"\[(`?[^`\]]+`?)\]"
            r"\(((?:\./)?[^)]+\.(?:md|txt|json|yaml|js|py|html))\)"
        )
        content = re.sub(pattern_markdown, replace_markdown_link, content, flags=re.IGNORECASE)

        return content

    def get_skill(self, name: str) -> Skill | None:
        """按名称获取 Skill 对象"""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """返回所有已加载技能名称列表"""
        return list(self._skills.keys())

    def get_skill_catalog(self) -> str:
        """生成 Level 1 元数据文本，用于注入 System Prompt"""
        if not self._skills:
            return ""

        lines: list[str] = [
            "## 可用技能\n",
            "你拥有以下专业技能，可在需要时通过 get_skill 工具加载完整操作指南：\n",
        ]

        for skill in self._skills.values():
            lines.append(f"- `{skill.name}`: {skill.description}")

        lines.append("")
        lines.append("使用方式：")
        lines.append("1. 判断用户需求是否匹配某个技能")
        lines.append("2. 调用 get_skill(skill_name=\"xxx\") 加载完整操作指南")
        lines.append("3. 严格按照技能指令执行任务")

        return "\n".join(lines)

    def get_tool_schema(self) -> ToolSchema | None:
        """返回 get_skill 工具的 ToolSchema（如果没有技能则返回 None）"""
        if not self._skills:
            return None

        return ToolSchema(
            name=self.TOOL_NAME,
            description="加载指定技能的完整操作指南。在执行技能相关任务前，必须先调用此工具获取详细指令。",
            parameters={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "要加载的技能名称",
                    }
                },
                "required": ["skill_name"],
            },
        )

    def execute_tool(self, skill_name: str) -> str:
        """执行 get_skill 工具调用，返回完整技能内容字符串"""
        skill: Skill | None = self._skills.get(skill_name)
        if not skill:
            available: str = ", ".join(self._skills.keys())
            return f"Error: 技能 [{skill_name}] 不存在。可用技能: {available}"
        return skill.to_prompt()
