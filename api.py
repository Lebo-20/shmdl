import httpx
import logging
import json

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("API_BASE_URL", "https://shortmax.dramabos.my.id/api/v1")
TOKEN = os.environ.get("API_TOKEN", "A8D6AB170F7B89F2182561D3B32F390D")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Referer": "https://shortmax.dramabos.my.id/"
}

async def get_popular_feed(page=1):
    """Fetches popular dramas from the Shortmax v1 API."""
    url = f"{BASE_URL}/popular"
    params = {"lang": "id", "page": page}
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            res_data = data.get("data", [])
            if isinstance(res_data, dict):
                return res_data.get("items") or res_data.get("list") or []
            return res_data
        except Exception as e:
            logger.error(f"Error fetching popular feed: {e}")
            return []

async def get_drama_detail(drama_id: str):
    """Fetches drama detail and ALL episodes from Shortmax v1 API."""
    # Using /alleps because it's the endpoint that takes the token ('code')
    # and typically returns episode/play data.
    url = f"{BASE_URL}/alleps/{drama_id}"
    params = {
        "lang": "id",
        "code": TOKEN
    }
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                error_msg = data.get('error')
                logger.error(f"API Error for {drama_id}: {error_msg}")
                return None, error_msg
                
            return data.get("data"), None
        except Exception as e:
            logger.error(f"Error fetching drama detail for {drama_id}: {e}")
            return None, str(e)

async def search_drama(query: str):
    """Searches for a drama by name using the Shortmax v1 API."""
    url = f"{BASE_URL}/search"
    params = {
        "q": query,
        "lang": "id"
    }
    
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            res_data = data.get("data", [])
            if isinstance(res_data, dict):
                return res_data.get("items") or res_data.get("list") or []
            return res_data
        except Exception as e:
            logger.error(f"Error searching drama '{query}': {e}")
            return []

# The episode data is now included in the detail.
# We modify get_episode_data to just return an episode from the detail since it's already fetched,
# or we just remove it and refactor main.py to use detail["items"].
async def get_episode_data(drama_id: str, ep_num: int):
    """Fetches episode data. Since all episodes are in detail, we must fetch detail first."""
    detail, error = await get_drama_detail(drama_id)
    if not detail or "episodes" not in detail:
        return None
    
    # ep_num is 1-indexed. Let's find the episode in the episodes list.
    episodes = detail.get("episodes", [])
    if ep_num - 1 < len(episodes):
        ep = episodes[ep_num - 1]
        # In v1 API, 'video' is a dict of qualities: {"video_720": "...", "video_480": "..."}
        video_data = ep.get("video")
        if isinstance(video_data, dict):
            # Try 720, then 480, then first available
            url = video_data.get("video_720") or video_data.get("video_480") or next(iter(video_data.values()), None)
            ep["video_url"] = url 
        elif isinstance(video_data, str):
            ep["video_url"] = video_data
        return ep
    return None
