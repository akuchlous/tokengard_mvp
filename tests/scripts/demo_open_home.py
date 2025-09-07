#!/usr/bin/env python3
"""
Simple Selenium demo: open the front page and wait for Enter to exit.

Requirements:
- Selenium installed (already in requirements.txt)
- Chrome/Chromium installed locally with compatible driver available in PATH

This script intentionally pauses until you press Enter to close the browser.
"""

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException


def create_chrome_driver():
    options = ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Set to headful for demo visibility; change to --headless=new if needed
    # options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def main():
    url = "http://localhost:5000"
    try:
        driver = create_chrome_driver()
    except WebDriverException as e:
        print(f"Failed to start Chrome WebDriver: {e}")
        sys.exit(1)

    try:
        driver.set_window_size(1280, 900)
        driver.get(url)
        print(f"Opened {url}")
        print(f"Page title: {driver.title}")
        # Small delay to allow page animations
        time.sleep(0.5)
        # Highlight the Sign Up button (btn-secondary)
        try:
            signup = driver.find_element("css selector", ".action-buttons a.btn.btn-secondary")
            driver.execute_script(
                "arguments[0].style.outline='3px solid #ff9800'; arguments[0].style.transition='outline 0.3s ease-in-out';",
                signup,
            )
            # Brief pause, then click Sign Up
            time.sleep(0.5)
            signup.click()
            print("Clicked Sign Up. Navigated to:", driver.current_url)
        except Exception as e:
            print(f"Could not highlight Sign Up button: {e}")
        # On register page: fill email, password, confirm password
        try:
            time.sleep(0.5)
            email_input = driver.find_element("css selector", "#email")
            pwd_input = driver.find_element("css selector", "#password")
            confirm_input = driver.find_element("css selector", "#confirmPassword")
            demo_email = "demo+{}@example.com".format(int(time.time()))
            email_input.clear(); email_input.send_keys(demo_email)
            pwd_input.clear(); pwd_input.send_keys("DemoPass123!")
            confirm_input.clear(); confirm_input.send_keys("DemoPass123!")
            print("Filled registration form for:", demo_email)
        except Exception as e:
            print(f"Could not fill registration form: {e}")
        # Highlight and click Create Account button
        try:
            submit = driver.find_element("css selector", "#submitBtn")
            driver.execute_script(
                "arguments[0].style.outline='3px solid #4caf50'; arguments[0].style.transition='outline 0.3s ease-in-out';",
                submit,
            )
            time.sleep(0.5)
            submit.click()
            print("Clicked Create Account. Current URL:", driver.current_url)
        except Exception as e:
            print(f"Could not highlight/click Create Account: {e}")
        print("Press Enter to close the demo...")
        input()
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()


