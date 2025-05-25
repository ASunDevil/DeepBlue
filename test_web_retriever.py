import asyncio
import unittest
from unittest.mock import patch # For potentially mocking WebBaseLoader in more advanced tests

# Assuming web_retriever.py is in the same directory or accessible via PYTHONPATH
try:
    from web_retriever import get_web_content
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from web_retriever import get_web_content

# A known public URL for testing that is simple and stable
VALID_URL_EXAMPLE_COM = "http://example.com/" # using http as it's simpler and often allowed for tests
VALID_URL_GOOGLE = "https://www.google.com/" # A more complex, real-world page

# A URL that is syntactically valid but highly unlikely to exist
NON_EXISTENT_DOMAIN_URL = "http://thishouldnotbearealdomain12345abcxyz.com/"

# Data URI for an empty HTML page
EMPTY_CONTENT_DATA_URI = "data:text/html,"
# Data URI for a page with minimal HTML but no visible content in body
MINIMAL_HTML_DATA_URI = "data:text/html,<html><head><title>Test</title></head><body></body></html>"


class TestGetWebContent(unittest.IsolatedAsyncioTestCase):

    async def test_valid_url_example_com(self):
        print(f"\nRunning: test_valid_url_example_com with URL: {VALID_URL_EXAMPLE_COM}")
        content = await get_web_content(VALID_URL_EXAMPLE_COM)
        self.assertIsInstance(content, str)
        self.assertTrue(len(content) > 0, "Content should not be empty for example.com")
        self.assertIn("<html", content.lower(), "HTML tag not found in content from example.com")
        self.assertIn("example domain", content.lower(), "Expected text 'example domain' not found in content")
        print(f"Content received (first 100 chars): {content[:100]}")

    async def test_valid_url_google_com(self):
        # This test is more prone to intermittent network issues or changes by Google
        # but serves as a real-world test.
        print(f"\nRunning: test_valid_url_google_com with URL: {VALID_URL_GOOGLE}")
        content = await get_web_content(VALID_URL_GOOGLE)
        self.assertIsInstance(content, str)
        self.assertTrue(len(content) > 0, "Content should not be empty for google.com")
        self.assertIn("<html", content.lower(), "HTML tag not found in content from google.com")
        # Google's page is complex and changes, so checking for a very generic tag.
        print(f"Content received (first 100 chars): {content[:100]}")


    async def test_invalid_url_scheme_ftp(self):
        print("\nRunning: test_invalid_url_scheme_ftp")
        url = "ftp://example.com"
        content = await get_web_content(url)
        self.assertEqual(content, "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'.")

    async def test_invalid_url_scheme_no_scheme(self):
        print("\nRunning: test_invalid_url_scheme_no_scheme")
        url = "example.com"
        content = await get_web_content(url)
        self.assertEqual(content, "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'.")

    async def test_non_string_url_integer(self):
        print("\nRunning: test_non_string_url_integer")
        url = 123
        content = await get_web_content(url) # type: ignore 
        self.assertEqual(content, "Error: URL must be a string.")

    async def test_non_string_url_list(self):
        print("\nRunning: test_non_string_url_list")
        url = ["http://example.com"]
        content = await get_web_content(url) # type: ignore
        self.assertEqual(content, "Error: URL must be a string.")

    async def test_network_error_non_existent_domain(self):
        print(f"\nRunning: test_network_error_non_existent_domain with URL: {NON_EXISTENT_DOMAIN_URL}")
        content = await get_web_content(NON_EXISTENT_DOMAIN_URL)
        self.assertTrue(content.startswith(f"Error: Could not retrieve content from URL: {NON_EXISTENT_DOMAIN_URL}."), 
                        f"Unexpected error message: {content}")
        print(f"Error message received: {content}")

    async def test_empty_content_data_uri_empty(self):
        # WebBaseLoader with default BS4 parser might still produce '<html><head></head><body></body></html>'
        # for a completely empty data URI if it auto-creates the structure.
        # Let's check what it actually returns.
        print(f"\nRunning: test_empty_content_data_uri_empty with URL: {EMPTY_CONTENT_DATA_URI}")
        content = await get_web_content(EMPTY_CONTENT_DATA_URI)
        # Based on langchain.document_loaders.web_base.WebBaseLoader behavior,
        # an empty data URI "data:text/html," often results in "<html><head></head><body></body></html>"
        # because BeautifulSoup creates a basic structure.
        # So, it's not "No content found" but rather minimal HTML.
        # We can check if the content is exactly this minimal structure or very small.
        expected_minimal_html = "<html><head></head><body></body></html>"
        if content == expected_minimal_html or content == "": # Some loaders might return ""
             pass # This is acceptable for an "empty" data URI
        else:
            # If it's not this minimal structure, let's check if it's the "No content" error,
            # which might happen if the loader configuration changes or if it's a different loader.
            self.assertTrue(content.startswith("Error: No content found at the URL"),
                            f"Expected minimal HTML or 'No content found' error, but got: '{content}'")
        print(f"Content from empty data URI: '{content}'")

    async def test_empty_content_data_uri_minimal_html(self):
        print(f"\nRunning: test_empty_content_data_uri_minimal_html with URL: {MINIMAL_HTML_DATA_URI}")
        content = await get_web_content(MINIMAL_HTML_DATA_URI)
        # This should return the HTML provided in the data URI
        self.assertEqual(content, "<html><head><title>Test</title></head><body></body></html>")
        print(f"Content from minimal HTML data URI: '{content}'")


if __name__ == '__main__':
    unittest.main()
