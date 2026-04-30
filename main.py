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

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ.get("DATABASE_URL")

def init_db():
    if not DATABASE_URL:
        logger.info("📡 No DATABASE_URL found. Using local JSON only.")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS processed_dramas (drama_id TEXT PRIMARY KEY, title TEXT, processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        # New table for failure tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS failed_dramas (
                drama_id TEXT PRIMARY KEY, 
                title TEXT, 
                fail_count INTEGER DEFAULT 0, 
                last_fail_date DATE DEFAULT CURRENT_DATE
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ PostgreSQL Database initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")

# Initialize state
def load_processed():
    ids = set()
    titles = set()
    # Load from local file
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    ids.update(data)
                elif isinstance(data, dict):
                    ids.update(data.get("ids", []))
                    titles.update(data.get("titles", []))
        except:
            pass
    
    # Load from DB if available
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT drama_id, title FROM processed_dramas")
            rows = cur.fetchall()
            for row in rows:
                ids.add(row[0])
                if row[1]: titles.add(row[1].lower().strip())
            cur.close()
            conn.close()
            logger.info(f"📥 Loaded {len(rows)} entries from Database.")
        except Exception as e:
            logger.error(f"Error loading from DB: {e}")
            
    return ids, titles

def save_processed(ids, titles):
    # Save to local file
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"ids": list(ids), "titles": list(titles)}, f)

def mark_as_processed(drama_id, title="Unknown"):
    processed_ids.add(str(drama_id))
    processed_titles.add(title.lower().strip())
    save_processed(processed_ids, processed_titles)
    
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO processed_dramas (drama_id, title) VALUES (%s, %s) ON CONFLICT (drama_id) DO UPDATE SET title = EXCLUDED.title",
                (str(drama_id), title)
            )
            # Clear failures on success
            cur.execute("DELETE FROM failed_dramas WHERE drama_id = %s", (str(drama_id),))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")

