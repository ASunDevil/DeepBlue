import asyncio
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import traceback

# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.fast_mcp import FastMCP
from mcp.log import logger as mcp_logger # Use MCP's logger

# Runner import (assuming python_runner.py is in the same directory or PYTHONPATH)
try:
    from python_runner import run_python_code, DEFAULT_PYTHON_IMAGE, DEFAULT_CPU_LIMIT, DEFAULT_MEMORY_LIMIT
except ImportError:
    mcp_logger.error(
        "Failed to import run_python_code from python_runner.py. "
        "Ensure python_runner.py is in the same directory or PYTHONPATH."
    )
    # Define a placeholder if import fails, so server can start and report error via MCP if tool is called
    async def run_python_code(*args, **kwargs):
        return {
            "stdout": "",
            "stderr": "Error: python_runner.run_python_code could not be imported.",
            "exit_code": -1,
            "timed_out": False,
            "error": "Python runner backend not available."
        }
    DEFAULT_PYTHON_IMAGE = "python:3.10-slim" # Provide defaults for tool signature
    DEFAULT_CPU_LIMIT = "1.0"
    DEFAULT_MEMORY_LIMIT = "256m"


# --- Load Environment Variables (if any specific are needed for this server) ---
load_dotenv()

# --- MCP Server Setup ---
# Using FastMCP for a simpler server setup
# For production, consider security features like OAuth as shown in ADK docs or other MCP examples.
app = FastMCP(
    name="PythonCodeExecutionServer",
    version="0.1.0",
    description="MCP Server for executing Python code in a sandboxed Docker environment. "
                "WARNING: This server allows arbitrary Python code execution, which can be "
                "extremely dangerous if exposed to untrusted users or networks. "
                "Ensure robust authentication and authorization are implemented before deployment."
)

