import json
from pathlib import Path
from collections.abc import Generator
from datetime import datetime

from .gateway import BaseGateway
from .object import (
    Request,
    Delta,
    ToolCall,
    ToolResult,
    ToolSchema,
    Session
)
from .mcp import McpManager
from .local import LocalManager, LocalTool
from .agent import Profile, TaskAgent
from .utility import PROFILE_DIR, SESSION_DIR


# 默认智能体配置
default_profile: Profile = Profile(
    name="聊天助手",
    prompt="你是一个乐于助人的聊天助手，请根据用户的问题回答。",
    tools=[]
)


class AgentEngine:
    """
    智能体引擎：负责智能体类的发现和注册，并提供智能体实例创建的工厂方法。
    """

    def __init__(self, gateway: BaseGateway) -> None:
        """构造函数"""
        self.gateway: BaseGateway = gateway

        self._local_manager: LocalManager = LocalManager()
        self._mcp_manager: McpManager = McpManager()

        self._local_tools: dict[str, ToolSchema] = {}
        self._mcp_tools: dict[str, ToolSchema] = {}

        self._profiles: dict[str, Profile] = {}
        self._agents: dict[str, TaskAgent] = {}

    def init(self) -> None:
        """初始化引擎"""
        self._load_local_tools()
        self._load_mcp_tools()

        self._load_profiles()
        self._load_agents()

    def _load_local_tools(self) -> None:
        """加载本地工具"""
        for schema in self._local_manager.list_tools():
            self._local_tools[schema.name] = schema

    def _load_mcp_tools(self) -> None:
        """加载MCP工具"""
        for schema in self._mcp_manager.list_tools():
            self._mcp_tools[schema.name] = schema

    def _load_profiles(self) -> None:
        """加载智能体配置"""
        # 添加默认智能体配置
        self._profiles[default_profile.name] = default_profile

        # 加载用户自定义配置
        for file_path in PROFILE_DIR.glob("*.json"):
            with open(file_path, encoding="UTF-8") as f:
                data: dict = json.load(f)
                profile: Profile = Profile.model_validate(data)
                self._profiles[profile.name] = profile

    def _save_profile(self, profile: Profile) -> None:
        """保存智能体配置到JSON文件"""
        profile_path: Path = PROFILE_DIR.joinpath(f"{profile.name}.json")
        with open(profile_path, "w", encoding="UTF-8") as f:
            json.dump(profile.model_dump(), f, indent=4, ensure_ascii=False)

    def _load_agents(self) -> None:
        """从JSON文件加载所有智能体"""
        for file_path in SESSION_DIR.glob("*.json"):
            with open(file_path, encoding="UTF-8") as f:
                data: dict = json.load(f)
                session: Session = Session.model_validate(data)
                profile: Profile = self._profiles[session.profile]
                agent: TaskAgent = TaskAgent(self, profile, session)
                self._agents[session.id] = agent

    def add_profile(self, profile: Profile) -> bool:
        """添加智能体配置"""
        if profile.name in self._profiles:
            return False

        self._profiles[profile.name] = profile

        self._save_profile(profile)

        return True

    def update_profile(self, profile: Profile) -> bool:
        """更新智能体配置"""
        if profile.name not in self._profiles:
            return False

        self._profiles[profile.name] = profile

        self._save_profile(profile)

        return True

    def delete_profile(self, name: str) -> bool:
        """删除智能体配置"""
        if name not in self._profiles:
            return False

        self._profiles.pop(name)

        profile_path: Path = PROFILE_DIR.joinpath(f"{name}.json")
        profile_path.unlink()

        return True

    def get_profile(self, name: str) -> Profile | None:
        """获取智能体配置"""
        return self._profiles.get(name)

    def get_all_profiles(self) -> list[Profile]:
        """获取所有智能体配置"""
        return list(self._profiles.values())

    def create_agent(self, profile: Profile) -> TaskAgent:
        """新建智能体"""
        # 使用时间戳作为会话编号
        now: datetime = datetime.now()
        session_id: str = now.strftime("%Y%m%d_%H%M%S_%f")

        # 创建会话
        session: Session = Session(
            id=session_id,
            profile=profile.name,
            name="默认会话"
        )

        # 创建智能体
        agent: TaskAgent = TaskAgent(self, profile, session)

        # 保存会话
        self._agents[session.id] = agent

        return agent

    def delete_agent(self, session_id: str) -> bool:
        """删除智能体"""
        if session_id not in self._agents:
            return False

        self._agents.pop(session_id)

        session_path: Path = SESSION_DIR.joinpath(f"{session_id}.json")
        session_path.unlink()

        return True

    def get_agent(self, session_id: str) -> TaskAgent | None:
        """获取智能体"""
        return self._agents.get(session_id)

    def get_all_agents(self) -> list[TaskAgent]:
        """获取所有智能体"""
        return list(self._agents.values())

    def register_tool(self, tool: LocalTool) -> None:
        """注册本地工具函数"""
        self._local_manager.register_tool(tool)

        self._local_tools[tool.name] = tool.get_schema()

    def get_tool_schemas(self, tools: list[str] | None = None) -> list[ToolSchema]:
        """获取所有工具的Schema"""
        local_schemas: list[ToolSchema] = list(self._local_tools.values())
        mcp_schemas: list[ToolSchema] = list(self._mcp_tools.values())
        all_schemas: list[ToolSchema] = local_schemas + mcp_schemas

        if tools is not None:
            tool_schemas: list[ToolSchema] = []
            for schema in all_schemas:
                if schema.name in tools:
                    tool_schemas.append(schema)
            return tool_schemas
        else:
            return all_schemas

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        return self.gateway.list_models()

    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """执行单个工具并返回结果"""
        if tool_call.name in self._local_tools:
            result_content: str = self._local_manager.execute_tool(
                tool_call.name,
                tool_call.arguments
            )
        elif tool_call.name in self._mcp_tools:
            result_content = self._mcp_manager.execute_tool(
                tool_call.name,
                tool_call.arguments
            )
        else:
            result_content = ""

        return ToolResult(
            id=tool_call.id,
            name=tool_call.name,
            content=result_content,
            is_error=bool(result_content)
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """
        流式对话接口，通过生成器（Generator）实时返回 AI 的思考和回复。

        Args:
            request (Request): 请求对象。

        Yields:
            Generator[Delta, None, None]: 一个增量数据（Delta）的生成器。
        """
        return self.gateway.stream(request)
