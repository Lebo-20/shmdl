import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
AUTO_CHANNEL = int(os.environ.get("AUTO_CHANNEL", "0"))
MESSAGE_THREAD_ID = int(os.environ.get("MESSAGE_THREAD_ID", "0"))

async def test_send():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    print(f"Sending test message to {AUTO_CHANNEL} (Topic: {MESSAGE_THREAD_ID})...")
    try:
        entity = await client.get_entity(AUTO_CHANNEL)
        await client.send_message(
            entity, 
            "🚀 **Tes Pengiriman Pesan Ke Topik**\n\nBot berhasil dikonfigurasi untuk mengirim ke topik ini!",
            reply_to=MESSAGE_THREAD_ID
        )
        print("SUCCESS: Message sent successfully!")
    except Exception as e:
        print(f"FAILED: Failed to send message: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_send())
