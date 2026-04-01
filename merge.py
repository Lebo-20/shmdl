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
        
        for video_file in videos:
            ep_str = video_file.replace("ep_", "").replace(".mp4", "")
            sub_file = f"ep_{ep_str}.srt"
            sub_path = os.path.join(video_dir, sub_file)
            input_path = os.path.join(video_dir, video_file)
            temp_output = os.path.join(video_dir, f"hard_{video_file}")
            
            # If subtitle exists, burn it
            if os.path.exists(sub_path):
                # FFmpeg subtitles filter syntax for Windows needs escaping of path
                # Path like C:\foo\bar.srt -> C\\:/foo/bar.srt or similar
                # For Windows paths in FFmpeg filter: replace \ with / and escape : 
                sub_path_fixed = sub_path.replace("\\", "/").replace(":", "\\:")
                
                # ASS Style string: Fontname, FontSize, PrimaryColour, Bold, Outline, MarginV
                # PrimaryColour is in BGR hex format: &HAABBGGRR. White is &H00FFFFFF.
                style = f"Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,Bold=1,Outline=1,OutlineColour=&H000000,MarginV=90"
                
                command = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", f"subtitles='{sub_path_fixed}':force_style='{style}'",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "copy",
                    temp_output
                ]
            else:
                # No subtitle, just copy or encode for consistency? 
                # Better to encode so concat works smoothly
                command = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "copy",
                    temp_output
                ]
                
            logger.info(f"Burning subtitles for {video_file}...")
            process = subprocess.run(command, capture_output=True, text=True)
            if process.returncode != 0:
                logger.error(f"FFmpeg burning failed for {video_file}:\n{process.stderr}")
                # Fallback to copy if encoding fails? No, better return failure to investigate.
                return False
            
            processed_videos.append(f"hard_{video_file}")
            
        # Now concat the hard-subbed videos
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
