import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

async def test_admin():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    print(f"Sending test message to ADMIN {ADMIN_ID}...")
    try:
        await client.send_message(
            ADMIN_ID, 
            "🚀 **Tes Bot**\n\nBot berhasil mengirim pesan ke Admin!"
        )
        print("SUCCESS: Message sent to Admin!")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_admin())
