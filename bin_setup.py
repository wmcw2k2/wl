import os
import subprocess
import sys

# Define a persistent, writable path
INSTALL_PATH = "/app/playwright-browser"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = INSTALL_PATH

print("[*] Installing Playwright browser to:", INSTALL_PATH)
# This command will download and install the browser into our specific folder
subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
print("[*] Installation complete.")
