import os
import re
import io
import asyncio
import tempfile
import urllib.request
import shutil
import cv2
import random
import time
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl, DocumentAttributeVideo, UpdateBotChatInviteRequester
from telethon.sessions import StringSession
from curl_cffi import requests as c_requests

# === SPEED CHECK ==
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
    -1004433802308, -1004484922375, -1003198230573, -1003741372960,-1003977346004,
    -1003781006610,-1003483564136
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

FORWARD_TO_CH2 = True
# =========================================================

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

# --- GLOBAL BOT STATE & QUEUE ---
bot_locks = defaultdict(asyncio.Lock)
join_requests = {RAW_CH1: set(), RAW_CH2: set()}

LINK_QUEUE = asyncio.Queue()  # Holds incoming links sequentially
WORKING_PROXIES = []          # Remembers proxies that successfully bypassed StackProtect


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

            task_buttons = await page.locator(".step.linky").all()
            for i, step in enumerate(task_buttons, 1):
                try:
                    await step.click(force=True)
                    await asyncio.sleep(2)
                except Exception: pass
            
            print("[*] Waiting 10 seconds for the internal JS timer...")
            await asyncio.sleep(10)

            unlock_btn = page.locator("#file")
            if await unlock_btn.is_visible():
                await unlock_btn.evaluate("el => el.removeAttribute('disabled')")
                try:
                    async with page.expect_navigation(timeout=15000) as nav_info:
                        await unlock_btn.click(force=True)
                    final_url = page.url
                    if "t.me" in final_url: return final_url
                except: pass

                await asyncio.sleep(2)
                for p in page.context.pages:
                    if "t.me" in p.url: return p.url
                        
            content = await page.content()
            return None 

        except Exception as e:
            print(f"❌ Playwright execution error: {e}")
        finally:
            await browser.close()
            return extracted_link


