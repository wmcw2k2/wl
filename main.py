import os
import re
import io
import asyncio
import tempfile
import urllib.request
import shutil
from urllib.parse import urlparse, parse_qs
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.sessions import StringSession
from curl_cffi import requests as c_requests

# ================= CONFIGURATION =================
API_ID = int(os.environ.get('API_ID', '0')) 
API_HASH = os.environ.get('API_HASH', '')
SESSION_STRING = os.environ.get('SESSION_STRING', '')

SOURCE_CHATS = [
    -1003514128213,  
    -1002634794692,  
    -1002345296875,
    -1003549482364,
    -1003895656006,
    '@Ukussapremium_bot', 
    2047350734,
    '@PremiumJil_bot'
]

DESTINATION_CHAT = -1001676677601 

DEFAULT_DOMAINS = ["jillanthaya.giize", "jilhub.giize", "files.fm", "kozow.com"]
# =================================================

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

def scrape_target_url(url, allowed_domains):
    print(f"Scraping URL: {url}")
    IGNORED_EXTENSIONS = ('.ico', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.xml', '.json')
    html_content = "" 

    session = c_requests.Session(impersonate="chrome110")

    try:
        response = session.get(url, allow_redirects=True, timeout=20)
        
        if response.status_code == 403:
            return None, f"❌ Target actively blocked Chrome impersonation (403): {url}"
            
        html_content = response.text

        # =========================================================
        # INTERNAL JS MAP EXTRACTOR
        # =========================================================
        def attempt_js_map_extract(page_url, page_html):
            if "${code}" in page_html and "t.me/" in page_html:
                print("Detecting JS-based locker page...")
                bot_match = re.search(r'https://t\.me/([a-zA-Z0-9_]+)\?start=\$\{code\}', page_html)
                
                if bot_match:
                    bot_username = bot_match.group(1)
                    parsed_url = urlparse(page_url)
                    query_params = parse_qs(parsed_url.query)
                    
                    if 'p' in query_params:
                        raw_param = query_params['p'][0]
                        final_code = raw_param 
                        
                        try:
                            base_path = page_url.split('?')[0].rsplit('/', 1)[0]
                            map_url = f"{base_path}/obfuscatedMap.js"
                            
                            map_resp = session.get(map_url, timeout=10)
                            if map_resp.status_code == 200:
                                map_match = re.search(rf'["\']{re.escape(raw_param)}["\']\s*:\s*["\']([^"\']+)["\']', map_resp.text)
                                if map_match:
                                    final_code = map_match.group(1)
                                    print(f"✅ Decoded obfuscated param: {raw_param} -> {final_code}")
                        except Exception as e:
                            print(f"⚠️ Could not process obfuscatedMap.js: {e}")
                        
                        telegram_link = f"https://t.me/{bot_username}?start={final_code}"
                        print(f"✅ Generated Telegram Deep Link: {telegram_link}")
                        return telegram_link
            return None

        # =========================================================
        # INTERNAL DOWNLOAD FUNCTION
        # =========================================================
        def attempt_direct_download(page_url, page_html):
            video_url = None
            if "files.fm" in page_url:
                meta_match = re.search(r'property="og:image".*?content="https://([^/]+)/thumb_video_picture\.php\?i=([^"]+)"', page_html)
                sess_match = re.search(r"var\s+PHPSESSID\s*=\s*['\"]([^'\"]+)['\"]", page_html)
                
                if meta_match and sess_match:
                    host = meta_match.group(1).strip()
                    file_hash = meta_match.group(2).strip()
                    sess_id = sess_match.group(1).strip()
                    
                    v_match = re.search(r'\.mp4\?v=(\d+)', page_html)
                    v_val = v_match.group(1).strip() if v_match else "1771587749"
                    
                    video_url = f"https://{host}/thumb_video/{file_hash}.mp4?v={v_val}&PHPSESSID={sess_id}"

            if video_url:
                print(f"✅ Generated Direct Video Link: {video_url}")
                print("⬇️ Downloading file natively to bypass HTTP/2 chunking bugs...")
                
                try:
                    cookie_str = "; ".join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
                    
                    req = urllib.request.Request(
                        video_url, 
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                            'Referer': page_url,
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Connection': 'keep-alive',
                            'Cookie': cookie_str
                        }
                    )
                    
                    with urllib.request.urlopen(req, timeout=120) as vid_resp:
                        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        shutil.copyfileobj(vid_resp, tmp_file)
                        tmp_file.close()
                        
                        if os.path.getsize(tmp_file.name) > 100000:
                            return "DOWNLOADED_FILE", tmp_file.name
                        else:
                            os.remove(tmp_file.name)
                            print("❌ Downloaded file was too small. Likely an HTML error page.")
                            
                except Exception as e:
                    print(f"❌ Exception during native download: {e}")
                    
            return None, None
        # =========================================================

        # CHECK 1: Is the FIRST link files.fm?
        dl_flag, dl_path = attempt_direct_download(url, html_content)
        if dl_flag == "DOWNLOADED_FILE":
            return dl_flag, dl_path

        # CHECK 1b: Is it a JS Map Locker page?
        js_tg_link = attempt_js_map_extract(url, html_content)
        if js_tg_link:
            return js_tg_link, html_content

        # Step 2: Telegram Link logic
        tg_pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(tg_pattern, html_content)
        
        if match:
            print("✅ Found Telegram link on the FIRST page!")
            return match.group(1), html_content
            
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
            if not matched_domain or link.lower().endswith(IGNORED_EXTENSIONS):
                continue
            if "/202" in link or ".html" in link or "/video" in link:
                intermediary_link = link
                break
            if not intermediary_link:
                intermediary_link = link

        if not intermediary_link:
            print("❌ Failed: No valid intermediary links matched our domain list.")
            return None, html_content
            
        print(f"Found matching intermediary link: {intermediary_link}")
        print("Scraping intermediary page...")
        
        response2 = session.get(intermediary_link, allow_redirects=True, timeout=20)
        
        if response2.status_code == 403:
            return None, f"❌ Intermediary page blocked us (403): {intermediary_link}"
            
        html_content = response2.text
        
        # CHECK 2: Is the INTERMEDIARY link files.fm?
        dl_flag, dl_path = attempt_direct_download(intermediary_link, html_content)
        if dl_flag == "DOWNLOADED_FILE":
            return dl_flag, dl_path

        # CHECK 2b: Is it a JS Map Locker page?
        js_tg_link = attempt_js_map_extract(intermediary_link, html_content)
        if js_tg_link:
            return js_tg_link, html_content

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


