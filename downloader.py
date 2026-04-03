import os
import asyncio
import subprocess
import logging

logger = logging.getLogger(__name__)

async def aria2c_download(url: str, path: str):
    """Downloads a file using aria2c or ffmpeg (for m3u8)."""
    dir_name = os.path.dirname(path)
    file_name = os.path.basename(path)
    
    # If it's an m3u8, use ffmpeg to download
    if ".m3u8" in url.split("?")[0]:
        logger.info(f"M3U8 detected, using ffmpeg for {file_name}")
        command = [
            "ffmpeg", "-y", "-i", url,
            "-c", "copy", "-bsf:a", "aac_adtstoasc",
            path
        ]
    else:
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
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"process failed for {url}:\n{stderr.decode()}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error during process download for {url}: {e}")
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
