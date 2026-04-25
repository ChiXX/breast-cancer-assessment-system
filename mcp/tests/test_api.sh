#!/bin/bash
# mcp/test_api.sh

SERVER_URL="http://127.0.0.1:9001"

echo "--- 1. 测试技能查询 (GET /v1/knowledge/skills) ---"
curl -s "$SERVER_URL/v1/knowledge/skills" | python3 -m json.tool

echo -e "\n\n--- 2. 测试症状评估 (POST /v1/evaluate) ---"
curl -s -X POST "$SERVER_URL/v1/evaluate" \
     -H "Content-Type: application/json" \
     -d '{
       "user_input": "你好，我手脚发麻。",
       "session_id": "manual_test_001"
     }' | python3 -m json.tool

echo -e "\n\n--- 3. 测试会话回溯 (GET /v1/sessions/{session_id}) ---"
curl -s "$SERVER_URL/v1/sessions/manual_test_001" | python3 -m json.tool

echo -e "\n\n--- 4. 测试触发学习 (POST /v1/knowledge/learn) ---"
curl -s -X POST "$SERVER_URL/v1/knowledge/learn" | python3 -m json.tool