@app.tool(
    name="execute_python_code",
    description="Executes a snippet of Python code in a sandboxed Docker environment. "
                "Supports specifying pip requirements and execution timeout. "
                "WARNING: Arbitrary code execution is a security risk.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The Python code to execute."},
            "requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of pip package requirements (e.g., ['requests', 'numpy==1.21.0']).",
                "default": []
            },
            "timeout": {
                "type": "integer",
                "description": "Optional maximum execution time in seconds.",
                "default": 60
            },
            "python_image": {
                "type": "string",
                "description": f"Optional custom Python Docker image. Defaults to {DEFAULT_PYTHON_IMAGE}.",
                "default": DEFAULT_PYTHON_IMAGE
            },
            "cpu_limit": {
                "type": "string",
                "description": f"Optional Docker CPU limit (e.g., '1.0'). Defaults to {DEFAULT_CPU_LIMIT}.",
                "default": DEFAULT_CPU_LIMIT
            },
            "memory_limit": {
                "type": "string",
                "description": f"Optional Docker memory limit (e.g., '256m'). Defaults to {DEFAULT_MEMORY_LIMIT}.",
                "default": DEFAULT_MEMORY_LIMIT
            }
        },
        "required": ["code"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "stdout": {"type": "string", "description": "Standard output from the execution."},
            "stderr": {"type": "string", "description": "Standard error from the execution."},
            "exit_code": {"type": "integer", "description": "Exit code of the script."},
            "timed_out": {"type": "boolean", "description": "True if execution timed out."},
            "error": {
                "type": ["string", "null"], 
                "description": "High-level error message if setup or Docker interaction failed before code execution."
            }
        },
        "required": ["stdout", "stderr", "exit_code", "timed_out", "error"]
    }
)
async def execute_python_code_tool(
    code: str, 
    requirements: Optional[List[str]] = None, 
    timeout: Optional[int] = 60,
    python_image: Optional[str] = DEFAULT_PYTHON_IMAGE,
    cpu_limit: Optional[str] = DEFAULT_CPU_LIMIT,
    memory_limit: Optional[str] = DEFAULT_MEMORY_LIMIT
) -> Dict[str, Any]:
    """
    MCP Tool wrapper for python_runner.run_python_code.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering execute_python_code_tool with code (first 100 chars)='{code[:100]}...', requirements={requirements}, timeout={timeout}, python_image='{python_image}', cpu_limit='{cpu_limit}', memory_limit='{memory_limit}'")
    mcp_logger.info(
        f"Executing Python code. Timeout: {timeout}, Requirements: {requirements}, "
        f"Image: {python_image}, CPU: {cpu_limit}, Mem: {memory_limit}"
    )
    if requirements is None: # Handle default from schema if not passed
        requirements = []
    print(f"DEBUG: [%{datetime.now().isoformat()}] Requirements after default handling: {requirements}")
        
    try:
        # run_python_code is synchronous, but FastMCP tool functions can be async.
        # To avoid blocking the asyncio event loop if run_python_code is lengthy (due to Docker ops),
        # it's better to run it in a thread pool executor.
        loop = asyncio.get_running_loop()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Calling run_python_code in executor with code (first 100 chars)='{code[:100]}...', requirements={requirements}, timeout={timeout}, python_image='{python_image}', cpu_limit='{cpu_limit}', memory_limit='{memory_limit}'")
        result = await loop.run_in_executor(
            None,  # Uses the default ThreadPoolExecutor
            run_python_code, 
            code, 
            requirements, 
            timeout,
            python_image,
            cpu_limit,
            memory_limit
        )
        print(f"DEBUG: [%{datetime.now().isoformat()}] run_python_code (in executor) returned: {result}")
        # Ensure all expected keys are present, even if None
        result.setdefault('stdout', '')
        result.setdefault('stderr', '')
        result.setdefault('exit_code', -1)
        result.setdefault('timed_out', False)
        result.setdefault('error', None)
        
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exception calling run_python_code via executor: {e}\nTraceback:\n{formatted_traceback}")
        mcp_logger.error(f"Exception calling run_python_code: {e}", exc_info=True)
        return {
            "stdout": "",
            "stderr": f"Server-side error invoking python_runner: {str(e)}",
            "exit_code": -1,
            "timed_out": False,
            "error": "Server-side error."
        }
        
    mcp_logger.info(f"Python code execution result: {{'exit_code': result.get('exit_code'), 'timed_out': result.get('timed_out'), 'error': result.get('error')}}")
    print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting execute_python_code_tool with result: {result}")
    return result

# --- MCP Server Runner ---
if __name__ == "__main__":
    print(f"DEBUG: [%{datetime.now().isoformat()}] Starting PythonCodeExecutionServer MCP server...")
    mcp_logger.info("Starting Python Code Execution MCP Server...")
    # FastMCP's run method is synchronous but internally manages an asyncio loop for SSE if chosen.
    # For simple stdio, it's straightforward.
    # To run with SSE for network access:
    # app.run_sse_stdio() or app.run_sse_async(host="0.0.0.0", port=8000)
    # For this example, let's use simple stdio for compatibility with ADK's StdioServerParameters
    
    # If mcp package version is < 0.6.0, use app.run_stdio()
    # If mcp package version is >= 0.6.0, use app.run_simple_stdio() or app.run_sse_stdio()
    # Checking for a specific method to be safe with version changes:
    if hasattr(app, "run_simple_stdio"):
        print(f"DEBUG: [%{datetime.now().isoformat()}] Running with FastMCP run_simple_stdio (mcp >= 0.6.0)")
        mcp_logger.info("Running with FastMCP run_simple_stdio (mcp >= 0.6.0)")
        app.run_simple_stdio()
    elif hasattr(app, "run_stdio"): # Older mcp versions
        print(f"DEBUG: [%{datetime.now().isoformat()}] Running with FastMCP run_stdio (mcp < 0.6.0)")
        mcp_logger.info("Running with FastMCP run_stdio (mcp < 0.6.0)")
        app.run_stdio()
    else:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Could not find a suitable stdio runner method in FastMCP.")
        mcp_logger.error("Could not find a suitable stdio runner method in FastMCP. Please check your 'mcp' package version.")
        # Fallback or raise error
        # For testing, can try to run SSE on a port if stdio methods are missing
        # try:
        #     asyncio.run(app.run_sse_async(host="127.0.0.1", port=8081))
        # except Exception as e:
        #     mcp_logger.error(f"Failed to start server with SSE: {e}")
        
    print(f"DEBUG: [%{datetime.now().isoformat()}] PythonCodeExecutionServer MCP server stopped.")
    mcp_logger.info("Python Code Execution MCP Server stopped.")
