import os
import re
import io
import asyncio
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.sessions import StringSession
from curl_cffi import requests as c_requests

# ================= CONFIGURATION =================
# Pulled from Heroku Environment Variables
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')

SOURCE_CHATS = [
    -1003514128213,  
    -1002634794692,  
    '@Ukussapremium_bot', 
    2047350734,
    '@PremiumJil_bot'
            
]

DESTINATION_CHAT = -1001676677601 

# Default domains to search for if the direct Telegram link isn't found.
# These will survive Heroku restarts.
DEFAULT_DOMAINS = ["jillanthaya.giize", "jilhub.giize"]
# =================================================

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# We store our search keywords in a set to avoid duplicates
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

def scrape_target_url(url, allowed_domains):
    """
    Two-step scraper using curl_cffi.
    Returns a tuple: (extracted_link, html_content_for_debugging)
    """
    print(f"Scraping URL: {url}")
    
    IGNORED_EXTENSIONS = ('.ico', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.xml', '.json')
    html_content = "" # Keep track of the HTML so we can return it on failure

    try:
        # Step 1: Scrape the first page
        response = c_requests.get(
            url, 
            impersonate="chrome110", 
            allow_redirects=True, 
            timeout=20
        )
        
        if response.status_code == 403:
            return None, f"❌ Target actively blocked Chrome impersonation (403): {url}"
            
        html_content = response.text
        
        # Regex for Telegram deep links
        tg_pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(tg_pattern, html_content)
        
        if match:
            print("✅ Found Telegram link on the FIRST page!")
            return match.group(1), html_content
            
        # Step 2: Telegram link not found. Look for an intermediary link.
        print("No Telegram link found. Searching for intermediary links...")
        
        link_pattern = r'["\'](https?://[^\'"]+)["\']'
        all_links = re.findall(link_pattern, html_content)
        
        intermediary_link = None
        for link in all_links:
            # Check 1: Does it match our domain?
            matched_domain = False
            for domain in allowed_domains:
                if domain in link:
                    matched_domain = True
                    break
            
            if not matched_domain:
                continue

            # Check 2: Is it a junk file (favicon, image, css)?
            if link.lower().endswith(IGNORED_EXTENSIONS):
                continue
                
            # Check 3 (Optional): Prioritize links that look like posts
            if "/202" in link or ".html" in link or "/video" in link:
                intermediary_link = link
                break
            
            # Keep as backup if not a "perfect" match
            if not intermediary_link:
                intermediary_link = link

        if not intermediary_link:
            print("❌ Failed: No valid intermediary links matched our domain list.")
            return None, html_content
            
        # Step 3: Scrape the intermediary page
        print(f"Found matching intermediary link: {intermediary_link}")
        print("Scraping intermediary page...")
        
        response2 = c_requests.get(
            intermediary_link, 
            impersonate="chrome110", 
            allow_redirects=True, 
            timeout=20
        )
        
        if response2.status_code == 403:
            return None, f"❌ Intermediary page blocked us (403): {intermediary_link}"
            
        html_content = response2.text
        
        match2 = re.search(tg_pattern, html_content)
        if match2:
            print("✅ Found Telegram link on the SECOND page!")
            return match2.group(1), html_content
        else:
            print("❌ Failed: Intermediary page did not contain a Telegram link.")
            return None, html_content
            
    except Exception as e:
        print(f"❌ Error scraping URL: {e}")
        return None, f"Error Exception: {str(e)}\n\nLast HTML extracted:\n{html_content}"

def get_all_links(event):
    """ Extracts ALL URLs from a message (Inline Buttons + Text Hyperlinks) """
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

# --- NEW FEATURE: Command to add domains dynamically ---
@client.on(events.NewMessage(pattern=r'/adddomain (.*)', from_users='me'))
async def add_domain_handler(event):
    url = event.pattern_match.group(1).strip()
    
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        keyword = netloc.split('.')[0] 
        
        if keyword:
            INTERMEDIARY_DOMAINS.add(keyword)
            await event.reply(f"✅ Successfully added keyword: **{keyword}**\n\nCurrently active domains:\n{', '.join(INTERMEDIARY_DOMAINS)}")
        else:
            await event.reply("❌ Could not extract a valid domain from that link.")
            
    except Exception as e:
        await event.reply(f"❌ Error parsing link: {e}")

# --- Main Link Handler ---
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

        loop = asyncio.get_running_loop()
        scrape_result = await loop.run_in_executor(None, scrape_target_url, url_to_visit, INTERMEDIARY_DOMAINS)
        
        # Unpack the two values returned by the scraper
        bot_start_link, debug_content = scrape_result

        # ---> FAILURE LOGIC: Send HTML to Saved Messages <---
        if not bot_start_link:
            print("Failed to get link. Sending debug HTML to Saved Messages...")
            caption = f"❌ **Extraction Failed**\nCould not find a valid link inside:\n{url_to_visit}"
            
            if debug_content:
                # Create an in-memory file to avoid Heroku storage issues
                debug_file = io.BytesIO(debug_content.encode('utf-8'))
                debug_file.name = "debug_page_source.txt"
                
                await client.send_file('me', file=debug_file, caption=caption)
            else:
                await client.send_message('me', caption + "\n\n(No HTML content was retrieved)")
                
            continue 

        parse_pattern = r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)"
        parsed = re.search(parse_pattern, bot_start_link)

        if parsed:
            bot_username = parsed.group(1)
            start_token = parsed.group(2)

            try:
                print(f"Interacting with @{bot_username}...")
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
                    else:
                        print("Bot replied, but did not send a media file.")
                        await client.send_message(
                            'me', 
                            f"⚠️ **Target Bot Failed**\n@{bot_username} did not send a video for link:\n{url_to_visit}"
                        )
            except asyncio.TimeoutError:
                 print("Conversation timed out.")
                 await client.send_message(
                     'me', 
                     f"⏱ **Timeout**\n@{bot_username} took too long to respond for link:\n{url_to_visit}"
                 )
            except Exception as e:
                print(f"Conversation failed: {e}")
        
        await asyncio.sleep(2)

# --- STARTUP LOGIC ---
async def main():
    print("Starting bot...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())

