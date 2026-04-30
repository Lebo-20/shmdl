import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def merge_and_hardsub(video_dir: str, output_path: str, progress_callback=None):
    """
    Merges all episodes and burns subtitles into each before merging.
    Now supports an async progress_callback.
    """
    try:
        # Get all video files
        videos = [f for f in os.listdir(video_dir) if f.endswith(".mp4") and "ep_" in f]
        videos.sort()
        total_vids = len(videos)
        
        processed_videos = []
        # First, check if ANY subtitle exists
        any_sub_exists = any(os.path.exists(os.path.join(video_dir, f.replace(".mp4", ".srt"))) for f in videos)
        
        if not any_sub_exists:
            logger.info("No subtitles found for any episode. Skipping all hardsub processing.")
            processed_videos = videos
        else:
            for i, video_file in enumerate(videos):
                ep_str = video_file.replace("ep_", "").replace(".mp4", "")
                sub_file = f"ep_{ep_str}.srt"
                sub_path = os.path.join(video_dir, sub_file)
                input_path = os.path.join(video_dir, video_file)
                temp_output = os.path.join(video_dir, f"hard_{video_file}")
                
                # Report progress
                if progress_callback:
                    await progress_callback(i, total_vids, f"Memproses Episode {i+1}/{total_vids}")

                # If subtitle exists, burn it (Hardsub)
                if os.path.exists(sub_path):
                    logger.info(f"Subtitles found for {video_file}, burning...")
                    sub_path_fixed = sub_path.replace("\\", "/").replace(":", "\\:")
                    style = f"Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,Bold=1,Outline=1,OutlineColour=&H000000,MarginV=90"
                    
                    command = [
                        "ffmpeg", "-y", "-i", input_path,
                        "-vf", f"subtitles='{sub_path_fixed}':force_style='{style}'",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "copy",
                        temp_output
                    ]
                    
                    process = await asyncio.create_subprocess_exec(
                        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    
                    if process.returncode != 0:
                        logger.error(f"FFmpeg burning failed for {video_file}")
                        return False
                    processed_videos.append(f"hard_{video_file}")
                else:
                    processed_videos.append(video_file)
            
            if progress_callback:
                await progress_callback(total_vids, total_vids, "Hampir selesai...")

        # Now concat the videos
        list_file_path = os.path.join(video_dir, "list.txt")
        with open(list_file_path, "w") as f:
            for file in processed_videos:
                f.write(f"file '{file}'\n")

        concat_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            output_path
        ]
        
        logger.info(f"Concatenating {len(processed_videos)} episodes...")
        process = await asyncio.create_subprocess_exec(
            *concat_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode != 0:
            logger.error("FFmpeg concat failed")
            return False
            
        logger.info(f"Successfully merged into {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error during hardsub/merge: {e}")
        return False
