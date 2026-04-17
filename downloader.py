import os
import asyncio
import logging

logger = logging.getLogger(__name__)

# Timeout per episode (detik) — HLS bisa besar, beri waktu cukup
DOWNLOAD_TIMEOUT = 600  # 10 menit per episode

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"


async def aria2c_download(url: str, path: str) -> bool:
    """Downloads a file using ffmpeg (for m3u8/HLS) or aria2c (direct MP4)."""
    dir_name = os.path.dirname(path)
    file_name = os.path.basename(path)

    is_m3u8 = ".m3u8" in url.split("?")[0]

    if is_m3u8:
        logger.info(f"M3U8 detected, using ffmpeg for {file_name}")
        command = [
            "ffmpeg", "-y",
            # Browser-like headers agar CDN tidak reject
            "-headers", f"User-Agent: {UA}\r\nReferer: https://shorttv.live/\r\n",
            "-i", url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            path,
        ]
    else:
        logger.info(f"Direct URL detected, using aria2c for {file_name}")
        command = [
            "aria2c",
            "-x", "8",
            "-s", "8",
            "-k", "1M",
            f"--user-agent={UA}",
            "--allow-overwrite=true",
            "--dir", dir_name,
            "--out", file_name,
            url,
        ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=DOWNLOAD_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            logger.error(f"Timeout ({DOWNLOAD_TIMEOUT}s) saat download: {url[:80]}")
            return False

        if process.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            # Tampilkan hanya 5 baris terakhir agar log tidak terlalu panjang
            short_err = "\n".join(err.split("\n")[-5:])
            logger.error(f"Download gagal [{file_name}] rc={process.returncode}:\n{short_err}")
            return False

        # Validasi: pastikan file benar-benar ada dan tidak kosong
        if not os.path.exists(path) or os.path.getsize(path) < 1024:
            logger.error(f"File tidak valid setelah download: {path}")
            return False

        logger.info(f"Download OK: {file_name} ({os.path.getsize(path):,} bytes)")
        return True

    except Exception as e:
        logger.error(f"Error download [{file_name}]: {e}")
        return False


async def download_episode_with_subs(ep_num: int, video_url: str, sub_url: str | None, download_dir: str) -> bool:
    """Downloads video and (optionally) subtitle for a specific episode."""
    ep_str = str(ep_num).zfill(3)
    video_path = os.path.join(download_dir, f"ep_{ep_str}.mp4")
    sub_path   = os.path.join(download_dir, f"ep_{ep_str}.srt")

    tasks = [aria2c_download(video_url, video_path)]
    if sub_url:
        tasks.append(aria2c_download(sub_url, sub_path))

    results = await asyncio.gather(*tasks, return_exceptions=False)
    return all(results)
