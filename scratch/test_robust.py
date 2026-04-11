import asyncio
import os
from telethon import TelegramClient
from telethon.tl.types import PeerChannel
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
AUTO_CHANNEL = int(os.environ.get("AUTO_CHANNEL", "0"))
MESSAGE_THREAD_ID = int(os.environ.get("MESSAGE_THREAD_ID", "0"))

async def test_send_robust():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    # Try different ID formats
    ids_to_try = [AUTO_CHANNEL]
    
    # If it was -100..., try without -100 as well (though for channels it needs -100)
    # but maybe it's not a channel?
    base_id = abs(AUTO_CHANNEL)
    if str(base_id).startswith("100"):
        ids_to_try.append(int(str(base_id)[3:]))
    
    print(f"Trying to send to IDs: {ids_to_try}")
    
    for target_id in ids_to_try:
        try:
            print(f"Attempting to send to {target_id}...")
            await client.send_message(
                target_id, 
                "🚀 **Tes Pengiriman Pesan Ke Topik**\n\nJika Anda melihat pesan ini, konfigurasi ID berhasil!",
                reply_to=MESSAGE_THREAD_ID
            )
            print(f"SUCCESS: Sent to {target_id}")
            await client.disconnect()
            return
        except Exception as e:
            print(f"FAILED for {target_id}: {e}")
            
    print("\nListing dialogs again to see if anything changed...")
    # Telethon bots can't iter_dialogs, but maybe they can get_entity if they know the hash?
    # Usually bots can't 'guess' entities.
    
    print("TIP: Please make sure you have ADDED the bot to the group and sent a message there.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_send_robust())
