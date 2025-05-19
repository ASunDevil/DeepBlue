import sys
import base64
import json
from playwright.sync_api import sync_playwright

def main():
    if len(sys.argv) != 5:
        print(json.dumps({"error": "Incorrect number of arguments. Expected URL, width, height, timeout_ms."}), file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    width = int(sys.argv[2])
    height = int(sys.argv[3])
    timeout_ms = int(sys.argv[4])
    
    results = {
        "image_base64": None,
        "actual_url": None,
        "page_title": None,
        "error": None
    }

    try:
        with sync_playwright() as p:
            # Using chromium.launch() which should use a bundled browser if Playwright was installed correctly in the image.
            # Add args=['--no-sandbox'] IF NEEDED due to Docker environment, but Playwright's official images often handle this.
            browser = p.chromium.launch() 
            context = browser.new_context(
                viewport={'width': width, 'height': height},
                ignore_https_errors=True # Consider making this an option later
            )
            page = context.new_page()
            # Using 'load' state for more reliability than 'domcontentloaded' if external resources matter for screenshot
            page.goto(url, timeout=timeout_ms, wait_until='load') 
            
            image_bytes = page.screenshot(type='png')
            results["image_base64"] = base64.b64encode(image_bytes).decode()
            results["actual_url"] = page.url
            results["page_title"] = page.title()
            browser.close()
    except Exception as e:
        results["error"] = f"Playwright error: {type(e).__name__} - {str(e)}"
    
    # Print JSON result to stdout, so the calling process can capture it.
    print(json.dumps(results))

if __name__ == '__main__':
    main()
```
