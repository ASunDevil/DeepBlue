from dify_plugin import Tool, ToolInvokeMessage, ToolInput
from typing import Any, Generator, Dict
import sys
import os
from datetime import datetime
import traceback

# --- IMPORTANT: Python Path Configuration for Importing Original ADK Tool Logic ---
adk_project_root_relative = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
original_bash_tool_module_found = False
if adk_project_root_relative not in sys.path:
    sys.path.insert(0, adk_project_root_relative)
try:
    from bash_tool import run_bash_command
    original_bash_tool_module_found = True
    timestamp_init_ok = datetime.now().isoformat()
    print(f"DEBUG: [{timestamp_init_ok}] bash_tool_dify.py: Successfully imported run_bash_command from ADK project.", file=sys.stderr)
except ImportError as e:
    timestamp_init_err = datetime.now().isoformat()
    print(f"ERROR: [{timestamp_init_err}] bash_tool_dify.py: Could not import 'run_bash_command' from ADK project (path: {adk_project_root_relative}). Error: {e}. Ensure 'bash_tool.py' is accessible.", file=sys.stderr)
    # Fallback function if original cannot be imported
    def run_bash_command(*args, **kwargs):
        return {
            "stdout": "",
            "stderr": "CRITICAL ERROR: Original bash_tool.py not found or importable by Dify plugin.",
            "exit_code": -999,
            "timed_out": False,
            "error": "Original bash_tool.py not found."
        }

class BashToolDify(Tool):
    def _invoke(self, user_id: str, tool_parameters: Dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        timestamp_entry = datetime.now().isoformat()
        print(f"DEBUG: [{timestamp_entry}] BashToolDify._invoke called by user '{user_id}' with parameters: {tool_parameters}", file=sys.stderr)

        command = tool_parameters.get("command")
        # Dify should provide defaults based on YAML, but good to have fallbacks.
        timeout = tool_parameters.get("timeout", 60) 
        working_directory = tool_parameters.get("working_directory") 

        if not command:
            timestamp_err_cmd = datetime.now().isoformat()
            error_msg = "Error: 'command' parameter is required for execute_bash tool."
            print(f"DEBUG: [{timestamp_err_cmd}] BashToolDify._invoke: {error_msg}", file=sys.stderr)
            yield self.create_text_message(error_msg)
            return

        if not original_bash_tool_module_found:
            timestamp_err_load = datetime.now().isoformat()
            critical_error_msg = "CRITICAL ERROR: Original bash_tool.py could not be loaded by the Dify plugin. Bash execution unavailable."
            print(f"ERROR: [{timestamp_err_load}] BashToolDify._invoke: {critical_error_msg}", file=sys.stderr)
            yield self.create_json_message({
                "stdout": "", 
                "stderr": critical_error_msg, 
                "exit_code": -999, 
                "timed_out": False, 
                "error": "Plugin misconfiguration."
            })
            return
            
        try:
            timestamp_call = datetime.now().isoformat()
            print(f"DEBUG: [{timestamp_call}] BashToolDify._invoke: Calling original run_bash_command with command='{command}', timeout={timeout}, working_directory='{working_directory}'", file=sys.stderr)
            result = run_bash_command(
                command=str(command), # Ensure command is string
                timeout=int(timeout),
                working_directory=str(working_directory) if working_directory is not None else None
            )
            timestamp_result = datetime.now().isoformat()
            print(f"DEBUG: [{timestamp_result}] BashToolDify._invoke: run_bash_command returned: {result}", file=sys.stderr)
            yield self.create_json_message(result)

        except Exception as e:
            timestamp_err_exec = datetime.now().isoformat()
            formatted_traceback = traceback.format_exc()
            error_details = f"Unexpected error in BashToolDify: {type(e).__name__} - {str(e)}"
            print(f"ERROR: [{timestamp_err_exec}] BashToolDify._invoke: {error_details}\nParameters: {tool_parameters}\nTraceback:\n{formatted_traceback}", file=sys.stderr)
            yield self.create_json_message({"error": "Tool execution failed", "details": error_details, "traceback": formatted_traceback})
