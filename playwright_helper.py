import sys
import base64
import json
from playwright.sync_api import sync_playwright
from datetime import datetime
import traceback

def main():
    print(f"DEBUG: [%{datetime.now().isoformat()}] playwright_helper.py main() called with argv={sys.argv}", file=sys.stderr)
    if len(sys.argv) != 5:
        error_message = "Incorrect number of arguments. Expected URL, width, height, timeout_ms."
        results_for_error = {"error": error_message}
        print(f"DEBUG: [%{datetime.now().isoformat()}] Incorrect number of arguments. Preparing error JSON for stdout.", file=sys.stderr)
        print(json.dumps(results_for_error), file=sys.stdout) # This was printing to stderr before, but instruction implies error to stdout for caller
        print(f"DEBUG: [%{datetime.now().isoformat()}] playwright_helper.py exiting due to incorrect arguments. Error: {error_message}", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    width = int(sys.argv[2])
    height = int(sys.argv[3])
    timeout_ms = int(sys.argv[4])
    print(f"DEBUG: [%{datetime.now().isoformat()}] Parsed arguments: url='{url}', width={width}, height={height}, timeout_ms={timeout_ms}", file=sys.stderr)
    
    results = {
        "image_base64": None,
        "actual_url": None,
        "page_title": None,
        "error": None
    }

    try:
        with sync_playwright() as p:
            print(f"DEBUG: [%{datetime.now().isoformat()}] Playwright context initialized.", file=sys.stderr)
            # Using chromium.launch() which should use a bundled browser if Playwright was installed correctly in the image.
            # Add args=['--no-sandbox'] IF NEEDED due to Docker environment, but Playwright's official images often handle this.
            browser = p.chromium.launch() 
            print(f"DEBUG: [%{datetime.now().isoformat()}] Browser launched. Options used: default (potentially add args if specified)", file=sys.stderr)
            context = browser.new_context(
                viewport={'width': width, 'height': height},
                ignore_https_errors=True # Consider making this an option later
            )
            print(f"DEBUG: [%{datetime.now().isoformat()}] Browser context created. Viewport: {{'width': {width}, 'height': {height}}}, Ignore HTTPS errors: True", file=sys.stderr)
            page = context.new_page()
            print(f"DEBUG: [%{datetime.now().isoformat()}] New page created.", file=sys.stderr)
            # Using 'load' state for more reliability than 'domcontentloaded' if external resources matter for screenshot
            print(f"DEBUG: [%{datetime.now().isoformat()}] Navigating to URL: {url} with timeout {timeout_ms}ms, wait_until='load'", file=sys.stderr)
            page.goto(url, timeout=timeout_ms, wait_until='load') 
            print(f"DEBUG: [%{datetime.now().isoformat()}] Page navigation successful. Actual URL: {page.url}, Title: {page.title()}", file=sys.stderr)
            
            print(f"DEBUG: [%{datetime.now().isoformat()}] Taking screenshot.", file=sys.stderr)
            image_bytes = page.screenshot(type='png')
            print(f"DEBUG: [%{datetime.now().isoformat()}] Screenshot taken. Image size: {len(image_bytes)} bytes.", file=sys.stderr)
            results["image_base64"] = base64.b64encode(image_bytes).decode()
            results["actual_url"] = page.url
            results["page_title"] = page.title()
            print(f"DEBUG: [%{datetime.now().isoformat()}] Closing browser.", file=sys.stderr)
            browser.close()
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exception during Playwright operation: {e}\nTraceback:\n{formatted_traceback}", file=sys.stderr)
        results["error"] = f"Playwright error: {type(e).__name__} - {str(e)}"
    
    # Print JSON result to stdout, so the calling process can capture it.
    print(f"DEBUG: [%{datetime.now().isoformat()}] playwright_helper.py returning results (to stdout): {results}", file=sys.stderr)
    print(json.dumps(results))

if __name__ == '__main__':
    main()
```
