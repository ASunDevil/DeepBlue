# Bash Command Execution Tool (`run_bash_command`)

## Overview
The `run_bash_command` tool, found in `bash_tool.py`, provides a Python interface for executing bash commands. It captures the standard output (stdout), standard error (stderr), and exit code of the executed command, and also supports configurable timeouts and custom working directories.

## Features
- Executes bash commands.
- Captures `stdout`, `stderr`, and the `exit_code` of the command.
- Supports configurable timeouts to prevent indefinite hanging.
- Allows specifying a custom `working_directory` for command execution.
- Returns a dictionary containing detailed results of the execution, including a `timed_out` status.
- Uses `shlex.split()` for parsing the command string, which helps prevent shell injection vulnerabilities when the command string might be constructed from external input.

## Usage

### Prerequisites
The tool is implemented in Python 3. It relies on the `subprocess`, `shlex`, and `os` modules, which are part of the standard Python library, so no external packages need to be installed.

### Importing and Calling the Tool
To use the `run_bash_command` tool, import it from the `bash_tool.py` file.

```python
from bash_tool import run_bash_command

# Example: List files in the current directory
result = run_bash_command("ls -l")

if result['exit_code'] == 0:
    print("Command successful!")
    print("Stdout:")
    print(result['stdout'])
else:
    print(f"Command failed with exit code: {result['exit_code']}")
    print("Stderr:")
    print(result['stderr'])

if result['timed_out']:
    print("Command timed out.")

# Example: Running a command with a timeout of 5 seconds
# and in a specific directory.
# This command will time out as it tries to sleep for 10 seconds.
result_custom = run_bash_command(
    "sleep 10 && echo 'Done sleeping'", # Command to execute
    timeout=5,                          # Max 5 seconds
    working_directory="/tmp"            # Run in /tmp directory
)

print("\nCustom command execution details:")
print(f"STDOUT: {result_custom['stdout']}")
print(f"STDERR: {result_custom['stderr']}")
print(f"Exit Code: {result_custom['exit_code']}")
print(f"Timed Out: {result_custom['timed_out']}")

# Example: Command that does not exist
result_error = run_bash_command("my_non_existent_command_123")
print("\nNon-existent command execution details:")
print(f"STDOUT: {result_error['stdout']}")
print(f"STDERR: {result_error['stderr']}")
print(f"Exit Code: {result_error['exit_code']}")
print(f"Timed Out: {result_error['timed_out']}")
```

### Input Parameters
The `run_bash_command` function accepts the following parameters:

-   `command` (str | list): The bash command to execute. This can be a single string (which will be tokenized by `shlex.split()`) or a list of command parts (e.g., `['ls', '-l']`).
-   `timeout` (int, optional): The maximum time in seconds to wait for the command to complete. If the command duration exceeds this value, it will be terminated. Defaults to `60` seconds.
-   `working_directory` (str, optional): The directory in which to execute the command. If `None` or not provided, the command will be executed in the current working directory of the Python script. Defaults to `None`.

### Output
The function returns a dictionary with the following keys:

-   `stdout` (str): The standard output produced by the command. This will be an empty string if the command produces no standard output or if an error occurs before output is captured.
-   `stderr` (str): The standard error output produced by the command. This will be an empty string if the command produces no standard error, or it may contain error messages from the tool itself (e.g., timeout notifications, command not found).
-   `exit_code` (int): The exit code of the executed command. Conventionally, an exit code of `0` indicates success. A non-zero exit code usually indicates an error. The tool itself uses `-1` for certain internal errors like timeout or command not found due to `FileNotFoundError` or empty command.
-   `timed_out` (bool): `True` if the command execution exceeded the specified `timeout` and was terminated; `False` otherwise.

## Testing
A comprehensive test suite is provided in `test_bash_tool.py`. These tests ensure the reliability and correctness of the `run_bash_command` tool across various scenarios.

To run the tests, navigate to the root directory of the project in your terminal and execute the following command:

