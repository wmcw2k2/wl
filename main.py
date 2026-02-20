import os
import re
import io
import asyncio
import tempfile
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.sessions import StringSession
from curl_cffi import requests as c_requests

# ================= CONFIGURATION =================
# Pulled from Heroku Environment Variables
API_ID = int(os.environ.get('API_ID', '0')) # Default to 0 to prevent crash if missing locally
API_HASH = os.environ.get('API_HASH', '')
SESSION_STRING = os.environ.get('SESSION_STRING', '')

SOURCE_CHATS = [
    -1003514128213,  
    -1002634794692,  
    '@Ukussapremium_bot', 
    2047350734,
    '@PremiumJil_bot'
]

DESTINATION_CHAT = -1001676677601 

# Default domains to search for if the direct Telegram link isn't found.
DEFAULT_DOMAINS = ["jillanthaya.giize", "jilhub.giize", "files.fm"]
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
        
        # =========================================================
        # CHECK 1: Is the FIRST link files.fm?
        # =========================================================
        if "files.fm" in url:
            print("Detecting files.fm (Step 1), attempting to extract direct video variables...")
            img_match = re.search(r'https://([^/]+)/thumb_video_picture\.php\?i=([^"\']+)', html_content)
            sess_match = re.search(r"var\s+PHPSESSID\s*=\s*['\"]([^'\"]+)['\"]", html_content)
            
            if img_match and sess_match:
                file_host = img_match.group(1).strip()
                file_hash = img_match.group(2).strip()
                sess_id = sess_match.group(1).strip()
                
                v_match = re.search(r'\.mp4\?v=(\d+)', html_content)
                v_val = v_match.group(1).strip() if v_match else "1771587749"
                
                video_url = f"https://{file_host}/thumb_video/{file_hash}.mp4?v={v_val}&PHPSESSID={sess_id}"
                video_url = video_url.strip()
                
                print(f"✅ Generated Files.fm Direct Video Link: {video_url}")
                return "DIRECT_VIDEO", video_url

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
            matched_domain = False
            for domain in allowed_domains:
                if domain in link:
                    matched_domain = True
                    break
            
            if not matched_domain:
                continue

            if link.lower().endswith(IGNORED_EXTENSIONS):
                continue
                
            if "/202" in link or ".html" in link or "/video" in link:
                intermediary_link = link
                break
            
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
        
        # =========================================================
        # CHECK 2: Is the INTERMEDIARY link files.fm?
        # =========================================================
        if "files.fm" in intermediary_link:
            print("Detecting files.fm (Step 3), attempting to extract direct video variables...")
            img_match = re.search(r'https://([^/]+)/thumb_video_picture\.php\?i=([^"\']+)', html_content)
            sess_match = re.search(r"var\s+PHPSESSID\s*=\s*['\"]([^'\"]+)['\"]", html_content)
            
            if img_match and sess_match:
                file_host = img_match.group(1).strip()
                file_hash = img_match.group(2).strip()
                sess_id = sess_match.group(1).strip()
                
                v_match = re.search(r'\.mp4\?v=(\d+)', html_content)
                v_val = v_match.group(1).strip() if v_match else "1771587749"
                
                video_url = f"https://{file_host}/thumb_video/{file_hash}.mp4?v={v_val}&PHPSESSID={sess_id}"
                video_url = video_url.strip()
                
                print(f"✅ Generated Files.fm Direct Video Link: {video_url}")
                return "DIRECT_VIDEO", video_url

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


# --- Command to add domains dynamically ---
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
        
        bot_start_link, debug_content = scrape_result

        # ==========================================================
        # FEATURE: Download Direct Video via System Curl
        # ==========================================================
        # ==========================================================
        # FEATURE: Download Direct Video via System Curl
        # ==========================================================
        if bot_start_link == "DIRECT_VIDEO":
            video_url = debug_content.strip()
            print(f"Downloading direct video via curl from: {video_url}")
            temp_file_name = None
            
            try:
                # Create a temporary file path
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                    temp_file_name = tmp_file.name

                print("Starting system curl download...")
                
                # Added -f so curl fails immediately on 404/403 errors
                command = f'curl -f -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -o "{temp_file_name}" "{video_url}"'
                
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.getsize(temp_file_name) > 1000:
                    file_size_mb = os.path.getsize(temp_file_name) / (1024 * 1024)
                    print(f"✅ Video downloaded successfully! Size: {file_size_mb:.2f} MB")
                    print("🚀 Starting Telegram upload...")
                    
                    # --- Progress tracker function ---
                    async def upload_progress(current, total):
                        # Prints upload percentage on the same line
                        print(f"Uploading: {current * 100 / total:.1f}% ({current}/{total} bytes)", end='\r')

                    try:
                        # Uploading to Telegram
                        await client.send_file(
                            DESTINATION_CHAT, 
                            file=temp_file_name, 
                            caption=f"Extracted direct video from {chat_name}\nLink: {url_to_visit}",
                            progress_callback=upload_progress,
                            supports_streaming=True # Helps Telegram recognize it as a streamable video
                        )
                        print("\n✅ Upload complete!")
                    except Exception as upload_err:
                        print(f"\n❌ FAILED DURING UPLOAD TO TELEGRAM: {upload_err}")
                        bot_start_link = None
                        debug_content = f"Telegram Upload Error: {str(upload_err)}"
                    
                    # Clean up
                    if os.path.exists(temp_file_name):
                        os.remove(temp_file_name)
                        
                    if bot_start_link == "DIRECT_VIDEO": 
                        continue # Finished successfully, skip to next link
                else:
                    print(f"❌ Curl download failed. Return code: {process.returncode}")
                    print(f"Curl Error Log: {stderr.decode()}")
                    if temp_file_name and os.path.exists(temp_file_name):
                        os.remove(temp_file_name)
                        
                    bot_start_link = None
                    debug_content = f"Failed to download direct video via curl.\nError: {stderr.decode()}"
            
            except Exception as e:
                print(f"❌ System Error during direct video process: {e}")
                if temp_file_name and os.path.exists(temp_file_name):
                    os.remove(temp_file_name)
                bot_start_link = None
                debug_content = f"Exception downloading video: {str(e)}"
        # ==========================================================


        # ---> FAILURE LOGIC: Send HTML to Saved Messages <---
        if not bot_start_link:
            print("Failed to get link. Sending debug HTML to Saved Messages...")
            caption = f"❌ **Extraction Failed**\nCould not find a valid link inside:\n{url_to_visit}"
            
            if debug_content:
                debug_file = io.BytesIO(debug_content.encode('utf-8'))
                debug_file.name = "debug_page_source.txt"
                
                await client.send_file('me', file=debug_file, caption=caption)
            else:
                await client.send_message('me', caption + "\n\n(No HTML content was retrieved)")
                
            continue 

        # If it's a telegram deep link, interact with the bot
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

