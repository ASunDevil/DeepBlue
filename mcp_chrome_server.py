# !!! CRITICAL SECURITY WARNING - DEVELOPMENT AND TESTING ONLY !!!
#
# This MCP server exposes a tool (`capture_webpage`) that allows for fetching
# and rendering arbitrary web URLs using a headless Chrome browser (via Playwright).
# This capability is EXTREMELY DANGEROUS if exposed without robust security measures.
#
# Risks include, but are not limited to:
# 1. Server-Side Request Forgery (SSRF): The server can be made to send requests to
#    internal network resources or services that are not meant to be exposed.
# 2. Resource Consumption & Denial-of-Service (DoS): Fetching complex or malicious
#    webpages can consume significant CPU, memory, and network bandwidth, potentially
#    leading to DoS if not properly rate-limited and monitored.
# 3. Execution of Arbitrary JavaScript: While sandboxed within the browser, malicious
#    JavaScript on fetched pages could attempt to exploit vulnerabilities in the
#    headless browser or perform other unwanted actions.
# 4. Data Exfiltration: If the server has access to sensitive information, there's a
#    risk that a compromised rendering process could exfiltrate data, although Playwright's
#    sandboxing aims to prevent direct host access.
#
# DO NOT EXPOSE THIS SERVER TO UNTRUSTED NETWORKS OR USERS
# WITHOUT IMPLEMENTING AND VERIFYING:
#    - Strong MCP-level authentication and authorization (e.g., OAuth 2.0).
#    - Input validation and sanitization for URLs.
#    - Egress filtering to restrict where the server can make requests.
#    - Comprehensive monitoring and rate limiting.
#
# Consider this a template for a highly privileged tool requiring maximum security scrutiny.

from typing import Union, Dict, Any # For type hinting

# Attempt to import FastMCP and Context, and install if missing
try:
    from mcp.server.fastmcp import FastMCP, Context, Image
except ImportError:
    print("MCP package not found. Attempting to install 'mcp[cli]'...")
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]"])
        from mcp.server.fastmcp import FastMCP, Context, Image
        print("MCP package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install mcp: {e}")
        print("Please install it manually using: pip install \"mcp[cli]\"")
        sys.exit(1)
    except ImportError:
        print("Failed to import FastMCP, Context, or Image even after attempting installation.")
        print("Please ensure 'mcp[cli]' is installed and accessible.")
        sys.exit(1)

# Potentially: from mcp.server.auth import AuthSettings
from chrome_screenshot_taker import take_screenshot # Assumes chrome_screenshot_taker.py is in the same directory

# Conceptual Authentication Setup (Similar to other MCP servers)
# from my_oauth_provider import MyCustomOAuthServerProvider # Your implementation
# from mcp.server.auth import AuthSettings
# auth_settings = AuthSettings(
#     issuer_url="https_your_auth_server_com",
#     required_scopes=["screenshot_tool_access"], # Define specific scopes
# )
# mcp_app = FastMCP(
#     name="ChromeScreenshotServer",
#     description="MCP Server for capturing webpage screenshots. REQUIRES AUTHENTICATION.",
#     auth_server_provider=MyCustomOAuthServerProvider(),
#     auth=auth_settings
# )

# Current UNSECURED implementation:
mcp_app = FastMCP(
    name="ChromeScreenshotServer",
    description="MCP Server for capturing webpage screenshots. WARNING: CRITICALLY DANGEROUS IF NOT SECURED."
)

@mcp_app.tool()
def capture_webpage(ctx: Context, url: str, width: int = 1280, height: int = 720) -> Union[Image, Dict[str, str]]:
    """
    Captures a screenshot of a given webpage URL using a headless Chrome browser.

    The screenshot is taken at the specified viewport width and height.
    The underlying mechanism uses Playwright within a Docker container for sandboxing.

    Args:
        ctx: The MCP Context object, used for logging.
        url: The URL of the webpage to capture.
        width: The viewport width for the headless browser. Defaults to 1280.
        height: The viewport height for the headless browser. Defaults to 720.

    Returns:
        An MCP Image object containing the PNG screenshot data on success.
        On failure, returns a dictionary with "error" and "message" keys detailing the issue.
        Example successful return: Image(data=b'png_bytes', format='png')
        Example error return: {"error": "ScreenshotFailed", "message": "Details of the failure..."}
    """
    ctx.info(f"Attempting to capture webpage. URL: '{url}', Width: {width}, Height: {height}")

    # Default page_load_timeout_sec from take_screenshot is 30 seconds.
    # This can be exposed as another MCP tool parameter if needed.
    screenshot_result = take_screenshot(url=url, width=width, height=height)

    if screenshot_result.get("image_data"):
        ctx.info(f"Screenshot successful for '{url}'. Page Title: '{screenshot_result.get('page_title', 'N/A')}', Actual URL: '{screenshot_result.get('actual_url', 'N/A')}'")
        return Image(data=screenshot_result["image_data"], format=screenshot_result["image_format"]) # image_format is "png"
    else:
        error_message = screenshot_result.get("error", "Unknown error during screenshot.")
        docker_error_detail = screenshot_result.get("docker_error", "")
        # Combine error messages for clarity, avoiding duplication if they are the same.
        full_error_details = f"{error_message}{f' (Docker/Helper error: {docker_error_detail})' if docker_error_detail and docker_error_detail != error_message else ''}"
        
        ctx.error(f"Screenshot failed for '{url}': {full_error_details}")
        # Return a dictionary that signals an error. FastMCP should handle this.
        return {"error": "ScreenshotFailed", "message": full_error_details}

# Main block to run the server
if __name__ == "__main__":
    print("Starting ChromeScreenshotServer MCP server...")
    print("!!! CRITICAL SECURITY WARNING: This server allows fetching arbitrary URLs and is EXTREMELY DANGEROUS if not properly secured. For development/testing ONLY. !!!")
    print("Ensure Docker is running and accessible.")
    
    try:
        mcp_app.run() # Default host="127.0.0.1", port=8000
    except ImportError as e:
        if "uvicorn" in str(e).lower():
            print(f"Error running server: {e}")
            print("Make sure 'uvicorn' is installed. It should be a dependency of 'mcp[cli]'.")
            print("You might need to run: pip install \"mcp[cli]\" uvicorn")
        else:
            print(f"An import error occurred: {e}. Ensure 'mcp[cli]' and its dependencies are installed.")
    except Exception as e:
        print(f"An unexpected error occurred while trying to run the server: {e}")

```
