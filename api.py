import httpx
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PRIMARY API  (shortmax.dramabos.my.id)
# ─────────────────────────────────────────────
PRIMARY_BASE_URL = os.environ.get("API_BASE_URL", "https://shortmax.dramabos.my.id/api/v1")
PRIMARY_TOKEN    = os.environ.get("API_TOKEN", "A8D6AB170F7B89F2182561D3B32F390D")
PRIMARY_HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Referer": "https://shortmax.dramabos.my.id/",
}

# ─────────────────────────────────────────────
# BACKUP API  (captain.sapimu.au/shortmax)
# ─────────────────────────────────────────────
BACKUP_BASE_URL = os.environ.get("BACKUP_API_BASE_URL", "https://captain.sapimu.au/shortmax/api/v1")
BACKUP_TOKEN    = os.environ.get("BACKUP_API_TOKEN", "5cf419a4c7fb1c8585314b9f797bf77e7b10a705f32c91aac65b901559780e12")
BACKUP_HEADERS  = {
    "Authorization": f"Bearer {BACKUP_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
}

# Shortcut: alias for code that still uses the old single-API names
BASE_URL = PRIMARY_BASE_URL
TOKEN    = PRIMARY_TOKEN
HEADERS  = PRIMARY_HEADERS


# ═════════════════════════════════════════════
# BACKUP API HELPERS
# ═════════════════════════════════════════════

def _update_backup_token():
    """Refresh BACKUP_HEADERS whenever the token env-var changes at runtime."""
    tok = os.environ.get("BACKUP_API_TOKEN", BACKUP_TOKEN)
    return {
        "Authorization": f"Bearer {tok}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }


async def _backup_request(path: str, params: dict | None = None) -> dict | None:
    """
    Generic GET request to the backup API.
    Returns parsed JSON dict on success, None on failure.
    """
    url = f"{BACKUP_BASE_URL}{path}"
    headers = _update_backup_token()
    try:
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"[BACKUP API] Request to {path} failed: {e}")
        return None


# ─────────────────────────────────────────────
# Backup: search
# ─────────────────────────────────────────────
async def backup_search_drama(query: str, page: int = 1) -> list:
    """Search dramas via backup API.
    Response fields: id, code, name, cover, episodes(int), summary
    """
    data = await _backup_request("/search", {"q": query, "lang": "id", "page": page})
    if not data:
        return []
    res = data.get("data", [])
    # Normalise 'name' -> 'title' for compatibility with primary API consumers
    if isinstance(res, list):
        for item in res:
            if "name" in item and "title" not in item:
                item["title"] = item["name"]
        return res
    if isinstance(res, dict):
        items = res.get("items") or res.get("list") or []
        for item in items:
            if "name" in item and "title" not in item:
                item["title"] = item["name"]
        return items
    return []


# ─────────────────────────────────────────────
# Backup: drama detail
# ─────────────────────────────────────────────
async def backup_get_drama_detail(code: str) -> tuple[dict | None, str | None]:
    """Get drama detail via backup API.
    Response fields: id, code, name, cover, summary
    episodes field: can be int (count) OR list of episode dicts with video URLs.
    We preserve whatever the API returns.
    """
    data = await _backup_request(f"/detail/{code}", {"lang": "id"})
    if not data:
        return None, "Backup API returned no data"
    if "error" in data:
        return None, data["error"]
    detail = data.get("data")
    if isinstance(detail, dict):
        # Normalise 'name' -> 'title'
        if "name" in detail and "title" not in detail:
            detail["title"] = detail["name"]
        # Preserve episode list; only set total_episodes when episodes is an int
        raw_ep = detail.get("episodes")
        if isinstance(raw_ep, int):
            detail["total_episodes"] = raw_ep
        elif isinstance(raw_ep, list):
            detail["total_episodes"] = len(raw_ep)
            # Normalise video quality field for each ep (same as primary API)
            for ep in raw_ep:
                if "video" not in ep:
                    continue
                v = ep["video"]
                if isinstance(v, dict):
                    ep["video_url"] = (
                        v.get("video_1080")
                        or v.get("video_720")
                        or v.get("video_480")
                        or next(iter(v.values()), None)
                    )
    return detail, None


# ─────────────────────────────────────────────
# Backup: play (episode video URL)
# ─────────────────────────────────────────────
async def backup_get_play_url(code: str, ep: int) -> str | None:
    """Get episode video URL via backup API (VIP).
    Response: data.video = {video_720, video_1080, video_480} — all HLS m3u8 URLs.
    Returns best quality available: 1080 > 720 > 480.
    """
    data = await _backup_request(f"/play/{code}", {"ep": ep, "lang": "id"})
    if not data:
        return None
    res = data.get("data") or {}
    video = res.get("video")
    if isinstance(video, dict):
        return (
            video.get("video_1080")
            or video.get("video_720")
            or video.get("video_480")
            or next(iter(video.values()), None)
        )
    # Fallback: flat URL fields
    return res.get("url") or res.get("video_url") or res.get("play_url")


