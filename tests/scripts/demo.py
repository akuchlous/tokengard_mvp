#!/usr/bin/env python3
"""
Selenium demo flow (black-box):
1) Open home → highlight/click Sign Up
2) Fill register → submit
3) Read activation token from Flask logs (auth_utils.py prints) → activate
4) Return home → highlight/click Sign In
5) Fill login → submit → pause
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException


def create_chrome_driver():
    options = ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # For headless, uncomment the next line
    # options.add_argument("--headless=new")
    return webdriver.Chrome(options=options)


def highlight(driver, element, color="#ff9800"):
    try:
        driver.execute_script(
            "arguments[0].style.outline='3px solid %s'; arguments[0].style.transition='outline 0.2s';" % color,
            element,
        )
    except Exception:
        pass


def wait_ms(ms=500):
    time.sleep(ms / 1000.0)


def open_home(driver, base_url):
    try:
        driver.maximize_window()
    except Exception:
        try:
            driver.set_window_size(1920, 1080)
        except Exception:
            pass
    driver.get(base_url)
    print(f"Opened {base_url}")
    print(f"Page title: {driver.title}")
    wait_ms(500)


def click_signup(driver):
    signup = driver.find_element("css selector", ".action-buttons a.btn.btn-secondary")
    highlight(driver, signup, "#ff9800")
    wait_ms(500)
    signup.click()
    print("Clicked Sign Up. Current URL:", driver.current_url)


def fill_registration(driver, email, password):
    email_input = driver.find_element("css selector", "#email")
    pwd_input = driver.find_element("css selector", "#password")
    confirm_input = driver.find_element("css selector", "#confirmPassword")
    email_input.clear(); email_input.send_keys(email)
    pwd_input.clear(); pwd_input.send_keys(password)
    confirm_input.clear(); confirm_input.send_keys(password)
    print("Filled registration form for:", email)


def submit_registration(driver):
    submit = driver.find_element("css selector", "#submitBtn")
    highlight(driver, submit, "#4caf50")
    wait_ms(500)
    submit.click()
    print("Clicked Create Account. Current URL:", driver.current_url)


def read_activation_token_from_logs(max_wait_ms=10000):
    log_path = os.getenv("DEMO_LOG_FILE")
    if not log_path or not os.path.exists(log_path):
        return ""
    deadline = time.time() + (max_wait_ms / 1000.0)
    while time.time() < deadline:
        try:
            with open(log_path, 'r') as f:
                content = f.read()
            for line in content.splitlines()[::-1]:
                if line.startswith("Activation token: "):
                    return line.split(": ", 1)[1].strip()
        except Exception:
            pass
        wait_ms(500)
    return ""


def activate_account(driver, base_url):
    token = read_activation_token_from_logs()
    if not token:
        print("No activation token found in logs; continuing (login may fail if not activated).")
        return
    activate_url = f"{base_url}/auth/activate/{token}"
    print("Activating via:", activate_url)
    wait_ms(500)
    driver.get(activate_url)
    print("Activation complete. Current URL:", driver.current_url)
    wait_ms(500)


def click_signin(driver, base_url):
    driver.get(base_url)
    print("At home page before login.")
    signin = driver.find_element("css selector", ".action-buttons a.btn.btn-primary")
    highlight(driver, signin, "#2196f3")
    wait_ms(500)
    signin.click()
    print("Clicked Sign In. Current URL:", driver.current_url)


def login(driver, email, password):
    wait_ms(500)
    login_email = driver.find_element("css selector", "#email")
    login_pwd = driver.find_element("css selector", "#password")
    submit_login = driver.find_element("css selector", "#submitBtn")
    login_email.clear(); login_email.send_keys(email)
    login_pwd.clear(); login_pwd.send_keys(password)
    highlight(driver, submit_login, "#ff9800")
    wait_ms(500)
    submit_login.click()
    print("Submitted login form. Current URL:", driver.current_url)


def click_view_api_keys(driver):
    # On user profile page, click "View API Keys"
    wait_ms(500)
    try:
        link = driver.find_element("css selector", ".btn.btn-keys")
    except Exception:
        # Fallback: try link text
        try:
            link = driver.find_element("link text", "View API Keys")
        except Exception as e:
            print(f"Could not find 'View API Keys' link: {e}")
            return
    highlight(driver, link, "teal")
    wait_ms(500)
    link.click()
    print("Clicked View API Keys. Current URL:", driver.current_url)


def click_test_for_second_key(driver):
    # Click the Test button for the second key (if available)
    wait_ms(500)
    try:
        test_buttons = driver.find_elements("css selector", ".test-btn")
        if len(test_buttons) >= 2:
            btn = test_buttons[1]
            highlight(driver, btn, "#9c27b0")
            wait_ms(500)
            btn.click()
            print("Clicked Test for second key. Current URL:", driver.current_url)
            wait_ms(800)
        else:
            print("Second key test button not found (less than two keys or second is disabled).")
    except Exception as e:
        print(f"Failed to click Test for second key: {e}")

def set_test_payload_text(driver, text_value):
    # On the test page, set the payload textarea to include banned text
    wait_ms(300)
    try:
        textarea = driver.find_element("css selector", "#payload")
        payload = '{"text": "%s"}' % text_value.replace('"', '\\"')
        textarea.clear()
        textarea.send_keys(payload)
        print("Set test payload to:", payload)
        wait_ms(300)
    except Exception as e:
        print(f"Failed to set test payload: {e}")

def scroll_to_results(driver):
    """Scroll results section into view for visibility."""
    try:
        results = driver.find_element("css selector", "#resultsSection")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", results)
        wait_ms(500)
    except Exception:
        pass

def run_cache_demo(driver):
    """Run an additional cache demo on the same test page."""
    try:
        def scroll_to_payload():
            try:
                el = driver.find_element("css selector", "#payload")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", el)
                wait_ms(500)
            except Exception:
                pass

        def scroll_to_log_details():
            try:
                el = driver.find_element("css selector", "#logDetailsSection")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", el)
                wait_ms(500)
            except Exception:
                pass

        # 1) Cold call
        scroll_to_payload()
        set_test_payload_text(driver, "what is the significance of number 42")
        wait_ms(1000)
        click_test_api_key(driver)
        scroll_to_results(driver)
        wait_ms(500)
        scroll_to_log_details()
        wait_ms(500)

        # 2) Semantically similar call (expect cache hit)
        scroll_to_payload()
        set_test_payload_text(driver, "tell me about 42 number")
        wait_ms(1000)
        click_test_api_key(driver)
        scroll_to_results(driver)
        wait_ms(1000)
        scroll_to_log_details()
        wait_ms(500)

        # 3) Another similar variant
        scroll_to_payload()
        set_test_payload_text(driver, "tell me number 42 in detail")
        wait_ms(1000)
        click_test_api_key(driver)
        scroll_to_results(driver)
        wait_ms(1000)
        scroll_to_log_details()
        wait_ms(1000)
    except Exception as e:
        print(f"Cache demo encountered an issue: {e}")

def click_test_api_key(driver):
    # On the test page, click the "Test API Key" button
    wait_ms(500)
    try:
        btn = driver.find_element("css selector", "#testBtn")
        highlight(driver, btn, "#4caf50")
        wait_ms(500)
        btn.click()
        print("Clicked 'Test API Key'.")
        wait_ms(1000)
    except Exception as e:
        print(f"Failed to click 'Test API Key': {e}")

def click_back_to_keys(driver):
    # From test page, navigate back to the keys list
    wait_ms(500)
    try:
        # Prefer the explicit Back to Keys link in header
        link = driver.find_element("css selector", ".test-header a[href*='/keys/']")
        highlight(driver, link, "#2196f3")
        wait_ms(300)
        link.click()
        wait_ms(700)
        print("Navigated back to keys page.")
    except Exception:
        try:
            # Fallback to any keys link on the page
            link = driver.find_element("css selector", "a[href*='/keys/']")
            highlight(driver, link, "#2196f3")
            wait_ms(300)
            link.click()
            wait_ms(700)
            print("Navigated back to keys page (fallback).")
        except Exception as e:
            # Last resort: browser back
            print(f"Could not find Back to Keys link, using browser back: {e}")
            driver.back()
            wait_ms(700)

def deactivate_first_key_and_refresh(driver):
    # Click the first Deactivate button on keys page, accept confirm, then refresh
    wait_ms(500)
    try:
        btn = driver.find_element("css selector", ".deactivate-btn")
        highlight(driver, btn, "#e53935")
        wait_ms(500)
        btn.click()
        try:
            alert = driver.switch_to.alert
            wait_ms(200)
            alert.accept()
        except Exception:
            pass
        wait_ms(800)
        driver.refresh()
        print("Deactivated first key and refreshed page.")
    except Exception as e:
        print(f"No deactivate button found or failed to deactivate: {e}")

def main():
    base_url = "http://localhost:5000"
    password = "DemoPass123!"
    demo_email = f"demo+{int(time.time())}@example.com"
    try:
        driver = create_chrome_driver()
    except WebDriverException as e:
        print(f"Failed to start Chrome WebDriver: {e}")
        sys.exit(1)

    try:
        open_home(driver, base_url)
        click_signup(driver)
        fill_registration(driver, demo_email, password)
        submit_registration(driver)
        activate_account(driver, base_url)
        click_signin(driver, base_url)
        login(driver, demo_email, password)
        click_view_api_keys(driver)
        click_test_for_second_key(driver)
        set_test_payload_text(driver, "hello adult! check LLM for banned keyword \"adult\"")
        click_test_api_key(driver)
        # Additional test: cold vs cache responses for semantically similar prompts
        run_cache_demo(driver)
        # click_back_to_keys(driver)
        # deactivate_first_key_and_refresh(driver)
        print("Press Enter to close the demo...")
        input()
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()


