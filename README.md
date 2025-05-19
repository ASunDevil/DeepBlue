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