# ====================================================================
# NEW FEATURE: Background Task Processor for Parallel Link Handling
# ====================================================================
async def process_single_link(url_to_visit, chat_name):
    """Processes a single URL independently so the main event loop isn't blocked."""
    print(f"\nProcessing Link: {url_to_visit}")

    loop = asyncio.get_running_loop()
    scrape_result = await loop.run_in_executor(None, scrape_target_url, url_to_visit, INTERMEDIARY_DOMAINS)
    
    bot_start_link, debug_content = scrape_result

    # ==========================================================
    # DIRECT VIDEO UPLOADER
    # ==========================================================
    if bot_start_link == "DOWNLOADED_FILE":
        temp_file_name = debug_content
        file_size_mb = os.path.getsize(temp_file_name) / (1024 * 1024)
        print(f"✅ Local download complete! Size: {file_size_mb:.2f} MB")
        print("🚀 Starting Telegram upload...")
        
        async def upload_progress(current, total):
            print(f"Uploading: {current * 100 / total:.1f}%", end='\r')

        try:
            await client.send_file(
                DESTINATION_CHAT, 
                file=temp_file_name, 
                caption=f"Extracted direct video from {chat_name}\nLink: {url_to_visit}",
                progress_callback=upload_progress,
                supports_streaming=True
            )
            print("\n✅ Upload complete!")
        except Exception as upload_err:
            print(f"\n❌ FAILED DURING UPLOAD TO TELEGRAM: {upload_err}")
            bot_start_link = None
            debug_content = f"Telegram Upload Error: {str(upload_err)}"
        
        if os.path.exists(temp_file_name):
            os.remove(temp_file_name)
            
        if bot_start_link == "DOWNLOADED_FILE": 
            return 

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
            
        return 

    # ==========================================================
    # BOT CONVERSATION HANDLER (Smart checking for Videos/Docs)
    # ==========================================================
    parse_pattern = r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)"
    parsed = re.search(parse_pattern, bot_start_link)

    if parsed:
        bot_username = parsed.group(1)
        start_token = parsed.group(2)

        try:
            print(f"Interacting with @{bot_username}...")
            async with client.conversation(bot_username, timeout=30) as conv:
                await conv.send_message(f"/start {start_token}")
                
                # Listen to up to 10 sequential messages to find the video
                target_video_msg = None
                for _ in range(10):
                    try:
                        # Wait 10 seconds for each message chunk
                        response = await conv.get_response(timeout=10)
                        
                        # Only accept it if it's explicitly a Video or a Document
                        # (Ignores welcome photos, ad banners, and plain text)
                        if response.video or response.document:
                            target_video_msg = response
                            break 
                    except asyncio.TimeoutError:
                        break # Stop checking if the bot stops talking

                if target_video_msg:
                    print(f"✅ Video received from @{bot_username}! Forwarding...")
                    await client.send_file(
                        DESTINATION_CHAT, 
                        target_video_msg.media, 
                        caption=f"Extracted from {chat_name}"
                    )
                else:
                    print("❌ Bot replied, but did not send a video or document file.")
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


@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handler(event):
    chat = await event.get_chat()
    chat_name = getattr(chat, 'title', getattr(chat, 'username', chat.id))
    
    links = get_all_links(event)
    if not links:
        return

    print(f"--- New Message from {chat_name} (Found {len(links)} links) ---")
    
    # Launch a background task for each link so multiple messages 
    # and albums are processed concurrently without blocking!
    for url_to_visit in links:
        asyncio.create_task(process_single_link(url_to_visit, chat_name))


async def main():
    print("Starting bot...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
