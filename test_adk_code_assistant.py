import asyncio
import unittest
from unittest.mock import patch, AsyncMock, call

# Assuming adk_code_assistant.py is in the same directory or accessible via PYTHONPATH
try:
    from adk_code_assistant import create_code_assistant_agent, LlmAgent
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from adk_code_assistant import create_code_assistant_agent, LlmAgent


class MockAdkTool:
    def __init__(self, name, description="Mocked Tool"):
        self.name = name
        self.description = description
        self.run_async = AsyncMock(return_value={"output": f"{name} executed"}) # Correct: f-string for Python code

    def __str__(self):
        return f"MockAdkTool(name='{self.name}')" # Correct

    def __repr__(self):
        return f"<MockAdkTool name='{self.name}' id='{id(self)}'>" # Correct
    
    def __eq__(self, other):
        if isinstance(other, MockAdkTool):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)


class TestCreateCodeAssistantAgent(unittest.IsolatedAsyncioTestCase):

    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_successful_tool_loading_all_servers(self, mock_mcp_from_server):
        print("\nRunning: test_successful_tool_loading_all_servers")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        
        mock_exit_stack_instance = AsyncMock()

        mock_mcp_from_server.side_effect = [
            (mock_bash_tools, mock_exit_stack_instance),
            (mock_cpp_tools, mock_exit_stack_instance),
            (mock_chrome_tools, mock_exit_stack_instance)
        ]

        agent, exit_stack = await create_code_assistant_agent()

        self.assertIsInstance(agent, LlmAgent)
        self.assertEqual(agent.name, 'code_assistant')
        self.assertEqual(agent.model, 'gemini-2.0-flash')
        self.assertIn('You are a helpful AI code assistant.', agent.instruction)
        
        expected_tools = mock_bash_tools + mock_cpp_tools + mock_chrome_tools
        self.assertEqual(len(agent.tools), len(expected_tools))
        for tool in expected_tools:
            self.assertTrue(any(t.name == tool.name for t in agent.tools), f"Tool {tool.name} not found in agent tools.") # Correct

        self.assertEqual(mock_mcp_from_server.call_count, 3)
        
        calls = [
            call(connection_params=unittest.mock.ANY, async_exit_stack=mock_exit_stack_instance),
            call(connection_params=unittest.mock.ANY, async_exit_stack=mock_exit_stack_instance),
            call(connection_params=unittest.mock.ANY, async_exit_stack=mock_exit_stack_instance)
        ]
        mock_mcp_from_server.assert_has_calls(calls, any_order=False)

        actual_call_args = mock_mcp_from_server.call_args_list
        self.assertEqual(actual_call_args[0][1]['connection_params'].args, ['mcp_server.py'])
        self.assertEqual(actual_call_args[1][1]['connection_params'].args, ['mcp_cpp_server.py'])
        self.assertEqual(actual_call_args[2][1]['connection_params'].args, ['mcp_chrome_server.py'])

        self.assertEqual(exit_stack, mock_exit_stack_instance)

    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_partial_tool_loading_one_server_returns_no_tools(self, mock_mcp_from_server):
        print("\nRunning: test_partial_tool_loading_one_server_returns_no_tools")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools_empty = [] 
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_exit_stack_instance = AsyncMock()

        mock_mcp_from_server.side_effect = [
            (mock_bash_tools, mock_exit_stack_instance),
            (mock_cpp_tools_empty, mock_exit_stack_instance), 
            (mock_chrome_tools, mock_exit_stack_instance)
        ]

        agent, _ = await create_code_assistant_agent()

        self.assertIsInstance(agent, LlmAgent)
        expected_tools = mock_bash_tools + mock_chrome_tools
        self.assertEqual(len(agent.tools), len(expected_tools))
        for tool in expected_tools:
            self.assertTrue(any(t.name == tool.name for t in agent.tools), f"Tool {tool.name} not found.") # Correct
        self.assertFalse(any(t.name == "execute_cpp" for t in agent.tools))


    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_no_tools_loaded_all_servers_return_no_tools(self, mock_mcp_from_server):
        print("\nRunning: test_no_tools_loaded_all_servers_return_no_tools")
        mock_exit_stack_instance = AsyncMock()
        mock_mcp_from_server.side_effect = [
            ([], mock_exit_stack_instance), 
            ([], mock_exit_stack_instance), 
            ([], mock_exit_stack_instance)
        ]

        agent, _ = await create_code_assistant_agent()

        self.assertIsInstance(agent, LlmAgent)
        self.assertEqual(len(agent.tools), 0)

    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_mcp_toolset_from_server_raises_file_not_found(self, mock_mcp_from_server):
        print("\nRunning: test_mcp_toolset_from_server_raises_file_not_found")
        mock_mcp_from_server.side_effect = FileNotFoundError("mcp_server.py script not found error")

        with self.assertRaisesRegex(FileNotFoundError, "mcp_server.py script not found error"):
            await create_code_assistant_agent()
        
        mock_mcp_from_server.assert_called_once()
        self.assertEqual(mock_mcp_from_server.call_args_list[0][1]['connection_params'].args, ['mcp_server.py'])


    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_mcp_toolset_from_server_raises_generic_exception(self, mock_mcp_from_server):
        print("\nRunning: test_mcp_toolset_from_server_raises_generic_exception")
        mock_mcp_from_server.side_effect = Exception("A generic MCP tool loading error occurred")

        with self.assertRaisesRegex(Exception, "A generic MCP tool loading error occurred"):
            await create_code_assistant_agent()
            
        mock_mcp_from_server.assert_called_once()
        self.assertEqual(mock_mcp_from_server.call_args_list[0][1]['connection_params'].args, ['mcp_server.py'])


