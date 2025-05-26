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

## Langflow Code Critique MCP Server

### Overview
`mcp_langflow_critique_server.py` implements an MCP server that exposes a `critique_code` tool. This tool leverages a user-configured Langflow agent to provide AI-powered critiques of code snippets. The critique typically covers aspects like code quality, style, potential bugs, and suggestions for improvements.

### Core Logic
The server acts as a bridge between the ADK Code Assistant (or any MCP client) and a Langflow agent.
1.  The `mcp_langflow_critique_server.py` receives a code snippet.
2.  It forwards this code to a specified Langflow API endpoint.
3.  The Langflow agent at that endpoint processes the code and generates a critique.
4.  The server returns this critique to the client.

### Dependencies
-   **For the MCP server (`mcp_langflow_critique_server.py`)**:
    -   The `mcp` Python package. Install with `pip install "mcp[cli]"`.
    -   The `requests` package for making HTTP calls to the Langflow API. Install with `pip install requests`.
-   **For the Langflow Agent**:
    -   A running Langflow instance.
    -   A deployed Langflow agent/flow designed for code critique, exposed as an API endpoint.

### Setup and Configuration

1.  **Set up your Langflow Agent for Code Critique:**
    *   You need to design and deploy a flow within Langflow that is capable of receiving code as input and outputting a textual critique.
    *   **For detailed guidance on designing such an agent in Langflow, please refer to the `code_critique_agent_design.md` file in this repository.** This document outlines the recommended components, prompt design, and expected API interaction for the Langflow agent.
    *   Once your Langflow agent is ready, ensure it is deployed and accessible via an API endpoint.

2.  **Configure the API Endpoint for the MCP Server:**
    *   The `mcp_langflow_critique_server.py` needs to know the URL of your Langflow agent's API endpoint.
    *   This is configured using the `LANGFLOW_CRITIQUE_API_URL` environment variable.
    *   **Example:**
        ```bash
        export LANGFLOW_CRITIQUE_API_URL="http://your-langflow-instance:7860/api/v1/run/your_critique_flow_id"
        ```
    *   If this environment variable is not set, the server will use a default placeholder URL: `http://localhost:7860/api/v1/run/your_langflow_agent_id`. You **must** replace this with your actual endpoint for the tool to function.

### Running the Server
-   **Command:** `python mcp_langflow_critique_server.py`
-   **Default URL:** Typically `http://127.0.0.1:8000/mcp` (if not conflicting with other MCP servers).
-   **Port Conflict Note:** If you have other MCP servers (like the bash, C++, or Chrome tool servers) that also default to port 8000, you will need to configure one of them to use a different port or ensure only one is running at a time.

### **IMPORTANT NOTES**
1.  **Langflow Agent Quality:** The quality and usefulness of the code critique depend entirely on the design and capabilities of your Langflow agent.
2.  **API Security:** If your Langflow instance or API endpoint requires authentication, you may need to modify `mcp_langflow_critique_server.py` (specifically the `run_tool` function) to include necessary authentication headers in the `requests.post` call.
3.  **Error Handling:** The server includes basic error handling for API calls (network issues, timeouts, bad responses). Check the server's console output (stderr) for diagnostic messages.

### Interacting with the `critique_code` Tool
-   **Tool Name:** `critique_code`
-   **Arguments:**
    -   `code_to_critique` (str): The code snippet to be critiqued.
-   **Return Value (on Success):**
    -   A string containing the textual critique generated by the Langflow agent.
-   **Return Value (on Failure):**
    -   If an error occurs (e.g., Langflow API unreachable, misconfiguration), the MCP tool call will result in `tool_result.success = False` and `tool_result.error` will be an `mcp.types.ToolError` object containing details.
-   **Conceptual Client Example:**
    ```python
    # Conceptual client example (assumes an MCP session 'session' is active)
    # See test_mcp_langflow_critique_server.py for runnable client unit tests.

    code_snippet = "def foo(n):\\n    if n % 2 == 0\\n        print('even')\\n    else:\\n        print('odd')"
    
    # tool_result = await session.call_tool(
    #     "critique_code",
    #     {"code_to_critique": code_snippet}
    # )
    
    # if tool_result.success:
    #     critique_text = tool_result.content 
    #     print("Critique Received:")
    #     print(critique_text)
    # else:
    #     if tool_result.error:
    #         print(f"Critique failed: {tool_result.error.type} - {tool_result.error.message}")
    #     else:
    #         print("Critique failed with no error information.")
    ```
Unit tests for this server are available in `test_mcp_langflow_critique_server.py`.

## ADK Code Assistant (`adk_code_assistant.py`)

