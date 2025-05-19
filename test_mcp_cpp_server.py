import unittest
import asyncio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from typing import Dict, Any, Union # For type hinting

# Default URL for the C++ MCP server.
MCP_CPP_SERVER_URL = "http://127.0.0.1:8000/mcp" 

class TestCppMCPServerIntegration(unittest.IsolatedAsyncioTestCase):

    async def helper_call_execute_cpp(self, cpp_code: str, stdin_text: Union[str, None] = None, compiler_choice: Union[str, None] = None) -> Union[Dict[str, Any], None]:
        """Helper function to connect and call the execute_cpp tool."""
        try:
            async with streamablehttp_client(MCP_CPP_SERVER_URL) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_name = "execute_cpp"
                    arguments = {"cpp_code": cpp_code}
                    if stdin_text is not None:
                        arguments["stdin_text"] = stdin_text
                    if compiler_choice is not None:
                        arguments["compiler_choice"] = compiler_choice
                    
                    code_preview = cpp_code[:50].replace('\n', '\\n') + ('...' if len(cpp_code) > 50 else '')
                    print(f"\nCalling tool '{tool_name}' on {MCP_CPP_SERVER_URL} with cpp_code (first 50 chars): '{code_preview}'")
                    if stdin_text:
                        print(f"stdin_text: '{stdin_text}'")
                    if compiler_choice:
                        print(f"compiler_choice: '{compiler_choice}'")
                        
                    tool_result = await session.call_tool(tool_name, arguments)
                    
                    self.assertIsInstance(tool_result, types.ToolResult, f"Unexpected response type from MCP server: {type(tool_result)}")
                    if not tool_result.success:
                         self.fail(f"Tool call itself failed. Error type: {tool_result.error_type}, Message: {tool_result.error_message}")
                    
                    self.assertIsInstance(tool_result.content, dict, f"ToolResult.content is not a dictionary: {type(tool_result.content)}")
                    return tool_result.content
                    
        except ConnectionRefusedError:
            self.fail(f"Connection to MCP C++ server at {MCP_CPP_SERVER_URL} refused. "
                      "Please ensure 'python mcp_cpp_server.py' is running.")
        except Exception as e:
            if "ConnectError" in str(type(e)) or "ConnectTimeout" in str(type(e)):
                 self.fail(f"Connection to MCP C++ server at {MCP_CPP_SERVER_URL} failed. "
                      "Please ensure 'python mcp_cpp_server.py' is running. "
                      f"Details: {type(e).__name__} - {e}")
            else:
                self.fail(f"An unexpected error occurred during MCP C++ integration test: {type(e).__name__} - {e}")
        return None

    async def _run_successful_cpp_execution_test(self, compiler_choice_arg: Union[str, None], expected_compiler_used: str):
        """Helper for successful execution tests."""
        cpp_code = f"""
        #include <iostream>
        int main() {{
            #if defined(__clang__)
                std::cout << "Hello from Clang MCP!" << std::endl;
            #elif defined(__GNUC__)
                std::cout << "Hello from GCC MCP!" << std::endl;
            #else
                std::cout << "Hello from Unknown Compiler MCP!" << std::endl;
            #endif
            return 0;
        }}
        """
        expected_output_fragment = "Clang" if expected_compiler_used == "clang++" else "GCC"
        
        result = await self.helper_call_execute_cpp(cpp_code, compiler_choice=compiler_choice_arg)
        if result is None: return

        self.assertEqual(result.get('compiler_used'), expected_compiler_used, "Compiler used does not match expected.")
        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed for {expected_compiler_used}: STDERR:\n{result.get('compilation_stderr')}\nSTDOUT:\n{result.get('compilation_stdout')}")
        self.assertFalse(result.get('timed_out_compilation'), "Compilation should not time out.")
        self.assertEqual(result.get('execution_exit_code'), 0, msg=f"Execution failed for {expected_compiler_used}: STDERR:\n{result.get('execution_stderr')}")
        self.assertFalse(result.get('timed_out_execution'), "Execution should not time out.")
        self.assertIn(expected_output_fragment, result.get('execution_stdout', ''))
        self.assertEqual(result.get('execution_stderr'), "")

    async def test_successful_cpp_execution_gpp_default(self):
        """Tests successful execution with g++ (default)."""
        await self._run_successful_cpp_execution_test(compiler_choice_arg=None, expected_compiler_used="g++")

    async def test_successful_cpp_execution_gpp_explicit(self):
        """Tests successful execution with g++ (explicitly chosen)."""
        await self._run_successful_cpp_execution_test(compiler_choice_arg="g++", expected_compiler_used="g++")

    async def test_successful_cpp_execution_clangpp(self):
        """Tests successful execution with clang++."""
        await self._run_successful_cpp_execution_test(compiler_choice_arg="clang++", expected_compiler_used="clang++")

    async def _run_cpp_compilation_error_test(self, compiler_choice: str):
        """Helper for compilation error tests."""
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Syntax Error Here" << std::end; // Error: std::end instead of std::endl
            return 0;
        }
        """
        result = await self.helper_call_execute_cpp(cpp_code, compiler_choice=compiler_choice)
        if result is None: return

        self.assertEqual(result.get('compiler_used'), compiler_choice)
        self.assertNotEqual(result.get('compilation_exit_code'), 0, f"Compilation should have failed for {compiler_choice} (non-zero exit code).")
        self.assertFalse(result.get('timed_out_compilation'), "Compilation should not time out for a syntax error.")
        self.assertIn("error:", result.get('compilation_stderr', '').lower(), f"Expected 'error:' in compilation_stderr for {compiler_choice}.")
        self.assertIn("std::end", result.get('compilation_stderr', ''), f"Specific error related to 'std::end' not found for {compiler_choice}.")
        
        self.assertIsNone(result.get('execution_stdout'), "execution_stdout should be None after compilation error.")
        self.assertIsNone(result.get('execution_stderr'), "execution_stderr should be None after compilation error.")
        self.assertIsNone(result.get('execution_exit_code'), "execution_exit_code should be None after compilation error.")
        self.assertFalse(result.get('timed_out_execution'), "Execution should not be marked as timed out if not run.")

    async def test_cpp_compilation_error_gpp(self):
        """Tests compilation error with g++."""
        await self._run_cpp_compilation_error_test("g++")

    async def test_cpp_compilation_error_clangpp(self):
        """Tests compilation error with clang++."""
        await self._run_cpp_compilation_error_test("clang++")

    async def test_invalid_compiler_choice_mcp(self):
        """Tests calling execute_cpp with an invalid compiler choice via MCP."""
        cpp_code = "#include <iostream>\nint main() { std::cout << \"test\"; return 0; }"
        invalid_compiler = "nonexistent_compiler_123"
        result = await self.helper_call_execute_cpp(cpp_code, compiler_choice=invalid_compiler)
        if result is None: return

        # cpp_runner.py sets 'compiler_used' to 'none' and compilation_exit_code to -100
        self.assertEqual(result.get('compiler_used'), "none", "compiler_used should be 'none' for invalid choice.")
        self.assertEqual(result.get('compilation_exit_code'), -100, "compilation_exit_code should be -100 for invalid compiler.")
        self.assertIn(f"Unsupported compiler: '{invalid_compiler}'", result.get('compilation_stderr', ''), "Expected error message for unsupported compiler not found.")
        self.assertIsNone(result.get('execution_stdout'))
        self.assertFalse(result.get('timed_out_compilation'))
        self.assertFalse(result.get('timed_out_execution'))

    # Keep other tests like runtime_error and stdin_handling, perhaps run them with default compiler or one specific one.
    # For brevity here, I'm assuming they would be similar to how successful_execution was refactored if needed for both compilers.
    async def test_cpp_runtime_error_default_compiler(self):
        """Tests handling of C++ code that causes a runtime error (division by zero) with default compiler."""
        cpp_code = """
        #include <iostream>
        int main() {
            int x = 0;
            std::cout << "Result: " << (10 / x) << std::endl; // Division by zero
            return 0;
        }
        """
        result = await self.helper_call_execute_cpp(cpp_code) # Default compiler (g++)
        if result is None: return

        self.assertEqual(result.get('compiler_used'), "g++") # Check default
        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed: {result.get('compilation_stderr')}")
        self.assertFalse(result.get('timed_out_compilation'))
        self.assertNotEqual(result.get('execution_exit_code'), 0, "Execution should have failed (non-zero exit code) due to runtime error.")
        self.assertFalse(result.get('timed_out_execution'))

    async def test_cpp_with_stdin_default_compiler(self):
        """Tests C++ code that reads from stdin (with default compiler)."""
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
        result = await self.helper_call_execute_cpp(cpp_code, stdin_text=stdin_text) # Default compiler (g++)
        if result is None: return

        self.assertEqual(result.get('compiler_used'), "g++") # Check default
        self.assertEqual(result.get('compilation_exit_code'), 0, msg=f"Compilation failed: {result.get('compilation_stderr')}")
        self.assertFalse(result.get('timed_out_compilation'))
        self.assertEqual(result.get('execution_exit_code'), 0, msg=f"Execution failed: {result.get('execution_stderr')}")
        self.assertFalse(result.get('timed_out_execution'))
        self.assertEqual(result.get('execution_stdout'), f"Enter your name: Hello, {stdin_text}!\n")


if __name__ == '__main__':
    print(f"Running MCP C++ Server Integration Tests...")
    print(f"IMPORTANT: Ensure the MCP C++ server (`python mcp_cpp_server.py`) is running on {MCP_CPP_SERVER_URL} before starting these tests.")
    print("These tests will attempt to use both g++ and clang++ via the server.")
    print("If you also have the bash MCP server (`mcp_server.py`), ensure they are on different ports if both use port 8000 by default.")
    
    try:
        import mcp
        import httpx 
    except ImportError:
        print("\nAttempting to install missing packages 'mcp[cli]' and 'httpx'...")
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]", "httpx"])
            print("Packages installed successfully. Please re-run the tests.")
            sys.exit(0) 
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e}")
            print("Please install them manually: pip install \"mcp[cli]\" httpx")
            sys.exit(1)

    unittest.main()
```
