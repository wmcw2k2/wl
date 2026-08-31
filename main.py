import os
import re
import io
import asyncio
import tempfile
import urllib.request
import shutil
import cv2  
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl, DocumentAttributeVideo, UpdateBotChatInviteRequester
from telethon.sessions import StringSession
from curl_cffi import requests as c_requests

# === SPEED CHECK ===
try:
    import cryptg
    print("✅ cryptg is installed! Telethon encryption will run at MAX speed.")
except ImportError:
    print("⚠️ WARNING: cryptg is NOT installed! Downloads/uploads will be EXTREMELY SLOW. Add it to requirements.txt")

try:
    from playwright.async_api import async_playwright
    print("✅ Playwright is installed for advanced Cloudflare bypasses!")
except ImportError:
    print("⚠️ WARNING: playwright is NOT installed! Sub2Unlock links will fail. Add it to requirements.txt")

# ================= USERBOT CONFIGURATION =================
API_ID = int(os.environ.get('API_ID', '0')) 
API_HASH = os.environ.get('API_HASH', '')
SESSION_STRING = os.environ.get('SESSION_STRING', '')

SOURCE_CHATS = [
    -1003514128213, -1002634794692, -1002345296875, -1003549482364,
    -1003895656006, '@Ukussapremium_bot', 2047350734, '@PremiumJil_bot',
    '@sepalanthaya_bot', -1004426349670, -1003614577146, '@kamasthranew_bot',
    -1004347282963, -1003919794212, -1003995891596, -1001577090635,
    -1004433802308, -1004484922375, -1003198230573, -1003741372960,-1003977346004
]

DESTINATION_CHAT = -1001676677601 
DESTINATION_CHAT_2 = -1004233359054

DEFAULT_DOMAINS = [
    "jillanthaya.giize", "jilhub.giize", "jilhub.xyz", "video.jilhub.xyz", 
    "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz", 
    "files.fm", "kozow.com", "sub2unlock.me"
]

# ================= BOT CONFIGURATION =================
BOT_TOKEN = '8854380624:AAGUIkAFRtiraWZFyFPt_uBQ3_BWSyK5iHU'
MY_OWNER_ID = 2076006645 # Only you can use the toggle command

CHANNEL_1_LINK = "https://t.me/+q0A3T5Sm3l5kMWFh"
CHANNEL_2_LINK = "https://t.me/+ilqc6YCcH105M2Rh"
FINAL_CHANNEL_LINK = "https://t.me/+dGavgBgyBlA1MTVh"

# The IDs of the two channels (Ensure bot is ADMIN with 'Invite Users' permission in both)
CHANNEL_1_ID = -1004390399908
CHANNEL_2_ID = -1004435996353

RAW_CH1 = int(str(CHANNEL_1_ID).replace("-100", ""))
RAW_CH2 = int(str(CHANNEL_2_ID).replace("-100", ""))
# =========================================================

# Global state for forwarding to Destination 2
FORWARD_TO_CH2 = True

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

# Locks & memory
bot_locks = defaultdict(asyncio.Lock)
join_requests = {RAW_CH1: set(), RAW_CH2: set()}


