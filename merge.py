import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def merge_and_hardsub(video_dir: str, output_path: str):
    """
    Merges all episodes and burns subtitles into each before merging, 
    or merges them and then burns subtitles to the whole video.
    For DramaWave, we'll process each episode with hardsubs and then concat.
    
    Style requested:
    - Font: Standard Symbols PS
    - Color: White (FFFFFF)
    - Size: 10
    - Bold: 1
    - Outline: 1 (Black 000000)
    - Offset: 90 (MarginV)
    """
    try:
        # Get all video files
        videos = [f for f in os.listdir(video_dir) if f.endswith(".mp4") and "ep_" in f]
        videos.sort()
        
        processed_videos = []
        # First, check if ANY subtitle exists to determine if we need any re-encoding
        any_sub_exists = any(os.path.exists(os.path.join(video_dir, f.replace(".mp4", ".srt"))) for f in videos)
        
        if not any_sub_exists:
            logger.info("No subtitles found for any episode. Skipping all hardsub processing.")
            processed_videos = videos
        else:
            for video_file in videos:
                ep_str = video_file.replace("ep_", "").replace(".mp4", "")
                sub_file = f"ep_{ep_str}.srt"
                sub_path = os.path.join(video_dir, sub_file)
                input_path = os.path.join(video_dir, video_file)
                temp_output = os.path.join(video_dir, f"hard_{video_file}")
                
                # If subtitle exists, burn it (Hardsub)
                if os.path.exists(sub_path):
                    logger.info(f"Subtitles found for {video_file}, burning...")
                    # FFmpeg subtitles filter syntax for Windows needs escaping of path
                    sub_path_fixed = sub_path.replace("\\", "/").replace(":", "\\:")
                    
                    # ASS Style string: Fontname, FontSize, PrimaryColour, Bold, Outline, MarginV
                    style = f"Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,Bold=1,Outline=1,OutlineColour=&H000000,MarginV=90"
                    
                    command = [
                        "ffmpeg", "-y", "-i", input_path,
                        "-vf", f"subtitles='{sub_path_fixed}':force_style='{style}'",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "copy",
                        temp_output
                    ]
                    
                    process = subprocess.run(command, capture_output=True, text=True)
                    if process.returncode != 0:
                        logger.error(f"FFmpeg burning failed for {video_file}:\n{process.stderr}")
                        return False
                    processed_videos.append(f"hard_{video_file}")
                else:
                    # No subtitle for THIS video, but some exist in the set.
                    # We skip re-encoding for this one but warn about potential concat issues.
                    logger.info(f"No subtitles found for {video_file}, skipping hardsub.")
                    processed_videos.append(video_file)
            
        # Now concat the videos
        list_file_path = os.path.join(video_dir, "list.txt")
        with open(list_file_path, "w") as f:
            for file in processed_videos:
                f.write(f"file '{file}'\n")

        # Concat command
        concat_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            output_path
        ]
        
        logger.info(f"Concatenating {len(processed_videos)} episodes...")
        process = subprocess.run(concat_command, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"FFmpeg concat failed:\n{process.stderr}")
            return False
            
        logger.info(f"Successfully processed hardsubs and merged into {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error during hardsub/merge: {e}")
        return False
