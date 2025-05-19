import unittest
import asyncio
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

# Define the default base URL for the MCP server.
# FastMCP by default might run on 127.0.0.1:8000.
# The MCP streamable HTTP endpoint is often /mcp.
# This might need adjustment if the server runs on a different port/path.
MCP_SERVER_URL = "http://127.0.0.1:8000/mcp" 

class TestMCPServerIntegration(unittest.IsolatedAsyncioTestCase):

    async def test_execute_bash_echo(self):
        """
        Tests the 'execute_bash' tool via the MCP server with a simple echo command.
        IMPORTANT: This test expects the MCP server (`python mcp_server.py`) 
        to be running separately before this test is executed.
        """
        try:
            async with streamablehttp_client(MCP_SERVER_URL) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tool_name = "execute_bash" # Corresponds to the function name in mcp_server.py
                    arguments = {"command": "echo Hello MCP World"}
                    
                    print(f"Attempting to call tool '{tool_name}' with args: {arguments} on {MCP_SERVER_URL}")

                    # The session.call_tool method returns a mcp.types.ToolResult object
                    tool_result: types.ToolResult = await session.call_tool(tool_name, arguments)
                    
                    print(f"Tool call result: {tool_result}")
                    print(f"Tool call result content type: {type(tool_result.content)}")
                    print(f"Tool call result content: {tool_result.content}")


                    # The actual result from our 'execute_bash' tool is expected to be a dictionary.
                    # This dictionary is typically found in the 'content' attribute of the ToolResult object.
                    self.assertIsInstance(tool_result, types.ToolResult, "Response should be a ToolResult object.")
                    self.assertTrue(tool_result.success, f"Tool call was not successful. Error: {tool_result.error_message}")
                    
                    # The content of the ToolResult should be the dictionary returned by our tool.
                    result_dict = tool_result.content
                    
                    self.assertIsInstance(result_dict, dict, "ToolResult.content should be a dictionary.")
                    self.assertEqual(result_dict.get('stdout'), "Hello MCP World\n")
                    self.assertEqual(result_dict.get('stderr'), "")
                    self.assertEqual(result_dict.get('exit_code'), 0)
                    self.assertFalse(result_dict.get('timed_out'))

        except ConnectionRefusedError:
            self.fail(f"Connection to MCP server at {MCP_SERVER_URL} refused. "
                      "Please ensure the server is running by executing 'python mcp_server.py' in another terminal.")
        except Exception as e:
            # Catching httpx.ConnectError specifically if possible, or just general Exception
            # Example: if 'httpx.ConnectError' in str(type(e)):
            if "ConnectError" in str(type(e)) or "ConnectionRefusedError" in str(type(e)):
                 self.fail(f"Connection to MCP server at {MCP_SERVER_URL} failed. "
                      "Please ensure the server is running by executing 'python mcp_server.py' in another terminal. "
                      f"Details: {e}")
            else:
                self.fail(f"An unexpected error occurred during the integration test: {type(e).__name__} - {e}")

if __name__ == '__main__':
    print("Running MCP Server Integration Tests...")
    print(f"IMPORTANT: Ensure the MCP server (`python mcp_server.py`) is running on {MCP_SERVER_URL} (or the configured URL) before starting these tests.")
    # Attempt to install mcp if not found, for the client side (test execution environment)
    try:
        import mcp
        import httpx # A common dependency for mcp http client
    except ImportError:
        print("MCP or httpx package not found. Attempting to install 'mcp[cli]' and 'httpx'...")
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]", "httpx"])
            print("MCP and httpx installed successfully. Please re-run the test.")
            sys.exit(0) # Exit so user can re-run
        except subprocess.CalledProcessError as e:
            print(f"Failed to install mcp/httpx: {e}")
            print("Please install them manually using: pip install \"mcp[cli]\" httpx")
            sys.exit(1)

    unittest.main()
