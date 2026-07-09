import os
import subprocess
import sys

# Tell Playwright where to store browsers in the Heroku /app folder
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.cache/ms-playwright"

print("[*] Manually installing Playwright browser binaries...")
subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
print("[*] Installation complete.")
