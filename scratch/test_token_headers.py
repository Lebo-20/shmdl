import httpx
import json
import asyncio

async def test_api_headers():
    BASE_URL = "https://shortmax.dramabos.online/api/v1"
    TOKEN = "A8D6AB170F7B89F2182561D3B32F390D"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://shortmax.dramabos.online/",
        "Authorization": f"Bearer {TOKEN}"
    }
    
    drama_id = "4539"
    url = f"{BASE_URL}/alleps/{drama_id}?lang=id"
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        response = await client.get(url)
        print(f"Status Code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    asyncio.run(test_api_headers())
