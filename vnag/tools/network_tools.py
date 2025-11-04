"""
常用的网络函数工具
"""
import socket
import subprocess
import uuid

import requests

from vnag.local import LocalTool


def ping(host: str) -> str:
    """
    通过执行ping命令并返回结果，检查与主机的网络连通性。

    :param host: 要ping的主机名或IP地址。
    :return: ping命令的输出，如果主机无法访问则返回错误消息。
    """
    try:
        output: bytes = subprocess.check_output(
            f"ping {host} -n 1",
            stderr=subprocess.STDOUT,
            shell=True
        )
        result: str = output.decode("gbk")
        return result
    except subprocess.CalledProcessError as e:
        result = e.output.decode("gbk")
        return result


def telnet(host: str, port: int) -> str:
    """
    通过尝试与指定主机的端口建立套接字连接来测试端口是否打开。

    :param host: 要连接的主机名或IP地址。
    :param port: 要测试的端口号。
    :return: 成功或失败消息。
    """
    try:
        with socket.create_connection((host, port), timeout=2):
            return f"成功连接到 {host} 位于端口 {port}"
    except OSError as e:
        return f"连接到 {host} 位于端口 {port} 失败: {e}"


def get_local_ip() -> str:
    """
    获取本机的局域网IP地址。

    :return: 局域网IP地址的字符串，如果无法确定则返回“未知”。
    """
    try:
        s: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address: str = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception:
        return "127.0.0.1"


def get_public_ip() -> str:
    """
    通过请求外部服务来获取本机的公网IP地址。

    :return: 公网IP地址的字符串，如果请求失败则返回错误消息。
    """
    try:
        response: requests.Response = requests.get("https://api.vnpy.com/ip")
        response.raise_for_status()
        result: str = response.text
        return result
    except requests.exceptions.RequestException as e:
        return f"获取公网IP地址时出错: {e}"


def get_mac_address() -> str:
    """
    获取本机的MAC地址。

    :return: MAC地址的字符串，格式为 XX:XX:XX:XX:XX:XX。
    """
    mac_hex: str = f"{uuid.getnode():012X}"
    return ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))


# 注册工具
ping_tool: LocalTool = LocalTool(ping)

telnet_tool: LocalTool = LocalTool(telnet)

get_local_ip_tool: LocalTool = LocalTool(get_local_ip)

get_public_ip_tool: LocalTool = LocalTool(get_public_ip)

get_mac_address_tool: LocalTool = LocalTool(get_mac_address)