FAILURES_FILE = "failures.json"
def load_failures():
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT drama_id, fail_count, last_fail_date FROM failed_dramas")
            rows = cur.fetchall()
            failures = {row[0]: {"count": row[1], "date": str(row[2])} for row in rows}
            cur.close()
            conn.close()
            return failures
        except Exception as e:
            logger.error(f"Error loading failures from DB: {e}")
            
    if os.path.exists(FAILURES_FILE):
        try:
            with open(FAILURES_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def mark_as_failed(drama_id, title="Unknown"):
    from datetime import date
    today = str(date.today())
    failures = load_failures()
    
    if drama_id in failures and failures[drama_id]["date"] == today:
        failures[drama_id]["count"] += 1
    else:
        failures[drama_id] = {"count": 1, "date": today}
    
    with open(FAILURES_FILE, "w") as f:
        json.dump(failures, f)
        
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO failed_dramas (drama_id, title, fail_count, last_fail_date) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (drama_id) DO UPDATE SET 
                    fail_count = CASE WHEN failed_dramas.last_fail_date = EXCLUDED.last_fail_date THEN failed_dramas.fail_count + 1 ELSE 1 END,
                    last_fail_date = EXCLUDED.last_fail_date,
                    title = EXCLUDED.title
            """, (str(drama_id), title, 1, today))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving failure to DB: {e}")

init_db()
processed_ids, processed_titles = load_processed()



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

@client.on(events.NewMessage(pattern='/shortmax update'))
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

@client.on(events.NewMessage(pattern='/shortmax panel'))
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

@client.on(events.NewMessage(pattern='/shortmax start'))
async def start(event):
    await event.reply("Selamat datang di Bot Downloader DramaWave! 🎉\n\nGunakan perintah `/shortmax cari {judul}` atau `/shortmax download {ID}` untuk mulai.")

@client.on(events.NewMessage(pattern=r'/shortmax cari (.+)'))
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
        mark_as_processed(drama_id)

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
        mark_as_processed(drama_id)

@client.on(events.NewMessage(pattern=r'/shortmax download ([\w-]+)'))
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
        mark_as_processed(drama_id)

@client.on(events.NewMessage(pattern=r'/shortmax post ([\w-]+)'))
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
        mark_as_processed(drama_id)

# Sentinel value to distinguish premium token errors from regular failures
PREMIUM_ERROR = "PREMIUM_ERROR"

async def process_drama_full(drama_id, chat_id, status_msg=None, message_thread_id=None):
    """DramaWave Pipeline: Fetch -> Download with Subs -> Burn Subtitles -> Merge -> Upload."""
    try:
        detail, error_msg = await get_drama_detail(drama_id)
        if not detail:
            is_premium_err = error_msg and "premium" in error_msg.lower()
            error_txt = f"❌ Gagal mengambil detail drama: {error_msg}" if error_msg else f"❌ Drama `{drama_id}` tidak ditemukan."
            if status_msg: await status_msg.edit(error_txt)
            logger.error(f"Failed to fetch detail for {drama_id}: {error_msg}")
            if is_premium_err:
                return PREMIUM_ERROR
            return False

        title = detail.get("name") or detail.get("title") or f"Drama_{drama_id}"
        description = detail.get("description") or detail.get("intro") or detail.get("summary") or "Tidak ada deskripsi."
        poster = detail.get("cover") or detail.get("poster") or ""

        # ── Deteksi sumber episode ──────────────────────────────────────
        # Primary API:  detail["episodes"] = list of episode dicts
        # Backup API:   detail["episodes"] = int (total count)
        #               detail["total_episodes"] = int (set oleh backup_get_drama_detail)
        raw_episodes = detail.get("episodes")
        if isinstance(raw_episodes, list) and raw_episodes:
            # ✅ Primary API — episode list tersedia
            detail_items = raw_episodes
            total_eps = len(detail_items)
            use_backup_play = False
        else:
            # ✅ Backup API — episodes hanya angka, harus fetch per episode via /play
            detail_items = []
            total_eps = (
                detail.get("total_episodes")          # set oleh backup_get_drama_detail
                or (raw_episodes if isinstance(raw_episodes, int) else 0)
                or detail.get("episodes_count")
                or detail.get("max_episode")
                or 0
            )
            use_backup_play = True

        if total_eps == 0:
            if status_msg: await status_msg.edit(f"❌ Jumlah episode tidak diketahui untuk `{drama_id}`.")
            logger.error(f"total_eps=0 for {drama_id}, detail keys: {list(detail.keys())}")
            return False

        if status_msg: await status_msg.edit(f"🎬 Memproses **{title}** ({total_eps} episode)...")

        temp_dir = tempfile.mkdtemp(prefix=f"dw_{drama_id}_")
        video_dir = os.path.join(temp_dir, "episodes")
        os.makedirs(video_dir, exist_ok=True)

        semaphore = asyncio.Semaphore(3)  # dikurangi agar tidak flood CDN
        
        # Track download progress
        completed_count = 0
        
        def get_progress_text(phase, current, total):
            perc = (current / total) * 100
            filled = int(10 * perc / 100)
            bar = "█" * filled + "░" * (10 - filled)
            return f"**{phase}**\n`[{bar}] {perc:.1f}%` ({current}/{total})"

        async def download_task(ep_num):
            nonlocal completed_count
            async with semaphore:
                video_url = None
                sub_url = None

                if use_backup_play:
                    # ── Backup API: ambil URL via /play/:code?ep=N ──────
                    from api import backup_get_play_url
                    video_url = await backup_get_play_url(str(drama_id), ep_num)
                    sub_url = None  # backup API tidak sertakan subtitle
                else:
                    # ── Primary API: ambil dari detail_items list ───────
                    if ep_num - 1 >= len(detail_items):
                        return False
                    play_data = detail_items[ep_num - 1]

                    # Gunakan video_url yang sudah dinormalisasi oleh backup_get_drama_detail
                    video_url = play_data.get("video_url")

                    if not video_url:
                        video_val = play_data.get("video")
                        if isinstance(video_val, dict):
                            video_url = (
                                video_val.get("video_1080")
                                or video_val.get("video_720")
                                or video_val.get("video_480")
                                or next(iter(video_val.values()), None)
                            )
                        elif isinstance(video_val, str):
                            video_url = video_val

                    if not video_url:
                        video_url = play_data.get("1080p_mp4") or play_data.get("720p_mp4")

                    sub_list = play_data.get("subtitle") or play_data.get("subtitle_list") or []
                    if isinstance(sub_list, list):
                        for s in sub_list:
                            lang = s.get("language") or s.get("lang") or ""
                            if lang in ["id-ID", "id", "in"]:
                                sub_url = s.get("subtitle") or s.get("vtt")
                                break
                        if not sub_url and sub_list:
                            sub_url = sub_list[0].get("subtitle") or sub_list[0].get("vtt")

                if not video_url:
                    logger.error(f"No video URL for ep {ep_num} of drama {drama_id}")
                    return False

                # logger.info(f"Downloading ep {ep_num}/{total_eps}: {video_url[:60]}...")
                res = await download_episode_with_subs(ep_num, video_url, sub_url, video_dir)
                
                if res:
                    completed_count += 1
                    if status_msg:
                        try:
                            await status_msg.edit(get_progress_text("📥 Mendownload Episode:", completed_count, total_eps))
                        except: pass
                return res

        download_results = await asyncio.gather(*(download_task(i) for i in range(1, total_eps + 1)))

        failed = [i+1 for i, ok in enumerate(download_results) if not ok]
        if failed:
            logger.error(f"Download gagal untuk episode: {failed}")
            if status_msg: await status_msg.edit(f"❌ Gagal mendownload episode: {failed}")
            return False  # ← STOP jika ada episode yang gagal

        # ── Hardsub & Merge ─────────────────────────────────────────────
        if status_msg: await status_msg.edit(f"🔥 Membakar subtitle & menggabungkan video...")
        output_path = os.path.join(temp_dir, f"{title}.mp4")

        async def merge_progress(curr, total, text):
            if status_msg:
                try:
                    await status_msg.edit(get_progress_text("🔥 Memproses Video:", curr, total))
                except: pass

        merge_success = await merge_and_hardsub(video_dir, output_path, progress_callback=merge_progress)
        if not merge_success:
            if status_msg: await status_msg.edit("❌ Proses Hardsub/Merge Gagal.")
            return False

        # ── Upload ───────────────────────────────────────────────────────
        if status_msg: await status_msg.edit(f"📤 Mengunggah **{title}** ke Telegram...")
        upload_success = await upload_drama(
            client, chat_id, title, description, poster, output_path,
            message_thread_id=message_thread_id, status_msg=status_msg
        )

        if upload_success:
            if status_msg: await status_msg.delete()
            return True
        else:
            if status_msg: await status_msg.edit("❌ Upload Gagal.")
            return False

    except Exception as e:
        logger.error(f"Error processing drama {drama_id}: {e}", exc_info=True)
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
                title = (drama.get("name") or drama.get("title") or "Tidak Diketahui").strip()
                title_lower = title.lower()
                
                # Check if already processed (ID or Title)
                if drama_id in processed_ids or title_lower in processed_titles:
                    logger.info(f"⏭ Skipping (already processed): {title}")
                    continue
                
                # Check failures
                failures = load_failures()
                from datetime import date
                today = str(date.today())
                if drama_id in failures and failures[drama_id]["date"] == today:
                    if failures[drama_id]["count"] >= 2:
                        logger.warning(f"⏭ Skipping (failed 2x today): {title}")
                        continue

                logger.info(f"✨ New drama found: {title} ({drama_id})")
                
                try:
                    status_msg = await client.send_message(ADMIN_ID, f"🆕 **Auto-Detect Drama Baru!**\n🎬 {title}\n🆔 `{drama_id}`\n⏳ Sedang memproses hardsub...")
                except: status_msg = None
                
                BotState.is_processing = True
                result = await process_drama_full(drama_id, AUTO_CHANNEL, status_msg=status_msg, message_thread_id=MESSAGE_THREAD_ID)
                BotState.is_processing = False
                
                if result == PREMIUM_ERROR:
                    # Token tidak valid / tidak premium — hentikan auto mode
                    logger.error("AUTO MODE: Premium token error detected. Stopping auto mode.")
                    BotState.is_auto_running = False
                    try:
                        await client.send_message(
                            ADMIN_ID,
                            "⛔ **AUTO MODE DIHENTIKAN**\n\n"
                            "Token API tidak memiliki akses premium.\n"
                            "Silakan perbarui `API_TOKEN` di file `.env` dengan token premium yang valid,\n"
                            "lalu ketik /panel dan tekan **Mulai Auto** untuk melanjutkan."
                        )
                    except: pass
                    break  # Keluar dari loop drama, tidak perlu coba drama lain
                elif result:
                    mark_as_processed(drama_id, title)
                    await client.send_message(ADMIN_ID, f"✅ Sukses Post: **{title}**\n😴 Istirahat 2 jam sebelum lanjut...")
                    logger.info(f"Successfully processed {title}. Sleeping for 2 hours...")
                    await asyncio.sleep(2 * 60 * 60) # 2 hours break
                else:
                    logger.error(f"Failed to process {title}")
                    mark_as_failed(drama_id, title)
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
