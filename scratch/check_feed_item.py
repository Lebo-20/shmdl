import httpx
import json
import asyncio

async def test_feed():
    BASE_URL = "https://shortmax.dramabos.online/api/v1"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://shortmax.dramabos.online/"
    }
    
    url = f"{BASE_URL}/popular"
    params = {"lang": "id", "page": 1}
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        response = await client.get(url, params=params)
        data = response.json()
        items = data.get("data", [])
        if items:
            print(json.dumps(items[0], indent=2))
        else:
            print("No items found")

if __name__ == "__main__":
    asyncio.run(test_feed())
