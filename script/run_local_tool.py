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

    date = manager.execute_tool("get_current_date", {})
    print(f"get_current_date: {date}")

    time = manager.execute_tool("get_current_time", {})
    print(f"get_current_time: {time}")

    datetime = manager.execute_tool("get_current_datetime", {})
    print(f"get_current_datetime: {datetime}")

    day = manager.execute_tool("get_day_of_week", {})
    print(f"get_day_of_week: {day}")


if __name__ == "__main__":
    run()
