import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://shortmax.dramabos.my.id/api/v1"

async def test_popular():
    url = f"{BASE_URL}/popular"
    params = {"lang": "id", "page": 1}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://shortmax.dramabos.my.id/"
    }
    
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        try:
            print(f"Fetching: {url}")
            response = await client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text[:500]}")
            response.raise_for_status()
            data = response.json()
            print("Successfully parsed JSON")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_popular())
