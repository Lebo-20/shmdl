import httpx
import json
import asyncio

async def test_drama(drama_id):
    BASE_URL = "https://shortmax.dramabos.online/api/v1"
    TOKEN = "A8D6AB170F7B89F2182561D3B32F390D"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Referer": "https://shortmax.dramabos.online/"
    }
    
    url = f"{BASE_URL}/alleps/{drama_id}?lang=id&code={TOKEN}"
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        response = await client.get(url)
        return response.json()

async def main():
    ids = ["13821", "18936", "10649", "17020"]
    for d_id in ids:
        print(f"Testing ID {d_id}...")
        res = await test_drama(d_id)
        if "error" in res:
            print(f"ID {d_id} failed: {res['error']}")
        else:
            print(f"ID {d_id} SUCCESS!")
            break

if __name__ == "__main__":
    asyncio.run(main())
