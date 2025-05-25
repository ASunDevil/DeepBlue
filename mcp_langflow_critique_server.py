#!/usr/bin/env python3
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import os
import sys
import requests
from datetime import datetime
import traceback

# Define the tool specification.
TOOL_SPEC = {
    "name": "critique_code",
    "description": "Critiques the provided code using a Langflow-based AI agent, offering feedback on quality, style, potential bugs, and improvements.",
    "arguments": [
        {
            "name": "code_to_critique",
            "type": "string",
            "description": "The code snippet to be critiqued."
        }
    ]
}

DEFAULT_LANGFLOW_API_URL = "http://localhost:7860/api/v1/run/your_langflow_agent_id"

def run_tool(code_to_critique: str) -> str:
    """
    Invokes the Langflow code critique agent.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering run_tool with code_to_critique (first 100 chars)='{code_to_critique[:100]}...'", file=sys.stderr)
    langflow_api_url = os.environ.get("LANGFLOW_CRITIQUE_API_URL", DEFAULT_LANGFLOW_API_URL)
    print(f"DEBUG: [%{datetime.now().isoformat()}] Langflow API URL: {langflow_api_url}", file=sys.stderr)

    print(f"DEBUG: [%{datetime.now().isoformat()}] Attempting to critique code using Langflow API: {langflow_api_url}", file=sys.stderr)

    payload = {"code": code_to_critique}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(langflow_api_url, json=payload, headers=headers, timeout=60) # Added timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
    except requests.exceptions.Timeout as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Langflow API call timed out: {e}\nTraceback:\n{formatted_traceback}", file=sys.stderr)
        print(f"Error calling Langflow API: Timeout - {e}", file=sys.stderr)
        value_to_return = json.dumps({"error": f"Langflow API request timed out: {e}"})
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {value_to_return[:500]}...", file=sys.stderr)
        return value_to_return
    except requests.exceptions.RequestException as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Langflow API RequestException: {e}\nResponse content (if any): {e.response.text if e.response else 'No response content'}\nTraceback:\n{formatted_traceback}", file=sys.stderr)
        print(f"Error calling Langflow API: {e}", file=sys.stderr)
        # Attempt to get more details from response if available
        error_detail = ""
        if e.response is not None:
            try:
                error_detail = e.response.json()
            except json.JSONDecodeError:
                error_detail = e.response.text
        value_to_return = json.dumps({"error": f"Failed to connect to Langflow API: {e}. Detail: {error_detail}"})
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {value_to_return[:500]}...", file=sys.stderr)
        return value_to_return

    try:
        response_json = response.json()
    except json.JSONDecodeError as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Failed to decode JSON response from Langflow: {e}\nResponse text: {response.text}\nTraceback:\n{formatted_traceback}", file=sys.stderr)
        print(f"Error decoding JSON response from Langflow API: {e}", file=sys.stderr)
        print(f"Response text: {response.text}", file=sys.stderr)
        value_to_return = json.dumps({"error": f"Invalid JSON response from Langflow API: {e}"})
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {value_to_return[:500]}...", file=sys.stderr)
        return value_to_return

    # Based on "Simplified/Ideal Response Format" from design: {"critique": "..."}
    # Langflow's actual API might wrap this, e.g. in an 'outputs' list as shown in the design doc.
    # If the "Simplified/Ideal Response Format" is directly from Langflow, this is fine.
    # If Langflow wraps it, this part needs adjustment.
    # Example from design doc: response_json.get("outputs", [{}])[0].get("outputs", {}).get("critique_display", {}).get("text")
    # Assuming the "Simplified/Ideal Response Format" is what the API endpoint is configured to return directly.

    if "critique" in response_json:
        critique = response_json["critique"]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Received critique directly.", file=sys.stderr)
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {critique[:500]}...", file=sys.stderr)
        return critique # Per MCP, we return the direct result string if successful
    elif "outputs" in response_json and isinstance(response_json["outputs"], list) and len(response_json["outputs"]) > 0:
        # Handling the more complex Langflow output structure if "Simplified/Ideal" is not met
        # This structure is based on the example in code_critique_agent_design.md:
        # { "outputs": [ { "outputs": { "critique_display": { "text": "..." } } } ] }
        try:
            # Navigate through the nested structure
            first_output_element = response_json["outputs"][0]
            # The component name 'critique_display' was an example name for the TextOutput component.
            # It might be different in the actual Langflow flow.
            # Making it more robust by checking common output structures.
            if "outputs" in first_output_element and isinstance(first_output_element["outputs"], dict):
                # This is the { "outputs": { "COMPONENT_NAME": { "text": "..." } } } structure
                outputs_dict = first_output_element["outputs"]
                # We don't know the exact component name, so we look for a key that has a 'text' field.
                for component_output in outputs_dict.values():
                    if isinstance(component_output, dict) and "text" in component_output:
                        critique = component_output["text"]
                        print(f"DEBUG: [%{datetime.now().isoformat()}] Received critique from nested Langflow structure (outputs.COMPONENT.text).", file=sys.stderr)
                        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {critique[:500]}...", file=sys.stderr)
                        return critique
            elif "results" in first_output_element and isinstance(first_output_element["results"], dict):
                 # Langflow's /api/v1/run/{flow_id}/ KEEPS CHANGING.
                 # Sometimes it's {"results": {"COMPONENT_NAME": {"message": {"text": "output"}}}}
                 # or {"results": {"COMPONENT_NAME": {"artifacts": [], "text": "output"}}}
                results_dict = first_output_element["results"]
                for component_result in results_dict.values():
                    if isinstance(component_result, dict):
                        if "message" in component_result and isinstance(component_result["message"], dict) and "text" in component_result["message"]:
                            critique = component_result["message"]["text"]
                            print(f"DEBUG: [%{datetime.now().isoformat()}] Received critique from Langflow 'results.COMPONENT.message.text' structure.", file=sys.stderr)
                            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {critique[:500]}...", file=sys.stderr)
                            return critique
                        elif "text" in component_result: # Direct text output from a component in results
                            critique = component_result["text"]
                            print(f"DEBUG: [%{datetime.now().isoformat()}] Received critique from Langflow 'results.COMPONENT.text' structure.", file=sys.stderr)
                            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {critique[:500]}...", file=sys.stderr)
                            return critique


            # Fallback if the above structures are not found but there's some message text
            # This is a common pattern for Langflow outputs that are just text.
            if "message" in first_output_element and isinstance(first_output_element["message"], dict) and "text" in first_output_element["message"]:
                 critique = first_output_element["message"]["text"]
                 print(f"DEBUG: [%{datetime.now().isoformat()}] Received critique from Langflow 'outputs[0].message.text' structure.", file=sys.stderr)
                 print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {critique[:500]}...", file=sys.stderr)
                 return critique


        except (KeyError, TypeError, IndexError) as e:
            print(f"DEBUG: [%{datetime.now().isoformat()}] Error parsing known nested Langflow API response structure: {e}", file=sys.stderr)
            print(f"Full response: {response_json}", file=sys.stderr) # This existing print is fine
            value_to_return = json.dumps({"error": f"Could not find 'critique' or known nested text field in Langflow API response. Full response: {response_json}"})
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {value_to_return[:500]}...", file=sys.stderr)
            return value_to_return

    print(f"DEBUG: [%{datetime.now().isoformat()}] Error: 'critique' field (or known nested structure) not found in Langflow API response.", file=sys.stderr)
    print(f"Full response: {response_json}", file=sys.stderr) # This existing print is fine
    value_to_return = json.dumps({"error": f"'critique' field (or known nested structure) not found in Langflow API response. Full response: {response_json}"})
    print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_tool, returning to stdout: {value_to_return[:500]}...", file=sys.stderr)
    return value_to_return


def main():
    print(f"DEBUG: [%{datetime.now().isoformat()}] mcp_langflow_critique_server.py main() called with raw args: {sys.argv}", file=sys.stderr)
    parser = argparse.ArgumentParser(description="MCP server for Langflow Code Critique.")
    parser.add_argument("--tool_spec", action="store_true", help="Print tool spec and exit.")

    args, remaining_args = parser.parse_known_args()
    print(f"DEBUG: [%{datetime.now().isoformat()}] Parsed initial args: {args}, remaining_args: {remaining_args}", file=sys.stderr)

    if args.tool_spec:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Printing tool spec and exiting.", file=sys.stderr)
        print(json.dumps({"tools": [TOOL_SPEC]}))
        sys.exit(0)

    # Expect one argument: the JSON string for the tool invocation.
    if len(remaining_args) != 1:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: Expected one argument (JSON string for tool invocation). Exiting.", file=sys.stderr)
        print("Error: Expected one argument (JSON string for tool invocation).", file=sys.stderr)
        sys.exit(1)

    try:
        tool_invocation = json.loads(remaining_args[0])
        print(f"DEBUG: [%{datetime.now().isoformat()}] Parsed tool_invocation JSON: {tool_invocation}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: Invalid JSON argument: {e}. Exiting.", file=sys.stderr)
        print(f"Error: Invalid JSON argument: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(tool_invocation, dict) or "tool_name" not in tool_invocation or "arguments" not in tool_invocation:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: JSON argument must be an object with 'tool_name' and 'arguments'. Exiting.", file=sys.stderr)
        print("Error: JSON argument must be an object with 'tool_name' and 'arguments'.", file=sys.stderr)
        sys.exit(1)

    if tool_invocation["tool_name"] != TOOL_SPEC["name"]:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: Unknown tool_name '{tool_invocation['tool_name']}'. Expected '{TOOL_SPEC['name']}'. Exiting.", file=sys.stderr)
        print(f"Error: Unknown tool_name '{tool_invocation['tool_name']}'. Expected '{TOOL_SPEC['name']}'.", file=sys.stderr)
        sys.exit(1)

    tool_args = tool_invocation["arguments"]
    if not isinstance(tool_args, dict) or "code_to_critique" not in tool_args:
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: Missing 'code_to_critique' in tool arguments. Exiting.", file=sys.stderr)
        print("Error: Missing 'code_to_critique' in tool arguments.", file=sys.stderr)
        sys.exit(1)

    code = tool_args["code_to_critique"]
    print(f"DEBUG: [%{datetime.now().isoformat()}] Extracted code_to_critique (first 100 chars): {code[:100]}...", file=sys.stderr)
    if not isinstance(code, str):
        print(f"DEBUG: [%{datetime.now().isoformat()}] Error: 'code_to_critique' argument must be a string. Exiting.", file=sys.stderr)
        print("Error: 'code_to_critique' argument must be a string.", file=sys.stderr)
        sys.exit(1)

    result = run_tool(code)
    print(f"DEBUG: [%{datetime.now().isoformat()}] run_tool returned result (first 500 chars): {result[:500]}...", file=sys.stderr)

    # If run_tool returned an error JSON string, print it as is (it's already formatted for MCP error)
    # Otherwise, wrap successful result in the MCP JSON structure.
    output_for_stdout = ""
    try:
        # Check if result is an error JSON from run_tool
        error_check = json.loads(result)
        if isinstance(error_check, dict) and "error" in error_check:
            output_for_stdout = result # It's an error object, print directly
        else:
            # This case should ideally not be reached if errors are formatted correctly,
            # but as a safeguard:
            output_for_stdout = json.dumps({"result": result})
    except json.JSONDecodeError:
        # This means 'result' is a simple string (successful critique)
        output_for_stdout = json.dumps({"result": result})
    
    print(f"DEBUG: [%{datetime.now().isoformat()}] Final output to stdout (first 500 chars): {output_for_stdout[:500]}...", file=sys.stderr)
    print(output_for_stdout)

if __name__ == "__main__":
    main()
