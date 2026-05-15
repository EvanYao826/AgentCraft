import requests
import json

BASE_URL = "http://localhost:8000/api/ask"

def test_memory():
    """测试记忆系统"""
    conversation_id = "test-memory-001"

    # 第一轮
    print("=== 第一轮对话 ===")
    resp1 = requests.post(BASE_URL, json={
        "question": "你好，我是张三",
        "conversation_id": conversation_id
    })
    data1 = resp1.json()
    print(f"问题: 你好，我是张三")
    print(f"回答: {data1.get('answer', '')[:100]}")
    print()

    # 第二轮
    print("=== 第二轮对话 ===")
    resp2 = requests.post(BASE_URL, json={
        "question": "我叫什么名字？",
        "conversation_id": conversation_id
    })
    data2 = resp2.json()
    print(f"问题: 我叫什么名字？")
    print(f"回答: {data2.get('answer', '')[:100]}")
    print()

    # 判断记忆是否生效
    answer = data2.get('answer', '')
    if '张三' in answer:
        print("✅ 记忆系统生效！AI 记住了你的名字")
    else:
        print("❌ 记忆系统未生效，AI 没记住你的名字")

if __name__ == "__main__":
    test_memory()
