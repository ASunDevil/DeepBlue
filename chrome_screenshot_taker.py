import subprocess
import json
import base64
import os
import tempfile
from datetime import datetime
import traceback

# Assuming playwright_helper.py is in the same directory as this script.
# When running in Docker, the script's path needs to be volume-mounted.
PLAYWRIGHT_HELPER_SCRIPT_NAME = "playwright_helper.py"
# Use a specific Playwright image version for consistency.
# Check https://mcr.microsoft.com/v2/playwright/python/tags/list for available tags.
DOCKER_IMAGE = "mcr.microsoft.com/playwright/python:v1.42.0" # Example version

def take_screenshot(url: str, width: int = 1280, height: int = 720, page_load_timeout_sec: int = 30) -> dict:
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering take_screenshot with url='{url}', width={width}, height={height}, page_load_timeout_sec={page_load_timeout_sec}")
    results = {
        "image_data": None,
        "image_format": None,
        "error": None,
        "url_requested": url,
        "actual_url": None,
        "page_title": None,
        "docker_error": None # For errors related to Docker execution itself
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    helper_script_path_host = os.path.join(script_dir, PLAYWRIGHT_HELPER_SCRIPT_NAME)
    print(f"DEBUG: [%{datetime.now().isoformat()}] Helper script host path: {helper_script_path_host}")

    if not os.path.exists(helper_script_path_host):
        results["error"] = f"Critical error: {PLAYWRIGHT_HELPER_SCRIPT_NAME} not found at {helper_script_path_host}"
        results["docker_error"] = results["error"] # Also a form of docker/setup error
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting take_screenshot (helper script not found) with results: {results}")
        return results

    # Path of the helper script INSIDE the Docker container
    helper_script_path_container = f"/app/{PLAYWRIGHT_HELPER_SCRIPT_NAME}"
    
    # Timeout for the script execution within Docker, converting page_load_timeout_sec to ms for playwright_helper
    # Add a small buffer for Playwright startup within Docker.
    docker_execution_timeout_sec = page_load_timeout_sec + 15 # Total time Docker container can run
    playwright_timeout_ms = page_load_timeout_sec * 1000

    docker_command = [
        "docker", "run",
        "--rm",                       # Remove container after execution
        "--network=host",             # Use host network; simpler for URLs, but consider security.
                                      # For more isolation: remove this and ensure container has DNS.
                                      # If issues with DNS, may need '--dns=8.8.8.8' or similar.
        # "--cap-add=SYS_ADMIN",      # Sometimes needed for Chrome sandboxing in Docker, Playwright images might handle this.
        "-v", f"{helper_script_path_host}:{helper_script_path_container}:ro", # Mount helper script read-only
        "-w", "/app",                 # Set working directory in container
        DOCKER_IMAGE,
        "python", helper_script_path_container,
        url,
        str(width),
        str(height),
        str(playwright_timeout_ms) # Pass timeout in milliseconds
    ]
    print(f"DEBUG: [%{datetime.now().isoformat()}] Constructed Docker command: {' '.join(docker_command)}")

    try:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Attempting to run Docker command. Timeout: {docker_execution_timeout_sec}s")
        process = subprocess.run(
            docker_command,
            capture_output=True,
            text=True, # Decodes stdout/stderr as UTF-8
            timeout=docker_execution_timeout_sec,
            check=False # Don't raise exception for non-zero exit codes from Docker itself
        )
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker process completed. Return code: {process.returncode}")
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker process stdout (first 500 chars): {process.stdout[:500]}")
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker process stderr (first 500 chars): {process.stderr[:500]}")

        if process.returncode != 0:
            results["docker_error"] = f"Docker process exited with code {process.returncode}. Stderr: {process.stderr.strip()}"
            # Set a general error, which might be overwritten if playwright_helper.py also reported a specific error.
            results["error"] = f"Failed to execute screenshot script in Docker. See docker_error for details."
            
            if process.stdout: # If playwright_helper.py managed to output JSON despite an error
                try:
                    helper_output = json.loads(process.stdout.strip())
                    if helper_output.get("error"): # If playwright_helper reported a specific error
                         results["error"] = helper_output.get("error") # Overwrite general Docker error
                except json.JSONDecodeError:
                    # results["error"] remains the Docker execution error
                    pass 
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting take_screenshot (Docker process error) with results: {results}")
            return results

        # Try to parse the JSON output from playwright_helper.py (printed to its stdout)
        try:
            helper_output = json.loads(process.stdout.strip())
            
            if helper_output.get("error"):
                results["error"] = helper_output["error"]
            else:
                if helper_output.get("image_base64"):
                    results["image_data"] = base64.b64decode(helper_output["image_base64"])
                    results["image_format"] = "png"
                results["actual_url"] = helper_output.get("actual_url")
                results["page_title"] = helper_output.get("page_title")

        except json.JSONDecodeError as e:
            formatted_traceback = traceback.format_exc()
            print(f"DEBUG: [%{datetime.now().isoformat()}] JSONDecodeError: {e}\nRaw output for parsing: {process.stdout.strip()}\nTraceback:\n{formatted_traceback}")
            results["error"] = f"Failed to parse JSON output from screenshot script: {e}. Raw output: {process.stdout.strip()}"
            results["docker_error"] = results["error"] # Also flag as a docker_error as script output was bad

    except subprocess.TimeoutExpired:
        results["error"] = f"Screenshot operation timed out after {docker_execution_timeout_sec} seconds (Docker execution)."
        results["docker_error"] = results["error"]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker command timed out. Error: {results['error']}")
    except FileNotFoundError: # Docker command not found
        results["error"] = "Docker command not found. Please ensure Docker is installed and in PATH."
        results["docker_error"] = results["error"]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker command not found. Error: {results['error']}")
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] An unexpected exception occurred: {e}\nTraceback:\n{formatted_traceback}")
        results["error"] = f"{type(e).__name__} - {str(e)}"
        results["docker_error"] = results["error"] # Flag as a docker_error

    print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting take_screenshot with results: {results}")
    return results