This repository also includes `adk_code_assistant.py`, which demonstrates how to build an AI agent using the [Agent Development Kit (ADK)](https://github.com/google/adk-python). This agent leverages all the MCP servers provided in this repository (`mcp_server.py` for bash, `mcp_cpp_server.py` for C++) and also integrates the official [GitHub MCP Server](https://github.com/github/github-mcp-server) for interacting with GitHub APIs.

### Overview

The `adk_code_assistant.py` script defines an ADK `LlmAgent`. This agent is configured to use a variety of tools:
*   Bash command execution (via `mcp_server.py`).
*   C++ code compilation and execution (via `mcp_cpp_server.py`).
*   Webpage screenshot capture (via `mcp_chrome_server.py`).
*   **Code critique via Langflow** (via `mcp_langflow_critique_server.py`).
*   GitHub interactions (via `ghcr.io/github/github-mcp-server`), such as reading files, listing issues, and more.

This creates a versatile "code assistant" that can understand natural language queries and utilize these tools to perform a wide range of coding-related tasks, including code analysis, repository management, and information retrieval from GitHub.

### Prerequisites

Before running the ADK Code Assistant, ensure you have the following:

1.  **Python 3.9+**
2.  **Install ADK**:
    ```bash
    pip install google-adk
    ```
3.  **Local MCP Server Dependencies**: 
    *   Each local MCP server script (`mcp_server.py`, `mcp_cpp_server.py`, `mcp_chrome_server.py`, `mcp_langflow_critique_server.py`) has its own dependencies (e.g., `mcp` package for all, Docker for C++ and Chrome tools, `requests` for Langflow). Ensure these are met as described in their respective sections earlier in this README.
    *   You'll likely need: `pip install "mcp[cli]" requests`.
    *   Docker must be installed and running for the C++ and Chrome screenshot tools to be functional.
4.  **Langflow Code Critique Server Prerequisites**:
    *   A running Langflow instance with a configured code critique agent exposed as an API.
    *   The `LANGFLOW_CRITIQUE_API_URL` environment variable must be set to point to your Langflow agent's API endpoint. See the "Langflow Code Critique MCP Server" section for details.
5.  **GitHub MCP Server Prerequisites**:
    *   **Docker**: Must be installed and running, and able to pull images from `ghcr.io`.
    *   **GitHub Personal Access Token (PAT)**: You need a GitHub PAT with appropriate permissions (e.g., `repo` for accessing repositories, `issues:read`, `user:read`). This token must be made available as an environment variable:
        ```bash
        export GITHUB_TOKEN="your_github_personal_access_token_here"
        ```
        The `adk_code_assistant.py` script will pass this token to the GitHub MCP Server process.
5.  **Environment Setup for ADK/Gemini (Optional but Recommended)**:
    If you are using a Gemini model with ADK (like the default 'gemini-2.0-flash' in the script), you might need to set up authentication for Google Cloud and potentially Vertex AI. Refer to the [ADK documentation](https://google.github.io/adk-docs/) for guidance. Typically, this might involve:
    ```bash
    gcloud auth application-default login
    # export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    # export GOOGLE_GENAI_USE_VERTEXAI="True" 
    # export GOOGLE_CLOUD_LOCATION="your-gcp-region"
    ```

### Running the ADK Code Assistant

1.  Ensure all prerequisites above are met, especially setting the `GITHUB_TOKEN` environment variable if you want GitHub tools to be available.
2.  Navigate to the root directory of this repository.
3.  Run the script:
    ```bash
    python3 adk_code_assistant.py
    ```

The script will:
*   Attempt to initialize `MCPToolset` for each of the local MCP server scripts (bash, C++, Chrome, Langflow critique).
*   If `GITHUB_TOKEN` is set, attempt to initialize `MCPToolset` for the `github-mcp-server` Docker container.
*   Print diagnostic information about all tools loaded.
*   Define the `code_assistant` agent with all available tools, including `critique_code` if the Langflow server is set up.
*   The `if __name__ == '__main__':` block runs a test creation sequence, printing details of the agent and its tools. It also includes conceptual comments on using ADK's `Runner` for actual interaction.

### How it Works

The `adk_code_assistant.py` script uses `MCPToolset.from_server` with `StdioServerParameters`. 
*   For local servers (`mcp_server.py`, `mcp_cpp_server.py`, `mcp_chrome_server.py`, `mcp_langflow_critique_server.py`), ADK launches these Python scripts as background processes.
*   For the GitHub MCP Server, ADK launches a `docker run ... ghcr.io/github/github-mcp-server` command as a background process, passing the `GITHUB_TOKEN` to it.
ADK then communicates with all these MCP server processes over their standard input/output. The tools discovered are provided to the ADK `LlmAgent`.

### Using with Dify Agent Framework (Optional)

The `adk_code_assistant.py` script can optionally use [Dify](https://dify.ai/) as its agent framework instead of the default ADK LlmAgent. This allows leveraging Dify's platform features, including its agent orchestration, plugin management, and API.

#### Configuration for Dify Mode

To run the assistant in Dify mode, you need to configure the following environment variables:

1.  **`AGENT_FRAMEWORK`**: Set this to `dify`.
    ```bash
    export AGENT_FRAMEWORK="dify"
    ```
    If this variable is not set or set to `adk`, the assistant will default to using the ADK LlmAgent.

2.  **`DIFY_API_URL`**: The base API URL of your Dify instance.
    *   For Dify Cloud, this is typically `https://api.dify.ai/v1` (or just `https://api.dify.ai` and the client will append `/v1`).
    *   For self-hosted instances, it might be like `http://your-dify-domain/api/v1` or `http://your-dify-domain/v1` depending on your setup. The client in `adk_code_assistant.py` currently appends `/v1/chat-messages` to this base URL.
    ```bash
    export DIFY_API_URL="your_dify_api_base_url"
    ```

3.  **`DIFY_API_KEY`**: The API key for your Dify application (Agent).
    ```bash
    export DIFY_API_KEY="your_dify_application_api_key"
    ```

#### Dify Tools Plugin (`dify_adk_tools_plugin`)

When running in Dify mode, the assistant interacts with a Dify Agent. For this Dify Agent to use the familiar tools from this repository (like bash execution, C++ execution, etc.), these tools must be made available to Dify as **custom Dify plugins**.

This repository includes the generated source code for a proof-of-concept Dify plugin (`adk_tools_provider.yaml`, `tools/execute_bash_tool.yaml`, `tools/bash_tool_dify.py`) that wraps the bash execution functionality. The worker would have printed these file contents when it created the PoC Dify tool. You would need to take that output and create the actual plugin files and directory structure.

**To use the Dify mode effectively:**

1.  **Create and Deploy Dify Plugins:** You will need to take the provided tool wrapper code (like the bash tool PoC and eventually wrappers for other tools like C++, Python execution, etc.) and package them into a Dify plugin structure. This plugin (e.g., named `dify_adk_tools_plugin`) then needs to be deployed to your Dify instance. Refer to the Dify documentation on plugin development and deployment. The Python code within these Dify plugins calls the original Python functions from this project (e.g., `bash_tool.run_bash_command`).
2.  **Configure Dify Agent:** In your Dify platform, create an Agent application and configure it to use the deployed `dify_adk_tools_plugin` (or however you name it) and enable the specific tools (e.g., `execute_bash`). Ensure the Dify agent's prompts are set up to correctly utilize these tools.

#### Running in Dify Mode

Once the environment variables are set and your Dify agent is configured with the necessary tools plugin:

1.  Navigate to the root directory of this repository.
2.  Run the script:
    ```bash
    python3 adk_code_assistant.py
    ```
The script will detect `AGENT_FRAMEWORK="dify"` and attempt to connect to your Dify agent. You can then interact with it via the command line. The `adk_code_assistant.py` script will show "You (Dify): " when prompting for input.

**Note:** The integration currently provides a client for chat interactions with a Dify agent and a proof-of-concept for one tool (bash). Implementing Dify plugin wrappers for all other tools (C++, Python, Go, web capture, RAG) is a future step to achieve full feature parity in Dify mode.

### How the Code Critique Tool is Used by the Agent
If the `mcp_langflow_critique_server.py` is running and correctly configured with the `LANGFLOW_CRITIQUE_API_URL`, the `adk_code_assistant` will automatically have access to a `critique_code` tool. The agent's instruction prompt has been updated to inform it of this capability. You can then ask the assistant to critique code snippets as part of your interaction.

### Customization

*   **Model**: You can change the LLM model used by the agent by modifying the `model` parameter in `LlmAgent` within `adk_code_assistant.py`.
*   **Instructions**: The agent's behavior can be further customized by modifying the `instruction` prompt. The current prompt includes mention of GitHub capabilities.
*   **Tool Usage**: To interact with the agent, use ADK's `Runner` class (see conceptual comments in the script) or deploy the agent using options like `adk web` or Agent Engine.
*   **GitHub Toolsets**: The `github-mcp-server` can be configured to load only specific sets of tools (e.g., only 'repos' and 'issues'). This can be done by modifying the `docker run` arguments in `adk_code_assistant.py` to pass the `GITHUB_TOOLSETS` environment variable to the container (e.g., adding `'-e'`, `'GITHUB_TOOLSETS=repos,issues'` to the `args` list and also to the `env` dict for `StdioServerParameters`).

**Security Note**: 
*   Remember the security warnings for each local MCP server (bash, C++ execution). 
*   For the GitHub MCP Server, be mindful of the permissions granted to your `GITHUB_TOKEN`. The agent will be able to perform actions on GitHub with the same permissions as the token. Use a token with the minimum necessary privileges.
While `adk_code_assistant.py` runs these as local subprocesses, broader exposure of the ADK agent or underlying MCP servers requires careful security considerations.

### Testing the ADK Code Assistant

Unit and basic integration tests for the ADK Code Assistant are provided in `test_adk_code_assistant.py`. These tests use Python's built-in `unittest` framework and `unittest.mock` to verify the agent creation logic and the integration of mocked tools, including mocked GitHub tools.

**Prerequisites for Testing:**

*   Ensure `google-adk` is installed:
    ```bash
    pip install google-adk
    ```
*   No external services (like live MCP servers, Docker, or a live `GITHUB_TOKEN`) are required to run these specific tests as they rely on mocking.

**Running the Tests:**

To run the tests, navigate to the root directory of the repository and execute:
```bash
python3 -m unittest test_adk_code_assistant.py
```
Or directly:
```bash
python3 test_adk_code_assistant.py
```
The tests will print output indicating the status of each test case and a summary.


---
<br/>

## Node.js Dynamic Site Generator

This suite of tools provides components to generate a basic Node.js dynamic web application structure using Express.js and EJS templates. It includes a project scaffolder, a text-to-route generator, and an EJS view generator. Unit tests are provided for each component.

### Core Components

1.  **Project Structure Generator (`generate_project.js`)**
    *   **Purpose:** Scaffolds a new Node.js project with a predefined structure.
    *   **Usage:**
        ```bash
        node generate_project.js <projectName>
        ```
        Replace `<projectName>` with your desired project name (e.g., `my-new-app`).
    *   **Generated Structure Example** (for `node generate_project.js my-new-app`):
        ```
        my-new-app/
        ├── app.js
        ├── package.json
        ├── public/
        │   ├── css/
        │   │   └── style.css
        │   └── js/
        │       └── main.js
        └── views/
            └── index.ejs
        ```
    *   **Details:**
        *   `app.js`: Contains a basic Express server setup, configured to use EJS as the view engine and serve static files from the `public` directory. Includes a default route `/` that renders `views/index.ejs`.
        *   `package.json`: Includes `express` and `ejs` as dependencies and a basic `start` script.
        *   `public/`: For static assets. `css/style.css` and `js/main.js` are created as placeholders.
        *   `views/`: For EJS templates. `index.ejs` is a sample welcome page.

2.  **Route Parser (`route_parser.js`)**
    *   **Purpose:** Generates Express.js route definition code from a specific textual command.
    *   **Function:** `parseRouteText(routeDescription)` (exported from `route_parser.js`)
    *   **Input String Format:**
        `CREATE <HTTP_METHOD> ROUTE FOR <PATH> THAT RENDERS EJS VIEW <VIEW_NAME> AND PASSES TITLE VARIABLE '<TITLE_VALUE>'`
    *   **Example Input:**
        ```
        CREATE GET ROUTE FOR /products THAT RENDERS EJS VIEW product-list AND PASSES TITLE VARIABLE 'Product List Page'
        ```
    *   **Example Output (JavaScript code string):**
        ```javascript
        app.get('/products', (req, res) => {
          res.render('product-list', { title: 'Product List Page' });
        });
        ```
    *   **Supported Methods:** GET, POST, PUT, DELETE. Returns an error message for invalid formats or unsupported methods.

3.  **EJS View Generator (`view_generator.js`)**
    *   **Purpose:** Generates basic EJS view files.
    *   **Function:** `generateEjsView(viewName, headingText)` (exported from `view_generator.js`)
        *   Note: While `headingText` is a parameter, the current implementation primarily uses a passed-in `title` variable (e.g., `<%= title %>`) within the EJS template for the main heading and HTML title.
    *   **Action:** Creates a `<viewName>.ejs` file inside a `views` directory (creates the directory if it doesn't exist).
    *   **Example Generated Content for `generateEjsView('user-profile', ...)` (file: `views/user-profile.ejs`):**
        ```html
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title><%= title %></title>
            <link rel="stylesheet" href="/css/style.css">
        </head>
        <body>
            <h1><%= title %></h1>
            <p>This is the <%= title %> page.</p>
            <script src="/js/main.js"></script>
        </body>
        </html>
        ```

### Running the Unit Tests

Each component comes with unit tests using Node.js's built-in `assert` module. To run them, navigate to the project root and execute:

*   For the project generator:
    ```bash
    node generate_project.test.js
    ```
*   For the route parser:
    ```bash
    node route_parser.test.js
    ```
*   For the view generator:
    ```bash
    node view_generator.test.js
    ```
These tests verify the core functionalities and include cleanup for any files or directories created during the test runs.

---
