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
