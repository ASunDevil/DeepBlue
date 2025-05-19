import unittest
import asyncio
from mcp import ClientSession, types  # types should contain Image, ToolResult, ToolError
from mcp.client.streamable_http import streamablehttp_client
from typing import Any, Union # For type hinting

MCP_CHROME_SERVER_URL = "http://127.0.0.1:8000/mcp" 
# Simple data URL for testing to avoid external dependencies if possible.
# Ensure Chrome in Docker can handle this.
DATA_URL_SIMPLE_PAGE = "data:text/html,%3Ch1%3ETest%20Title%3C%2Fh1%3E%3Cp%3EHello%20Screenshotters!%3C%2Fp%3E"
RELIABLE_PUBLIC_URL = "https://www.example.com" 


class TestChromeMCPServerIntegration(unittest.IsolatedAsyncioTestCase):

    async def helper_call_capture_webpage(self, url: str, width: Union[int, None] = None, height: Union[int, None] = None) -> Union[types.ToolResult, None]:
        """Helper function to connect and call the capture_webpage tool."""
        try:
            async with streamablehttp_client(MCP_CHROME_SERVER_URL) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_name = "capture_webpage"
                    arguments = {"url": url}
                    if width is not None:
                        arguments["width"] = width
                    if height is not None:
                        arguments["height"] = height
                    
                    print(f"\nCalling tool '{tool_name}' on {MCP_CHROME_SERVER_URL} with args: {arguments}")
                    tool_result = await session.call_tool(tool_name, arguments)
                    
                    self.assertIsInstance(tool_result, types.ToolResult, f"Unexpected response type from MCP server: {type(tool_result)}")
                    return tool_result
                    
        except ConnectionRefusedError:
            self.fail(f"Connection to MCP Chrome server at {MCP_CHROME_SERVER_URL} refused. "
                      "Please ensure 'python mcp_chrome_server.py' is running.")
        except Exception as e:
            # Check for httpx specific connection errors if httpx is used by streamablehttp_client
            if "ConnectError" in str(type(e)) or "ConnectTimeout" in str(type(e)):
                 self.fail(f"Connection to MCP Chrome server at {MCP_CHROME_SERVER_URL} failed. "
                      "Please ensure 'python mcp_chrome_server.py' is running. "
                      f"Details: {type(e).__name__} - {e}")
            else:
                self.fail(f"An unexpected error occurred during MCP Chrome integration test: {type(e).__name__} - {e}")
        return None

    async def test_capture_successful_screenshot(self):
        """Tests successful screenshot capture of a simple data URL."""
        print(f"Running test_capture_successful_screenshot with URL: {DATA_URL_SIMPLE_PAGE}")
        tool_result = await self.helper_call_capture_webpage(url=DATA_URL_SIMPLE_PAGE)
        if tool_result is None: return # Connection failed, helper already called self.fail()

        self.assertTrue(tool_result.success, f"Tool call failed: Error Type '{tool_result.error.type if tool_result.error else 'N/A'}', Message: '{tool_result.error.message if tool_result.error else 'N/A'}'")
        self.assertIsNone(tool_result.error, "tool_result.error should be None for a successful call.")
        self.assertIsNotNone(tool_result.content, "ToolResult.content is None for successful screenshot.")
        
        # Assuming tool_result.content is mcp.types.Image for successful calls returning Image
        # This is based on how FastMCP handles specific return types like mcp.server.fastmcp.Image
        self.assertIsInstance(tool_result.content, types.Image, f"Expected content to be mcp.types.Image, got {type(tool_result.content)}")
        if isinstance(tool_result.content, types.Image): # Redundant due to assertIsInstance, but good for type checker
            self.assertEqual(tool_result.content.format, "png", "Image format should be PNG.")
            self.assertIsInstance(tool_result.content.data, bytes, "Image data should be bytes.")
            self.assertTrue(len(tool_result.content.data) > 100, "Image data seems too small for a PNG.")

    async def test_capture_with_custom_dimensions(self):
        """Tests successful screenshot capture with custom dimensions."""
        width, height = 800, 600
        print(f"Running test_capture_with_custom_dimensions with URL: {RELIABLE_PUBLIC_URL}, Viewport: {width}x{height}")
        tool_result = await self.helper_call_capture_webpage(url=RELIABLE_PUBLIC_URL, width=width, height=height)
        if tool_result is None: return

        self.assertTrue(tool_result.success, f"Tool call failed: Error Type '{tool_result.error.type if tool_result.error else 'N/A'}', Message: '{tool_result.error.message if tool_result.error else 'N/A'}'")
        self.assertIsNone(tool_result.error)
        self.assertIsNotNone(tool_result.content)
        
        self.assertIsInstance(tool_result.content, types.Image, f"Expected content to be mcp.types.Image, got {type(tool_result.content)}")
        if isinstance(tool_result.content, types.Image):
            self.assertEqual(tool_result.content.format, "png")
            self.assertIsInstance(tool_result.content.data, bytes)
            self.assertTrue(len(tool_result.content.data) > 100) 
            # Note: Verifying the actual dimensions of the image would require an image library.
            # For this test, we primarily verify that the call succeeds and returns an image.

    async def test_capture_url_navigation_error(self):
        """Tests screenshot capture of a non-existent domain URL."""
        invalid_url = "http://thissitedefinitelydoesnotexistandneverwill12345.com"
        print(f"Running test_capture_url_navigation_error with URL: {invalid_url}")
        tool_result = await self.helper_call_capture_webpage(url=invalid_url)
        if tool_result is None: return

        self.assertFalse(tool_result.success, "Tool call should have failed for a non-existent domain.")
        self.assertIsNotNone(tool_result.error, "tool_result.error should be populated for a failed call.")
        
        if tool_result.error: # Check to satisfy type checker
            self.assertEqual(tool_result.error.type, "ScreenshotFailed", f"Expected error type 'ScreenshotFailed', got '{tool_result.error.type}'")
            self.assertIsInstance(tool_result.error.message, str)
            # Check for playwright specific error messages in the detailed message string
            # Example: "net::ERR_NAME_NOT_RESOLVED" or "Navigation timeout" or "Execution context was destroyed"
            error_message_lower = tool_result.error.message.lower()
            self.assertTrue(
                "err_name_not_resolved" in error_message_lower or
                "timeout" in error_message_lower or # Playwright's own navigation timeout
                "dns_lookup_failed" in error_message_lower or # Error from playwright_helper.py
                "context was destroyed" in error_message_lower,
                f"Error message '{tool_result.error.message}' does not contain expected details for navigation failure."
            )
        self.assertIsNone(tool_result.content, "ToolResult.content should be None for a failed call.")


if __name__ == '__main__':
    print(f"Running MCP Chrome Server Integration Tests...")
    print(f"IMPORTANT: Ensure the MCP Chrome server (`python mcp_chrome_server.py`) is running on {MCP_CHROME_SERVER_URL}.")
    print("If you also have other MCP servers (e.g., bash tool, C++ tool), ensure they are on different ports if any also use port 8000 by default.")
    
    # Attempt to install mcp and httpx if not found
    try:
        import mcp
        import httpx # A common dependency for mcp http client
    except ImportError:
        print("\nAttempting to install missing packages 'mcp[cli]' and 'httpx'...")
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]", "httpx"])
            print("Packages installed successfully. Please re-run the tests.")
            sys.exit(0) # Exit so user can re-run with packages installed
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e}")
            print("Please install them manually: pip install \"mcp[cli]\" httpx")
            sys.exit(1) # Exit with error

    unittest.main()
```
