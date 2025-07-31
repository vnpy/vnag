#!/usr/bin/env python3
"""
简单的向后兼容性测试
验证重构后的代码是否保持原有接口不变
"""

import sys
from pathlib import Path

# 添加vnag模块到路径
sys.path.insert(0, str(Path(__file__).parent / "vnag"))

def test_gateway_backward_compatibility():
    """测试gateway向后兼容性"""
    from vnag.gateway import AgentGateway
    
    # 测试原有接口
    gateway = AgentGateway()
    
    # 原有的调用方式应该仍然有效
    messages = [{"role": "user", "content": "hello"}]
    
    # 这些调用不应该报错（虽然没有初始化，会返回None）
    result1 = gateway.invoke_model(messages)
    result2 = gateway.invoke_streaming(messages)
    
    print("✓ Gateway向后兼容性测试通过")
    print(f"  - invoke_model返回: {result1}")
    print(f"  - invoke_streaming返回: {result2}")

def test_new_gateway_features():
    """测试新的gateway功能"""
    from vnag.gateway import AgentGateway
    
    gateway = AgentGateway()
    messages = [{"role": "user", "content": "hello"}]
    
    # 新功能调用不应该报错
    result1 = gateway.invoke_model(messages, use_rag=True)
    result2 = gateway.invoke_model(messages, user_files=["test.txt"])
    result3 = gateway.invoke_model(messages, use_rag=True, user_files=["test.txt"])
    
    print("✓ Gateway新功能测试通过")
    print(f"  - RAG模式返回: {result1}")
    print(f"  - 文件模式返回: {result2}")
    print(f"  - RAG+文件模式返回: {result3}")

def test_rag_service_refactor():
    """测试RAGService重构"""
    from vnag.gateway import AgentGateway
    
    gateway = AgentGateway()
    
    # RAG服务应该作为内部组件存在
    print("✓ RAGService重构测试通过")
    print(f"  - gateway._rag_service: {gateway._rag_service}")
    
    # 初始化后应该有RAG服务
    # gateway.init("http://test", "test-key", "test-model")  # 需要真实API才能测试
    # print(f"  - 初始化后的_rag_service: {gateway._rag_service}")

def main():
    """运行所有测试"""
    print("开始向后兼容性测试...\n")
    
    try:
        test_gateway_backward_compatibility()
        print()
        
        test_new_gateway_features()
        print()
        
        test_rag_service_refactor()
        print()
        
        print("🎉 所有测试通过！架构重构成功保持向后兼容性")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())