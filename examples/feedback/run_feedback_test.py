"""
反馈收集服务测试脚本

运行前请先启动服务器：
uvicorn feedback_server.app:app --reload --port 8000
"""

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta

import requests

# 配置
SERVER_URL = "http://localhost:8000"
USER_ID = "test_user_001"


def create_test_session() -> tuple[dict, str]:
    """创建测试session数据"""
    session_data: dict = {
        "id": "test_session_001",
        "profile": "默认助手",
        "name": "测试对话",
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "你好"},
            {
                "role": "assistant",
                "content": "你好！有什么可以帮助你的吗？",
            },
            {"role": "user", "content": "介绍一下Python"},
            {
                "role": "assistant",
                "content": "Python是一种高级编程语言，具有简洁的语法和强大的功能。",
            },
        ],
    }

    session_json: str = json.dumps(session_data, ensure_ascii=False, indent=2)
    return session_data, session_json


def create_test_profile() -> tuple[dict, str, str, str]:
    """创建测试profile数据"""
    profile_data: dict = {
        "name": "默认助手",
        "description": "通用AI助手",
        "instructions": "你是一个友好、专业的AI助手。",
        "temperature": 0.7,
        "tools": [],
    }

    profile_json: str = json.dumps(
        profile_data, sort_keys=True, ensure_ascii=False
    )
    profile_hash: str = hashlib.md5(profile_json.encode()).hexdigest()
    profile_filename: str = f"{profile_hash}--{profile_data['name']}.json"

    return profile_data, profile_json, profile_hash, profile_filename


def test_upload_feedback(rating: str = "thumbs_up", comment: str = "") -> bool:
    """测试上传反馈"""
    print(f"\n{'='*60}")
    print(f"测试上传反馈 - Rating: {rating}")
    print(f"{'='*60}\n")

    session_data: dict
    session_json: str
    session_data, session_json = create_test_session()

    profile_data: dict
    profile_json: str
    profile_hash: str
    profile_filename: str
    (
        profile_data,
        profile_json,
        profile_hash,
        profile_filename,
    ) = create_test_profile()

    files: dict = {
        "session_file": ("session.json", session_json),
        "profile_file": (profile_filename, profile_json),
    }

    data: dict = {
        "user_id": USER_ID,
        "session_id": session_data["id"],
        "session_name": session_data["name"],
        "profile_name": profile_data["name"],
        "profile_hash": profile_hash,
        "model": session_data["model"],
        "rating": rating,
        "comment": comment,
    }

    print("发送请求到服务器...")
    session_id_value: str = data['session_id']
    print(f"Session ID: {session_id_value}")
    profile_hash_short: str = profile_hash[:8]
    profile_name_value: str = data['profile_name']
    print(f"Profile: {profile_name_value} (hash: {profile_hash_short}...)")
    print(f"Model: {data['model']}")
    print(f"Rating: {data['rating']}")
    if comment:
        print(f"Comment: {comment}")

    response = requests.post(
        f"{SERVER_URL}/api/feedback", files=files, data=data, timeout=10
    )

    if response.status_code == 200:
        print("\n[成功] 上传成功！")
        return True

    print(f"\n[失败] 上传失败: {response.status_code}")
    print(f"响应: {response.text}")
    return False


def test_query_feedback() -> bool:
    """测试查询反馈"""
    print(f"\n{'='*60}")
    print("测试查询反馈")
    print(f"{'='*60}\n")

    response = requests.get(
        f"{SERVER_URL}/api/feedbacks",
        params={"user_id": USER_ID},
        timeout=10,
    )

    if response.status_code == 200:
        result: dict = response.json()
        feedbacks: list = result["feedbacks"]
        if feedbacks:
            feedback: dict = feedbacks[0]
            print("[成功] 查询成功！")
            print(f"\nSession: {feedback['session_name']}")
            print(f"Profile: {feedback['profile_name']}")
            print(f"Model: {feedback['model']}")
            print(f"Rating: {feedback['rating']}")
            print(f"Comment: {feedback['comment']}")
            print(f"Updated: {feedback['updated_at']}")
            return True

        print("[失败] 未找到反馈记录")
        return False

    print(f"[失败] 查询失败: {response.status_code}")
    return False


def test_load_feedbacks() -> bool:
    """测试批量加载反馈"""
    print(f"\n{'='*60}")
    print("测试批量加载反馈")
    print(f"{'='*60}\n")

    response = requests.get(
        f"{SERVER_URL}/api/feedbacks", params={"user_id": USER_ID}, timeout=10
    )

    if response.status_code == 200:
        result: dict = response.json()
        feedbacks: list = result["feedbacks"]
        feedbacks_count: int = len(feedbacks)
        print(f"[成功] 加载成功！找到 {feedbacks_count} 条反馈记录\n")

        for i, feedback in enumerate(feedbacks, 1):
            print(f"{i}. {feedback['session_name']}")
            rating_info: str = feedback['rating']
            model_info: str = feedback['model']
            print(f"   Model: {model_info}, Rating: {rating_info}")
            updated_info: str = feedback['updated_at']
            print(f"   Updated: {updated_info}")

        return True

    print(f"[失败] 加载失败: {response.status_code}")
    return False


