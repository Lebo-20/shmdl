import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

async def list_chats():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    
    print("Listing all chats the bot can see:")
    async for dialog in client.iter_dialogs():
        print(f"ID: {dialog.id} | Title: {dialog.title}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(list_chats())
