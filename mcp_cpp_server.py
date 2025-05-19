# !!! EXTREMELY DANGEROUS - FOR DEVELOPMENT AND TESTING ONLY !!!
#
# This MCP server exposes a tool (`execute_cpp`) that allows for the compilation
# and execution of arbitrary C++ code. While the `cpp_runner.py` module attempts
# to sandbox this execution using Docker, providing such a powerful capability
# remotely is inherently very risky.
#
# DO NOT EXPOSE THIS SERVER TO UNTRUSTED NETWORKS OR USERS
# WITHOUT IMPLEMENTING AND VERIFYING ROBUST AUTHENTICATION, AUTHORIZATION,
# AND POSSIBLY FURTHER SANDBOXING OR RESOURCE LIMITATIONS.
#
# Failure to secure this server properly can lead to:
# - Arbitrary code execution on the host system if Docker sandboxing is bypassed.
# - Denial-of-service attacks by consuming excessive CPU, memory, or disk space.
# - Exposure of sensitive information if the executed C++ code interacts with the network
#   or mounted volumes in unexpected ways.
#
# The MCP SDK provides OAuth 2.0 capabilities that SHOULD be implemented.
# Consider this file a template for a highly privileged tool that requires
# maximum security scrutiny.

from typing import Union, Dict, Any # For type hinting

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
from cpp_runner import run_cpp_code # Assuming cpp_runner.py is in the same directory

# Conceptual Authentication Setup (Similar to mcp_server.py for bash tool)
# from my_oauth_provider import MyCustomOAuthServerProvider # This would be your implementation
# from mcp.server.auth import AuthSettings
# auth_settings = AuthSettings(
#     issuer_url="https_your_auth_server_com",
#     required_scopes=["cpp_execution_scope"], # Define specific scopes
# )
# mcp_app = FastMCP(
#     name="CppExecutionServer",
#     description="MCP Server for C++ code execution. REQUIRES AUTHENTICATION.",
#     auth_server_provider=MyCustomOAuthServerProvider(),
#     auth=auth_settings
# )

# Current UNSECURED implementation:
mcp_app = FastMCP(
    name="CppExecutionServer",
    description="MCP Server for compiling and executing C++ code. WARNING: EXTREMELY DANGEROUS IF NOT SECURED."
)

@mcp_app.tool()
def execute_cpp(ctx: Context, cpp_code: str, stdin_text: Union[str, None] = None, compiler_choice: Union[str, None] = "g++") -> Dict[str, Any]:
    """
    Compiles and executes a given snippet of C++ code in a sandboxed Docker environment,
    allowing selection between g++ and clang++.

    The C++ code is compiled using the chosen compiler (e.g., -std=c++17) and run.
    Only the C++ Standard Library is typically available, limited by the Docker image used
    in `cpp_runner.py` (ubuntu:22.04, which has g++ and clang installed by the script).

    Args:
        ctx: The MCP Context object, used for logging.
        cpp_code: A string containing the C++ source code to compile and run.
        stdin_text: Optional. A string to be provided as standard input to the C++ program.
        compiler_choice: Optional. The C++ compiler to use. Supported values are "g++"
                         (default) and "clang++". If None or an empty string is provided,
                         it defaults to "g++".

    Returns:
        A dictionary containing detailed results from the compilation and execution phases,
        including stdout, stderr, exit codes, timeout statuses for both, and the
        `compiler_used`.
        Example: {
            "compilation_stdout": "...", "compilation_stderr": "...", "compilation_exit_code": 0,
            "timed_out_compilation": False, "execution_stdout": "...", "execution_stderr": "...",
            "execution_exit_code": 0, "timed_out_execution": False, "compiler_used": "g++"
        }
    """
    selected_compiler = compiler_choice if compiler_choice and compiler_choice.strip() else "g++"

    # Log the request, being mindful of potentially large cpp_code.
    code_preview = cpp_code[:100] + "..." if len(cpp_code) > 100 else cpp_code
    ctx.info(
        f"Attempting to execute C++ code. "
        f"Compiler: {selected_compiler}, "
        f"stdin_text provided: {stdin_text is not None}. "
        f"Code preview: '{code_preview}'"
    )

    # Call the cpp_runner function. Default timeouts from cpp_runner are used unless overridden.
    result = run_cpp_code(
        cpp_code=cpp_code,
        stdin_data=stdin_text,
        compiler=selected_compiler
    )

    # The 'compiler_used' field is already in the result from run_cpp_code
    ctx.info(
        f"C++ execution task completed. "
        f"Compiler used: {result.get('compiler_used')}, "
        f"Compilation exit: {result.get('compilation_exit_code')}, "
        f"Execution exit: {result.get('execution_exit_code')}, "
        f"Compilation timeout: {result.get('timed_out_compilation')}, "
        f"Execution timeout: {result.get('timed_out_execution')}"
    )
    return result

# Main block to run the server
if __name__ == "__main__":
    print("Starting CppExecutionServer MCP server...")
    print("!!! WARNING: This server is EXTREMELY DANGEROUS if not properly secured. For development/testing ONLY. !!!")
    # The mcp_app.run() method typically starts a Uvicorn server for development.
    # Ensure 'uvicorn' and 'fastapi' are installed as dependencies of 'mcp[cli]'.
    try:
        mcp_app.run() # Default host="127.0.0.1", port=8000
    except ImportError as e:
        if "uvicorn" in str(e).lower():
            print(f"Error running server: {e}")
            print("Make sure 'uvicorn' is installed. It should be a dependency of 'mcp[cli]'.")
            print("You might need to run: pip install \"mcp[cli]\" uvicorn")
        else:
            print(f"An import error occurred: {e}. Ensure 'mcp[cli]' and its dependencies are installed.")
    except Exception as e:
        print(f"An unexpected error occurred while trying to run the server: {e}")

```
