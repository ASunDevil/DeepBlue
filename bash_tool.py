import subprocess
import shlex
import os

def run_bash_command(command: str, timeout: int = 60, working_directory: str = None) -> dict:
    """
    Executes a bash command and returns its output, error, exit code, and timeout status.

    Args:
        command: The bash command to execute.
        timeout: Maximum time (in seconds) to wait for the command to complete. Defaults to 60.
        working_directory: The directory in which to execute the command. Defaults to the current working directory.

    Returns:
        A dictionary containing:
            - stdout: Standard output of the command.
            - stderr: Standard error output of the command.
            - exit_code: Exit code of the command.
            - timed_out: Boolean indicating whether the command timed out.
    """
    if working_directory is None:
        working_directory = os.getcwd()

    # For security, if the command is a string, split it into a sequence using shlex.
    # This helps prevent shell injection if the command string were to be constructed from untrusted input.
    # However, the primary design assumes the MCP/developer provides the command.
    if isinstance(command, str):
        cmd_parts = shlex.split(command)
    else:
        # If it's already a list, use it as is. This might be useful if the caller
        # has already tokenized the command safely.
        cmd_parts = command

    if not cmd_parts: # Handle empty command after shlex.split or if an empty list was passed
        return {
            "stdout": "",
            "stderr": "Error: Empty command provided.",
            "exit_code": -1, # Or a specific code for empty command
            "timed_out": False,
        }

    try:
        process = subprocess.Popen(
            cmd_parts,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Decode stdout/stderr as text
        )
        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate() # Get whatever output was captured before timeout
        exit_code = -1  # Or some other indicator of timeout
        timed_out = True
        stderr = f"Command timed out after {timeout} seconds.\n{stderr}"
    except FileNotFoundError:
        stdout = ""
        stderr = f"Error: Command or executable not found: {cmd_parts[0] if cmd_parts else ''}"
        exit_code = -1 # Or use a specific code like 127 for "command not found"
        timed_out = False
    except Exception as e:
        stdout = ""
        stderr = f"An unexpected error occurred: {str(e)}"
        exit_code = -1 # Generic error
        timed_out = False

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
    }
