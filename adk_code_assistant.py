import asyncio
from contextlib import AsyncExitStack

# Attempt to import ADK components. Provide helpful error messages if ADK is not installed.
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
except ImportError as e:
    print(f"ADK Import Error: {e}")
    print("Please ensure you have the 'google-adk' package installed. You can install it using: pip install google-adk")
    raise SystemExit("ADK not found. Please install it and try again.")


async def create_code_assistant_agent():
    """
    Creates an ADK LlmAgent equipped with tools from MCP servers
    for bash execution, C++ execution, and webpage capturing.
    """
    common_exit_stack = AsyncExitStack()
    all_mcp_tools = []
    
    mcp_server_scripts = [
        ("mcp_server.py", "bash execution"),
        ("mcp_cpp_server.py", "C++ execution"),
        ("mcp_chrome_server.py", "webpage capture")
    ]

    try:
        for script_name, description in mcp_server_scripts:
            print(f"Attempting to load tools from {script_name} ({description})...")
            tools, _ = await MCPToolset.from_server(
                connection_params=StdioServerParameters(
                    command='python3',  # Assuming python3 is in PATH
                    args=[script_name]  # Assumes script is in the same directory or PATH
                ),
                async_exit_stack=common_exit_stack
            )
            
            if tools:
                all_mcp_tools.extend(tools)
                tool_names = [tool.name for tool in tools]
                print(f"Successfully loaded {len(tools)} tools from {script_name}: {tool_names}")
            else:
                print(f"No tools loaded from {script_name}, or an error occurred during its MCPToolset initialization. Check server script logs if possible.")

        if not all_mcp_tools:
            print("Warning: No tools were loaded from any MCP server. The agent will have no functional capabilities.")

    except FileNotFoundError as e:
        print(f"Error: MCP Server script not found: {e}. Ensure 'python3' is installed and MCP scripts are in the current directory.")
        raise
    except Exception as e:
        print(f"Critical error during MCPToolset initialization: {e}")
        print("This might be due to issues with the MCP server scripts themselves (e.g., syntax errors, missing dependencies like Docker for C++ or Chrome tools), or problems with ADK's interaction with them.")
        raise

    agent = LlmAgent(
        model='gemini-2.0-flash',  # Ensure this model is available/configured in your ADK setup
        name='code_assistant',
        instruction=(
            'You are a helpful AI code assistant. '
            'You have tools to execute bash commands, compile and run C++ code snippets, '
            'and capture screenshots of webpages. '
            'Use these tools as needed to answer user requests, debug code, '
            'fetch documentation, or perform other coding-related tasks.'
        ),
        tools=all_mcp_tools,
    )
    return agent, common_exit_stack

if __name__ == '__main__':
    # Renamed from test_agent_creation to main for a more standard entry point
    async def main():
        print("Starting ADK Code Assistant...")
        agent, exit_stack = None, None
        try:
            # 1. Create the agent and its tools
            agent, exit_stack = await create_code_assistant_agent()

            if agent:
                print(f"Agent '{agent.name}' created successfully with {len(agent.tools)} tools.")
                if not agent.tools:
                    print("ADK Agent was created but has NO TOOLS. Please check the output above for errors from MCPToolset initialization.")
                    print("Ensure MCP server scripts are correctly placed, executable, and their dependencies (like Docker) are met.")
                else:
                    print("Registered tools:")
                    for tool in agent.tools:
                        print(f"  - Tool: {tool.name}, Description: {tool.description}")
                
                print("\nAgent is ready.")
                # 2. This is where you would typically set up an ADK Runner
                #    and process user input in a loop or handle a single query.
                # Example (conceptual, actual Runner setup might vary):
                #
                # from google.adk.runners import Runner
                # from google.adk.sessions import InMemorySessionService
                # from google.genai import types as genai_types # Ensure google.generativeai is installed
                #
                # session_service = InMemorySessionService()
                # session = session_service.create_session()
                # runner = Runner(agent=agent, session_service=session_service)
                #
                # user_query = "List files in the current directory using bash." 
                # print(f"Simulating user query: {user_query}")
                # # Note: Ensure genai_types.Content and genai_types.Part are correctly used as per your ADK/Gemini version
                # message = genai_types.Content(role="user", parts=[genai_types.Part(text=user_query)])
                #
                # async for event in runner.run_async(session_id=session.id, new_message=message):
                #     print(f"Runner Event: {event}")
                #     # Process events, e.g., extract and print LLM responses
                #     if event.type == "llm_response" and event.data.get("candidates"):
                #         # Accessing response text might vary based on event structure
                #         response_text = event.data['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', 'No text in response')
                #         print(f"Agent Response: {response_text}")
                
                print("\nTo interact with this agent, you would typically use ADK's Runner")
                print("or integrate it into a larger application (e.g., using `adk web`).")
                print("The MCP server processes (for bash, cpp, chrome) should have been started by MCPToolset if tool loading was successful.")

            else:
                # This case implies create_code_assistant_agent itself failed critically before returning an agent
                print("Agent creation failed. Cannot proceed.")

        except Exception as e:
            print(f"An error occurred during agent setup or conceptual execution: {e}")
            print("\nTroubleshooting tips:")
            print("1. Verify 'google-adk' is installed (e.g., `pip show google-adk`).")
            print("2. Ensure 'python3' is in your system PATH.")
            print("3. Confirm MCP server scripts (mcp_server.py, etc.) are in the same directory as adk_code_assistant.py.")
            print("4. Check for errors when the MCP server scripts are run manually (e.g., `python3 mcp_server.py`). They might be missing dependencies (e.g., `pip install mcp`, Docker for C++ and Chrome tools).")
            print("5. If using Docker-dependent tools (C++, Chrome), ensure Docker is running and accessible by the user running this script.")
            print("6. Check for any output from the MCP server scripts themselves if they are started but tools fail to load.")
        finally:
            if exit_stack:
                print("\nClosing AsyncExitStack for MCP server connections...")
                await exit_stack.aclose()
                print("AsyncExitStack closed.")
            print("ADK Code Assistant finished.")

    asyncio.run(main())
