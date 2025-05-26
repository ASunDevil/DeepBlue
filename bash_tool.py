import subprocess
import shlex
import os
from datetime import datetime
import traceback

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
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering run_bash_command with command='{command}', timeout={timeout}, working_directory='{working_directory}'")
    if working_directory is None:
        working_directory = os.getcwd()
        print(f"DEBUG: [%{datetime.now().isoformat()}] working_directory defaulted to: {working_directory}")

    # For security, if the command is a string, split it into a sequence using shlex.
    # This helps prevent shell injection if the command string were to be constructed from untrusted input.
    # However, the primary design assumes the MCP/developer provides the command.
    if isinstance(command, str):
        cmd_parts = shlex.split(command)
    else:
        # If it's already a list, use it as is. This might be useful if the caller
        # has already tokenized the command safely.
        cmd_parts = command
    print(f"DEBUG: [%{datetime.now().isoformat()}] Executing command parts: {cmd_parts}")

    if not cmd_parts: # Handle empty command after shlex.split or if an empty list was passed
        result_dict = {
            "stdout": "",
            "stderr": "Error: Empty command provided.",
            "exit_code": -1, # Or a specific code for empty command
            "timed_out": False,
        }
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_bash_command (empty command) with result: {result_dict}")
        return result_dict

    try:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Attempting to Popen: {cmd_parts} in {working_directory}")
        process = subprocess.Popen(
            cmd_parts,
            cwd=working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Decode stdout/stderr as text
        )
        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode
        print(f"DEBUG: [%{datetime.now().isoformat()}] Popen communicate completed. exit_code: {process.returncode}")
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate() # Get whatever output was captured before timeout
        exit_code = -1  # Or some other indicator of timeout
        timed_out = True
        stderr = f"Command timed out after {timeout} seconds.\n{stderr}"
        print(f"DEBUG: [%{datetime.now().isoformat()}] Command timed out. stderr: {stderr}")
    except FileNotFoundError:
        stdout = ""
        stderr = f"Error: Command or executable not found: {cmd_parts[0] if cmd_parts else ''}"
        print(f"DEBUG: [%{datetime.now().isoformat()}] FileNotFoundError. cmd_parts[0]: {cmd_parts[0] if cmd_parts else 'N/A'}, stderr: {stderr}")
        exit_code = -1 # Or use a specific code like 127 for "command not found"
        timed_out = False
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] An unexpected exception occurred: {e}\nTraceback:\n{formatted_traceback}")
        stdout = ""
        stderr = f"An unexpected error occurred: {type(e).__name__} - {str(e)}"
        exit_code = -1 # Generic error
        timed_out = False

    result_dict = {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
    }
    print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_bash_command with result: {result_dict}")
    return result_dict
