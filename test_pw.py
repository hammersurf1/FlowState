import sys
import traceback
import os
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print("Playwright started successfully!")
except Exception as e:
    with open(os.path.expanduser("~\\test_pw_error.log"), "w") as f:
        f.write(traceback.format_exc())
