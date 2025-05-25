import asyncio
from contextlib import AsyncExitStack
import os # For GITHUB_TOKEN and OPENAI_API_KEY

# Attempt to import ADK components.
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import Tool 
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
    # Updated import: from get_web_content to create_vector_store_from_url
    from web_retriever import create_vector_store_from_url 
except ImportError as e:
    print(f"ADK Import Error: {e}")
    print("Please ensure you have the 'google-adk' package installed. You can install it using: pip install google-adk")
    print("Also ensure 'langchain-openai', 'faiss-cpu', and other dependencies are installed.")
    raise SystemExit("ADK or related dependencies not found. Please install them and try again.")

async def query_website_content_tool_func(input_str: str) -> str:
    """
    Retrieves relevant content chunks from a website URL based on a query,
    using a vector store and similarity search.
    """
    print(f"Tool 'query_website_content_tool_func' called with input: '{input_str}'")
    try:
        parts = input_str.split(',', 1)
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'URL,QUERY_STRING'. Example: 'https://example.com,What is this page about?'"
        
        url, query_string = parts[0].strip(), parts[1].strip()

        if not url or not query_string:
            return "Error: URL or query string cannot be empty. Expected 'URL,QUERY_STRING'."

        print(f"Parsed URL: '{url}', Query: '{query_string}'")

    except Exception as e:
        return f"Error parsing input string: {e}. Expected 'URL,QUERY_STRING'."

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        return "Error: OPENAI_API_KEY environment variable not set. This tool cannot function without it."

    print("Attempting to create vector store...")
    vector_store = await create_vector_store_from_url(url, openai_api_key)

    if vector_store is None:
        # create_vector_store_from_url already prints detailed errors
        return f"Error: Could not create vector store for the URL '{url}'. Previous logs may have more details."

    print(f"Vector store created. Performing similarity search for query: '{query_string}'")
    try:
        retrieved_docs = await vector_store.asimilarity_search(query_string, k=3)
    except Exception as e:
        return f"Error during similarity search: {e}"

    if not retrieved_docs:
        return "No relevant documents found for your query in the website content."

    print(f"Found {len(retrieved_docs)} relevant document(s). Formatting output...")
    formatted_results = []
    for i, doc in enumerate(retrieved_docs):
        # Ensure page_content is not None and is a string
        content = doc.page_content if doc.page_content is not None else "Content not available"
        formatted_results.append(f"Relevant Chunk {i+1}:\n{content}\n---")
    
    return "\n".join(formatted_results)


async def create_code_assistant_agent():
    """
    Creates an ADK LlmAgent equipped with tools from various MCP servers and custom tools.
    """
    common_exit_stack = AsyncExitStack()
    all_mcp_tools = []
    
    local_mcp_servers = [
        ("mcp_server.py", "bash execution"),
        ("mcp_cpp_server.py", "C++ execution"),
        ("mcp_chrome_server.py", "webpage capture"),
        ("mcp_langflow_critique_server.py", "Langflow code critique")
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

        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token:
            print("Attempting to load tools from github-mcp-server...")
            try:
                github_tools, _ = await MCPToolset.from_server(
                    connection_params=StdioServerParameters(
                        command='docker',
                        args=['run', '-i', '--rm', 
                              '-e', 'GITHUB_PERSONAL_ACCESS_TOKEN',
                              'ghcr.io/github/github-mcp-server'],
                        env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token}
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

        # Define and add the MODIFIED web content retrieval tool (now RAG-based)
        try:
            web_rag_tool = Tool(
                name="get_website_content", # Keeping the original name as per instruction context
                description=(
                    "Retrieves relevant content from a given URL based on a query. "
                    "Input should be a comma-separated string: 'URL,QUERY_STRING'. "
                    "For example: 'https://example.com,What is this page about?'"
                ),
                func=query_website_content_tool_func, # Using the new RAG wrapper function
            )
            all_mcp_tools.append(web_rag_tool)
            print(f"Successfully added/updated custom tool: {web_rag_tool.name} with new RAG functionality.")
        except Exception as e_custom_tool:
            print(f"Error adding/updating custom tool 'get_website_content': {e_custom_tool}")


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
            "You also have a tool called 'get_website_content'. This tool now performs Retrieval Augmented Generation (RAG): " # Updated instruction
            "it takes a comma-separated string 'URL,QUERY_STRING' (e.g., 'https://example.com,What is this page about?'), "
            "fetches content from the URL, creates a temporary vector store, and returns the most relevant text chunks based on the query. "
            'Use these tools as needed to answer user requests, debug code, '
            'fetch documentation, manage repositories, critique code, retrieve and query web content, or perform other coding-related tasks.'
        ),
        tools=all_mcp_tools,
    )
    return agent, common_exit_stack

