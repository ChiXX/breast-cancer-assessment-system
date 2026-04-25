import httpx
import json

def test_mcp():
    base_url = "http://127.0.0.1:9001"
    
    print("=== [1] 测试评估接口 ===")
    try:
        r = httpx.post(f"{base_url}/v1/evaluate", json={
            "user_input": "你好，最近有点腹泻。",
            "session_id": "session_test_python"
        }, timeout=60.0)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== [2] 测试会话详情 ===")
    try:
        r = httpx.get(f"{base_url}/v1/sessions/session_test_python")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== [3] 查看所有技能 ===")
    try:
        r = httpx.get(f"{base_url}/v1/knowledge/skills")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mcp()
