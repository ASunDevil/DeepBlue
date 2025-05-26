from typing import Union # For Python 3.9+ compatibility with str | None
from datetime import datetime
import traceback

# Attempt to import FastMCP and Context, and install if missing
try:
    from mcp.server.fastmcp import FastMCP, Context
except ImportError:
    print("MCP package not found. Attempting to install 'mcp[cli]'...")
    import subprocess
    import sys
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]"])
        from mcp.server.fastmcp import FastMCP, Context
        print("MCP package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install mcp: {e}")
        print("Please install it manually using: pip install \"mcp[cli]\"")
        sys.exit(1)
    except ImportError:
        print("Failed to import FastMCP or Context even after attempting installation.")
        print("Please ensure 'mcp[cli]' is installed and accessible.")
        sys.exit(1)

# Potentially: from mcp.server.auth import AuthSettings #, OAuthServerProvider (though provider needs implementation)
from bash_tool import run_bash_command

# !!! SECURITY WARNING !!!
# The following server exposes a tool (`execute_bash`) that can run arbitrary shell commands.
# This is EXTREMELY DANGEROUS if exposed without strong authentication and authorization.
# The MCP SDK provides OAuth 2.0 capabilities that SHOULD be implemented and configured
# before deploying such a tool in any sensitive environment.

# Example (Conceptual - Requires actual OAuthServerProvider implementation and AuthSettings):
# from my_oauth_provider import MyCustomOAuthServerProvider # This would be your implementation
# from mcp.server.auth import AuthSettings
# auth_settings = AuthSettings(
#     issuer_url="https_your_auth_server_com", # e.g., "https://accounts.google.com" or your Keycloak, Auth0 URL
#     required_scopes=["bash_tool_access"], # Define scopes for your tool
#     # audience="your_api_identifier" # Optional: if your auth server uses audiences
# )
# mcp_app = FastMCP(
#     name="BashToolServer",
#     description="MCP Server for executing bash commands. REQUIRES AUTHENTICATION.",
#     auth_server_provider=MyCustomOAuthServerProvider(), # Your provider instance
#     auth=auth_settings
# )

# Current implementation (UNSECURED without the above auth setup):
mcp_app = FastMCP(
    name="BashToolServer",
    description="MCP Server for executing bash commands. WARNING: CURRENTLY UNSECURED."
)


@mcp_app.tool()
def execute_bash(ctx: Context, command: str, timeout: int = 60, working_directory: Union[str, None] = None) -> dict:
    """
    Executes a given bash command using the run_bash_command tool and returns its output.

    This tool allows for the execution of arbitrary bash commands on the server.
    It captures standard output, standard error, the exit code, and timeout status.
    Execution is logged via the provided context.

    Args:
        ctx: The MCP Context object, used for logging.
        command: The bash command string to execute. (e.g., "ls -l", "echo 'Hello World'")
        timeout: Optional. The maximum time in seconds to wait for the command to complete.
                 If the command runs longer, it will be terminated. Defaults to 60 seconds.
        working_directory: Optional. The directory in which to execute the command.
                           If not specified (None), the command will be run in the
                           current working directory of the server process.
                           (e.g., "/tmp", "./my_project_dir")

    Returns:
        A dictionary containing the execution details:
        - stdout (str): The standard output captured from the command.
        - stderr (str): The standard error captured from the command. This includes
                        errors from the command itself or messages from the tool
                        (e.g., timeout notifications, command not found).
        - exit_code (int): The exit code of the command. '0' typically means success.
                           Non-zero values indicate errors. '-1' is used by the underlying
                           tool for specific errors like timeout or command not found.
        - timed_out (bool): True if the command execution exceeded the 'timeout' value
                            and was terminated, False otherwise.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering execute_bash tool with command='{command}', timeout={timeout}, working_directory='{working_directory}'")
    # Log the attempt to execute the command using the context.
    # Caller information might be available in ctx depending on MCP server setup and auth.
    # For now, we log the command details.
    ctx.info(f"Attempting to execute bash command: {{'command': '{command}', 'timeout': {timeout}, 'working_directory': '{working_directory}'}}")

    # The run_bash_command function from bash_tool.py already handles
    # working_directory=None by defaulting to the current working directory.
    print(f"DEBUG: [%{datetime.now().isoformat()}] Calling run_bash_command with command='{command}', timeout={timeout}, working_directory='{working_directory}'")
    result = run_bash_command(command=command, timeout=timeout, working_directory=working_directory)
    print(f"DEBUG: [%{datetime.now().isoformat()}] run_bash_command returned: {result}")

    # Log the outcome
    ctx.info(f"Command execution result: {{'exit_code': {result['exit_code']}, 'timed_out': {result['timed_out']}}}")

    print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting execute_bash tool with result: {result}")
    return result

# Main block to run the server
if __name__ == "__main__":
    print(f"DEBUG: [%{datetime.now().isoformat()}] Starting BashToolServer MCP server...")
    # The mcp_app.run() method typically starts a Uvicorn server for development.
    # Ensure 'uvicorn' and 'fastapi' are installed as dependencies of 'mcp[cli]'.
    try:
        mcp_app.run()
    except ImportError as e:
        print(f"DEBUG: [%{datetime.now().isoformat()}] ImportError during server run: {e}")
        print(f"Error running server: {e}")
        print("Make sure 'uvicorn' is installed. It should be a dependency of 'mcp[cli]'.")
        print("You might need to run: pip install \"mcp[cli]\" uvicorn")
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] An unexpected exception occurred during server run: {e}\nTraceback:\n{formatted_traceback}")
        print(f"An unexpected error occurred while trying to run the server: {e}")
