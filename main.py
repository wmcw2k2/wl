import os
import re
import requests
import asyncio
import cloudscraper
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.sessions import StringSession

# ================= CONFIGURATION =================
# We now pull these from Heroku's Environment Variables
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')

SOURCE_CHATS = [
    -1003514128213,  
    -1002634794692,  
    '@Ukussapremium_bot',
    '@PremiumJil_bot', 
    12345678        
]

DESTINATION_CHAT = -1001676677601 
# =================================================

# Initialize with StringSession!
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def scrape_target_url(url):
    print(f"Scraping URL: {url}")
    try:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        response = scraper.get(url, allow_redirects=True, timeout=15)
        response.raise_for_status()
        
        pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(pattern, response.text)
        
        if match:
            return match.group(1)
            
    except Exception as e:
        print(f"Error scraping URL: {e}")
        
    return None

def get_all_links(event):
    urls = set()
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if hasattr(btn, 'url') and btn.url:
                    urls.add(btn.url)

    if event.message.entities:
        for ent in event.message.entities:
            if isinstance(ent, MessageEntityTextUrl):
                urls.add(ent.url)
            elif isinstance(ent, MessageEntityUrl):
                url_text = event.text[ent.offset : ent.offset + ent.length]
                urls.add(url_text)
    
    return list(urls)

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handler(event):
    chat = await event.get_chat()
    chat_name = getattr(chat, 'title', getattr(chat, 'username', chat.id))
    
    links = get_all_links(event)
    if not links:
        return

    print(f"--- New Message from {chat_name} ---")
    
    for i, url_to_visit in enumerate(links, 1):
        print(f"\nProcessing Link: {url_to_visit}")

        loop = asyncio.get_event_loop()
        bot_start_link = await loop.run_in_executor(None, scrape_target_url, url_to_visit)

        if not bot_start_link:
            continue 

        parse_pattern = r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)"
        parsed = re.search(parse_pattern, bot_start_link)

        if parsed:
            bot_username = parsed.group(1)
            start_token = parsed.group(2)

            try:
                async with client.conversation(bot_username, timeout=20) as conv:
                    await conv.send_message(f"/start {start_token}")
                    response = await conv.get_response()

                    limit = 3
                    while limit > 0 and not response.media:
                         response = await conv.get_response()
                         limit -= 1

                    if response.media:
                        print("Video received! Forwarding...")
                        await client.send_file(
                            DESTINATION_CHAT, 
                            response.media, 
                            caption=f"Extracted from {chat_name}"
                        )
            except Exception as e:
                print(f"Conversation failed: {e}")
        
        await asyncio.sleep(2)

print("Starting bot...")
client.start()
client.run_until_disconnected()