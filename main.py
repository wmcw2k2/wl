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
CONCURRENT_WORKERS = 4  
task_queue = asyncio.Queue()

# Telethon clients
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, flood_sleep_threshold=60)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)
INTERMEDIARY_DOMAINS = set(DEFAULT_DOMAINS)

# Locks & memory
bot_locks = defaultdict(asyncio.Lock)
telegram_api_lock = asyncio.Lock()  # GLOBAL LOCK: Prevents 3023s Flood Wait
join_requests = {RAW_CH1: set(), RAW_CH2: set()}


# ====================================================================
# UNIVERSAL FIRESTORE BYPASSER
# ====================================================================
def bypass_firestore_sync(url):
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
                        return val
    except Exception: pass
    return None

# ====================================================================
# ADVANCED PLAYWRIGHT BYPASSER FOR SUB2UNLOCK (.ME)
# ====================================================================
async def bypass_sub2unlock(url):
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
                    if "url" in body and "t.me" in body["url"]: extracted_link = body["url"]
                except Exception: pass
        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            task_buttons = await page.locator(".step.linky").all()
            for i, step in enumerate(task_buttons, 1):
                try:
                    await step.click(force=True)
                    await asyncio.sleep(2)
                except Exception: pass
            
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
            return None 
        except Exception: pass
        finally:
            await browser.close()
            return extracted_link