def test_datetime_filter() -> bool:
    """测试时间范围过滤"""
    print(f"\n{'='*60}")
    print("测试时间范围过滤")
    print(f"{'='*60}\n")

    now: datetime = datetime.now()
    start: str = (now - timedelta(days=7)).date().isoformat()
    end: str = now.date().isoformat()

    print(f"查询范围: {start} 到 {end}\n")

    response = requests.get(
        f"{SERVER_URL}/api/feedbacks",
        params={"start_time": start, "end_time": end},
        timeout=10,
    )

    if response.status_code == 200:
        result: dict = response.json()
        feedbacks: list = result["feedbacks"]
        print(f"[成功] 查询成功！共 {len(feedbacks)} 条记录")
        return True

    print(f"[失败] 查询失败: {response.status_code}")
    return False


def upload_feedback(
    session_id: str,
    profile_name: str,
    rating: str,
    comment: str,
    user_id: str = USER_ID,
) -> bool:
    """上传反馈（用于UPSERT测试）"""
    session_data: dict = {
        "id": session_id,
        "profile": profile_name,
        "name": f"测试会话_{session_id}",
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "测试消息"},
            {"role": "assistant", "content": "测试回复"},
        ],
    }

    session_json: str = json.dumps(session_data, ensure_ascii=False)

    profile_data: dict = {
        "name": profile_name,
        "description": f"{profile_name}的描述",
        "instructions": f"你是{profile_name}",
        "temperature": 0.7,
        "tools": [],
    }

    profile_json: str = json.dumps(
        profile_data, sort_keys=True, ensure_ascii=False
    )
    profile_hash: str = hashlib.md5(profile_json.encode()).hexdigest()
    profile_filename: str = f"{profile_hash}--{profile_data['name']}.json"

    files: dict = {
        "session_file": ("session.json", session_json),
        "profile_file": (profile_filename, profile_json),
    }

    data: dict = {
        "user_id": user_id,
        "session_id": session_id,
        "session_name": session_data["name"],
        "profile_name": profile_data["name"],
        "profile_hash": profile_hash,
        "model": session_data["model"],
        "rating": rating,
        "comment": comment,
    }

    try:
        response = requests.post(
            f"{SERVER_URL}/api/feedback", files=files, data=data, timeout=10
        )
        success: bool = response.status_code == 200
        return success
    except Exception as e:
        print(f"上传失败: {e}")
        return False


def test_upsert() -> bool:
    """测试upsert功能"""
    print(f"\n{'='*60}")
    print("测试UPSERT功能")
    print(f"{'='*60}\n")

    print("1. 首次上传（thumbs_up）")
    upload_feedback("upsert_001", "UPSERT测试", "thumbs_up", "首次上传测试")

    print("\n2. 更新记录（thumbs_down）")
    upload_feedback(
        "upsert_001", "UPSERT测试", "thumbs_down", "修改为踩，并添加评论"
    )

    print("\n3. 查询验证最终状态")
    response = requests.get(
        f"{SERVER_URL}/api/feedbacks",
        params={"user_id": USER_ID},
        timeout=10,
    )

    if response.status_code == 200:
        result: dict = response.json()
        feedbacks: list = result["feedbacks"]
        for feedback in feedbacks:
            if feedback["session_id"] == "upsert_001":
                print(f"[成功] Rating: {feedback['rating']}")
                print(f"Comment: {feedback['comment']}")
                is_correct: bool = feedback["rating"] == "thumbs_down"
                return is_correct

    print("[失败] 未找到记录")
    return False


def main() -> None:
    """主测试流程"""
    print("\n" + "=" * 60)
    print("反馈收集服务测试")
    print("=" * 60)

    print("\n请确保服务器已启动：")
    print("uvicorn feedback_server.app:app --reload --port 8000\n")

    input("按回车键开始测试...")

    tests: list[tuple[str, Callable[[], bool]]] = [
        (
            "基础上传测试（thumbs_up）",
            lambda: test_upload_feedback("thumbs_up", "这个对话很有帮助"),
        ),
        (
            "上传测试（thumbs_down）",
            lambda: test_upload_feedback("thumbs_down", "回答不够准确"),
        ),
        ("查询反馈", test_query_feedback),
        ("批量加载", test_load_feedbacks),
        ("时间过滤", test_datetime_filter),
        ("UPSERT功能", test_upsert),
    ]

    results: list[tuple[str, bool]] = []
    for name, test_func in tests:
        try:
            result: bool = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[失败] 测试失败: {e}")
            results.append((name, False))

    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}\n")

    passed: int = sum(1 for _, result in results if result)
    total: int = len(results)

    test_name: str
    test_result: bool
    for test_name, test_result in results:
        status: str
        if test_result:
            status = "[通过]"
        else:
            status = "[失败]"
        print(f"{status} - {test_name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n所有测试通过！")
    else:
        print("\n部分测试失败，请检查日志")


if __name__ == "__main__":
    main()
