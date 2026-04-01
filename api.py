import httpx
import logging
import json

logger = logging.getLogger(__name__)

BASE_URL = "https://captain.sapimu.au/dramawave"
TOKEN = "5cf419a4c7fb1c8585314b9f797bf77e7b10a705f32c91aac65b901559780e12"

async def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}"
    }

async def get_popular_feed(page=1):
    """Fetches popular dramas from DramaWave API."""
    url = f"{BASE_URL}/api/v1/feed/popular"
    params = {
        "page": page,
        "lang": "id-ID"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params, headers=await get_headers())
            response.raise_for_status()
            data = response.json()
            # Handle possible structures: data['data']['items'] or data['data'] as list
            inner_data = data.get("data", {})
            if isinstance(inner_data, list):
                return inner_data
            if isinstance(inner_data, dict):
                return inner_data.get("items", []) or inner_data.get("list", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching popular feed: {e}")
            return []

async def get_drama_detail(drama_id: str):
    """Fetches drama detail from DramaWave API."""
    url = f"{BASE_URL}/api/v1/dramas/{drama_id}"
    params = {"lang": "id-ID"}
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params, headers=await get_headers())
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except Exception as e:
            logger.error(f"Error fetching drama detail for {drama_id}: {e}")
            return None

async def get_episode_data(drama_id: str, episode_num: int):
    """Fetches play URL and subtitles for a specific episode."""
    url = f"{BASE_URL}/api/v1/dramas/{drama_id}/play/{episode_num}"
    params = {"lang": "id-ID"}
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params, headers=await get_headers())
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except Exception as e:
            logger.error(f"Error fetching play data for {drama_id} Ep {episode_num}: {e}")
            return None

async def search_drama(query: str):
    """Searches for a drama by name."""
    url = f"{BASE_URL}/api/v1/search"
    params = {
        "q": query,
        "lang": "id-ID"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params, headers=await get_headers())
            response.raise_for_status()
            data = response.json()
            inner_data = data.get("data", {})
            if isinstance(inner_data, list):
                return inner_data
            if isinstance(inner_data, dict):
                return inner_data.get("items", []) or inner_data.get("list", [])
            return []
        except Exception as e:
            logger.error(f"Error searching drama '{query}': {e}")
            return []