if __name__ == '__main__':
    async def main():
        # To run this script in interactive mode, execute it directly.
        # Once the agent is initialized, you can type messages and receive responses.
        # Type 'quit' or 'exit' to end the interactive session.
        print("Starting ADK Code Assistant...")
        # For the RAG tool to work, OPENAI_API_KEY must be set in the environment.
        if not os.environ.get("OPENAI_API_KEY"):
            print("WARNING: OPENAI_API_KEY environment variable is not set. The 'get_website_content' (RAG) tool will not function.")
        
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
                # Start of interactive loop
                print("\nEntering interactive mode. Type 'quit' or 'exit' to end.")
                while True:
                    try:
                        print("\nAgent is ready for your input...") # Added
                        user_input = input("You: ")
                        print(f"DEBUG: Received user input: '{user_input}'") # Added

                        if user_input.lower() in ['quit', 'exit']:
                            print("Exiting interactive mode.")
                            break
                        
                        print("DEBUG: Sending input to agent for processing...") # Added
                        # Agent interaction logic (agent.chat, agent.process, etc.)
                        # ... (existing agent call logic) ...
                        # Example:
                        # response_obj = await agent.chat(user_input) 
                        # print(f"DEBUG: Raw response object from agent: {response_obj}") # Added

                        # --- Start of existing agent interaction logic ---
                        if hasattr(agent, 'chat') and callable(getattr(agent, 'chat')):
                            response_obj = await agent.chat(user_input)
                        elif hasattr(agent, 'process') and callable(getattr(agent, 'process')):
                            response_obj = await agent.process(user_input)
                        elif hasattr(agent, 'process_utterance') and callable(getattr(agent, 'process_utterance')):
                            response_obj = await agent.process_utterance(user_input)
                        else:
                            print("Agent: Error - Could not find a method to interact with the agent (e.g., chat, process, process_utterance). Further investigation is needed.")
                            response_obj = None
                        # --- End of existing agent interaction logic ---

                        print(f"DEBUG: Raw response object from agent: {response_obj}") # Added

                        if response_obj:
                            agent_reply_text = None
                            if isinstance(response_obj, str):
                                agent_reply_text = response_obj
                            elif hasattr(response_obj, 'text') and callable(getattr(response_obj, 'text')): # if text is a method
                                agent_reply_text = response_obj.text()
                            elif hasattr(response_obj, 'text') and isinstance(response_obj.text, str): # if text is an attribute
                                agent_reply_text = response_obj.text
                            elif isinstance(response_obj, dict) and 'output' in response_obj:
                                agent_reply_text = response_obj['output']
                            else:
                                # If the structure is unknown, convert to string for debugging
                                agent_reply_text = str(response_obj) 
                                print(f"DEBUG: Agent response is of type {type(response_obj)}, attempting to print as string.")

                            print(f"Agent: {agent_reply_text}") # Existing print for final response
                        else:
                            print("Agent: No response received or error in processing.") # Modified for clarity

                    except KeyboardInterrupt:
                        print("\nExiting interactive mode due to user interruption.")
                        break
                    except Exception as e:
                        print(f"An error occurred: {e}")
                        # import traceback # Optionally, for more detailed error during development
                        # traceback.print_exc()
                # End of interactive loop
            else:
                print("Agent creation failed.")

        except Exception as e:
            print(f"An error occurred during agent setup or conceptual execution: {e}")
            # Print traceback for more detailed debugging
            import traceback
            traceback.print_exc()
            print("\nTroubleshooting tips:")
            print("1. Verify 'google-adk' and related packages (langchain, openai, faiss-cpu) are installed.")
            print("2. Ensure 'python3' and 'docker' are in your system PATH.")
            print("3. Confirm local MCP server scripts are in the current directory.")
            print("4. For GitHub tools, ensure GITHUB_TOKEN is set and Docker can pull the image.")
            print("5. For the 'get_website_content' RAG tool, ensure OPENAI_API_KEY is set.")
        finally:
            if exit_stack:
                print("\nClosing AsyncExitStack for MCP server connections...")
                await exit_stack.aclose()
                print("AsyncExitStack closed.")
            print("ADK Code Assistant finished.")

    asyncio.run(main())
