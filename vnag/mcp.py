import asyncio
from concurrent.futures import Future
from typing import Any
from threading import Event, Thread

from mcp.types import Tool as McpToolType
from fastmcp import Client
from fastmcp.client.client import MCPConfig, CallToolResult

from .utility import load_json
from .object import ToolSchema


class McpManager:
    """MCP 管理器：负责 MCP 工具管理和执行"""

    config_path: str = "mcp_config.json"

    def __init__(self) -> None:
        """构造函数"""
        self.client: Client | None = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: Thread | None = None

        self.shutdown_future: asyncio.Future | None = None
        self.started_event: Event = Event()

        config_data: dict[str, Any] = load_json(self.config_path)
        if config_data:
            mcp_config: MCPConfig = MCPConfig.from_dict(config_data)
            self.client = Client(mcp_config)

            self.thread = Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def _run_loop(self) -> None:
        """在后台线程中运行事件循环"""
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 创建关闭事件循环的 future
        self.shutdown_future = self.loop.create_future()

        # 运行主循环
        async def main_loop() -> None:
            """主循环"""
            if not self.client:
                return

            # 启动MCP服务
            async with self.client:
                # 设置启动事件
                self.started_event.set()

                # 等待关闭事件
                if self.shutdown_future:
                    await self.shutdown_future

        self.loop.run_until_complete(main_loop())

    def __del__(self) -> None:
        """安全关闭后台线程和事件循环"""
        if self.loop and self.shutdown_future:
            self.loop.call_soon_threadsafe(self.shutdown_future.set_result, None)

        if self.thread:
            self.thread.join()

        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    def list_tools(self) -> list[ToolSchema]:
        """列出所有可用的 MCP 工具"""
        # 等待后台服务启动完成
        self.started_event.wait()

        # 如果客户端不存在（没有配置文件），则返回空列表
        if not self.client or not self.loop:
            return []

        # 在后台事件循环中执行任务
        async def _async_list_tools() -> list[ToolSchema]:
            """用于在事件循环中运行的异步函数"""
            try:
                assert self.client is not None

                # 列出所有MCP工具
                mcp_tools: list[McpToolType] = await self.client.list_tools()

                # 转换数据格式并返回
                tool_schemas: list[ToolSchema] = []

                for mcp_tool in mcp_tools:
                    tool_schema: ToolSchema = ToolSchema(
                        name=mcp_tool.name,
                        description=mcp_tool.description or "",
                        parameters=mcp_tool.inputSchema
                    )
                    tool_schemas.append(tool_schema)

                return tool_schemas
            except Exception as e:
                print(f"Failed to list MCP tools: {e}")
                return []

        future: Future[list[ToolSchema]] = asyncio.run_coroutine_threadsafe(
            coro=_async_list_tools(),
            loop=self.loop
        )
        return future.result()

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """执行 MCP 工具"""
        # 如果客户端不存在（没有配置文件），则返回错误信息
        if not self.client or not self.loop:
            return ""

        # 等待后台服务启动完成
        self.started_event.wait()

        # 在后台事件循环中执行任务
        async def _async_execute_tool() -> str:
            """用于在事件循环中运行的异步函数"""
            try:
                assert self.client is not None

                # 执行MCP工具调用
                result: CallToolResult = await self.client.call_tool(
                    tool_name, arguments
                )

                return str(result)
            except Exception as e:
                return f"Error executing MCP tool '{tool_name}': {str(e)}"

        future: Future[str] = asyncio.run_coroutine_threadsafe(
            coro=_async_execute_tool(),
            loop=self.loop
        )
        return future.result()