```bash
python3 -m unittest test_bash_tool.py
```
The tests will run and report their status (e.g., OK if all pass, or details of any failures).

## MCP Server for Bash Command Execution

### Overview
The `mcp_server.py` script implements an MCP (Master Control Program) server. This server exposes the `execute_bash` tool, allowing MCP clients to remotely execute bash commands.

### Dependencies
The server requires the `mcp` Python package. You can install it and its typical dependencies (including `uvicorn` for running the server) using pip:
```bash
pip install "mcp[cli]"
```
The `mcp_server.py` script itself includes a helper to attempt this installation if `mcp` is not initially found when it starts.

### Running the Server
To run the MCP server, execute the following command in your terminal from the root directory of this project:
```bash
python mcp_server.py
```
The server will typically start on `http://127.0.0.1:8000`. You should see output in the console indicating the server is running.

### **IMPORTANT SECURITY WARNING**
The `execute_bash` tool provided by this server allows for arbitrary bash command execution. This is **extremely dangerous** if the server is exposed without proper security measures. Before deploying or using this server in any environment where it could be accessed by untrusted parties, you **MUST** implement robust authentication and authorization. The `mcp_server.py` file contains comments and placeholders indicating where MCP's built-in OAuth 2.0 features should be integrated. Failure to secure this tool can lead to severe security vulnerabilities, including unauthorized access to and compromise of the system running the server.

### Interacting with the Tool
Once the MCP server is running, clients can connect to it and call the `execute_bash` tool. The tool name as registered with the MCP server is `execute_bash`.

The tool expects the following arguments:
-   `command` (str): The bash command string to execute.
-   `timeout` (int, optional): The maximum time in seconds to wait for the command to complete. Defaults to 60 if not provided.
-   `working_directory` (str or None, optional): The directory in which to execute the command. If `None` or not specified, it defaults to the server's current working directory.

It returns a dictionary containing:
-   `stdout` (str): The standard output from the command.
-   `stderr` (str): The standard error output from the command.
-   `exit_code` (int): The exit code of the command.
-   `timed_out` (bool): `True` if the command timed out, `False` otherwise.

Here's a conceptual Python client example:
```python
# Conceptual client example (assumes you have an MCP session connected)
# See test_mcp_server.py for a more complete, runnable client example.
# Ensure 'mcp' and 'httpx' packages are installed: pip install "mcp[cli]" httpx

# async with streamablehttp_client(MCP_SERVER_URL) as (read_stream, write_stream, _):
#     async with ClientSession(read_stream, write_stream) as session:
#         await session.initialize()
#
#         tool_name = "execute_bash"
#         arguments = {
#             "command": "echo 'Hello from MCP client!'",
#             "timeout": 30,
#             "working_directory": "/tmp"
#         }
#
#         # Note: The 'ctx' argument is handled by the MCP framework
#         # and does not need to be explicitly passed by the client here.
#         tool_result = await session.call_tool(tool_name, arguments)
#
#         if tool_result.success:
#             print("Tool executed successfully!")
#             # The actual result from 'execute_bash' is in tool_result.content
#             print(f"Result: {tool_result.content}") 
#             # Expecting a dictionary like {'stdout': 'Hello from MCP client!\n', 'stderr': '', ...}
#         else:
#             print(f"Tool execution failed: {tool_result.error_message}")

```
The `test_mcp_server.py` file contains a fully functional integration test that demonstrates client interaction.

## C++ Code Execution MCP Server (Simple Version)

### Overview
The `mcp_cpp_server.py` script implements an MCP server that exposes an `execute_cpp` tool. Its purpose is to allow remote compilation and execution of single C++ source file snippets within a sandboxed environment. This "simple version" is designed to work with the C++ Standard Library only; it does not support linking external libraries or providing user-defined compile flags beyond those hardcoded in `cpp_runner.py`.

