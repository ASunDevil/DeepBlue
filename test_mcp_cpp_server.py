import unittest
import asyncio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from typing import Dict, Any, Union # For type hinting

# Default URL for the C++ MCP server.
# NOTE: If mcp_server.py (bash tool) also uses 8000, one server will need to run on a different port.
MCP_CPP_SERVER_URL = "http://127.0.0.1:8000/mcp" 

class TestCppMCPServerIntegration(unittest.IsolatedAsyncioTestCase):

    async def helper_call_execute_cpp(self, cpp_code: str, stdin_text: Union[str, None] = None) -> Union[Dict[str, Any], None]:
        """Helper function to connect and call the execute_cpp tool."""
        try:
            async with streamablehttp_client(MCP_CPP_SERVER_URL) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_name = "execute_cpp"
                    arguments = {"cpp_code": cpp_code}
                    if stdin_text is not None:
                        arguments["stdin_text"] = stdin_text
                    
                    code_preview = cpp_code[:50].replace('\n', '\\n') + ('...' if len(cpp_code) > 50 else '')
                    print(f"\nCalling tool '{tool_name}' on {MCP_CPP_SERVER_URL} with cpp_code (first 50 chars): '{code_preview}'")
                    if stdin_text:
                        print(f"stdin_text: '{stdin_text}'")
                        
                    tool_result = await session.call_tool(tool_name, arguments)
                    
                    self.assertIsInstance(tool_result, types.ToolResult, f"Unexpected response type from MCP server: {type(tool_result)}")
                    # The 'execute_cpp' tool in mcp_cpp_server.py should return the dictionary directly.
                    # FastMCP wraps this in ToolResult.content if tool_result.success is True.
                    if not tool_result.success:
                         self.fail(f"Tool call itself failed. Error type: {tool_result.error_type}, Message: {tool_result.error_message}")
                    
                    self.assertIsInstance(tool_result.content, dict, f"ToolResult.content is not a dictionary: {type(tool_result.content)}")
                    return tool_result.content # This should be the dictionary from run_cpp_code
                    
        except ConnectionRefusedError:
            self.fail(f"Connection to MCP C++ server at {MCP_CPP_SERVER_URL} refused. "
                      "Please ensure 'python mcp_cpp_server.py' is running.")
        except Exception as e:
            # Check for httpx specific connection errors if httpx is used by streamablehttp_client
            if "ConnectError" in str(type(e)) or "ConnectTimeout" in str(type(e)):
                 self.fail(f"Connection to MCP C++ server at {MCP_CPP_SERVER_URL} failed. "
                      "Please ensure 'python mcp_cpp_server.py' is running. "
                      f"Details: {type(e).__name__} - {e}")
            else:
                self.fail(f"An unexpected error occurred during MCP C++ integration test: {type(e).__name__} - {e}")
        return None


    async def test_successful_cpp_execution(self):
        """Tests successful execution of simple C++ code."""
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Hello from C++ MCP!" << std::endl;
            return 0;
        }
        """
        result = await self.helper_call_execute_cpp(cpp_code)
        if result is None: return # Connection failed, helper_call_execute_cpp already called self.fail()

        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed: STDERR:\n{result.get('compilation_stderr')}\nSTDOUT:\n{result.get('compilation_stdout')}")
        self.assertFalse(result.get('timed_out_compilation'), "Compilation should not time out.")
        self.assertEqual(result.get('execution_exit_code'), 0, msg=f"Execution failed: STDERR:\n{result.get('execution_stderr')}")
        self.assertFalse(result.get('timed_out_execution'), "Execution should not time out.")
        self.assertEqual(result.get('execution_stdout'), "Hello from C++ MCP!\n")
        self.assertEqual(result.get('execution_stderr'), "")


    async def test_cpp_compilation_error(self):
        """Tests handling of C++ code with a syntax error."""
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Syntax Error Here" << std::end; // Error: std::end instead of std::endl
            return 0;
        }
        """
        result = await self.helper_call_execute_cpp(cpp_code)
        if result is None: return

        self.assertNotEqual(result.get('compilation_exit_code'), 0, "Compilation should have failed (non-zero exit code).")
        self.assertFalse(result.get('timed_out_compilation'), "Compilation should not time out for a syntax error.")
        self.assertIn("error:", result.get('compilation_stderr', '').lower(), "Expected 'error:' in compilation_stderr.")
        # Execution fields should be None as execution is skipped after compilation error
        self.assertIsNone(result.get('execution_stdout'), "execution_stdout should be None after compilation error.")
        self.assertIsNone(result.get('execution_stderr'), "execution_stderr should be None after compilation error.")
        self.assertIsNone(result.get('execution_exit_code'), "execution_exit_code should be None after compilation error.")
        self.assertFalse(result.get('timed_out_execution'), "Execution should not be marked as timed out if not run.")


    async def test_cpp_runtime_error(self):
        """Tests handling of C++ code that compiles but causes a runtime error (division by zero)."""
        cpp_code = """
        #include <iostream>
        int main() {
            int x = 0;
            std::cout << "Result: " << (10 / x) << std::endl; // Division by zero
            return 0;
        }
        """
        result = await self.helper_call_execute_cpp(cpp_code)
        if result is None: return

        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed: {result.get('compilation_stderr')}")
        self.assertFalse(result.get('timed_out_compilation'))
        self.assertNotEqual(result.get('execution_exit_code'), 0, "Execution should have failed (non-zero exit code) due to runtime error.")
        self.assertFalse(result.get('timed_out_execution'), "Execution should not time out for a quick runtime error.")
        # Stderr for division by zero might vary (e.g., "Floating point exception"), or be empty if the signal terminates abruptly.
        # The key is the non-zero exit code.
        # self.assertIn("error", result.get('execution_stderr', '').lower()) # Optional: check stderr if consistent


    async def test_cpp_with_stdin(self):
        """Tests C++ code that reads from stdin and echoes it."""
        cpp_code = """
        #include <iostream>
        #include <string>
        int main() {
            std::string name;
            std::cout << "Enter your name: "; // Prompt
            std::getline(std::cin, name);
            std::cout << "Hello, " << name << "!" << std::endl;
            return 0;
        }
        """
        stdin_text = "MCP Coder"
        result = await self.helper_call_execute_cpp(cpp_code, stdin_text=stdin_text)
        if result is None: return

        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed: {result.get('compilation_stderr')}")
        self.assertFalse(result.get('timed_out_compilation'))
        self.assertEqual(result.get('execution_exit_code'), 0, msg=f"Execution failed: {result.get('execution_stderr')}")
        self.assertFalse(result.get('timed_out_execution'))
        # Output includes the prompt from the C++ code and then the processed output.
        self.assertEqual(result.get('execution_stdout'), f"Enter your name: Hello, {stdin_text}!\n")


if __name__ == '__main__':
    print(f"Running MCP C++ Server Integration Tests...")
    print(f"IMPORTANT: Ensure the MCP C++ server (`python mcp_cpp_server.py`) is running on {MCP_CPP_SERVER_URL} before starting these tests.")
    print("If you also have the bash MCP server (`mcp_server.py`), ensure they are on different ports if both use port 8000 by default (e.g., run one on port 8001).")
    
    # Attempt to install mcp and httpx if not found
    try:
        import mcp
        import httpx # A common dependency for mcp http client
    except ImportError:
        print("\nAttempting to install missing packages 'mcp[cli]' and 'httpx'...")
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]", "httpx"])
            print("Packages installed successfully. Please re-run the tests.")
            sys.exit(0) # Exit so user can re-run with packages installed
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e}")
            print("Please install them manually: pip install \"mcp[cli]\" httpx")
            sys.exit(1) # Exit with error

    unittest.main()
```