# ====================================================================
# FAST CURL_CFFI SCRAPER FOR FILES.FM / UNLOCKIFY / DEEP LINKS
# ====================================================================
def scrape_target_url(url, allowed_domains):
    print(f"Scraping URL: {url}")
    global WORKING_PROXIES
    IGNORED_EXTENSIONS = ('.ico', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.xml', '.json')

    def fetch_with_proxy(target_url):
        session = c_requests.Session(impersonate="chrome110")
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})
        
        is_unlockify = "unlockify.ink" in target_url
        
        # 1. Direct Connection Attempt
        try:
            resp = session.get(target_url, allow_redirects=True, timeout=15)
            if resp.status_code == 200 and "sp_fallback" not in resp.text:
                return resp.text, session
            if not is_unlockify:
                if resp.status_code == 403: return "403_FORBIDDEN", None
                return resp.text, session
        except Exception:
            if not is_unlockify: return None, None
            
        # 2. Infinite Loop Proxy Rotation for Unlockify
        print(f"⚠️ StackProtect blocked {target_url}. Activating Proxy Rotation (Infinite Retry)...")
        while True:
            # Phase A: Test known working proxies first
            for proxy in list(WORKING_PROXIES):
                session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                print(f"[*] Testing known working proxy: {proxy}")
                try:
                    resp = session.get(target_url, allow_redirects=True, timeout=10)
                    if resp.status_code == 200 and "sp_fallback" not in resp.text:
                        print(f"✅ Known Proxy {proxy} worked!")
                        return resp.text, session
                    else:
                        print(f"❌ Known proxy {proxy} failed/blocked. Removing from list.")
                        if proxy in WORKING_PROXIES: WORKING_PROXIES.remove(proxy)
                except Exception:
                    print(f"❌ Known proxy {proxy} error/timeout. Removing from list.")
                    if proxy in WORKING_PROXIES: WORKING_PROXIES.remove(proxy)
            
            # Phase B: Fetch fresh proxies if all known ones failed
            print("[*] Fetching fresh proxies from ProxyScrape...")
            try:
                p_resp = c_requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all", timeout=10)
                if p_resp.status_code == 200:
                    new_proxies = [p.strip() for p in p_resp.text.split('\n') if p.strip()]
                    random.shuffle(new_proxies)
                    
                    for proxy in new_proxies:
                        session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
                        try:
                            resp = session.get(target_url, allow_redirects=True, timeout=10)
                            if resp.status_code == 200 and "sp_fallback" not in resp.text:
                                print(f"✅ New Proxy {proxy} bypassed StackProtect! Saving to working list.")
                                if proxy not in WORKING_PROXIES: WORKING_PROXIES.append(proxy)
                                return resp.text, session
                        except Exception:
                            continue
            except Exception as e:
                print(f"⚠️ Failed to fetch new proxies: {e}")
                
            print("⏳ Exhausted proxy batch. Retrying in 5 seconds...")
            time.sleep(5)

    try:
        html_content, active_session = fetch_with_proxy(url)
        if html_content == "403_FORBIDDEN":
            return None, f"❌ Target actively blocked Chrome impersonation (403): {url}"
        if not html_content:
            return None, "❌ Failed to retrieve page."

        # ---------------- INTERNAL EXTRACTORS ----------------
        def attempt_js_map_extract(page_url, page_html):
            if "${code}" in page_html and "t.me/" in page_html:
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
                            map_resp = active_session.get(map_url, timeout=10)
                            if map_resp.status_code == 200:
                                map_match = re.search(rf'["\']{re.escape(raw_param)}["\']\s*:\s*["\']([^"\']+)["\']', map_resp.text)
                                if map_match: final_code = map_match.group(1)
                        except Exception: pass
                        return f"https://t.me/{bot_username}?start={final_code}"
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
                try:
                    cookie_str = "; ".join([f"{k}={v}" for k, v in active_session.cookies.get_dict().items()])
                    req = urllib.request.Request(video_url, headers={
                        'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': page_url, 'Cookie': cookie_str
                    })
                    with urllib.request.urlopen(req, timeout=120) as vid_resp:
                        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        shutil.copyfileobj(vid_resp, tmp_file)
                        tmp_file.close()
                        if os.path.getsize(tmp_file.name) > 100000: return "DOWNLOADED_FILE", tmp_file.name
                        else: os.remove(tmp_file.name)
                except Exception: pass
            return None, None
        # -----------------------------------------------------

        # Check First Page for direct video download
        dl_flag, dl_path = attempt_direct_download(url, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

        # Specially target the 'data-reward-url' attribute found in unlockify clones
        reward_match = re.search(r'data-reward-url=["\'](https://t\.me/[^"\']+)["\']', html_content)
        if reward_match: return reward_match.group(1), html_content

        js_tg_link = attempt_js_map_extract(url, html_content)
        if js_tg_link: return js_tg_link, html_content

        tg_pattern = r"(https://t\.me/[a-zA-Z0-9_]+(?:\?start=)[a-zA-Z0-9_\-]+)"
        match = re.search(tg_pattern, html_content)
        if match: return match.group(1), html_content
            
        all_links = re.findall(r'["\'](https?://[^\'"]+)["\']', html_content)
        intermediary_link = None
        for link in all_links:
            matched_domain = any(domain in link for domain in allowed_domains)
            if not matched_domain or link.lower().endswith(IGNORED_EXTENSIONS): continue
            if "/202" in link or ".html" in link or "/video" in link or "sub2unlock.me" in link:
                intermediary_link = link
                break
            if not intermediary_link: intermediary_link = link

        if not intermediary_link:
            return None, html_content

        # Internal Routing Fallbacks
        if "sub2unlock.me" in intermediary_link: return "SUB2UNLOCK", intermediary_link
        if any(d in intermediary_link for d in ["jilhub", "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"]):
            return "FIRESTORE", intermediary_link
            
        # Process Intermediary Link using the proxy logic
        html_content, active_session = fetch_with_proxy(intermediary_link)
        if html_content == "403_FORBIDDEN":
            return None, f"❌ Intermediary page blocked us (403): {intermediary_link}"
        if not html_content:
            return None, "❌ Failed to retrieve intermediary page."
        
        dl_flag, dl_path = attempt_direct_download(intermediary_link, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

        reward_match_2 = re.search(r'data-reward-url=["\'](https://t\.me/[^"\']+)["\']', html_content)
        if reward_match_2: return reward_match_2.group(1), html_content

        js_tg_link = attempt_js_map_extract(intermediary_link, html_content)
        if js_tg_link: return js_tg_link, html_content

        match2 = re.search(tg_pattern, html_content)
        if match2: return match2.group(1), html_content
        
        sub2_match = re.search(r'(https://sub2unlock\.me/[a-zA-Z0-9]+)', html_content)
        if sub2_match: return "SUB2UNLOCK", sub2_match.group(1)

        return None, html_content
            
    except Exception as e:
        return None, f"Error Exception: {str(e)}\n\nLast HTML extracted:\n{html_content}"


def get_all_links(event):
    urls = set()
    if event.message.buttons:
        for row in event.message.buttons:
            for btn in row:
                if hasattr(btn, 'url') and btn.url: urls.add(btn.url)
    if event.message.entities:
        for ent in event.message.entities:
            if isinstance(ent, MessageEntityTextUrl): urls.add(ent.url)
            elif isinstance(ent, MessageEntityUrl):
                urls.add(event.text[ent.offset : ent.offset + ent.length])
    return list(urls)


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
        return DocumentAttributeVideo(duration=duration, w=w, h=h, supports_streaming=True), thumb_path
    except Exception: return None, None


# ====================================================================
# CORE LINK PROCESSOR
# ====================================================================
async def process_single_link(url_to_visit, chat_name):
    print(f"\n⚙️ Processing: {url_to_visit}")
    bot_start_link = None
    debug_content = None

    is_firestore = any(domain in url_to_visit for domain in ["jilhub.xyz", "jilhub.giize", "jillanthaya.giize", "video.jilhub.xyz", "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"])
    
    if is_firestore:
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
            bot_start_link = await bypass_sub2unlock(debug_content)
        elif bot_start_link == "FIRESTORE":
            bot_start_link = await loop.run_in_executor(None, bypass_firestore_sync, debug_content)

    # --- NATIVE FILE DOWNLOAD ---
    if bot_start_link == "DOWNLOADED_FILE":
        temp_file_name = debug_content
        loop = asyncio.get_running_loop()
        attr, thumb_path = await loop.run_in_executor(None, extract_video_metadata, temp_file_name)
        
        try:
            sent_msg = await client.send_file(
                DESTINATION_CHAT, file=temp_file_name, 
                caption=f"Extracted direct video from {chat_name}\nLink: {url_to_visit}",
                supports_streaming=True, attributes=[attr] if attr else [], thumb=thumb_path
            )
            await asyncio.sleep(2)
            
            if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                
        except Exception as e: print(f"Upload failed: {e}")
        finally:
            if os.path.exists(temp_file_name): os.remove(temp_file_name)
            if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        return 

    # --- FAILURE LOGIC ---
    if not bot_start_link:
        print("Failed to get link. Sending debug HTML to Saved Messages...")
        caption = f"❌ **Extraction Failed**\nCould not find a valid link inside:\n{url_to_visit}"
        try:
            if debug_content and isinstance(debug_content, str):
                debug_file = io.BytesIO(debug_content.encode('utf-8'))
                debug_file.name = "debug_page_source.txt"
                await client.send_file('me', file=debug_file, caption=caption)
            else:
                await client.send_message('me', caption + "\n\n(No HTML content was retrieved)")
        except: pass
        return 

    # --- INTERACTING WITH BOTS ---
    parsed = re.search(r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)", bot_start_link)
    if parsed:
        bot_username, start_token = parsed.groups()
        try:
            async with bot_locks[bot_username]:
                async with client.conversation(bot_username, timeout=30) as conv:
                    await conv.send_message(f"/start {start_token}")
                    
                    target_media_msgs = []
                    while True:
                        try:
                            wait_time = 15 if not target_media_msgs else 3
                            response = await conv.get_response(timeout=wait_time)
                            if response.media and (response.video or response.document or response.photo):
                                target_media_msgs.append(response)
                        except asyncio.TimeoutError: break 

                    for idx, target_media_msg in enumerate(target_media_msgs, 1):
                        try:
                            sent_msg = await client.send_message(DESTINATION_CHAT, message=target_media_msg)
                            await asyncio.sleep(2)
                            
                            if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                                await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                                await asyncio.sleep(2)
                                
                        except Exception:
                            temp_path = None
                            thumb_path = None
                            try:
                                is_video = bool(target_media_msg.video or target_media_msg.document)
                                extension = ".mp4" if is_video else ".jpg"
                                video_attributes = []
                                if is_video and target_media_msg.document:
                                    for a in target_media_msg.document.attributes:
                                        if isinstance(a, DocumentAttributeVideo): video_attributes.append(a)
                                
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

                                sent_msg = await client.send_file(
                                    DESTINATION_CHAT, file=temp_path, 
                                    caption=f"Extracted from {chat_name}\nBot: @{bot_username}",
                                    supports_streaming=is_video, attributes=video_attributes if video_attributes else None, thumb=thumb_path if is_video else None
                                )
                                await asyncio.sleep(2)
                                
                                if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                                    await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                                    await asyncio.sleep(2)
                                    
                            except Exception: pass
                            finally:
                                if temp_path and os.path.exists(temp_path): os.remove(temp_path)
                                if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        except Exception as e:
            print(f"Conversation error: {e}")


# ====================================================================
# SEQUENTIAL LINK QUEUE WORKER
# ====================================================================
async def queue_worker():
    print("✅ Link Processing Queue is running...")
    while True:
        url_to_visit, chat_name = await LINK_QUEUE.get()
        try:
            await process_single_link(url_to_visit, chat_name)
        except Exception as e:
            print(f"❌ Worker Error: {e}")
        finally:
            # 4 Second interval ensures safe sequential processing between entirely separate links
            await asyncio.sleep(4) 
            LINK_QUEUE.task_done()


@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handler(event):
    chat = await event.get_chat()
    chat_name = getattr(chat, 'title', getattr(chat, 'username', chat.id))
    
    links = get_all_links(event)
    if not links: return

    print(f"--- New Message from {chat_name} (Found {len(links)} links) ---")
    
    # Enqueue links instantly without blocking incoming messages
    for url_to_visit in links:
        await LINK_QUEUE.put((url_to_visit, chat_name))
        print(f"➕ Queued: {url_to_visit} (Queue size: {LINK_QUEUE.qsize()})")


# ====================================================================
# JOIN-GATE BOT HANDLERS & TOGGLE
# ====================================================================
@bot_client.on(events.Raw)
async def track_join_requests(update):
    if isinstance(update, UpdateBotChatInviteRequester):
        channel_id = update.peer.channel_id
        user_id = update.user_id
        if channel_id in join_requests: join_requests[channel_id].add(user_id)

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply("Welcome to the bot! Please use /join to proceed.")

async def send_join_message(chat_id):
    buttons = [
        [Button.url('Channel 1', CHANNEL_1_LINK), Button.url('Channel 2', CHANNEL_2_LINK)],
        [Button.inline('Check Join', b'check_join')]
    ]
    await bot_client.send_message(chat_id, 'Backup ekata pahala channel walatath join weyalla', buttons=buttons)

@bot_client.on(events.NewMessage(pattern='/join'))
async def join_handler(event):
    await send_join_message(event.chat_id)

@bot_client.on(events.CallbackQuery(data=b'check_join'))
async def check_join_callback(event):
    user_id = event.sender_id
    req_1 = user_id in join_requests[RAW_CH1]
    req_2 = user_id in join_requests[RAW_CH2]

    async def is_member(channel_id):
        try:
            await bot_client.get_permissions(channel_id, user_id)
            return True
        except Exception: return False

    if (req_1 or await is_member(CHANNEL_1_ID)) and (req_2 or await is_member(CHANNEL_2_ID)):
        await event.answer("Verification Successful!", alert=False)
        msg = await event.reply(f"Here is your final link:\n{FINAL_CHANNEL_LINK}")
        async def delete_later(message):
            await asyncio.sleep(10)
            try: await message.delete()
            except Exception: pass
        asyncio.create_task(delete_later(msg))
    else:
        await event.answer("You haven't sent join requests to both channels yet!", alert=True)
        await send_join_message(event.chat_id)

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
    
    # Launch the background Queue Worker
    asyncio.create_task(queue_worker())
    
    print("✅ Both clients are running! Ready to process incoming messages.")
    await asyncio.gather(
        client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())