# Imports for Integration Tests (some might be already imported by unit tests)
# from google.adk.runners import Runner # Not used for direct tool call tests yet
# from google.adk.sessions import InMemorySessionService, Session # Not used yet
# from google.adk.tools import ToolContext # For type hinting if needed, not strictly for these mocks

# (MockAdkTool class is already defined above in the unit test section)

class TestAdkCodeAssistantIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Set up a complete agent with mocked tools for each test."""
        print("\nSetting up for an Integration Test...")
        self.mock_exit_stack_instance = AsyncMock()

        # Create distinct mocks for each tool for this test suite
        # These names must match the names the tools would have when loaded from MCP.
        # The actual MCP server for bash_tool.py registers 'execute_bash'.
        # The actual MCP server for cpp_runner.py registers 'execute_cpp'.
        # The actual MCP server for chrome_screenshot_taker.py registers 'capture_webpage'.
        self.mock_bash_tool_instance = MockAdkTool(name="execute_bash")
        self.mock_cpp_tool_instance = MockAdkTool(name="execute_cpp")
        self.mock_chrome_tool_instance = MockAdkTool(name="capture_webpage")

        # Patch MCPToolset.from_server for the duration of these tests
        # We use self.patcher to manage start/stop of the patch correctly.
        self.patcher = patch('adk_code_assistant.MCPToolset.from_server')
        mock_mcp_from_server = self.patcher.start() # mock_mcp_from_server is now the AsyncMock

        mock_mcp_from_server.side_effect = [
            ([self.mock_bash_tool_instance], self.mock_exit_stack_instance),
            ([self.mock_cpp_tool_instance], self.mock_exit_stack_instance),
            ([self.mock_chrome_tool_instance], self.mock_exit_stack_instance)
        ]
        
        self.agent, self.exit_stack = await create_code_assistant_agent()
        self.assertIsNotNone(self.agent, "Agent creation failed in setUp")
        # After MCPToolset.from_server is mocked to return 1 tool per server:
        self.assertTrue(len(self.agent.tools) == 3, 
                        f"Agent should have 3 tools for integration tests, got {len(self.agent.tools)}. Tools: {[t.name for t in self.agent.tools]}")
        
        self.mock_exit_stack_instance.aclose.reset_mock()

    async def asyncTearDown(self):
        """Clean up after each test."""
        print("Tearing down after an Integration Test...")
        if self.exit_stack:
            await self.exit_stack.aclose()
        self.patcher.stop() # Stop the patcher started in asyncSetUp

    async def test_bash_tool_integration_direct_call(self):
        print("\nRunning: test_bash_tool_integration_direct_call")
        # Tool names in tools_map are derived from the tool.name attribute
        bash_tool = self.agent.tools_map.get("execute_bash")
        self.assertIsNotNone(bash_tool, "execute_bash tool not found in agent's tools_map")
        # Check if the tool in the map is indeed our mocked instance by checking its run_async method
        self.assertEqual(bash_tool.run_async, self.mock_bash_tool_instance.run_async, 
                         "The bash_tool in agent.tools_map is not the mocked instance.")

        test_args = {"command": "ls -l", "timeout": 30}
        mock_tool_context = None # ADK might provide a default context or it might be optional
        
        # Directly call run_async on the tool obtained from the agent's tools_map
        await bash_tool.run_async(args=test_args, tool_context=mock_tool_context)
        
        # Assert that the mock tool's run_async (which is an AsyncMock) was called correctly
        self.mock_bash_tool_instance.run_async.assert_called_once_with(
            args=test_args, tool_context=mock_tool_context
        )

    async def test_cpp_tool_integration_direct_call(self):
        print("\nRunning: test_cpp_tool_integration_direct_call")
        cpp_tool = self.agent.tools_map.get("execute_cpp")
        self.assertIsNotNone(cpp_tool, "execute_cpp tool not found in agent's tools_map")
        self.assertEqual(cpp_tool.run_async, self.mock_cpp_tool_instance.run_async,
                         "The cpp_tool in agent.tools_map is not the mocked instance.")

        test_args = {"cpp_code": "int main() {return 0;}", "stdin_text": ""}
        mock_tool_context = None
        
        await cpp_tool.run_async(args=test_args, tool_context=mock_tool_context)
        
        self.mock_cpp_tool_instance.run_async.assert_called_once_with(
            args=test_args, tool_context=mock_tool_context
        )

    async def test_chrome_tool_integration_direct_call(self):
        print("\nRunning: test_chrome_tool_integration_direct_call")
        chrome_tool = self.agent.tools_map.get("capture_webpage")
        self.assertIsNotNone(chrome_tool, "capture_webpage tool not found in agent's tools_map")
        self.assertEqual(chrome_tool.run_async, self.mock_chrome_tool_instance.run_async,
                         "The chrome_tool in agent.tools_map is not the mocked instance.")

        test_args = {"url": "https://example.com", "width": 1280, "height": 720}
        mock_tool_context = None
        
        await chrome_tool.run_async(args=test_args, tool_context=mock_tool_context)
        
        self.mock_chrome_tool_instance.run_async.assert_called_once_with(
            args=test_args, tool_context=mock_tool_context
        )

# The if __name__ == '__main__': unittest.main() block should already be at the end of the file.
# This comment just serves as a reminder for the subtask.


if __name__ == '__main__':
    unittest.main()
