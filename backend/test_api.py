import httpx
import json
import asyncio

TOKEN = "sk-5a39ccb54b68dd98837860a3bc335de7af495c57882cb69a16c7a23a51132417"
BASE = "https://ai-api-gateway.app.baizhi.cloud/api/anthropic"

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        # Test 1: Try OpenAI format with "9*9=?"
        print("=== Test 1: Ask 9*9=? ===")
        resp = await client.post(
            f"{BASE}/v1/chat/completions",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-v4-pro",
                "messages": [
                    {"role": "user", "content": "9*9等于多少？直接回答数字。"}
                ],
                "max_tokens": 100
            }
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if "choices" in data:
            print(f"Answer: {data['choices'][0]['message']['content']}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])

        # Test 2: Try Anthropic Messages format
        print("\n=== Test 2: Anthropic Messages format ===")
        resp2 = await client.post(
            f"{BASE}/messages",
            headers={"x-api-key": TOKEN, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={
                "model": "deepseek-v4-pro",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "9*9等于多少？"}]
            }
        )
        print(f"Status: {resp2.status_code}")
        print(resp2.text[:500])

asyncio.run(test())
