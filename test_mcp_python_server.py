import asyncio
import unittest
from unittest.mock import patch, AsyncMock, ANY
import sys
import os
import json

# Ensure the server and runner are importable
# This might require adjusting sys.path if tests are run from a different directory
# or if the project structure isn't set up as a package.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.client.session import ClientSession, streamablehttp_client
from mcp.client.mcp_client import connect_to_subprocess_stdio

# The module to be tested (the MCP server)
PYTHON_SERVER_MODULE = "mcp_python_server" 

class TestMCPPythonServer(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Patch 'python_runner.run_python_code' before the server process starts.
        # This way, the server, when it imports python_runner, gets our mock.
        self.run_python_code_patcher = patch(f'{PYTHON_SERVER_MODULE}.run_python_code')
        self.mock_run_python_code = self.run_python_code_patcher.start()
        
        # Default mock response for run_python_code
        self.mock_run_python_code.return_value = {
            "stdout": "mocked_stdout",
            "stderr": "mocked_stderr",
            "exit_code": 0,
            "timed_out": False,
            "error": None
        }

        # Start the mcp_python_server.py script as a subprocess
        # Ensure the PYTHON_SERVER_MODULE (mcp_python_server.py) is executable or passed to python interpreter
        self.server_process = await asyncio.create_subprocess_exec(
            sys.executable, PYTHON_SERVER_MODULE + ".py", # e.g., 'python mcp_python_server.py'
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE # Capture server's own stderr for debugging tests
        )

        # Connect the MCP client to the server's stdio
        self.client_session = await connect_to_subprocess_stdio(self.server_process)
        await self.client_session.initialize()

    async def asyncTearDown(self):
        if self.client_session:
            await self.client_session.close()
        
        if self.server_process:
            # Terminate the server process
            if self.server_process.returncode is None: # Still running
                self.server_process.terminate()
                try:
                    # Wait a short period for graceful termination
                    await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("Server process did not terminate gracefully, killing.")
                    self.server_process.kill() # Force kill if terminate doesn't work
                except ProcessLookupError:
                    pass # Process already exited
            
            # Read any remaining stderr from the server process for debugging
            if self.server_process.stderr:
                try:
                    remaining_stderr = await self.server_process.stderr.read()
                    if remaining_stderr:
                        print(f"MCP Python Server STDERR on teardown:\n{remaining_stderr.decode(errors='ignore')}")
                except Exception as e:
                    print(f"Error reading server stderr on teardown: {e}")

        self.run_python_code_patcher.stop() # Stop the patch

    async def test_list_tools_contains_execute_python_code(self):
        print("\nRunning: test_list_tools_contains_execute_python_code")
        tools = await self.client_session.list_tools()
        self.assertIsNotNone(tools)
        self.assertGreater(len(tools), 0, "No tools listed by the server.")
        
        execute_python_tool = next((t for t in tools if t.name == "execute_python_code"), None)
        self.assertIsNotNone(execute_python_tool, "execute_python_code tool not found.")
        self.assertIn("Executes a snippet of Python code", execute_python_tool.description)
        self.assertIn("code", execute_python_tool.input_schema['properties'])

    async def test_call_execute_python_code_tool_success(self):
        print("\nRunning: test_call_execute_python_code_tool_success")
        tool_name = "execute_python_code"
        args = {
            "code": "print('hello world')",
            "requirements": ["requests"],
            "timeout": 30
            # python_image, cpu_limit, memory_limit will use defaults from schema
        }

        # Configure a specific return for this test if needed, or use setUp's default
        expected_runner_result = {
            "stdout": "hello world output", "stderr": "", 
            "exit_code": 0, "timed_out": False, "error": None
        }
        self.mock_run_python_code.return_value = expected_runner_result

        tool_result = await self.client_session.call_tool(tool_name, args)

        self.assertTrue(tool_result.success, f"Tool call failed: {tool_result.error_message}")
        self.assertDictEqual(tool_result.content, expected_runner_result)

        # Assert that the mocked python_runner.run_python_code was called correctly
        # The FastMCP server runs synchronous functions (like run_python_code) in a thread pool executor.
        # So, the mock is called in a different thread, but its call args should be preserved.
        self.mock_run_python_code.assert_called_once_with(
            args['code'], 
            args['requirements'], 
            args['timeout'],
            ANY, # python_image (will be default from schema)
            ANY, # cpu_limit (will be default from schema)
            ANY  # memory_limit (will be default from schema)
        )

    async def test_call_execute_python_code_runner_error(self):
        print("\nRunning: test_call_execute_python_code_runner_error")
        tool_name = "execute_python_code"
        args = {"code": "bad code"}

        # Simulate an error from python_runner.run_python_code
        error_runner_result = {
            "stdout": "", "stderr": "Syntax Error!", 
            "exit_code": 1, "timed_out": False, "error": "Runner execution failed"
        }
        self.mock_run_python_code.return_value = error_runner_result
        
        tool_result = await self.client_session.call_tool(tool_name, args)

        self.assertTrue(tool_result.success, "Tool call itself should succeed even if script fails.")
        # The content of the successful tool call is the dictionary from run_python_code
        self.assertEqual(tool_result.content['stderr'], "Syntax Error!")
        self.assertEqual(tool_result.content['exit_code'], 1)
        self.assertEqual(tool_result.content['error'], "Runner execution failed")

    async def test_call_with_missing_required_arg(self):
        print("\nRunning: test_call_with_missing_required_arg")
        tool_name = "execute_python_code"
        args = {"requirements": ["requests"]} # Missing 'code'

        tool_result = await self.client_session.call_tool(tool_name, args)
        
        self.assertFalse(tool_result.success, "Tool call should fail due to missing 'code' argument.")
        self.assertIsNotNone(tool_result.error_message)
        self.assertIn("Validation error", tool_result.error_message) 
        # FastMCP should provide a validation error based on the input_schema

    # Consider adding a test for when run_python_code itself raises an unexpected Exception
    # to ensure the server handles it gracefully.
    async def test_call_runner_raises_unexpected_exception(self):
        print("\nRunning: test_call_runner_raises_unexpected_exception")
        tool_name = "execute_python_code"
        args = {"code": "trigger unexpected exception"}

        self.mock_run_python_code.side_effect = Exception("Unexpected runner crash!")

        tool_result = await self.client_session.call_tool(tool_name, args)

        # The tool call itself might still be 'successful' from MCP perspective,
        # but the content would indicate a server-side error.
        self.assertTrue(tool_result.success) 
        self.assertIsNotNone(tool_result.content)
        self.assertIn("Server-side error invoking python_runner", tool_result.content.get('stderr', ''))
        self.assertEqual(tool_result.content.get('error'), "Server-side error.")
        self.assertEqual(tool_result.content.get('exit_code'), -1)


if __name__ == '__main__':
    unittest.main()
