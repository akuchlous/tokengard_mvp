"""
Frontend Selenium Tests for Analytics

This module contains frontend tests that require a running Flask server and Selenium.
"""

import pytest
import time
import json
import requests
import subprocess
import signal
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from app import create_app, db
from app.models import User, APIKey, ProxyLog
from app.utils.auth_utils import hash_password


class TestFrontendAnalytics:
    """Frontend tests for analytics functionality using Selenium."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment before each test."""
        # Create test app with test configuration
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'JWT_SECRET_KEY': 'test-jwt-secret-key',
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': 587,
            'MAIL_USE_TLS': False,
            'MAIL_USE_SSL': False,
            'MAIL_USERNAME': 'test@example.com',
            'MAIL_PASSWORD': 'test-password',
            'MAIL_DEFAULT_SENDER': 'test@example.com'
        }
        self.app = create_app(test_config)
        
        # Create test client
        self.client = self.app.test_client()
        
        # Create application context
        with self.app.app_context():
            # Create database tables
            db.create_all()
            
            # Create test data
            self.setup_test_data()
            
            yield
            
            # Clean up
            db.session.remove()
            db.drop_all()
    
    def setup_test_data(self):
        """Create test data for analytics testing."""
        # Create test user
        self.user = User(
            email='analytics@example.com',
            password_hash=hash_password('TestPass123!')
        )
        self.user.status = 'active'
        db.session.add(self.user)
        db.session.commit()
        
        # Create API keys
        self.api_key1 = APIKey(
            user_id=self.user.id,
            key_name='key_0',
            key_value='tk-analytics123456789012345678901234'
        )
        db.session.add(self.api_key1)
        
        self.api_key2 = APIKey(
            user_id=self.user.id,
            key_name='key_1',
            key_value='tk-analytics234567890123456789012345'
        )
        db.session.add(self.api_key2)
        db.session.commit()
        
        # Create sample log entries for analytics
        self.create_sample_logs()
    
    def create_sample_logs(self):
        """Create sample log entries for testing analytics."""
        # Create successful API calls
        for i in range(5):
            log = ProxyLog.create_log(
                api_key=self.api_key1,
                request_body=f'{{"test": "success_{i}", "data": "sample_data"}}',
                response_status='key_pass',
                response_body='{"status": "success", "message": "API key is valid"}',
                client_ip='127.0.0.1',
                user_agent='test-agent',
                request_id=f'test-request-{i}',
                processing_time_ms=100 + i * 10
            )
            db.session.commit()
            time.sleep(0.01)  # Ensure different timestamps
        
        # Create failed API calls
        for i in range(3):
            log = ProxyLog.create_log(
                api_key=self.api_key2,
                request_body=f'{{"test": "error_{i}", "data": "sample_data"}}',
                response_status='key_error',
                response_body='{"status": "error", "message": "API key is invalid"}',
                client_ip='127.0.0.1',
                user_agent='test-agent',
                request_id=f'test-error-{i}',
                processing_time_ms=50 + i * 5
            )
            db.session.commit()
            time.sleep(0.01)
    
    def setup_selenium_driver(self):
        """Set up Selenium WebDriver with Chrome options."""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        return driver
    
    def start_flask_server(self):
        """Start Flask server for testing."""
        # Create a temporary database file for the server
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Set environment variables for test server
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['FLASK_APP'] = 'app:create_app'
        os.environ['DATABASE_URL'] = f'sqlite:///{self.temp_db.name}'
        
        # Start Flask server in background
        self.server_process = subprocess.Popen(
            ['python', '-m', 'flask', 'run', '--port=5001'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get('http://localhost:5001/health', timeout=2)
                if response.status_code == 200:
                    print("✅ Flask server started successfully")
                    # Set up test data in the running server
                    self.setup_server_test_data()
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        print("❌ Failed to start Flask server")
        return False
    
    def setup_server_test_data(self):
        """Set up test data in the running server via direct database access."""
        try:
            from app import create_app, db
            from app.models import User, APIKey, ProxyLog
            from app.utils.auth_utils import hash_password
            
            # Create app with the same database
            server_app = create_app({
                'TESTING': True,
                'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.temp_db.name}',
                'SECRET_KEY': 'test-secret-key',
                'JWT_SECRET_KEY': 'test-jwt-secret-key'
            })
            
            with server_app.app_context():
                # Create all database tables
                db.create_all()
                
                # Create user if not exists
                user = User.query.filter_by(email='analytics@example.com').first()
                if not user:
                    user = User(
                        email='analytics@example.com',
                        password_hash=hash_password('TestPass123!')
                    )
                    user.status = 'active'  # Activate user
                    db.session.add(user)
                    db.session.commit()
                
                # Create API keys
                api_key1 = APIKey(
                    user_id=user.id,
                    key_name='key_0',
                    key_value='tk-analytics123456789012345678901234'
                )
                db.session.add(api_key1)
                
                api_key2 = APIKey(
                    user_id=user.id,
                    key_name='key_1',
                    key_value='tk-analytics234567890123456789012345'
                )
                db.session.add(api_key2)
                db.session.commit()
                
                # Create sample log entries
                for i in range(5):
                    log = ProxyLog.create_log(
                        api_key=api_key1,
                        request_body=f'{{"test": "success_{i}", "data": "sample_data"}}',
                        response_status='key_pass',
                        response_body='{"status": "success", "message": "API key is valid"}',
                        client_ip='127.0.0.1',
                        user_agent='test-agent',
                        request_id=f'test-request-{i}',
                        processing_time_ms=100 + i * 10
                    )
                    db.session.commit()
                    time.sleep(0.01)
                
                for i in range(3):
                    log = ProxyLog.create_log(
                        api_key=api_key2,
                        request_body=f'{{"test": "error_{i}", "data": "sample_data"}}',
                        response_status='key_error',
                        response_body='{"status": "error", "message": "API key is invalid"}',
                        client_ip='127.0.0.1',
                        user_agent='test-agent',
                        request_id=f'test-error-{i}',
                        processing_time_ms=50 + i * 5
                    )
                    db.session.commit()
                    time.sleep(0.01)
                
                print("✅ Test data set up in server")
                
        except Exception as e:
            print(f"Warning: Failed to set up test data: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_flask_server(self):
        """Stop Flask server."""
        if hasattr(self, 'server_process'):
            try:
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                self.server_process.wait(timeout=5)
                print("✅ Flask server stopped")
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    print("✅ Flask server force stopped")
                except ProcessLookupError:
                    pass
        
        # Clean up temporary database file
        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except OSError:
                pass
    
    def login_user(self, driver, base_url):
        """Login user and return to home page."""
        # Navigate to login page
        driver.get(f"{base_url}/auth/login")
        
        # Wait for login form
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        
        # Fill login form
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")
        
        email_field.send_keys("analytics@example.com")
        password_field.send_keys("TestPass123!")
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect to home page
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Verify we're logged in by checking for user profile link
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Profile"))
        )
    
    def test_analytics_page_frontend_flow(self):
        """Test complete frontend flow for analytics page."""
        # Start Flask server
        if not self.start_flask_server():
            pytest.skip("Could not start Flask server")
        
        driver = self.setup_selenium_driver()
        
        try:
            # Login user
            self.login_user(driver, "http://localhost:5001")
            
            # Navigate to user profile
            profile_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Profile"))
            )
            profile_link.click()
            
            # Wait for profile page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "View API Logs"))
            )
            
            # Click on API Logs link
            logs_link = driver.find_element(By.PARTIAL_LINK_TEXT, "View API Logs")
            logs_link.click()
            
            # Wait for logs page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "keys-header"))
            )
            
            # Verify page title and header
            assert "API Usage Logs" in driver.find_element(By.CLASS_NAME, "keys-header").text
            
            # Verify user info is displayed
            user_info = driver.find_element(By.CLASS_NAME, "user-info")
            assert "analytics@example.com" in user_info.text
            
            # Wait for stats to load (they're loaded via JavaScript)
            time.sleep(3)
            
            # Check that stats cards are present
            stats_cards = driver.find_elements(By.CLASS_NAME, "stat-card")
            assert len(stats_cards) == 4, f"Expected 4 stat cards, found {len(stats_cards)}"
            
            # Check individual stat cards
            stat_numbers = driver.find_elements(By.CLASS_NAME, "stat-number")
            stat_labels = driver.find_elements(By.CLASS_NAME, "stat-label")
            
            # Verify stat labels
            expected_labels = ["Total Calls", "Successful", "Failed", "Avg Response (ms)"]
            actual_labels = [label.text for label in stat_labels]
            for expected_label in expected_labels:
                assert expected_label in actual_labels, f"Expected label '{expected_label}' not found in {actual_labels}"
            
            # Verify that stat numbers are not just dashes (indicating data loaded)
            for stat_number in stat_numbers:
                assert stat_number.text != "-", f"Stat number should not be '-', found: {stat_number.text}"
            
            # Check that logs table is present
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "excel-table"))
            )
            
            # Verify table headers
            headers = table.find_elements(By.TAG_NAME, "th")
            expected_headers = ["Timestamp", "API Key", "Status", "Request Body", "Response", "Processing Time"]
            actual_headers = [header.text for header in headers]
            
            for expected_header in expected_headers:
                assert expected_header in actual_headers, f"Expected header '{expected_header}' not found in {actual_headers}"
            
            # Verify that log entries are displayed
            rows = table.find_elements(By.CLASS_NAME, "data-row")
            assert len(rows) > 0, "No log entries found in table"
            
            # Verify that we have both success and error statuses
            status_badges = driver.find_elements(By.CLASS_NAME, "status-badge")
            statuses = [badge.text for badge in status_badges]
            
            assert "Success" in statuses, "No success status found in logs"
            assert "Error" in statuses, "No error status found in logs"
            
            # Verify record count is displayed
            record_count = driver.find_element(By.ID, "recordCount")
            assert "Log Entries" in record_count.text
            
        finally:
            driver.quit()
            self.stop_flask_server()
    
    def test_analytics_filtering_frontend(self):
        """Test filtering functionality in frontend."""
        # Start Flask server
        if not self.start_flask_server():
            pytest.skip("Could not start Flask server")
        
        driver = self.setup_selenium_driver()
        
        try:
            # Login user
            self.login_user(driver, "http://localhost:5001")
            
            # Navigate to logs page
            driver.get("http://localhost:5001/logs/analytics@example.com")
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "filters-section"))
            )
            
            # Wait for filters to load
            time.sleep(2)
            
            # Test status filter
            status_filter = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "statusFilter"))
            )
            
            # Select "Success" status
            status_filter.click()
            success_option = driver.find_element(By.CSS_SELECTOR, "option[value='key_pass']")
            success_option.click()
            
            # Apply filters
            apply_button = driver.find_element(By.CSS_SELECTOR, "button[onclick='applyFilters()']")
            apply_button.click()
            
            # Wait for filtered results
            time.sleep(3)
            
            # Verify that only success statuses are shown
            status_badges = driver.find_elements(By.CLASS_NAME, "status-badge")
            for badge in status_badges:
                assert badge.text == "Success", f"Expected only Success status, found: {badge.text}"
            
        finally:
            driver.quit()
            self.stop_flask_server()
    
    def test_analytics_real_api_calls_frontend(self):
        """Test analytics by making real API calls and verifying they're logged in frontend."""
        # Start Flask server
        if not self.start_flask_server():
            pytest.skip("Could not start Flask server")
        
        driver = self.setup_selenium_driver()
        
        try:
            # Login user
            self.login_user(driver, "http://localhost:5001")
            
            # Make some API calls to the proxy endpoint
            test_payloads = [
                {'api_key': self.api_key1.key_value, 'text': 'test1'},
                {'api_key': self.api_key1.key_value, 'text': 'test2'},
                {'api_key': 'tk-invalidkey123456789012345678901', 'text': 'test3'}
            ]
            
            for payload in test_payloads:
                response = requests.post('http://localhost:5001/api/proxy', json=payload)
                assert response.status_code in [200, 401]  # Valid or invalid key
            
            # Wait a moment for logs to be processed
            time.sleep(2)
            
            # Navigate to logs page and verify new entries are visible
            driver.get("http://localhost:5001/logs/analytics@example.com")
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "excel-table"))
            )
            
            # Wait for logs to load
            time.sleep(3)
            
            # Verify that the new logs are displayed
            rows = driver.find_elements(By.CLASS_NAME, "data-row")
            assert len(rows) >= 3, f"Expected at least 3 log rows, found {len(rows)}"
            
        finally:
            driver.quit()
            self.stop_flask_server()
