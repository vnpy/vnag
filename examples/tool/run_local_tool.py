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
    date = manager.execute_tool("get_current_date", {})
    print(f"get_current_date: {date}")

    time = manager.execute_tool("get_current_time", {})
    print(f"get_current_time: {time}")

    datetime = manager.execute_tool("get_current_datetime", {})
    print(f"get_current_datetime: {datetime}")

    day = manager.execute_tool("get_day_of_week", {})
    print(f"get_day_of_week: {day}")

    # file_tools
    result = manager.execute_tool("list_directory", {"path": "."})
    print(f"list_directory: {result}\n")

    result = manager.execute_tool(
        "write_file",
        {"path": "test.txt", "content": "Hello from local_tool!"}
    )
    print(f"write_file: {result}\n")

    result = manager.execute_tool("read_file", {"path": "test.txt"})
    print(f"read_file: {result}")

    # network_tools
    result = manager.execute_tool("get_local_ip", {})
    print(f"get_local_ip: {result}\n")

    result = manager.execute_tool("get_mac_address", {})
    print(f"get_mac_address: {result}\n")

    result = manager.execute_tool("ping", {"host": "www.baidu.com"})
    print(f"ping: {result}\n")

    result = manager.execute_tool("telnet", {"host": "www.baidu.com", "port": 80})
    print(f"telnet: {result}\n")

    print("正在获取公网IP...")
    result = manager.execute_tool("get_public_ip", {})
    print(f"get_public_ip: {result}")


if __name__ == "__main__":
    run()