# ====================================================================
# UNIVERSAL FIRESTORE BYPASSER
# ====================================================================
def bypass_firestore_sync(url):
    print(f"\n[*] Executing Firestore exploit for: {url}")
    slug = url.rstrip('/').split('/')[-1]
    
    if any(domain in url for domain in ["clipgo.xyz", "sub2unlock.xyz"]):
        project_id = "linksite-5d1d5"
    elif any(domain in url for domain in ["video.jilhub.xyz", "jilzone.xyz"]):
        project_id = "jhub2-f9b30"
    elif "gabadawa.xyz" in url:
        project_id = "csongz"
    else:
        project_id = "jhub-46611"
        
    api_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/links/{slug}"
    session = c_requests.Session(impersonate="chrome110")
    
    try:
        resp = session.get(api_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            fields = data.get("fields", {})
            for key, value_dict in fields.items():
                if isinstance(value_dict, dict) and value_dict:
                    val = list(value_dict.values())[0]
                    if isinstance(val, str) and "t.me" in val:
                        print(f"✅ Firestore Direct Bypassed ({project_id}): {val}")
                        return val
        print(f"❌ Firestore returned {resp.status_code}. Document might be missing.")
    except Exception as e:
        print(f"❌ Firestore bypass failed: {e}")
    return None


# ====================================================================
# ADVANCED PLAYWRIGHT BYPASSER FOR SUB2UNLOCK (.ME)
# ====================================================================
async def bypass_sub2unlock(url):
    print(f"\n[*] Launching browser using Heroku Buildpack Chrome...")
    async with async_playwright() as p:
        chrome_path = "/app/.apt/usr/bin/google-chrome" 
        if not os.path.exists(chrome_path):
            chrome_path = "/app/.chrome-for-testing/chrome-linux64/chrome"

        browser = await p.chromium.launch(
            headless=True,
            executable_path=chrome_path,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        extracted_link = None
        page = await context.new_page()

        async def handle_new_page(new_page):
            print("[-] Task clicked. Blocked the pop-up tab.")
            try: await new_page.close()
            except Exception: pass
        context.on("page", handle_new_page)

        async def handle_response(response):
            nonlocal extracted_link
            if "links/go" in response.url and response.status == 200:
                try:
                    body = await response.json()
                    if "url" in body and "t.me" in body["url"]:
                        extracted_link = body["url"]
                except Exception: pass
        page.on("response", handle_response)

        try:
            print("[*] Navigating to page (using domcontentloaded)...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)

            print("[*] Clicking all required task buttons...")
            task_buttons = await page.locator(".step.linky").all()
            for i, step in enumerate(task_buttons, 1):
                try:
                    print(f"[*] Clicking Task #{i}...")
                    await step.click(force=True)
                    await asyncio.sleep(2)
                except Exception: pass
            
            print("[*] Waiting 10 seconds for the internal JS timer...")
            await asyncio.sleep(10)

            unlock_btn = page.locator("#file")
            if await unlock_btn.is_visible():
                print("[*] Clicking 'Get Your Link'...")
                await unlock_btn.evaluate("el => el.removeAttribute('disabled')")
                try:
                    async with page.expect_navigation(timeout=15000) as nav_info:
                        await unlock_btn.click(force=True)
                    final_url = page.url
                    if "t.me" in final_url:
                        print(f"✅ SUCCESS! Caught navigation to: {final_url}")
                        return final_url
                except:
                    print("[*] No immediate navigation detected.")

                await asyncio.sleep(2)
                for p in page.context.pages:
                    if "t.me" in p.url:
                        print(f"✅ SUCCESS! Caught link in new tab: {p.url}")
                        return p.url
                        
            print("❌ Bypass Failed: Link not found in API, Redirect, or DOM.")
            return None 

        except Exception as e:
            print(f"❌ Playwright execution error: {e}")
        finally:
            await browser.close()
            return extracted_link


# ====================================================================
# FAST CURL_CFFI SCRAPER FOR FILES.FM / JS MAPS / DEEP LINKS
# ====================================================================
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
            
        dl_flag, dl_path = attempt_direct_download(url, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

        js_tg_link = attempt_js_map_extract(url, html_content)
        if js_tg_link: return js_tg_link, html_content

        tg_pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(tg_pattern, html_content)
        if match:
            print("✅ Found Telegram link on the FIRST page!")
            return match.group(1), html_content
            
        print("No Telegram link found. Searching for intermediary links...")
        all_links = re.findall(r'["\'](https?://[^\'"]+)["\']', html_content)
        
        intermediary_link = None
        for link in all_links:
            matched_domain = False
            for domain in allowed_domains:
                if domain in link:
                    matched_domain = True
                    break
            if not matched_domain or link.lower().endswith(IGNORED_EXTENSIONS):
                continue
            if "/202" in link or ".html" in link or "/video" in link or "sub2unlock.me" in link:
                intermediary_link = link
                break
            if not intermediary_link:
                intermediary_link = link

        if not intermediary_link:
            print("❌ Failed: No valid intermediary links matched our domain list.")
            return None, html_content

        if "sub2unlock.me" in intermediary_link:
            print("✅ Found Sub2Unlock.me inside page! Sending back to Playwright...")
            return "SUB2UNLOCK", intermediary_link
            
        if any(d in intermediary_link for d in ["jilhub.xyz", "jilhub.giize", "jillanthaya.giize", "video.jilhub.xyz", "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"]):
            print("✅ Found Firestore Site inside page! Sending back to bypasser...")
            return "FIRESTORE", intermediary_link
            
        print(f"Found matching intermediary link: {intermediary_link}")
        response2 = session.get(intermediary_link, allow_redirects=True, timeout=20)
        
        if response2.status_code == 403:
            return None, f"❌ Intermediary page blocked us (403): {intermediary_link}"
            
        html_content = response2.text
        
        dl_flag, dl_path = attempt_direct_download(intermediary_link, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

        js_tg_link = attempt_js_map_extract(intermediary_link, html_content)
        if js_tg_link: return js_tg_link, html_content

        match2 = re.search(tg_pattern, html_content)
        if match2:
            print("✅ Found Telegram link on the SECOND page!")
            return match2.group(1), html_content
        
        sub2_match = re.search(r'(https://sub2unlock\.me/[a-zA-Z0-9]+)', html_content)
        if sub2_match:
            print("✅ Found Sub2Unlock.me inside SECOND page! Sending back to Playwright...")
            return "SUB2UNLOCK", sub2_match.group(1)

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


def extract_video_metadata(file_path):
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened(): return None, None
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = int(frames / fps) if fps > 0 else 0
        
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        ret, frame = cap.read()
        thumb_path = None
        if ret:
            thumb_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            thumb_path = thumb_file.name
            thumb_file.close()
            cv2.imwrite(thumb_path, frame)
        cap.release()
        
        attr = DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True)
        return attr, thumb_path
    except Exception as e:
        print(f"⚠️ Metadata extraction error: {e}")
        return None, None


# ====================================================================
# USERBOT: TASK PROCESSOR
# ====================================================================
async def process_single_link(url_to_visit, chat_name):
    print(f"\nProcessing Link: {url_to_visit}")

    bot_start_link = None
    debug_content = None

    is_firestore_site = any(domain in url_to_visit for domain in [
        "jilhub.xyz", "jilhub.giize", "jillanthaya.giize", "video.jilhub.xyz", 
        "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"
    ])
    
    if is_firestore_site:
        loop = asyncio.get_running_loop()
        bot_start_link = await loop.run_in_executor(None, bypass_firestore_sync, url_to_visit)
        debug_content = "Extracted via Direct Firestore API"
    elif "sub2unlock.me" in url_to_visit:
        bot_start_link = await bypass_sub2unlock(url_to_visit)
        debug_content = "Sub2Unlock Processed via Playwright"
    else:
        loop = asyncio.get_running_loop()
        scrape_result = await loop.run_in_executor(None, scrape_target_url, url_to_visit, INTERMEDIARY_DOMAINS)
        bot_start_link, debug_content = scrape_result
        
        if bot_start_link == "SUB2UNLOCK":
            print(f"🔄 Routing internal link to Sub2Unlock.me Bypasser...")
            sub2_url = debug_content
            bot_start_link = await bypass_sub2unlock(sub2_url)
            debug_content = "Sub2Unlock.me Processed via Playwright (from Intermediary)"
        elif bot_start_link == "FIRESTORE":
            print(f"🔄 Routing internal link to Firestore Bypasser...")
            firestore_url = debug_content
            bot_start_link = await loop.run_in_executor(None, bypass_firestore_sync, firestore_url)
            debug_content = "Processed via Firestore (from Intermediary)"

    # ==========================================================
    # DIRECT VIDEO UPLOADER
    # ==========================================================
    if bot_start_link == "DOWNLOADED_FILE":
        temp_file_name = debug_content
        file_size_mb = os.path.getsize(temp_file_name) / (1024 * 1024)
        print(f"✅ Local download complete! Size: {file_size_mb:.2f} MB")
        print("🔍 Extracting video metadata & generating thumbnail...")
        
        loop = asyncio.get_running_loop()
        attr, thumb_path = await loop.run_in_executor(None, extract_video_metadata, temp_file_name)
        attrs_list = [attr] if attr else []

        print("🚀 Starting fast Telegram upload...")
        async def upload_progress(current, total):
            print(f"Uploading: {current * 100 / total:.1f}%", end='\r')

        try:
            sent_msg = await client.send_file(
                DESTINATION_CHAT, 
                file=temp_file_name, 
                caption=f"Extracted direct video from {chat_name}\nLink: {url_to_visit}",
                progress_callback=upload_progress,
                supports_streaming=True,
                attributes=attrs_list,
                thumb=thumb_path
            )
            print("\n✅ Upload complete to DESTINATION_CHAT!")
            
            # --- FORWARD TO CH2 CONDITIONAL ---
            if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                print("✅ Copied to DESTINATION_CHAT_2 (Hidden Sender & Caption)!")
                
        except Exception as upload_err:
            print(f"\n❌ FAILED DURING UPLOAD TO TELEGRAM: {upload_err}")
            
        if os.path.exists(temp_file_name): os.remove(temp_file_name)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        return 

    # ---> FAILURE LOGIC <---
    if not bot_start_link:
        print("Failed to get link. Sending debug HTML to Saved Messages...")
        caption = f"❌ **Extraction Failed**\nCould not find a valid link inside:\n{url_to_visit}"
        
        if debug_content and isinstance(debug_content, str):
            debug_file = io.BytesIO(debug_content.encode('utf-8'))
            debug_file.name = "debug_page_source.txt"
            await client.send_file('me', file=debug_file, caption=caption)
        else:
            await client.send_message('me', caption + "\n\n(No HTML content was retrieved)")
        return 

    # ==========================================================
    # BOT CONVERSATION HANDLER
    # ==========================================================
    parse_pattern = r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)"
    parsed = re.search(parse_pattern, bot_start_link)

    if parsed:
        bot_username = parsed.group(1)
        start_token = parsed.group(2)

        try:
            print(f"⏳ Waiting in queue to interact with @{bot_username}...")
            async with bot_locks[bot_username]:
                print(f"🟢 Lock acquired! Interacting with @{bot_username}...")
                
                async with client.conversation(bot_username, timeout=30) as conv:
                    await conv.send_message(f"/start {start_token}")
                    
                    target_media_msgs = []
                    while True:
                        try:
                            wait_time = 15 if not target_media_msgs else 3
                            response = await conv.get_response(timeout=wait_time)
                            media_type = type(response.media).__name__ if response.media else "No Media"
                            print(f"[{bot_username}] Got msg | Media: {media_type}")
                            
                            if response.media and (response.video or response.document or response.photo):
                                target_media_msgs.append(response)
                        except asyncio.TimeoutError:
                            print(f"[{bot_username}] Finished gathering files for this link.")
                            break 

                    if target_media_msgs:
                        print(f"✅ Found {len(target_media_msgs)} media file(s) from @{bot_username}! Processing...")
                        for idx, target_media_msg in enumerate(target_media_msgs, 1):
                            print(f"➡️ Processing file {idx} of {len(target_media_msgs)}...")
                            try:
                                sent_msg = await client.send_message(DESTINATION_CHAT, message=target_media_msg)
                                print(f"✅ Successfully forwarded file {idx} to DESTINATION_CHAT!")
                                
                                # --- FORWARD TO CH2 CONDITIONAL ---
                                if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                                    await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                                    print(f"✅ Copied file {idx} to DESTINATION_CHAT_2 (Hidden Sender & Caption)!")
                                    
                            except Exception as forward_err:
                                print(f"⚠️ Direct forward failed ({forward_err}). Falling back to manual download...")
                                temp_path = None
                                thumb_path = None
                                try:
                                    is_video = bool(target_media_msg.video or target_media_msg.document)
                                    extension = ".mp4" if is_video else ".jpg"
                                    
                                    video_attributes = []
                                    if is_video and target_media_msg.document:
                                        for a in target_media_msg.document.attributes:
                                            if isinstance(a, DocumentAttributeVideo):
                                                video_attributes.append(a)
                                    
                                    if target_media_msg.document and target_media_msg.document.thumbs:
                                        thumb_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                                        await client.download_media(target_media_msg.document.thumbs[0], file=thumb_path)

                                    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
                                        temp_path = tmp_file.name
                                        
                                    await client.download_media(target_media_msg, file=temp_path)
                                    
                                    if is_video and not video_attributes:
                                        loop = asyncio.get_running_loop()
                                        attr, gen_thumb = await loop.run_in_executor(None, extract_video_metadata, temp_path)
                                        if attr: video_attributes.append(attr)
                                        if gen_thumb and not thumb_path: thumb_path = gen_thumb

                                    print(f"🚀 Download complete. Uploading file {idx}...")
                                    async def bot_upload_progress(current, total):
                                        print(f"Uploading bypassed file {idx}: {current * 100 / total:.1f}%", end='\r')
                                        
                                    sent_msg = await client.send_file(
                                        DESTINATION_CHAT, 
                                        file=temp_path, 
                                        caption=f"Extracted from {chat_name} (File {idx}/{len(target_media_msgs)})\nBot: @{bot_username}",
                                        progress_callback=bot_upload_progress,
                                        supports_streaming=is_video,
                                        attributes=video_attributes if video_attributes else None,
                                        thumb=thumb_path if is_video else None
                                    )
                                    print(f"\n✅ Manual upload of file {idx} to DESTINATION_CHAT complete!")
                                    
                                    # --- FORWARD TO CH2 CONDITIONAL ---
                                    if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                                        await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                                        print(f"✅ Copied file {idx} to DESTINATION_CHAT_2 (Hidden Sender & Caption)!")
                                        
                                except Exception as manual_err:
                                    print(f"\n❌ Manual download/upload for file {idx} failed: {manual_err}")
                                finally:
                                    if temp_path and os.path.exists(temp_path): os.remove(temp_path)
                                    if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
                    else:
                        print(f"❌ @{bot_username} did not send any media files.")
                        await client.send_message(
                            'me', 
                            f"⚠️ **Target Bot Failed**\n@{bot_username} did not send media for link:\n{url_to_visit}"
                        )
        except Exception as e:
            print(f"Conversation with @{bot_username} failed: {e}")


# ====================================================================
# USERBOT HANDLERS
# ====================================================================
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def source_chat_handler(event):
    chat = await event.get_chat()
    chat_name = getattr(chat, 'title', getattr(chat, 'username', chat.id))
    
    links = get_all_links(event)
    if not links: return

    print(f"--- New Message from {chat_name} (Found {len(links)} links) ---")
    for url_to_visit in links:
        asyncio.create_task(process_single_link(url_to_visit, chat_name))

@client.on(events.NewMessage(pattern=r'/adddomain (.*)', from_users='me'))
async def add_domain_handler(event):
    url = event.pattern_match.group(1).strip()
    try:
        netloc = urlparse(url).netloc
        if netloc.startswith('www.'): netloc = netloc[4:]
        keyword = netloc.split('.')[0] 
        if keyword:
            INTERMEDIARY_DOMAINS.add(keyword)
            await event.reply(f"✅ Successfully added keyword: **{keyword}**\n\nCurrently active domains:\n{', '.join(INTERMEDIARY_DOMAINS)}")
        else:
            await event.reply("❌ Could not extract a valid domain from that link.")
    except Exception as e:
        await event.reply(f"❌ Error parsing link: {e}")


# ====================================================================
# JOIN-GATE BOT HANDLERS & TOGGLE
# ====================================================================
@bot_client.on(events.Raw)
async def track_join_requests(update):
    if isinstance(update, UpdateBotChatInviteRequester):
        channel_id = update.peer.channel_id
        user_id = update.user_id
        if channel_id in join_requests:
            join_requests[channel_id].add(user_id)
            print(f"[*] User {user_id} requested to join channel {channel_id}")

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    # Edit this welcome text to whatever you prefer
    welcome_text = "Welcome to the bot! Please use /join to proceed."
    await event.reply(welcome_text)

async def send_join_message(chat_id):
    buttons = [
        [Button.url('Channel 1', CHANNEL_1_LINK), Button.url('Channel 2', CHANNEL_2_LINK)],
        [Button.inline('Check Join', b'check_join')]
    ]
    await bot_client.send_message(
        chat_id, 
        'Pahala channel walata join request ekk daala Check button eka click karahn', 
        buttons=buttons
    )

@bot_client.on(events.NewMessage(pattern='/join'))
async def join_handler(event):
    await send_join_message(event.chat_id)

@bot_client.on(events.CallbackQuery(data=b'check_join'))
async def check_join_callback(event):
    user_id = event.sender_id
    req_1 = user_id in join_requests[RAW_CH1]
    req_2 = user_id in join_requests[RAW_CH2]

    # Verify if they are already full members
    async def is_member(channel_id):
        try:
            await bot_client.get_permissions(channel_id, user_id)
            return True
        except Exception:
            return False

    member_1 = req_1 or await is_member(CHANNEL_1_ID)
    member_2 = req_2 or await is_member(CHANNEL_2_ID)

    if member_1 and member_2:
        await event.answer("Verification Successful!", alert=False)
        msg = await event.reply(f"Here is your final link:\n{FINAL_CHANNEL_LINK}")
        
        # Background task to delete after 10 seconds
        async def delete_later(message):
            await asyncio.sleep(10)
            try:
                await message.delete()
            except Exception:
                pass
        asyncio.create_task(delete_later(msg))
    else:
        await event.answer("You haven't sent join requests to both channels yet!", alert=True)
        await send_join_message(event.chat_id)

# --- Toggle for DESTINATION_CHAT_2 ---
@bot_client.on(events.NewMessage(pattern=r'/fwd2 (on|off)', from_users=MY_OWNER_ID))
async def toggle_fwd2_bot(event):
    global FORWARD_TO_CH2
    state = event.pattern_match.group(1).lower()
    
    if state == 'on':
        FORWARD_TO_CH2 = True
        await event.reply("✅ Forwarding to 2nd channel is now **ON**.")
    else:
        FORWARD_TO_CH2 = False
        await event.reply("❌ Forwarding to 2nd channel is now **OFF**.")


# ====================================================================
# MAIN EXECUTION
# ====================================================================
async def main():
    print("Starting Userbot...")
    await client.start()
    
    print("Starting Join-Gate Bot...")
    await bot_client.start(bot_token=BOT_TOKEN)
    
    print("✅ Both clients are running simultaneously!")
    await asyncio.gather(
        client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
