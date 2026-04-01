import os
import asyncio
import subprocess
import logging

logger = logging.getLogger(__name__)

async def aria2c_download(url: str, path: str):
    """Downloads a file using aria2c for speed and robustness."""
    dir_name = os.path.dirname(path)
    file_name = os.path.basename(path)
    
    # -x 16 (max connections per server), -s 16 (split files), -k 1M (min split size)
    command = [
        "aria2c", 
        "-x", "16", 
        "-s", "16", 
        "-k", "1M",
        "--dir", dir_name,
        "--out", file_name,
        "--allow-overwrite=true",
        url
    ]
    
    try:
        # Using subprocess for aria2c
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"aria2c failed for {url}:\n{stderr.decode()}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error during aria2c download for {url}: {e}")
        return False

async def download_episode_with_subs(ep_num: int, video_url: str, sub_url: str, download_dir: str):
    """Downloads video and subtitle for a specific episode."""
    ep_str = str(ep_num).zfill(3)
    video_path = os.path.join(download_dir, f"ep_{ep_str}.mp4")
    sub_path = os.path.join(download_dir, f"ep_{ep_str}.srt")
    
    tasks = [aria2c_download(video_url, video_path)]
    if sub_url:
        tasks.append(aria2c_download(sub_url, sub_path))
        
    results = await asyncio.gather(*tasks)
    return all(results)
