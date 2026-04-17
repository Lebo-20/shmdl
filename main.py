import os
import asyncio
import logging
import shutil
import tempfile
import random
import json
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv

load_dotenv()

# Local imports
from api import (
    get_drama_detail, get_episode_data, get_popular_feed, search_drama
)
from downloader import aria2c_download, download_episode_with_subs
from merge import merge_and_hardsub
from uploader import upload_drama

# Configuration
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
AUTO_CHANNEL = int(os.environ.get("AUTO_CHANNEL", ADMIN_ID))
MESSAGE_THREAD_ID = int(os.environ.get("MESSAGE_THREAD_ID", "0")) or None
PROCESSED_FILE = "processed.json"

# Initialize state
def load_processed():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed(data):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(data), f)

processed_ids = load_processed()

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BotState:
    is_auto_running = True
    is_processing = False

# Initialize client
client = TelegramClient('dramawave_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def get_panel_buttons():
    status_text = "🟢 BERJALAN" if BotState.is_auto_running else "🔴 BERHENTI"
    return [
        [Button.inline("▶️ Mulai Auto", b"start_auto"), Button.inline("⏹ Hentikan Auto", b"stop_auto")],
        [Button.inline(f"📊 Status: {status_text}", b"status")]
    ]

@client.on(events.NewMessage(pattern='/update'))
async def update_bot(event):
    if event.sender_id != ADMIN_ID: return
    import subprocess, sys
    status_msg = await event.reply("🔄 Menarik pembaruan...")
    try:
        subprocess.run(["git", "pull"], check=True)
        await status_msg.edit("✅ Update berhasil! Memulai ulang...")
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await status_msg.edit(f"❌ Gagal update: {e}")

@client.on(events.NewMessage(pattern='/panel'))
async def panel(event):
    if event.chat_id != ADMIN_ID: return
    await event.reply("🎛 **DramaWave Control Panel**", buttons=get_panel_buttons())

@client.on(events.CallbackQuery())
async def panel_callback(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data
    if data == b"start_auto":
        BotState.is_auto_running = True
        await event.answer("Mode Otomatis dimulai!")
    elif data == b"stop_auto":
        BotState.is_auto_running = False
        await event.answer("Mode Otomatis dihentikan!")
    elif data == b"status":
        await event.answer(f"Status: {'Berjalan' if BotState.is_auto_running else 'Berhenti'}")
    
    await event.edit("🎛 **DramaWave Control Panel**", buttons=get_panel_buttons())

import re

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Selamat datang di Bot Downloader DramaWave! 🎉\n\nGunakan perintah `/cari {judul}` atau `/download {ID}` untuk mulai.")

@client.on(events.NewMessage(pattern=r'/cari (.+)'))
async def on_search(event):
    query = event.pattern_match.group(1)
    status_msg = await event.reply(f"🔍 Mencari dramas untuk: `{query}`...")
    
    try:
        results = await search_drama(query)
        if not results:
            await status_msg.edit(f"❌ Tidak ditemukan hasil untuk `{query}`.")
            return
            
        # Display top results
        text = f"✨ **Hasil Pencarian: {query}**\n\n"
        
        for i, drama in enumerate(results[:8]):
            title = drama.get("name") or drama.get("title") or "Tidak Diketahui"
            drama_id = str(drama.get("playlet_id") or drama.get("id") or drama.get("code") or drama.get("key"))
            ep_count = drama.get("totalEpisodes") or drama.get("max_episode") or "?"
            
            text += f"{i+1}. **{title}** (Eps: {ep_count})\nID: `{drama_id}`\n"
            
            buttons = [Button.inline(f"📥 Download", data=f"dl_{drama_id}")]
            # Only add Channel button for admin
            if event.sender_id == ADMIN_ID:
                buttons.append(Button.inline(f"📢 Post ke Channel", data=f"post_{drama_id}"))
            
            await event.reply(f"🎬 **{title}**\nEps: {ep_count}\nID: `{drama_id}`", buttons=buttons)
            
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit(f"❌ Terjadi kesalahan saat mencari: {e}")

@client.on(events.CallbackQuery(data=re.compile(b"dl_(.+)")))
async def on_dl_callback(event):
    drama_id = event.data.decode().replace("dl_", "")
    
    if BotState.is_processing:
        await event.answer("⚠️ Sedang memproses drama lain. Mohon tunggu.", alert=True)
        return
        
    await event.answer("Memulai download...")
    status_msg = await event.reply(f"🔍 Menyiapkan download untuk ID `{drama_id}`...")
    
    BotState.is_processing = True
    success = await process_drama_full(drama_id, event.chat_id, status_msg)
    BotState.is_processing = False
    
    if success:
        processed_ids.add(drama_id)
        save_processed(processed_ids)

@client.on(events.CallbackQuery(data=re.compile(b"post_(.+)")))
async def on_post_callback(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("⚠️ Hanya Admin yang bisa posting ke channel.", alert=True)
        return
        
    drama_id = event.data.decode().replace("post_", "")
    
    if BotState.is_processing:
        await event.answer("⚠️ Sedang memproses drama lain.", alert=True)
        return
        
    await event.answer("Memulai posting ke channel...")
    status_msg = await event.reply(f"🚀 Memproses `{drama_id}` untuk channel...")
    
    BotState.is_processing = True
    success = await process_drama_full(drama_id, AUTO_CHANNEL, status_msg, message_thread_id=MESSAGE_THREAD_ID)
    BotState.is_processing = False
    
    if success:
        processed_ids.add(drama_id)
        save_processed(processed_ids)

@client.on(events.NewMessage(pattern=r'/download ([\w-]+)'))
async def on_download(event):
    if not event.is_group and event.chat_id != ADMIN_ID:
        return
        
    if BotState.is_processing:
        await event.reply("⚠️ Sedang memproses drama lain.")
        return
        
    drama_id = event.pattern_match.group(1)
    status_msg = await event.reply(f"🔍 Mencari drama `{drama_id}`...")
    
    BotState.is_processing = True
    success = await process_drama_full(drama_id, event.chat_id, status_msg)
    BotState.is_processing = False
    
    if success:
        processed_ids.add(drama_id)
        save_processed(processed_ids)

@client.on(events.NewMessage(pattern=r'/post ([\w-]+)'))
async def on_post(event):
    if event.sender_id != ADMIN_ID: return
        
    if BotState.is_processing:
        await event.reply("⚠️ Sedang memproses drama lain.")
        return
        
    drama_id = event.pattern_match.group(1)
    status_msg = await event.reply(f"🚀 Memproses `{drama_id}` untuk Channel...")
    
    BotState.is_processing = True
    success = await process_drama_full(drama_id, AUTO_CHANNEL, status_msg, message_thread_id=MESSAGE_THREAD_ID)
    BotState.is_processing = False
    
    if success:
        processed_ids.add(drama_id)
        save_processed(processed_ids)

async def process_drama_full(drama_id, chat_id, status_msg=None, message_thread_id=None):
    """DramaWave Pipeline: Fetch -> Download with Subs -> Burn Subtitles -> Merge -> Upload."""
    try:
        detail = await get_drama_detail(drama_id)
        if not detail:
            if status_msg: await status_msg.edit(f"❌ Drama `{drama_id}` tidak ditemukan.")
            return False

        title = detail.get("name") or detail.get("title") or f"Drama_{drama_id}"
        description = detail.get("description") or detail.get("intro") or detail.get("summary") or "Tidak ada deskripsi."
        poster = detail.get("cover") or detail.get("poster") or ""
        total_eps = detail.get("episodes_count") or detail.get("max_episode") or 0
        
        if status_msg: await status_msg.edit(f"🎬 Memproses **{title}** ({total_eps} episode)...")

        temp_dir = tempfile.mkdtemp(prefix=f"dw_{drama_id}_")
        video_dir = os.path.join(temp_dir, "episodes")
        os.makedirs(video_dir, exist_ok=True)

        # 3. Download episodes (1 -> total_eps)
        # We fetch detail once to get all episodes
        detail_items = detail.get("episodes", [])
        total_eps = len(detail_items) if detail_items else total_eps
        
        semaphore = asyncio.Semaphore(5)
        
        async def download_task(ep_num):
            async with semaphore:
                # ep_num is 1-indexed, get from detail_items directly instead of making an API call per ep
                if ep_num - 1 >= len(detail_items):
                    return False
                play_data = detail_items[ep_num - 1]
                
                # Extraction logic for version 1 API
                video_val = play_data.get("video")
                video_url = None
                if isinstance(video_val, dict):
                    video_url = video_val.get("video_720") or video_val.get("video_480") or next(iter(video_val.values()), None)
                elif isinstance(video_val, str):
                    video_url = video_val
                
                # Fallback for old structure
                if not video_url:
                    video_url = play_data.get("1080p_mp4") or play_data.get("720p_mp4") or play_data.get("video_url")
                
                sub_list = play_data.get("subtitle") or play_data.get("subtitle_list") or []
                
                # Fetch Indonesian subtitle if available
                sub_url = None
                if isinstance(sub_list, list):
                    for s in sub_list:
                        # Priority: id-ID, then id, then English as fallback
                        lang = s.get("language") or s.get("lang") or ""
                        if lang in ["id-ID", "id", "in"]:
                            sub_url = s.get("subtitle") or s.get("vtt")
                            break
                    if not sub_url and sub_list:
                        sub_url = sub_list[0].get("subtitle") or sub_list[0].get("vtt") # Take first as fallback
                
                if not video_url: return False
                return await download_episode_with_subs(ep_num, video_url, sub_url, video_dir)

        download_results = await asyncio.gather(*(download_task(i) for i in range(1, total_eps + 1)))
        
        if not all(download_results):
            if status_msg: await status_msg.edit(f"❌ Gagal mendownload beberapa episode.")
            # return False # Continue anyway? Or return False. Standard is return False.

        # 4. Hardsub and Merge
        if status_msg: await status_msg.edit(f"🔥 Membakar subtitle & menggabungkan video...")
        output_path = os.path.join(temp_dir, f"{title}.mp4")
        
        merge_success = await asyncio.get_event_loop().run_in_executor(None, merge_and_hardsub, video_dir, output_path)
        if not merge_success:
            if status_msg: await status_msg.edit("❌ Proses Hardsub/Merge Gagal.")
            return False

        # 5. Upload
        if status_msg: await status_msg.edit(f"📤 Mengunggah **{title}** ke Telegram...")
        upload_success = await upload_drama(client, chat_id, title, description, poster, output_path, message_thread_id=message_thread_id, status_msg=status_msg)
        
        if upload_success:
            if status_msg: await status_msg.delete()
            return True
        else:
            if status_msg: await status_msg.edit("❌ Upload Gagal.")
            return False

    except Exception as e:
        logger.error(f"Error processing drama {drama_id}: {e}")
        if status_msg: await status_msg.edit(f"❌ Error: {e}")
        return False
    finally:
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def auto_mode_loop():
    logger.info("🚀 DramaWave Auto-Mode Active.")
    is_initial = True
    
    while True:
        if not BotState.is_auto_running:
            await asyncio.sleep(10)
            continue
            
        try:
            logger.info("🔍 Checking popular feed...")
            dramas = await get_popular_feed(page=1)
            
            for drama in dramas:
                if not BotState.is_auto_running: break
                
                drama_id = drama.get("playlet_id") or drama.get("id") or drama.get("key")
                if not drama_id:
                    logger.warning(f"Drama found with no ID: {drama}")
                    continue
                
                drama_id = str(drama_id)
                if drama_id not in processed_ids:
                    title = drama.get("name") or drama.get("title") or "Tidak Diketahui"
                    logger.info(f"✨ New drama found: {title} ({drama_id})")
                    
                    try:
                        status_msg = await client.send_message(ADMIN_ID, f"🆕 **Auto-Detect Drama Baru!**\n🎬 {title}\n🆔 `{drama_id}`\n⏳ Sedang memproses hardsub...")
                    except: status_msg = None
                    
                    BotState.is_processing = True
                    success = await process_drama_full(drama_id, AUTO_CHANNEL, status_msg=status_msg, message_thread_id=MESSAGE_THREAD_ID)
                    BotState.is_processing = False
                    
                    if success:
                        processed_ids.add(drama_id)
                        save_processed(processed_ids)
                        await client.send_message(ADMIN_ID, f"✅ Sukses Post: **{title}**\n😴 Menunggu 20 menit untuk istirahat...")
                        logger.info(f"Successfully processed {title}. Sleeping for 20 minutes...")
                        await asyncio.sleep(20 * 60) # 20 minutes break
                    else:
                        logger.error(f"Failed to process {title}")
                        await asyncio.sleep(15) # Short wait on failure before next drama


            is_initial = False
            await asyncio.sleep(3600) # Check every hour
        except Exception as e:
            logger.error(f"Error in auto_mode: {e}")
            await asyncio.sleep(300)

if __name__ == '__main__':
    logger.info("Bot started.")
    client.loop.create_task(auto_mode_loop())
    client.run_until_disconnected()
