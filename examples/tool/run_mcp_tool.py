from vnag.mcp import McpManager


def main() -> None:
    """运行函数"""
    manager = McpManager()

    # 获取并打印所有MCP工具的Schema
    tools = manager.list_tools()
    print("列出所有 MCP 工具：")
    for tool in tools:
        print(tool.model_dump())

    # 执行工具并打印结果
    print("\n" + "=" * 30 + "\n")
    print("执行 MCP 工具：")

    # 如果存在名为 "filesystem_list_directory" 的工具，则执行它
    if any(tool.name == "filesystem_list_directory" for tool in tools):
        result = manager.execute_tool(
            "filesystem_list_directory",
            {"path": "."}
        )
        print(f"filesystem_list_directory: {result}")
    else:
        print("\n未找到名为 [filesystem_list_directory] 的 MCP 工具。")


if __name__ == "__main__":
    main()