# ====================================================================
# FAST CURL_CFFI SCRAPER FOR FILES.FM / JS MAPS / DEEP LINKS
# ====================================================================
def scrape_target_url(url, allowed_domains):
    IGNORED_EXTENSIONS = ('.ico', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.xml', '.json')
    html_content = "" 
    session = c_requests.Session(impersonate="chrome110")
    # Added robust headers for shorteners like unlockify
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})

    try:
        response = session.get(url, allow_redirects=True, timeout=20)
        if response.status_code == 403: return None, f"❌ 403 Forbidden"
        html_content = response.text

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
                            map_resp = session.get(map_url, timeout=10)
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
                    cookie_str = "; ".join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
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
            
        dl_flag, dl_path = attempt_direct_download(url, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

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

        if not intermediary_link: return None, html_content

        if "sub2unlock.me" in intermediary_link: return "SUB2UNLOCK", intermediary_link
        if any(d in intermediary_link for d in ["jilhub", "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"]):
            return "FIRESTORE", intermediary_link
            
        response2 = session.get(intermediary_link, allow_redirects=True, timeout=20)
        if response2.status_code == 403: return None, "403"
        html_content = response2.text
        
        dl_flag, dl_path = attempt_direct_download(intermediary_link, html_content)
        if dl_flag == "DOWNLOADED_FILE": return dl_flag, dl_path

        js_tg_link = attempt_js_map_extract(intermediary_link, html_content)
        if js_tg_link: return js_tg_link, html_content

        match2 = re.search(tg_pattern, html_content)
        if match2: return match2.group(1), html_content
        
        sub2_match = re.search(r'(https://sub2unlock\.me/[a-zA-Z0-9]+)', html_content)
        if sub2_match: return "SUB2UNLOCK", sub2_match.group(1)

        return None, html_content
    except Exception as e:
        return None, str(e)


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
# QUEUE WORKER: Staggered startups prevent DDoS triggers on shorteners
# ====================================================================
async def process_queue_worker(worker_id):
    # Stagger startups by 2 seconds so they don't hit URL shorteners simultaneously
    await asyncio.sleep(worker_id * 2.0)
    while True:
        url_to_visit, chat_name = await task_queue.get()
        try:
            await process_single_link(url_to_visit, chat_name)
        except Exception as e:
            print(f"❌ Worker Error: {e}")
        finally:
            task_queue.task_done()

# ====================================================================
# CORE LINK PROCESSOR
# ====================================================================
async def process_single_link(url_to_visit, chat_name):
    print(f"\n⚙️ Processing: {url_to_visit}")
    bot_start_link, debug_content = None, None

    is_firestore = any(d in url_to_visit for d in ["jilhub", "clipgo.xyz", "sub2unlock.xyz", "gabadawa.xyz", "jilzone.xyz"])
    
    if is_firestore:
        loop = asyncio.get_running_loop()
        bot_start_link = await loop.run_in_executor(None, bypass_firestore_sync, url_to_visit)
        debug_content = "Extracted via Direct Firestore API"
    elif "sub2unlock.me" in url_to_visit:
        bot_start_link = await bypass_sub2unlock(url_to_visit)
    else:
        loop = asyncio.get_running_loop()
        bot_start_link, debug_content = await loop.run_in_executor(None, scrape_target_url, url_to_visit, INTERMEDIARY_DOMAINS)
        
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
            async with telegram_api_lock:
                sent_msg = await client.send_file(
                    DESTINATION_CHAT, file=temp_file_name, 
                    caption=f"Extracted direct video from {chat_name}\nLink: {url_to_visit}",
                    supports_streaming=True, attributes=[attr] if attr else [], thumb=thumb_path
                )
                await asyncio.sleep(1.5) # Anti-Flood Pacemaker
            
            if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                async with telegram_api_lock:
                    await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                    await asyncio.sleep(1.5) # Anti-Flood Pacemaker
        except errors.FloodWaitError as e:
            print(f"🚨 FLOOD WAIT {e.seconds}s. Skipping to protect account.")
        except Exception as e: print(f"Upload failed: {e}")
        finally:
            if os.path.exists(temp_file_name): os.remove(temp_file_name)
            if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        return 

    # --- RESTORED FAILURE LOGIC ---
    if not bot_start_link:
        print(f"❌ Failed: {url_to_visit}. Sending debug to Saved Messages.")
        caption = f"❌ **Extraction Failed**\nCould not find a valid link inside:\n{url_to_visit}"
        try:
            async with telegram_api_lock:
                if debug_content and isinstance(debug_content, str) and len(debug_content) > 50:
                    debug_file = io.BytesIO(debug_content.encode('utf-8'))
                    debug_file.name = "debug_page_source.txt"
                    await client.send_file('me', file=debug_file, caption=caption)
                else:
                    await client.send_message('me', caption + f"\n\nError/Content:\n{debug_content}")
                await asyncio.sleep(1.5)
        except Exception: pass
        return 

    # --- INTERACTING WITH BOTS ---
    parsed = re.search(r"t\.me/([a-zA-Z0-9_]+)\?start=(.+)", bot_start_link)
    if parsed:
        bot_username, start_token = parsed.groups()
        try:
            async with bot_locks[bot_username]:
                async with client.conversation(bot_username, timeout=30) as conv:
                    try:
                        async with telegram_api_lock:
                            await conv.send_message(f"/start {start_token}")
                            await asyncio.sleep(1.5)
                    except errors.FloodWaitError as e:
                        print(f"🚨 FLOOD WAIT {e.seconds}s. Aborting conversation with {bot_username}.")
                        return
                    
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
                            async with telegram_api_lock:
                                sent_msg = await client.send_message(DESTINATION_CHAT, message=target_media_msg)
                                await asyncio.sleep(1.5) 
                            
                            if FORWARD_TO_CH2 and sent_msg and sent_msg.media:
                                async with telegram_api_lock:
                                    await client.send_file(DESTINATION_CHAT_2, file=sent_msg.media, caption="")
                                    await asyncio.sleep(1.5) 
                        except errors.FloodWaitError as e:
                            print(f"🚨 FLOOD WAIT {e.seconds}s on Forward.")
                        except Exception: pass
                
                await asyncio.sleep(4) 
                
        except Exception as e: print(f"Conversation error: {e}")

# ====================================================================
# TELEGRAM HANDLERS
# ====================================================================
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

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def source_chat_handler(event):
    chat = await event.get_chat()
    chat_name = getattr(chat, 'title', getattr(chat, 'username', chat.id))
    links = get_all_links(event)
    if links:
        print(f"📥 Received {len(links)} links. Adding to queue...")
        for url in links:
            await task_queue.put((url, chat_name))

@client.on(events.NewMessage(pattern=r'/adddomain (.*)', from_users='me'))
async def add_domain_handler(event):
    keyword = urlparse(event.pattern_match.group(1).strip()).netloc.replace('www.', '').split('.')[0]
    if keyword:
        INTERMEDIARY_DOMAINS.add(keyword)
        await event.reply(f"✅ Added domain: {keyword}")

# ================= JOIN-GATE BOT LOGIC =================
@bot_client.on(events.Raw)
async def track_join_requests(update):
    if isinstance(update, UpdateBotChatInviteRequester):
        cid = update.peer.channel_id
        if cid in join_requests: join_requests[cid].add(update.user_id)

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply("Welcome to the bot! Please use /join to proceed.")

async def send_join_message(chat_id):
    await bot_client.send_message(
        chat_id, 'Backup ekata pahala channel walatath join weyalla', 
        buttons=[
            [Button.url('Channel 1', CHANNEL_1_LINK), Button.url('Channel 2', CHANNEL_2_LINK)],
            [Button.inline('Check Join', b'check_join')]
        ]
    )

@bot_client.on(events.NewMessage(pattern='/join'))
async def join_handler(event):
    await send_join_message(event.chat_id)

@bot_client.on(events.CallbackQuery(data=b'check_join'))
async def check_join_callback(event):
    uid = event.sender_id
    async def is_member(cid):
        try:
            await bot_client.get_permissions(cid, uid)
            return True
        except Exception: return False

    if (uid in join_requests[RAW_CH1] or await is_member(CHANNEL_1_ID)) and \
       (uid in join_requests[RAW_CH2] or await is_member(CHANNEL_2_ID)):
        await event.answer("Verification Successful!", alert=False)
        msg = await event.reply(f"Here is your link:\n{FINAL_CHANNEL_LINK}")
        async def del_later(m):
            await asyncio.sleep(10)
            try: await m.delete()
            except: pass
        asyncio.create_task(del_later(msg))
    else:
        await event.answer("You haven't sent join requests to both channels yet!", alert=True)
        await send_join_message(event.chat_id)

@bot_client.on(events.NewMessage(pattern=r'/fwd2 (on|off)', from_users=MY_OWNER_ID))
async def toggle_fwd2_bot(event):
    global FORWARD_TO_CH2
    FORWARD_TO_CH2 = (event.pattern_match.group(1).lower() == 'on')
    state = "ON" if FORWARD_TO_CH2 else "OFF"
    await event.reply(f"✅ Forwarding to 2nd channel is now **{state}**.")

# ====================================================================
# MAIN EXECUTION
# ====================================================================
async def main():
    print("Starting Clients...")
    await client.start()
    await bot_client.start(bot_token=BOT_TOKEN)
    
    # Start the task workers staggered to prevent instant DDoS
    for i in range(CONCURRENT_WORKERS):
        asyncio.create_task(process_queue_worker(i))
        
    print("✅ System Online! Processing queue and listening for messages...")
    await asyncio.gather(
        client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