if __name__ == '__main__':
    print(f"DEBUG: [%{datetime.now().isoformat()}] Starting chrome_screenshot_taker.py example usage...")
    # Example Usage (requires Docker running and playwright_helper.py in the same directory)
    test_url = "https://www.google.com" # Replace with a simple, reliable URL for testing
    print(f"DEBUG: [%{datetime.now().isoformat()}] Example: Attempting to take screenshot of {test_url}...")
    output = take_screenshot(test_url, width=800, height=600, page_load_timeout_sec=20)

    if output.get("image_data"):
        # Create a temporary file for the screenshot to avoid cluttering the current directory
        # or use a dedicated 'screenshots' directory if preferred.
        temp_screenshot_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                tmpfile.write(output["image_data"])
                temp_screenshot_file = tmpfile.name
            print(f"Screenshot saved to {temp_screenshot_file}")
            print(f"Page title: {output.get('page_title')}")
            print(f"Actual URL: {output.get('actual_url')}")
            # For CI/testing, one might want to automatically open or verify the image.
            # For this example, just printing the path is sufficient.
        except Exception as e:
            formatted_traceback = traceback.format_exc()
            print(f"DEBUG: [%{datetime.now().isoformat()}] Error saving screenshot: {e}\nTraceback:\n{formatted_traceback}")
        # No automatic deletion here for the example, so user can inspect.
        # In a real app, manage temp files appropriately.
    else:
        print(f"Failed to take screenshot.")
        if output.get("error"):
            print(f"Error: {output.get('error')}")
        if output.get("docker_error") and output.get("docker_error") != output.get("error"):
             print(f"Docker specific error: {output.get('docker_error')}")

    test_url_timeout = "https://httpstat.us/200?sleep=30000" # sleeps for 30s
    print(f"DEBUG: [%{datetime.now().isoformat()}] Example: Attempting to take screenshot of {test_url_timeout}...")
    output_timeout = take_screenshot(test_url_timeout, width=800, height=600, page_load_timeout_sec=10)
    if output_timeout.get("error"):
        print(f"Error as expected: {output_timeout.get('error')}")
        # Specifically check if it's a Playwright error that mentions timeout
        if "Timeout" in output_timeout.get("error") or "timed out" in output_timeout.get("error"):
            print("Timeout error correctly reported by Playwright/Docker.")
        elif output_timeout.get("docker_error") and ("timed out" in output_timeout.get("docker_error")):
            print("Timeout error correctly reported by Docker execution.")
    else:
        print(f"Test failed: Expected a timeout error. Actual output: {output_timeout}")


    test_url_invalid = "http://thissitedoesnotexistandneverwill12345.com"
    print(f"DEBUG: [%{datetime.now().isoformat()}] Example: Attempting to take screenshot of {test_url_invalid}...")
    output_invalid = take_screenshot(test_url_invalid, width=800, height=600, page_load_timeout_sec=10)
    if output_invalid.get("error"):
        print(f"Error as expected: {output_invalid.get('error')}")
    else:
        print(f"Test failed: Expected an error for invalid site. Actual output: {output_invalid}")

    # Example of a site that might cause issues or have specific error messages
    test_url_bad_ssl = "https://expired.badssl.com/"
    print(f"DEBUG: [%{datetime.now().isoformat()}] Example: Attempting to take screenshot of {test_url_bad_ssl}...")
    # playwright_helper.py has ignore_https_errors=True, so this might succeed or show a browser error page
    output_bad_ssl = take_screenshot(test_url_bad_ssl, width=800, height=600, page_load_timeout_sec=15)
    if output_bad_ssl.get("image_data"):
        print(f"Screenshot of {test_url_bad_ssl} taken. Page title: {output_bad_ssl.get('page_title')}")
    elif output_bad_ssl.get("error"):
        print(f"Error for {test_url_bad_ssl}: {output_bad_ssl.get('error')}")
    else:
        print(f"Unexpected result for {test_url_bad_ssl}: {output_bad_ssl}")
    print(f"DEBUG: [%{datetime.now().isoformat()}] Finished chrome_screenshot_taker.py example usage.")
```
