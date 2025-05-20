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

    # Default mock for os.environ.get to simulate GITHUB_TOKEN being set
    MOCK_ENV_WITH_TOKEN = {"GITHUB_TOKEN": "test_token_123"}
    MOCK_ENV_NO_TOKEN = {} # Simulates GITHUB_TOKEN not being set

    @patch('adk_code_assistant.os.environ', MOCK_ENV_WITH_TOKEN) 
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_successful_tool_loading_all_servers_including_github(self, mock_mcp_from_server):
        print("\nRunning: test_successful_tool_loading_all_servers_including_github")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_github_tools = [MockAdkTool(name="github_get_file_content")]
        mock_exit_stack_instance = AsyncMock()

        mock_mcp_from_server.side_effect = [
            (mock_bash_tools, mock_exit_stack_instance),
            (mock_cpp_tools, mock_exit_stack_instance),
            (mock_chrome_tools, mock_exit_stack_instance),
            (mock_github_tools, mock_exit_stack_instance)
        ]

        agent, exit_stack = await create_code_assistant_agent()

        self.assertIsInstance(agent, LlmAgent)
        self.assertEqual(agent.name, 'code_assistant')
        self.assertIn("interact with GitHub", agent.instruction)
        
        expected_tools = mock_bash_tools + mock_cpp_tools + mock_chrome_tools + mock_github_tools
        self.assertEqual(len(agent.tools), len(expected_tools))
        for tool in expected_tools:
            self.assertTrue(any(t.name == tool.name for t in agent.tools), f"Tool {tool.name} not found")

        self.assertEqual(mock_mcp_from_server.call_count, 4)
        
        actual_call_args = mock_mcp_from_server.call_args_list
        self.assertEqual(actual_call_args[0][1]['connection_params'].args, ['mcp_server.py'])
        self.assertEqual(actual_call_args[1][1]['connection_params'].args, ['mcp_cpp_server.py'])
        self.assertEqual(actual_call_args[2][1]['connection_params'].args, ['mcp_chrome_server.py'])
        
        github_call_params = actual_call_args[3][1]['connection_params']
        self.assertEqual(github_call_params.command, 'docker')
        self.assertIn('ghcr.io/github/github-mcp-server', github_call_params.args)
        self.assertIn('GITHUB_PERSONAL_ACCESS_TOKEN', github_call_params.args) # Check env var name is passed to docker run
        self.assertEqual(github_call_params.env, {"GITHUB_PERSONAL_ACCESS_TOKEN": "test_token_123"}) # Check actual token value passed to env
        self.assertEqual(exit_stack, mock_exit_stack_instance)

    @patch('adk_code_assistant.os.environ', MOCK_ENV_NO_TOKEN) # Simulate GITHUB_TOKEN not set
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_successful_tool_loading_no_github_token(self, mock_mcp_from_server):
        print("\nRunning: test_successful_tool_loading_no_github_token")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_exit_stack_instance = AsyncMock()

        mock_mcp_from_server.side_effect = [
            (mock_bash_tools, mock_exit_stack_instance),
            (mock_cpp_tools, mock_exit_stack_instance),
            (mock_chrome_tools, mock_exit_stack_instance)
            # No 4th call expected for GitHub
        ]

        agent, _ = await create_code_assistant_agent()

        self.assertIsInstance(agent, LlmAgent)
        self.assertIn("interact with GitHub", agent.instruction) # Instruction is updated regardless
        
        expected_tools = mock_bash_tools + mock_cpp_tools + mock_chrome_tools
        self.assertEqual(len(agent.tools), len(expected_tools))
        self.assertFalse(any(t.name == "github_get_file_content" for t in agent.tools)) # No GitHub tools
        self.assertEqual(mock_mcp_from_server.call_count, 3)


    @patch('adk_code_assistant.os.environ', MOCK_ENV_WITH_TOKEN)
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_partial_loading_github_fails_returns_no_tools(self, mock_mcp_from_server):
        print("\nRunning: test_partial_loading_github_fails_returns_no_tools")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_exit_stack_instance = AsyncMock()

        mock_mcp_from_server.side_effect = [
            (mock_bash_tools, mock_exit_stack_instance),
            (mock_cpp_tools, mock_exit_stack_instance),
            (mock_chrome_tools, mock_exit_stack_instance),
            ([], mock_exit_stack_instance) # GitHub server returns no tools
        ]
        agent, _ = await create_code_assistant_agent()
        self.assertEqual(mock_mcp_from_server.call_count, 4) # Attempted to call all 4
        expected_tools = mock_bash_tools + mock_cpp_tools + mock_chrome_tools
        self.assertEqual(len(agent.tools), len(expected_tools)) # But only 3 sets of tools loaded
        self.assertFalse(any(t.name.startswith("github_") for t in agent.tools))

    @patch('adk_code_assistant.os.environ', MOCK_ENV_NO_TOKEN) 
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_no_tools_loaded_all_local_servers_fail_no_github(self, mock_mcp_from_server):
        print("\nRunning: test_no_tools_loaded_all_local_servers_fail_no_github")
        mock_exit_stack_instance = AsyncMock()
        mock_mcp_from_server.side_effect = [
            ([], mock_exit_stack_instance), 
            ([], mock_exit_stack_instance), 
            ([], mock_exit_stack_instance)
        ]
        agent, _ = await create_code_assistant_agent()
        self.assertIsInstance(agent, LlmAgent)
        self.assertEqual(len(agent.tools), 0)
        self.assertEqual(mock_mcp_from_server.call_count, 3) 

    @patch('adk_code_assistant.os.environ', MOCK_ENV_NO_TOKEN) 
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_mcp_toolset_raises_file_not_found_for_local_server(self, mock_mcp_from_server):
        print("\nRunning: test_mcp_toolset_raises_file_not_found_for_local_server")
        mock_mcp_from_server.side_effect = FileNotFoundError("mcp_server.py script not found error")
        with self.assertRaisesRegex(FileNotFoundError, "mcp_server.py script not found error"):
            await create_code_assistant_agent()
        mock_mcp_from_server.assert_called_once() 

    @patch('adk_code_assistant.os.environ', MOCK_ENV_WITH_TOKEN)
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_mcp_toolset_raises_file_not_found_for_docker_command(self, mock_mcp_from_server):
        print("\nRunning: test_mcp_toolset_raises_file_not_found_for_docker_command")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_exit_stack_instance = AsyncMock()

        def custom_side_effect(*args, **kwargs):
            connection_params = kwargs.get('connection_params')
            if connection_params and connection_params.command == 'docker':
                # This exception will be caught by the general try-except in create_code_assistant_agent
                # which then prints a message and continues if it's specific to github server.
                # For FileNotFoundError for docker itself, it should propagate up.
                # Let's simulate the FileNotFoundError for the docker command itself.
                # The actual FileNotFoundError would happen when subprocess tries to run 'docker'
                # For the mock, we raise it when we detect the attempt to run docker.
                raise FileNotFoundError("No such file or directory: 'docker'")
            elif connection_params and connection_params.args[0] == 'mcp_server.py':
                return (mock_bash_tools, mock_exit_stack_instance)
            elif connection_params and connection_params.args[0] == 'mcp_cpp_server.py':
                return (mock_cpp_tools, mock_exit_stack_instance)
            elif connection_params and connection_params.args[0] == 'mcp_chrome_server.py':
                return (mock_chrome_tools, mock_exit_stack_instance)
            return ([], mock_exit_stack_instance) 

        mock_mcp_from_server.side_effect = custom_side_effect
        
        with self.assertRaisesRegex(FileNotFoundError, "No such file or directory: 'docker'"):
            await create_code_assistant_agent()
        
        # It should try local servers (3 calls), then the GitHub one (1 call) which fails
        self.assertEqual(mock_mcp_from_server.call_count, 4)


    @patch('adk_code_assistant.os.environ', MOCK_ENV_WITH_TOKEN)
    @patch('adk_code_assistant.MCPToolset.from_server')
    async def test_mcp_toolset_github_server_raises_generic_exception(self, mock_mcp_from_server):
        print("\nRunning: test_mcp_toolset_github_server_raises_generic_exception")
        mock_bash_tools = [MockAdkTool(name="execute_bash")]
        mock_cpp_tools = [MockAdkTool(name="execute_cpp")]
        mock_chrome_tools = [MockAdkTool(name="capture_webpage")]
        mock_exit_stack_instance = AsyncMock()

        # Custom side_effect to raise an exception only for the GitHub server call
        def custom_side_effect_github_ex(*args, **kwargs):
            connection_params = kwargs.get('connection_params')
            if connection_params and connection_params.command == 'docker':
                # This exception should be caught by the specific try-except block for GitHub tools
                # in create_code_assistant_agent, and then not prevent agent creation.
                raise Exception("GitHub MCP Docker error") 
            elif connection_params and connection_params.args[0] == 'mcp_server.py':
                return (mock_bash_tools, mock_exit_stack_instance)
            elif connection_params and connection_params.args[0] == 'mcp_cpp_server.py':
                return (mock_cpp_tools, mock_exit_stack_instance)
            elif connection_params and connection_params.args[0] == 'mcp_chrome_server.py':
                return (mock_chrome_tools, mock_exit_stack_instance)
            return ([], mock_exit_stack_instance)

        mock_mcp_from_server.side_effect = custom_side_effect_github_ex
            
        # The exception from github server load is caught inside create_code_assistant_agent,
        # so the agent creation itself should not raise this specific exception.
        # Instead, it should print an error and continue.
        agent, _ = await create_code_assistant_agent()
        
        self.assertEqual(mock_mcp_from_server.call_count, 4) # All 4 attempted
        # Agent should be created with tools from the other 3 servers
        expected_tools = mock_bash_tools + mock_cpp_tools + mock_chrome_tools
        self.assertEqual(len(agent.tools), len(expected_tools))
        self.assertFalse(any(t.name.startswith("github_") for t in agent.tools))


class TestAdkCodeAssistantIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Set up a complete agent with mocked tools for each test, including GitHub tools."""
        print("\nSetting up for an Integration Test (including GitHub)...")
        self.mock_exit_stack_instance = AsyncMock()

        self.mock_bash_tool_instance = MockAdkTool(name="execute_bash")
        self.mock_cpp_tool_instance = MockAdkTool(name="execute_cpp")
        self.mock_chrome_tool_instance = MockAdkTool(name="capture_webpage")
        # Example GitHub tool name, actual names depend on github-mcp-server
        self.mock_github_tool_instance = MockAdkTool(name="github_get_file_contents") 

        # Patch os.environ to simulate GITHUB_TOKEN being present for these integration tests
        self.env_patcher = patch('adk_code_assistant.os.environ', TestCreateCodeAssistantAgent.MOCK_ENV_WITH_TOKEN)
        self.mock_environ = self.env_patcher.start()

        self.mcp_patcher = patch('adk_code_assistant.MCPToolset.from_server')
        mock_mcp_from_server = self.mcp_patcher.start()

        mock_mcp_from_server.side_effect = [
            ([self.mock_bash_tool_instance], self.mock_exit_stack_instance),
            ([self.mock_cpp_tool_instance], self.mock_exit_stack_instance),
            ([self.mock_chrome_tool_instance], self.mock_exit_stack_instance),
            ([self.mock_github_tool_instance], self.mock_exit_stack_instance) # For GitHub
        ]
        
        self.agent, self.exit_stack = await create_code_assistant_agent()
        self.assertIsNotNone(self.agent, "Agent creation failed in setUp")
        
        # Expect 4 tools now (bash, cpp, chrome, github)
        self.assertEqual(len(self.agent.tools), 4, 
                        f"Agent should have 4 tools for these integration tests, got {len(self.agent.tools)}. Tools: {[t.name for t in self.agent.tools]}") # Escaped braces for subtask f-string
        
        self.mock_exit_stack_instance.aclose.reset_mock()

    async def asyncTearDown(self):
        """Clean up after each test."""
        print("Tearing down after an Integration Test...")
        if self.exit_stack:
            await self.exit_stack.aclose()
        self.mcp_patcher.stop() 
        self.env_patcher.stop() 

    async def test_bash_tool_integration_direct_call(self):
        print("\nRunning: test_bash_tool_integration_direct_call")
        bash_tool = self.agent.tools_map.get("execute_bash")
        self.assertIsNotNone(bash_tool, "execute_bash tool not found")
        self.assertEqual(bash_tool.run_async, self.mock_bash_tool_instance.run_async)
        test_args = {"command": "ls -l", "timeout": 30} # Escaped braces
        await bash_tool.run_async(args=test_args, tool_context=None)
        self.mock_bash_tool_instance.run_async.assert_called_once_with(args=test_args, tool_context=None)

    async def test_cpp_tool_integration_direct_call(self):
        print("\nRunning: test_cpp_tool_integration_direct_call")
        cpp_tool = self.agent.tools_map.get("execute_cpp")
        self.assertIsNotNone(cpp_tool, "execute_cpp tool not found")
        self.assertEqual(cpp_tool.run_async, self.mock_cpp_tool_instance.run_async)
        test_args = {"cpp_code": "int main() {return 0;}", "stdin_text": ""} # Escaped braces
        await cpp_tool.run_async(args=test_args, tool_context=None)
        self.mock_cpp_tool_instance.run_async.assert_called_once_with(args=test_args, tool_context=None)

    async def test_chrome_tool_integration_direct_call(self):
        print("\nRunning: test_chrome_tool_integration_direct_call")
        chrome_tool = self.agent.tools_map.get("capture_webpage")
        self.assertIsNotNone(chrome_tool, "capture_webpage tool not found")
        self.assertEqual(chrome_tool.run_async, self.mock_chrome_tool_instance.run_async)
        test_args = {"url": "https://example.com", "width": 1280, "height": 720} # Escaped braces
        await chrome_tool.run_async(args=test_args, tool_context=None)
        self.mock_chrome_tool_instance.run_async.assert_called_once_with(args=test_args, tool_context=None)

    async def test_github_tool_integration_direct_call(self):
        print("\nRunning: test_github_tool_integration_direct_call")
        github_tool_name = "github_get_file_contents" 
        github_tool = self.agent.tools_map.get(github_tool_name)
        self.assertIsNotNone(github_tool, f"{github_tool_name} tool not found in agent's tools_map") # Escaped
        self.assertEqual(github_tool.run_async, self.mock_github_tool_instance.run_async,
                         f"The {github_tool_name} in agent.tools_map is not the mocked instance.") # Escaped

        test_args = {"owner": "testowner", "repo": "testrepo", "path": "README.md", "ref": "main"} # Escaped
        mock_tool_context = None
        
        await github_tool.run_async(args=test_args, tool_context=mock_tool_context)
        
        self.mock_github_tool_instance.run_async.assert_called_once_with(
            args=test_args, tool_context=mock_tool_context
        )

if __name__ == '__main__':
    unittest.main()