### Core Execution Logic (`cpp_runner.py`)
The actual C++ compilation and execution are handled by the `run_cpp_code` function within `cpp_runner.py`. This module uses `g++` (via a Docker container, e.g., `frolvlad/alpine-gxx:latest` or `gcc:latest`) to compile the C++ code and then runs the resulting executable, also within a Docker container. Docker is therefore a key dependency for providing this sandboxing layer.

### Dependencies
-   **For the MCP server (`mcp_cpp_server.py`)**:
    -   The `mcp` Python package. Install with `pip install "mcp[cli]"`. This typically includes `uvicorn` for running the FastAPI-based server.
-   **For the core C++ runner (`cpp_runner.py`)**:
    -   **Docker**: Must be installed, running, and the user executing the script must have permissions to interact with the Docker daemon. The specified Docker image (e.g., `frolvlad/alpine-gxx:latest`) must be pullable.
    -   Python standard libraries: `subprocess`, `tempfile`, `os`, `shutil`.

### Running the Server
To run the C++ MCP server, execute the following command from the project's root directory:
```bash
python mcp_cpp_server.py
```
The server will typically start on `http://127.0.0.1:8000`, and the MCP endpoint will be `/mcp` (so, `http://127.0.0.1:8000/mcp`).

**Port Conflict Note:** If you have other MCP servers (like the bash tool server described earlier) that also default to port 8000, you will need to configure one of them to use a different port or ensure only one is running at a time. This can often be done by modifying the `mcp_app.run()` call (e.g., `mcp_app.run(port=8001)`) or via uvicorn command-line options if running with uvicorn directly.

### **CRITICAL SECURITY WARNINGS**
1.  **Arbitrary Code Execution Risk:** The `execute_cpp` tool allows remote execution of C++ code. This is **EXTREMELY DANGEROUS**. Malicious C++ code can cause severe damage, data loss, or system compromise.
2.  **Sandboxing Layer (Docker):** The server uses Docker via `cpp_runner.py` to provide a layer of sandboxing for compilation and execution. This is a critical defense but relies on correct Docker configuration and up-to-date Docker versions.
3.  **MCP Server Authentication (Essential):** As with any powerful tool, this MCP server **MUST NOT** be exposed to untrusted networks or users without robust authentication and authorization implemented at the MCP level (e.g., using OAuth 2.0, as indicated by commented-out sections in `mcp_cpp_server.py`). Relying solely on the Docker sandbox is insufficient for a networked service.
4.  **Resource Limits:** The `cpp_runner.py` (and its underlying Docker calls) should enforce resource limits (CPU, memory, time). While default timeouts are set for compilation and execution within `cpp_runner.py`, ensure these are appropriate for your environment and consider that C++ code can be written to consume maximal resources within those timeouts.

### Interacting with the `execute_cpp` Tool
-   **Tool Name:** `execute_cpp` (as registered with the MCP server)
-   **Arguments:**
    -   `cpp_code` (str): The C++ source code snippet to be compiled and executed.
    -   `stdin_text` (str, optional): A string that will be provided as standard input to the C++ program during its execution phase. Defaults to `None` if not provided.
    -   `compiler_choice` (str, optional): Specifies the C++ compiler to use. Supported values are `"g++"` and `"clang++"`. Defaults to `"g++"` if not provided or if an empty/null string is passed.
