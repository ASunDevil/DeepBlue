import unittest
from unittest.mock import patch
import os # For path manipulation if needed for mocking
from chrome_screenshot_taker import take_screenshot, PLAYWRIGHT_HELPER_SCRIPT_NAME # Assumes chrome_screenshot_taker.py is accessible

# Ensure playwright_helper.py is in the same directory as chrome_screenshot_taker.py for tests to pass,
# or adjust paths if tests are run from a different root.

class TestChromeScreenshotTaker(unittest.TestCase):

    # Using a data URL for a very simple, self-contained test page for basic success.
    SIMPLE_TEST_PAGE_URL = "data:text/html,%3Ch1%3ETest%20Page%20Title%3C%2Fh1%3E%3Cp%3EHello%2C%20Screenshot!%3C%2Fp%3E"
    # A reliable public URL for tests that might need more complex rendering or navigation.
    RELIABLE_PUBLIC_URL = "https://www.example.com" 

    def test_successful_screenshot(self):
        """Tests a successful screenshot of a simple data URL."""
        print(f"\nRunning test_successful_screenshot with URL: {self.SIMPLE_TEST_PAGE_URL}")
        result = take_screenshot(self.SIMPLE_TEST_PAGE_URL)
        
        # For debugging if it fails:
        if result.get('error') or result.get('docker_error'):
            print(f"Error in test_successful_screenshot: {result.get('error')}")
            print(f"Docker error in test_successful_screenshot: {result.get('docker_error')}")

        self.assertIsNone(result.get('error'), msg=f"Unexpected error: {result.get('error')}. Docker error: {result.get('docker_error')}")
        self.assertIsNone(result.get('docker_error'), msg=f"Unexpected Docker error: {result.get('docker_error')}")
        self.assertIsNotNone(result.get('image_data'))
        self.assertIsInstance(result.get('image_data'), bytes)
        self.assertEqual(result.get('image_format'), "png")
        self.assertTrue(result.get('actual_url', '').startswith("data:text/html")) 
        self.assertEqual(result.get('page_title'), "Test Page Title")

    def test_different_viewport_size(self):
        """Tests screenshot with a specific viewport size."""
        width, height = 800, 600
        print(f"\nRunning test_different_viewport_size with URL: {self.RELIABLE_PUBLIC_URL}, Viewport: {width}x{height}")
        result = take_screenshot(self.RELIABLE_PUBLIC_URL, width=width, height=height)
        
        if result.get('error') or result.get('docker_error'):
            print(f"Error in test_different_viewport_size: {result.get('error')}")
            print(f"Docker error in test_different_viewport_size: {result.get('docker_error')}")

        self.assertIsNone(result.get('error'), msg=f"Unexpected error: {result.get('error')}. Docker error: {result.get('docker_error')}")
        self.assertIsNone(result.get('docker_error'), msg=f"Unexpected Docker error: {result.get('docker_error')}")
        self.assertIsNotNone(result.get('image_data'))
        self.assertIsInstance(result.get('image_data'), bytes)
        self.assertEqual(result.get('image_format'), "png")
        self.assertTrue(result.get('actual_url', '').startswith("http")) # Should be the URL itself or similar
        self.assertIsNotNone(result.get('page_title')) # Title can vary for example.com

    def test_url_navigation_error(self):
        """Tests with a non-existent domain URL."""
        invalid_url = "http://thissitedoesnotexistandneverwill12345abc.com"
        print(f"\nRunning test_url_navigation_error with URL: {invalid_url}")
        result = take_screenshot(invalid_url, page_load_timeout_sec=10) # Shorter timeout for faster failure
        
        if not result.get('error'):
            print(f"Warning: test_url_navigation_error did not produce an error. Result: {result}")

        self.assertIsNotNone(result.get('error'), "Expected an error for a non-existent domain.")
        # Error message can vary: "net::ERR_NAME_NOT_RESOLVED", "Navigation timeout", "Execution context was destroyed"
        # We check for common patterns.
        error_lower = result.get('error', '').lower()
        self.assertTrue(
            "err_name_not_resolved" in error_lower or 
            "timeout" in error_lower or 
            "navigation error" in error_lower or
            "context was destroyed" in error_lower or # Can happen if page fails to load quickly
            "dns_lookup_failed" in error_lower, # Specific error from playwright helper
            f"Error message '{result.get('error')}' doesn't match expected patterns for navigation error."
        )
        self.assertIsNone(result.get('image_data'))

    def test_page_load_timeout(self):
        """Tests with a URL that is too slow to load within the timeout."""
        slow_url = "https://httpstat.us/200?sleep=20000" # Sleeps for 20 seconds
        timeout_sec = 5
        print(f"\nRunning test_page_load_timeout with URL: {slow_url}, Timeout: {timeout_sec}s")
        result = take_screenshot(slow_url, page_load_timeout_sec=timeout_sec)

        if not result.get('error'):
            print(f"Warning: test_page_load_timeout did not produce an error. Result: {result}")

        self.assertIsNotNone(result.get('error'), "Expected an error due to page load timeout.")
        error_lower = result.get('error', '').lower()
        docker_error_lower = result.get('docker_error', '').lower()

        # The timeout can be reported by Playwright itself (inside helper) or by Docker execution timeout.
        playwright_timeout_expected = f"page.goto: Timeout {timeout_sec*1000}ms exceeded" 
        docker_timeout_expected = f"Screenshot operation timed out after {timeout_sec + 15} seconds"

        self.assertTrue(
            playwright_timeout_expected.lower() in error_lower or
            "timeout" in error_lower or # More generic timeout from playwright
            docker_timeout_expected.lower() in error_lower or # If docker_error is primary
            docker_timeout_expected.lower() in docker_error_lower, # If docker_error is set
            f"Error message '{result.get('error')}' or docker_error '{result.get('docker_error')}' doesn't match expected timeout patterns."
        )
        self.assertIsNone(result.get('image_data'))

    @patch('chrome_screenshot_taker.os.path.exists') # Patch os.path.exists in the context of chrome_screenshot_taker module
    def test_helper_script_not_found(self, mock_exists):
        """Tests behavior when the playwright_helper.py script is not found."""
        print(f"\nRunning test_helper_script_not_found (mocking os.path.exists)")
        
        # Configure the mock to return False when checking for PLAYWRIGHT_HELPER_SCRIPT_NAME
        def side_effect_func(path_to_check):
            # Get the directory of the chrome_screenshot_taker module to construct the full path
            # that take_screenshot will use for the helper script.
            module_dir = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chrome_screenshot_taker.py'))) # Assuming test is in a subdir or similar relative path setup
            # Fallback if path logic is tricky, assume it's in same dir as this test file for a simpler check
            # However, chrome_screenshot_taker.py uses os.path.dirname(os.path.abspath(__file__)) for its own location.
            # So we need to mock the path it will actually check.
            
            # The path checked by take_screenshot is:
            # script_dir = os.path.dirname(os.path.abspath(__file__)) <-- __file__ of chrome_screenshot_taker.py
            # helper_script_path_host = os.path.join(script_dir, PLAYWRIGHT_HELPER_SCRIPT_NAME)
            # We need this mock_exists to return False for *that* specific path.
            # A simpler way is to make it always return False for the helper script name.
            if path_to_check.endswith(PLAYWRIGHT_HELPER_SCRIPT_NAME):
                return False
            return True # For other os.path.exists calls if any

        mock_exists.side_effect = side_effect_func
        
        result = take_screenshot(self.RELIABLE_PUBLIC_URL) # URL doesn't matter much here
        
        self.assertIsNotNone(result.get('error'))
        self.assertIn(f"Critical error: {PLAYWRIGHT_HELPER_SCRIPT_NAME} not found", result.get('error', ''))
        self.assertIsNotNone(result.get('docker_error'), "docker_error should also be set indicating script not found.")
        self.assertIn(f"Critical error: {PLAYWRIGHT_HELPER_SCRIPT_NAME} not found", result.get('docker_error', ''))
        self.assertIsNone(result.get('image_data'))

if __name__ == '__main__':
    print("Running chrome_screenshot_taker tests...")
    print("IMPORTANT: Docker must be installed, running, and the user must have permissions to use it.")
    print(f"Playwright helper script ({PLAYWRIGHT_HELPER_SCRIPT_NAME}) must be in the same directory as chrome_screenshot_taker.py.")
    print(f"The Docker image used by chrome_screenshot_taker.py will be pulled if not present.")
    unittest.main()
```
