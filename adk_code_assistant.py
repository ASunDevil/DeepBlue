import asyncio
from contextlib import AsyncExitStack
import os # Added for GITHUB_TOKEN

# Attempt to import ADK components.
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import Tool # Added for custom Python function tool
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
    from web_retriever import get_web_content # Import the new web retrieval function
except ImportError as e:
    print(f"ADK Import Error: {e}")
    print("Please ensure you have the 'google-adk' package installed. You can install it using: pip install google-adk")
    raise SystemExit("ADK not found. Please install it and try again.")


async def create_code_assistant_agent():
    """
    Creates an ADK LlmAgent equipped with tools from various MCP servers.
    """
    common_exit_stack = AsyncExitStack()
    all_mcp_tools = []
    
    # Local Python-based MCP servers
    local_mcp_servers = [
        ("mcp_server.py", "bash execution"),
        ("mcp_cpp_server.py", "C++ execution"),
        ("mcp_chrome_server.py", "webpage capture"),
        ("mcp_langflow_critique_server.py", "Langflow code critique") # Added Langflow server
    ]

    try:
        for script_name, description in local_mcp_servers:
            print(f"Attempting to load tools from {script_name} ({description})...")
            tools, _ = await MCPToolset.from_server(
                connection_params=StdioServerParameters(
                    command='python3',
                    args=[script_name]
                ),
                async_exit_stack=common_exit_stack
            )
            if tools:
                all_mcp_tools.extend(tools)
                tool_names = [tool.name for tool in tools]
                print(f"Successfully loaded {len(tools)} tools from {script_name}: {tool_names}")
            else:
                print(f"No tools loaded from {script_name}.")

        # GitHub MCP Server Integration
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            print("Attempting to load tools from github-mcp-server...")
            try:
                github_tools, _ = await MCPToolset.from_server(
                    connection_params=StdioServerParameters(
                        command='docker',
                        args=['run', '-i', '--rm', 
                              '-e', 'GITHUB_PERSONAL_ACCESS_TOKEN', # Pass var name for Docker
                              'ghcr.io/github/github-mcp-server'],
                        env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token} # Pass actual token value to Docker env
                    ),
                    async_exit_stack=common_exit_stack
                )
                if github_tools:
                    all_mcp_tools.extend(github_tools)
                    tool_names = [tool.name for tool in github_tools]
                    print(f"Successfully loaded {len(github_tools)} tools from github-mcp-server: {tool_names}")
                else:
                    print("No tools loaded from github-mcp-server, or an error occurred during its initialization.")
            except Exception as e_github:
                print(f"Error loading tools from github-mcp-server: {e_github}")
                print("Ensure Docker is running and 'ghcr.io/github/github-mcp-server' image can be pulled.")
        else:
            print("Warning: GITHUB_TOKEN environment variable not set. Skipping GitHub tools.")

        # Define and add the web content retrieval tool
        try:
            web_content_tool = Tool(
                name="get_website_content",
                description="Retrieves the textual content of a given URL. Input should be a single URL string.",
                func=get_web_content,
            )
            all_mcp_tools.append(web_content_tool)
            print(f"Successfully added custom tool: {web_content_tool.name}")
        except Exception as e_custom_tool:
            print(f"Error adding custom tool 'get_website_content': {e_custom_tool}")


        if not all_mcp_tools:
            print("Warning: No tools were loaded from any MCP server or defined locally. The agent will have no functional capabilities.")

    except FileNotFoundError as e:
        print(f"Error: MCP Server script or Docker command not found: {e}. Ensure 'python3' and 'docker' are installed and MCP scripts are in the current directory.")
        raise
    except Exception as e:
        print(f"Critical error during MCPToolset initialization: {e}")
        raise

    agent = LlmAgent(
        model='gemini-2.0-flash',
        name='code_assistant',
        instruction=(
            'You are a helpful AI code assistant. '
            'You have tools to execute bash commands, compile and run C++ code snippets, '
            'capture screenshots of webpages, interact with GitHub (e.g., read files, list issues), '
            'and critique code (providing feedback on quality, style, and potential issues). '
            "You also have a tool to 'get_website_content' which takes a URL and returns its textual content. " # Updated instruction
            'Use these tools as needed to answer user requests, debug code, '
            'fetch documentation, manage repositories, critique code, retrieve web content, or perform other coding-related tasks.'
        ),
        tools=all_mcp_tools,
    )
    return agent, common_exit_stack

if __name__ == '__main__':
    async def main():
        print("Starting ADK Code Assistant...")
        agent, exit_stack = None, None
        try:
            agent, exit_stack = await create_code_assistant_agent()

            if agent:
                print(f"Agent '{agent.name}' created successfully with {len(agent.tools)} tools.")
                if not agent.tools:
                    print("ADK Agent was created but has NO TOOLS.")
                else:
                    print("Registered tools:")
                    for tool in agent.tools:
                        print(f"  - Tool: {tool.name}, Description: {tool.description}")
                
                print("\nAgent is ready.")
                # ... (conceptual Runner comments remain the same) ...
                print("\nTo interact with this agent, you would typically use ADK's Runner")
                print("or integrate it into a larger application (e.g., using `adk web`).")

            else:
                print("Agent creation failed.")

        except Exception as e:
            print(f"An error occurred during agent setup or conceptual execution: {e}")
            print("\nTroubleshooting tips:")
            print("1. Verify 'google-adk' is installed.")
            print("2. Ensure 'python3' and 'docker' are in your system PATH.")
            print("3. Confirm local MCP server scripts (mcp_server.py, mcp_cpp_server.py, mcp_chrome_server.py, mcp_langflow_critique_server.py, etc.) are in the current directory.") # Updated tip
            print("4. For GitHub tools, ensure GITHUB_TOKEN environment variable is set and Docker can pull 'ghcr.io/github/github-mcp-server'.")
            print("5. Check for errors from MCP server scripts or Docker if tools fail to load.")
            print("6. If using Docker-dependent tools (C++, Chrome, GitHub), ensure Docker is running and accessible.")
            print("7. For Langflow code critique, ensure the LANGFLOW_CRITIQUE_API_URL environment variable is correctly set if not using the default, and that the Langflow service is running and accessible.") # Added tip
        finally:
            if exit_stack:
                print("\nClosing AsyncExitStack for MCP server connections...")
                await exit_stack.aclose()
                print("AsyncExitStack closed.")
            print("ADK Code Assistant finished.")

    asyncio.run(main())