-   **Return Value:** The tool returns a dictionary (via `tool_result.content` from the MCP client's perspective) containing detailed information from both the compilation and execution phases. The structure is:
    ```json
    {
        "compilation_stdout": "...", 
        "compilation_stderr": "...", 
        "compilation_exit_code": 0,
        "timed_out_compilation": false, 
        "execution_stdout": "...", 
        "execution_stderr": "...",
        "execution_exit_code": 0, 
        "timed_out_execution": false,
        "compiler_used": "g++" 
    }
    ```
    (Actual stdout/stderr content, exit codes, and `compiler_used` will vary based on the C++ code, its execution, and the chosen compiler.)
    The dictionary also includes a `compiler_used` field (e.g., `"g++"` or `"clang++"`) indicating the compiler that was actually invoked for the compilation.

-   **Conceptual Client Example:**
    ```python
    # Conceptual client example (assumes an MCP session 'session' is active)
    # See test_mcp_cpp_server.py for a runnable client example.

    cpp_source = """
    #include <iostream>
    #include <string>
    int main() {
        std::string name;
        std::cout << "Enter your name: "; // Prompt to stdout
        std::cin >> name; // Reads a single word
        std::cout << "Hello, " << name << "!" << std::endl;
        return 0;
    }
    """
    stdin_input = "Jules" # Input for std::cin

    # Example with default compiler (g++)
    # tool_result_gpp = await session.call_tool(
    #     "execute_cpp",
    #     {
    #         "cpp_code": cpp_source, 
    #         "stdin_text": stdin_input,
    #         # "compiler_choice": "g++" // or leave out for default
    #     }
    # )
    # if tool_result_gpp.success:
    #     print(f"Result with g++ (default): {tool_result_gpp.content}")
    #     # Expected output in tool_result_gpp.content would include:
    #     # ... "compiler_used": "g++" ...

    # Example with clang++
    # tool_result_clangpp = await session.call_tool(
    #     "execute_cpp",
    #     {
    #         "cpp_code": cpp_source, 
    #         "stdin_text": stdin_input,
    #         "compiler_choice": "clang++"
    #     }
    # )
    # if tool_result_clangpp.success:
    #     print(f"Result with clang++: {tool_result_clangpp.content}")
    #     # Expected output in tool_result_clangpp.content would include:
    #     # ... "compiler_used": "clang++" ...
    
    # if tool_result.success: # Generic handling, adapt as needed
    #     print("C++ execution successful (from MCP tool perspective)!")
    #     print("Result dictionary from cpp_runner:")
    #     # tool_result.content is the dictionary returned by run_cpp_code
    #     # print(tool_result.content) 
    #     # Expected output in tool_result.content for the g++ example:
    #     # {
    #     #     "compilation_stdout": "", 
    #     #     "compilation_stderr": "", 
    #     #     "compilation_exit_code": 0,
    #     #     "timed_out_compilation": False, 
    #     #     "execution_stdout": "Enter your name: Hello, Jules!\n", 
    #     #     "execution_stderr": "",
    #     #     "execution_exit_code": 0, 
    #     #     "timed_out_execution": False,
    #     #     "compiler_used": "g++"
    #     # }
    # else:
    #     print(f"MCP tool call failed: {tool_result.error_message}")
    ```
The `test_mcp_cpp_server.py` file contains functional integration tests that demonstrate client interaction with the `execute_cpp` tool.

## Chrome Webpage Screenshot MCP Server

### Overview
`mcp_chrome_server.py` implements an MCP server exposing a `capture_webpage` tool. Its purpose is to take a screenshot of a given URL using a headless Chrome browser (via Playwright) running in a sandboxed Docker environment.

### Core Execution Logic (`chrome_screenshot_taker.py` & `playwright_helper.py`)
`chrome_screenshot_taker.py` orchestrates the process, using Docker to run `playwright_helper.py`. `playwright_helper.py` is the script that executes inside Docker using Playwright to control headless Chrome. Docker and a Playwright-compatible image (e.g., `mcr.microsoft.com/playwright/python`) are key dependencies.

### Dependencies
-   **For the MCP server (`mcp_chrome_server.py`)**:
    -   The `mcp` Python package. Install with `pip install "mcp[cli]"`. This typically includes `uvicorn` for running the FastAPI-based server.
-   **For the core screenshot runner (`chrome_screenshot_taker.py`)**:
    -   **Docker**: Must be installed, running, and the user executing the script must have permissions to interact with the Docker daemon. The specified Docker image (e.g., `mcr.microsoft.com/playwright/python`) must be pullable.
    -   Python standard libraries: `subprocess`, `json`, `base64`, `os`.
    -   `playwright_helper.py` (and thus the Docker image) needs `playwright`.

### Running the Server
-   **Command:** `python mcp_chrome_server.py`
-   **Default URL:** Typically `http://127.0.0.1:8000/mcp`.
-   **Port Conflict Note:** If you have other MCP servers (like the bash or C++ tool servers described earlier) that also default to port 8000, you will need to configure one of them to use a different port or ensure only one is running at a time.
-   **Helper Script Location:** `playwright_helper.py` must be in the same directory as `chrome_screenshot_taker.py` for the latter to find and mount it into Docker.

### **CRITICAL SECURITY WARNINGS**
1.  **Arbitrary URL Fetching Risks:** The `capture_webpage` tool fetches and renders content from arbitrary URLs. This can expose the server to risks like Server-Side Request Forgery (SSRF), attempts to access internal network resources, or rendering malicious web content (JavaScript execution happens in the headless browser).
2.  **Browser Vulnerabilities:** Headless browsers, like any browser, can have vulnerabilities. Ensure the Docker image (e.g., `mcr.microsoft.com/playwright/python`) is kept up-to-date to include the latest browser security patches.
3.  **Sandboxing (Docker & Playwright):** The server uses Docker and Playwright's browser contexts to provide significant sandboxing. This is a critical defense layer. The `--network=host` option in `chrome_screenshot_taker.py` simplifies development but has security trade-offs; for production, a more restrictive network setup for the Docker container is advised.
4.  **MCP Server Authentication (Essential):** This tool **MUST NOT** be exposed to untrusted networks or users without robust authentication and authorization implemented at the MCP level (e.g., using OAuth 2.0, as indicated by commented-out sections in `mcp_chrome_server.py`).
5.  **Resource Consumption:** Fetching and rendering web pages can be resource-intensive (CPU, memory, network). Implement rate limiting or other controls if exposing this to multiple users.

### Interacting with the `capture_webpage` Tool
-   **Tool Name:** `capture_webpage`
-   **Arguments:**
    -   `url` (str): The URL of the webpage to screenshot.
    -   `width` (int, optional): Desired viewport width in pixels. Defaults to 1280.
    -   `height` (int, optional): Desired viewport height in pixels. Defaults to 720.
-   **Return Value (on Success):**
    -   An `mcp.types.Image` object. The image is in PNG format.
    -   The `Image` object has attributes like `data` (bytes of the PNG) and `format` (string, e.g., 'png').
-   **Return Value (on Failure):**
    -   If an error occurs (e.g., navigation timeout, invalid URL, screenshot process failure), the MCP tool call will result in `tool_result.success = False` and `tool_result.error` will be an `mcp.types.ToolError` object containing details.
    -   The `tool_result.error.message` field will provide more specific information about the failure.
-   **Conceptual Client Example:**
    ```python
    # Conceptual client example (assumes an MCP session 'session' is active)
    # See test_mcp_chrome_server.py for a runnable client example.
    # Ensure 'mcp' and 'httpx' packages are installed: pip install "mcp[cli]" httpx
    # from mcp import types # If you need to check isinstance(..., types.Image)

    target_url = "https://www.example.com"
    
    # tool_result = await session.call_tool(
    #     "capture_webpage",
    #     {"url": target_url, "width": 1024, "height": 768}
    # )
    
    # if tool_result.success:
    #     image_content = tool_result.content # This should be an mcp.types.Image object
    #     if isinstance(image_content, types.Image): # types from mcp
    #         print(f"Screenshot successful! Format: {image_content.format}, Data length: {len(image_content.data)}")
    #         # with open("mcp_screenshot.png", "wb") as f:
    #         #     f.write(image_content.data)
    #     else:
    #         print(f"Screenshot successful, but content is not an Image object: {type(image_content)}")
    # else:
    #     if tool_result.error:
    #         print(f"Screenshot failed: {tool_result.error.type} - {tool_result.error.message}")
    #     else:
    #         print("Screenshot failed with no error information.")
    ```
The `test_mcp_chrome_server.py` file contains functional integration tests that demonstrate client interaction with the `capture_webpage` tool.


## ADK Code Assistant (`adk_code_assistant.py`)

This repository also includes `adk_code_assistant.py`, which demonstrates how to build an AI agent using the [Agent Development Kit (ADK)](https://github.com/google/adk-python) that leverages all the MCP servers provided in this repository (`mcp_server.py`, `mcp_cpp_server.py`, `mcp_chrome_server.py`).

### Overview

The `adk_code_assistant.py` script defines an ADK `LlmAgent` configured to use the bash execution, C++ compilation/execution, and webpage screenshot capabilities as tools. This creates a "code assistant" that can understand natural language queries and utilize these tools to perform coding-related tasks.

### Prerequisites

Before running the ADK Code Assistant, ensure you have the following:

1.  **Python 3.9+**
2.  **Install ADK**:
    ```bash
    pip install google-adk
    ```
3.  **MCP Server Dependencies**: Each MCP server script (`mcp_server.py`, `mcp_cpp_server.py`, `mcp_chrome_server.py`) has its own dependencies (e.g., `mcp` package, Docker for C++ and Chrome tools). Ensure these are met as described in their respective sections earlier in this README. For example, you'll likely need:
    ```bash
    pip install "mcp[cli]" 
    ```
    And Docker must be installed and running if you intend for the C++ and Chrome screenshot tools to be functional.
4.  **Environment Setup (Optional but Recommended for Gemini models)**:
    If you are using a Gemini model with ADK (like the default 'gemini-2.0-flash' in the script), you might need to set up authentication for Google Cloud and potentially Vertex AI. Refer to the [ADK documentation](https://google.github.io/adk-docs/) for the latest guidance on authentication and model configuration. Typically, this might involve:
    ```bash
    gcloud auth application-default login
    ```
    And setting your project ID:
    ```bash
    # Example:
    # export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    # export GOOGLE_GENAI_USE_VERTEXAI="True" 
    # export GOOGLE_CLOUD_LOCATION="your-gcp-region" # e.g., us-central1
    ```
    Consult the ADK documentation for specific environment variables and setup based on your chosen model and execution environment.

### Running the ADK Code Assistant

1.  Navigate to the root directory of this repository.
2.  Run the script:
    ```bash
    python3 adk_code_assistant.py
    ```

The script will:
*   Attempt to initialize `MCPToolset` for each of the three MCP server scripts. This involves ADK starting these server scripts as subprocesses.
*   Print diagnostic information about the tools loaded from each MCP server.
*   Define the `code_assistant` agent.
*   The `if __name__ == '__main__':` block in the script currently runs a test creation sequence that prints details of the loaded agent and its tools. It also includes commented-out conceptual code showing how you might use `adk.runners.Runner` to interact with the agent.

### How it Works

The `adk_code_assistant.py` script uses `MCPToolset.from_server` with `StdioServerParameters`. This means ADK launches the `mcp_server.py`, `mcp_cpp_server.py`, and `mcp_chrome_server.py` scripts as background processes and communicates with them over their standard input/output. The tools discovered from these MCP servers are then provided to the ADK `LlmAgent`.

### Customization

*   **Model**: You can change the LLM model used by the agent by modifying the `model` parameter in the `LlmAgent` instantiation within `adk_code_assistant.py`. Ensure the model you choose is compatible with your ADK setup and authentication.
*   **Instructions**: The agent's behavior can be further customized by modifying the `instruction` prompt provided to the `LlmAgent`.
*   **Tool Usage**: To actually interact with the agent (e.g., send it a query like "run ls -l"), you would typically use the `adk.runners.Runner` class as shown in the conceptual comments within `adk_code_assistant.py`, or by deploying/serving this agent using ADK's deployment options (like `adk web` or Agent Engine).

**Security Note**: Remember the security warnings associated with each MCP server, especially `mcp_server.py` (bash execution) and `mcp_cpp_server.py` (C++ execution). While `adk_code_assistant.py` runs them as local subprocesses managed by ADK, if you adapt this setup to expose the ADK agent or the MCP servers more broadly, ensure appropriate security measures are in place.
