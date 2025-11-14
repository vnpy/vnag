from vnag.local import LocalManager


def run() -> None:
    """运行函数"""
    # 初始化本地工具管理器
    manager = LocalManager()

    # 获取并打印所有本地工具的Schema
    tools = manager.list_tools()
    print("列出所有本地工具：")
    for tool in tools:
        print(tool.model_dump())

    # 执行工具并打印结果
    print("\n" + "=" * 30 + "\n")
    print("执行本地工具：")

    # datetime_tools
    print("-" * 30)
    date = manager.execute_tool("get_current_date", {})
    print(f"get_current_date: {date}")

    print("-" * 30)
    time = manager.execute_tool("get_current_time", {})
    print(f"get_current_time: {time}")

    print("-" * 30)
    datetime = manager.execute_tool("get_current_datetime", {})
    print(f"get_current_datetime: {datetime}")

    print("-" * 30)
    day = manager.execute_tool("get_day_of_week", {})
    print(f"get_day_of_week: {day}")

    # file_tools
    print("-" * 30)
    result = manager.execute_tool("list_directory", {"path": "."})
    print(f"list_directory: {result}\n")

    print("-" * 30)
    result = manager.execute_tool(
        "write_file",
        {"path": "test.txt", "content": "Hello from local_tool!"}
    )
    print(f"write_file: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("read_file", {"path": "test.txt"})
    print(f"read_file: {result}")

    print("-" * 30)
    result = manager.execute_tool("glob_files", {"path": ".", "pattern": "*.txt"})
    print(f"glob_files: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("search_content", {"path": ".\\examples", "content": "Hello from local_tool!"})
    print(f"search_content: {result}\n")

    print("-" * 30)
    result = manager.execute_tool(
        "replace_content",
        {"path": "test.txt", "old_content": "local_tool", "new_content": "vnag"}
    )
    print(f"replace_content: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("read_file", {"path": "test.txt"})
    print(f"read_file after replace: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("delete_file", {"path": "test.txt"})
    print(f"delete_file: {result}\n")

    # network_tools
    print("-" * 30)
    result = manager.execute_tool("get_local_ip", {})
    print(f"get_local_ip: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("get_mac_address", {})
    print(f"get_mac_address: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("ping", {"host": "www.baidu.com"})
    print(f"ping: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("telnet", {"host": "www.baidu.com", "port": 80})
    print(f"telnet: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("get_public_ip", {})
    print(f"get_public_ip: {result}")

    # web_tools
    print("-" * 30)
    result = manager.execute_tool("fetch_html", {"url": "http://www.vnpy.com"})
    print(f"fetch_html (first 100 chars): {str(result)[:100]}...\n")

    print("-" * 30)
    result = manager.execute_tool(
        "fetch_json",
        {"url": "https://api.vnpy.com/ip"}
    )
    print(f"fetch_json: {result}\n")

    print("-" * 30)
    result = manager.execute_tool("check_link", {"url": "http://www.vnpy.com"})
    print(f"check_link: {result}\n")


if __name__ == "__main__":
    run()
