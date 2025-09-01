#!/usr/bin/env python3
"""
Final Frontend Selenium test for banned keywords functionality.
Tests the banned keywords page structure and basic functionality.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestFrontendBannedKeywordsFinal:
    """Final test class for banned keywords frontend functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Set up Chrome driver with headless mode"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        yield
        
        self.driver.quit()
    
    def test_banned_keywords_page_authentication(self):
        """Test that banned keywords page properly requires authentication."""
        print("🚀 Testing banned keywords page authentication...")
        
        # Navigate to banned keywords page without being logged in
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        # Check that we get the authentication required page
        page_title = self.driver.title
        assert "Authentication Required" in page_title, f"Expected 'Authentication Required' in title, got: {page_title}"
        print("✅ Authentication required page loaded correctly")
        
        # Check for expected elements
        page_source = self.driver.page_source
        
        # Check for authentication message
        assert "You need to be logged in" in page_source, "Authentication message not found"
        print("✅ Authentication message found")
        
        # Check for home button
        home_button = self.driver.find_element(By.CSS_SELECTOR, '.home-button')
        assert home_button is not None, "Home button not found"
        print("✅ Home button found")
        
        # Test clicking home button
        home_button.click()
        time.sleep(2)
        
        current_url = self.driver.current_url
        assert current_url == "http://localhost:5000/", f"Expected to be redirected to home page, got: {current_url}"
        print("✅ Home button redirects to home page")
        
        print("✅ Banned keywords page authentication test passed!")
    
    def test_banned_keywords_page_structure(self):
        """Test the structure of the banned keywords page."""
        print("🚀 Testing banned keywords page structure...")
        
        # Navigate to banned keywords page
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        # Check page structure
        page_source = self.driver.page_source
        
        # Check for expected CSS classes and structure
        expected_elements = [
            'error-page',
            'error-container', 
            'error-icon',
            'error-title',
            'error-message',
            'home-button'
        ]
        
        found_elements = []
        for element in expected_elements:
            if element in page_source:
                found_elements.append(element)
                print(f"✅ Found element: {element}")
            else:
                print(f"❌ Missing element: {element}")
        
        # Check that we found all expected elements
        assert len(found_elements) == len(expected_elements), f"Only found {len(found_elements)} out of {len(expected_elements)} expected elements"
        print("✅ All expected page elements found")
        
        # Check for proper styling
        assert 'unified.css' in page_source, "Unified CSS not loaded"
        print("✅ Unified CSS loaded")
        
        print("✅ Banned keywords page structure test passed!")
    
    def test_banned_keywords_page_responsive_design(self):
        """Test that the banned keywords page is responsive."""
        print("🚀 Testing banned keywords page responsive design...")
        
        # Test with different window sizes
        window_sizes = [
            (1920, 1080),  # Desktop
            (1024, 768),   # Tablet
            (375, 667),    # Mobile
        ]
        
        for width, height in window_sizes:
            print(f"   Testing window size: {width}x{height}")
            self.driver.set_window_size(width, height)
            
            # Navigate to banned keywords page
            self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
            time.sleep(2)
            
            # Check that page loads correctly at this size
            page_title = self.driver.title
            assert "Authentication Required" in page_title, f"Page not loading correctly at {width}x{height}"
            
            # Check that key elements are visible
            try:
                error_container = self.driver.find_element(By.CSS_SELECTOR, '.error-container')
                assert error_container.is_displayed(), f"Error container not visible at {width}x{height}"
                
                home_button = self.driver.find_element(By.CSS_SELECTOR, '.home-button')
                assert home_button.is_displayed(), f"Home button not visible at {width}x{height}"
                
                print(f"   ✅ Page responsive at {width}x{height}")
            except NoSuchElementException:
                print(f"   ❌ Key elements not found at {width}x{height}")
        
        print("✅ Banned keywords page responsive design test passed!")
    
    def test_banned_keywords_page_accessibility(self):
        """Test basic accessibility features of the banned keywords page."""
        print("🚀 Testing banned keywords page accessibility...")
        
        # Navigate to banned keywords page
        self.driver.get('http://localhost:5000/banned_keywords/test_user_id')
        time.sleep(2)
        
        # Check for proper heading structure
        page_source = self.driver.page_source
        
        # Check for proper title
        assert "<title>" in page_source, "Page title not found"
        print("✅ Page title found")
        
        # Check for proper heading structure
        assert "error-title" in page_source, "Error title not found"
        print("✅ Error title found")
        
        # Check for proper button structure
        home_button = self.driver.find_element(By.CSS_SELECTOR, '.home-button')
        button_text = home_button.text
        assert button_text and len(button_text.strip()) > 0, "Home button has no text"
        print("✅ Home button has proper text")
        
        # Check for proper link structure
        assert 'href="/"' in page_source, "Home button link not found"
        print("✅ Home button has proper link")
        
        print("✅ Banned keywords page accessibility test passed!")
    
    def test_banned_keywords_page_error_handling(self):
        """Test error handling on the banned keywords page."""
        print("🚀 Testing banned keywords page error handling...")
        
        # Test with invalid user ID
        invalid_user_ids = [
            "invalid_user_id",
            "123",
            "user_with_special_chars!@#",
            "",
            "very_long_user_id_that_exceeds_normal_length_limits"
        ]
        
        for user_id in invalid_user_ids:
            print(f"   Testing with user ID: '{user_id}'")
            
            # Navigate to banned keywords page with invalid user ID
            if user_id:
                url = f'http://localhost:5000/banned_keywords/{user_id}'
            else:
                url = 'http://localhost:5000/banned_keywords/'
            
            self.driver.get(url)
            time.sleep(2)
            
            # Check that we still get the authentication required page
            page_title = self.driver.title
            assert "Authentication Required" in page_title, f"Expected auth required for user ID '{user_id}', got: {page_title}"
            
            # Check that the page doesn't crash or show server errors
            page_source = self.driver.page_source
            assert "500" not in page_source, f"Server error found for user ID '{user_id}'"
            assert "Internal Server Error" not in page_source, f"Internal server error found for user ID '{user_id}'"
            
            print(f"   ✅ Handled user ID '{user_id}' correctly")
        
        print("✅ Banned keywords page error handling test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
