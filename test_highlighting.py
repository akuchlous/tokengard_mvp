#!/usr/bin/env python3
"""
Test script to demonstrate Selenium element highlighting functionality.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def highlight_element(driver, element, duration=2000, color="red"):
    """Highlight an element with a colored border for specified duration."""
    try:
        # Apply highlight style
        highlight_script = f"""
        arguments[0].style.border = '3px solid {color}';
        arguments[0].style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
        arguments[0].style.boxShadow = '0 0 10px {color}';
        arguments[0].style.transition = 'all 0.3s ease';
        arguments[0].style.zIndex = '9999';
        """
        driver.execute_script(highlight_script, element)
        
        # Wait for highlight duration
        time.sleep(duration / 1000)
        
        # Restore original style
        restore_script = """
        arguments[0].style.border = '';
        arguments[0].style.backgroundColor = '';
        arguments[0].style.boxShadow = '';
        arguments[0].style.transition = '';
        arguments[0].style.zIndex = '';
        """
        driver.execute_script(restore_script, element)
        
        return True
    except Exception as e:
        print(f"⚠️  Could not highlight element: {e}")
        return False

def test_highlighting():
    """Test the highlighting functionality on a simple webpage."""
    print("🔍 Testing Selenium Element Highlighting")
    print("=" * 40)
    
    # Setup Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to a test page (using a simple HTML page)
        driver.get("data:text/html,<html><body><h1>Test Page</h1><button id='btn1'>Button 1</button><button id='btn2'>Button 2</button><input type='text' id='input1' placeholder='Test input'><a href='#' id='link1'>Test Link</a></body></html>")
        
        print("✅ Loaded test page")
        
        # Test highlighting different elements
        elements_to_test = [
            ("h1", "Heading", "blue"),
            ("#btn1", "Button 1", "green"),
            ("#btn2", "Button 2", "red"),
            ("#input1", "Input field", "orange"),
            ("#link1", "Test Link", "purple")
        ]
        
        for selector, description, color in elements_to_test:
            print(f"\n🔍 Highlighting {description} ({selector}) in {color}...")
            
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                highlight_element(driver, element, 2000, color)
                print(f"✅ Highlighted {description}")
            except Exception as e:
                print(f"❌ Failed to highlight {description}: {e}")
        
        print("\n🎉 Highlighting test completed!")
        print("Press Enter to close the browser...")
        input()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        driver.quit()
        print("✅ Browser closed")

if __name__ == "__main__":
    test_highlighting()
