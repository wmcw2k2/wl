import os
import re
import asyncio
import cloudscraper
import requests
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.sessions import StringSession

# ================= CONFIGURATION =================
# Pulled from Heroku Environment Variables
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')

SOURCE_CHATS = [
    -1003514128213,  
    -1002634794692,  
    '@Ukussapremium_bot', 
    12345678        
]

DESTINATION_CHAT = -1001676677601 

# Default domains to search for if the direct Telegram link isn't found.
# These will survive Heroku restarts.
DEFAULT_DOMAINS = ["nethmi-live-online"]
# =================================================

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# We store our search keywords in a set to avoid duplicates
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

def scrape_target_url(url, allowed_domains):
    """
    Two-step scraper with Anti-403 Short URL Bypass:
    1. Unshortens links using HEAD requests to skip bot checks.
    2. Looks for Telegram link.
    3. If not found, looks for an intermediary link.
    """
    print(f"Scraping URL: {url}")
    
    # --- ANTI-403 SHORTURL BYPASS ---
    try:
        # Realistic browser header to blend in
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'}
        
        # Send a HEAD request instead of GET. This forces the server to just give us the redirect location.
        pre_check = requests.head(url, headers=headers, allow_redirects=False, timeout=10)
        
        # If the server responds with a redirect status code (301, 302, etc.)
        if pre_check.status_code in [301, 302, 303, 307, 308] and 'Location' in pre_check.headers:
            new_url = pre_check.headers['Location']
            print(f"✅ Bypassed Short URL! Resolved to: {new_url}")
            url = new_url  # Replace the short link with the real destination
    except Exception as e:
        print(f"HEAD bypass check failed, continuing with original URL: {e}")
    # --------------------------------

    try:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        
        # Step 1: Scrape the page
        try:
            response = scraper.get(url, allow_redirects=True, timeout=15)
            response.raise_for_status()
            html_content = response.text
        except requests.exceptions.HTTPError as e:
            # Fallback: Sometimes Cloudflare blocks Cloudscraper but allows a plain request with a modern User-Agent
            if e.response.status_code == 403:
                print("⚠️ Cloudscraper blocked (403). Falling back to standard requests...")
                response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
                response.raise_for_status()
                html_content = response.text
            else:
                raise e
        
        # Regex for Telegram deep links (supports hyphens and underscores in tokens)
        tg_pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(tg_pattern, html_content)
        
        if match:
            print("✅ Found Telegram link on the FIRST page!")
            return match.group(1)
            
        # Step 2: Telegram link not found. Look for an intermediary link.
        print("No Telegram link found. Searching for intermediary links...")
        link_pattern = r'href=["\'](https?://[^\'"]+)["\']'
        all_links = re.findall(link_pattern, html_content)
        
        intermediary_link = None
        for link in all_links:
            for domain in allowed_domains:
                if domain in link:
                    intermediary_link = link
                    break
            if intermediary_link:
                break
                
        if not intermediary_link:
            print("❌ Failed: No intermediary links matched our domain list.")
            return None
            
        # Step 3: Scrape the intermediary page
        print(f"Found matching intermediary link: {intermediary_link}")
        print("Scraping intermediary page...")
        
        try:
            response2 = scraper.get(intermediary_link, allow_redirects=True, timeout=15)
            response2.raise_for_status()
            html_content2 = response2.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                response2 = requests.get(intermediary_link, headers=headers, allow_redirects=True, timeout=15)
                response2.raise_for_status()
                html_content2 = response2.text
            else:
                raise e
        
        match2 = re.search(tg_pattern, html_content2)
        if match2:
            print("✅ Found Telegram link on the SECOND page!")
            return match2.group(1)
        else:
            print("❌ Failed: Intermediary page did not contain a Telegram link.")
            
    except Exception as e:
        print(f"❌ Error scraping URL: {e}")
        
    return None
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
# Listens only to messages YOU send (from_users='me') anywhere.
@client.on(events.NewMessage(pattern=r'/adddomain (.*)', from_users='me'))
async def add_domain_handler(event):
    url = event.pattern_match.group(1).strip()
    
    try:
        # Extract the main keyword from the link
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        keyword = netloc.split('.')[0] # Grabs the first part before the dot
        
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
        # Pass the global set of domains to our scraper thread
        bot_start_link = await loop.run_in_executor(None, scrape_target_url, url_to_visit, INTERMEDIARY_DOMAINS)

        # ---> FAILURE LOGIC: Send to Saved Messages <---
        if not bot_start_link:
            print("Failed to get link. Sending to Saved Messages...")
            await client.send_message(
                'me', 
                f"❌ **Extraction Failed**\nCould not find a valid Telegram bot link inside:\n{url_to_visit}"
            )
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
                    # Skip up to 3 text-only "Please wait" messages
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
    # asyncio.run ensures an Event Loop is properly created for Heroku
    asyncio.run(main())