# ─────────────────────────────────────────────
# Backup: home feed
# ─────────────────────────────────────────────
async def backup_get_home(tab: int = 1) -> list:
    """Get home page content via backup API.
    Response fields per item: id, code, name, cover, episodes(int), summary
    """
    data = await _backup_request("/home", {"tab": tab, "lang": "id"})
    if not data:
        return []
    res = data.get("data", [])
    items = res if isinstance(res, list) else (res.get("items") or res.get("list") or [] if isinstance(res, dict) else [])
    for item in items:
        if "name" in item and "title" not in item:
            item["title"] = item["name"]
    return items


# ─────────────────────────────────────────────
# Backup: generic feed (recommend/vip/new/ranked/war/epic/romance/foryou)
# ─────────────────────────────────────────────
async def backup_get_feed(feed_type: str = "recommend", page: int = 1) -> list:
    """
    Get a feed from the backup API.
    feed_type: recommend | vip | new | ranked | war | epic | romance
    Use 'foryou' for the For You feed (supports page param).
    """
    if feed_type == "foryou":
        data = await _backup_request("/foryou", {"page": page, "lang": "id"})
    else:
        data = await _backup_request(f"/feed/{feed_type}", {"lang": "id"})
    if not data:
        return []
    res = data.get("data", [])
    if isinstance(res, dict):
        return res.get("items") or res.get("list") or []
    return res if isinstance(res, list) else []


# ═════════════════════════════════════════════
# PRIMARY API  (with auto-fallback to backup)
# ═════════════════════════════════════════════

async def get_popular_feed(page: int = 1) -> list:
    """Fetches popular dramas. Falls back to backup API on failure."""
    url = f"{PRIMARY_BASE_URL}/popular"
    params = {"lang": "id", "page": page}

    async with httpx.AsyncClient(timeout=30, headers=PRIMARY_HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            res_data = data.get("data", [])
            if isinstance(res_data, dict):
                return res_data.get("items") or res_data.get("list") or []
            return res_data
        except Exception as e:
            logger.warning(f"[PRIMARY] get_popular_feed failed: {e} — trying backup…")

    # Fallback: backup recommend feed is closest to "popular"
    return await backup_get_feed("recommend", page)


async def get_drama_detail(drama_id: str) -> tuple[dict | None, str | None]:
    """Fetches drama detail + all episodes. Falls back to backup API."""
    url = f"{PRIMARY_BASE_URL}/alleps/{drama_id}"
    params = {"lang": "id", "code": PRIMARY_TOKEN}

    async with httpx.AsyncClient(timeout=30, headers=PRIMARY_HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                error_msg = data.get("error")
                logger.warning(f"[PRIMARY] API error for {drama_id}: {error_msg} — trying backup…")
                return await backup_get_drama_detail(drama_id)
            return data.get("data"), None
        except Exception as e:
            logger.warning(f"[PRIMARY] get_drama_detail failed for {drama_id}: {e} — trying backup…")

    return await backup_get_drama_detail(drama_id)


async def search_drama(query: str) -> list:
    """Searches for dramas. Falls back to backup API on failure."""
    url = f"{PRIMARY_BASE_URL}/search"
    params = {"q": query, "lang": "id"}

    async with httpx.AsyncClient(timeout=30, headers=PRIMARY_HEADERS) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            res_data = data.get("data", [])
            if isinstance(res_data, dict):
                return res_data.get("items") or res_data.get("list") or []
            return res_data
        except Exception as e:
            logger.warning(f"[PRIMARY] search_drama failed for '{query}': {e} — trying backup…")

    return await backup_search_drama(query)


async def get_episode_data(drama_id: str, ep_num: int) -> dict | None:
    """Fetches episode data. Uses detail endpoint, falls back to backup play URL."""
    detail, error = await get_drama_detail(drama_id)

    if detail and "episodes" in detail:
        episodes = detail.get("episodes", [])
        if ep_num - 1 < len(episodes):
            ep = episodes[ep_num - 1]
            video_data = ep.get("video")
            if isinstance(video_data, dict):
                url = (
                    video_data.get("video_720")
                    or video_data.get("video_480")
                    or next(iter(video_data.values()), None)
                )
                ep["video_url"] = url
            elif isinstance(video_data, str):
                ep["video_url"] = video_data
            return ep

    # Fallback: try backup play endpoint directly
    logger.warning(f"[PRIMARY] No episode data for {drama_id} ep {ep_num} — trying backup play…")
    backup_url = await backup_get_play_url(drama_id, ep_num)
    if backup_url:
        return {"video_url": backup_url, "ep": ep_num, "source": "backup"}
    return None
