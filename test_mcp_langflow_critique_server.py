import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import sys
import io

# Add the directory containing mcp_langflow_critique_server to sys.path
# This is to ensure the module can be imported for testing
# In a real package structure, this might not be needed if using proper installation
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the module to be tested
try:
    import mcp_langflow_critique_server
except ModuleNotFoundError:
    # This might happen if the script is not directly in the same dir as test_mcp_langflow_critique_server.py
    # or if there's an issue with how it's being run.
    # For this environment, assuming they are in the same directory.
    print("Failed to import mcp_langflow_critique_server. Ensure it's in the same directory or adjust PYTHONPATH.", file=sys.stderr)
    raise

# Capture stderr for some tests
captured_stderr = io.StringIO()
sys.stderr = captured_stderr

class TestMCPLangflowCritiqueServer(unittest.TestCase):

    def setUp(self):
        # Reset stderr capture for each test
        captured_stderr.truncate(0)
        captured_stderr.seek(0)
        # Store original os.environ and sys.argv
        self.original_environ = os.environ.copy()
        self.original_argv = sys.argv.copy()
        # Ensure LANGFLOW_CRITIQUE_API_URL is not set by default for some tests
        if "LANGFLOW_CRITIQUE_API_URL" in os.environ:
            del os.environ["LANGFLOW_CRITIQUE_API_URL"]

    def tearDown(self):
        # Restore original os.environ and sys.argv
        os.environ.clear()
        os.environ.update(self.original_environ)
        sys.argv = self.original_argv
        sys.stderr = sys.__stderr__ # Restore original stderr

    def test_tool_spec_output(self):
        """Test that --tool_spec prints the tool specification and exits."""
        sys.argv = ["mcp_langflow_critique_server.py", "--tool_spec"]
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 0)
            output = json.loads(mock_stdout.getvalue())
            self.assertIn("tools", output)
            self.assertEqual(len(output["tools"]), 1)
            self.assertEqual(output["tools"][0]["name"], "critique_code")

    @patch('mcp_langflow_critique_server.requests.post')
    def test_successful_critique_direct_response(self, mock_post):
        """Test a successful critique with the ideal direct JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"critique": "This is a test critique."}
        mock_post.return_value = mock_response

        code_to_critique = "def hello(): print('world')"
        result_str = mcp_langflow_critique_server.run_tool(code_to_critique)
        
        self.assertEqual(result_str, "This is a test critique.")
        mock_post.assert_called_once_with(
            mcp_langflow_critique_server.DEFAULT_LANGFLOW_API_URL,
            json={"code": code_to_critique},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        self.assertIn("Received critique.", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_successful_critique_nested_outputs_text_response(self, mock_post):
        """Test successful critique with {"outputs": [{"outputs": {"comp": {"text": "..."}}}]} structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "outputs": [{
                "outputs": {
                    "critique_component_abc": {"text": "Nested output critique."}
                }
            }]
        }
        mock_post.return_value = mock_response
        result = mcp_langflow_critique_server.run_tool("code")
        self.assertEqual(result, "Nested output critique.")
        self.assertIn("Received critique from nested Langflow structure.", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_successful_critique_nested_results_message_text_response(self, mock_post):
        """Test successful critique with {"outputs": [{"results": {"comp": {"message": {"text": "..."}}}]} structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "outputs": [{
                "results": {
                    "critique_component_xyz": {"message": {"text": "Results message critique."}}
                }
            }]
        }
        mock_post.return_value = mock_response
        result = mcp_langflow_critique_server.run_tool("code")
        self.assertEqual(result, "Results message critique.")
        self.assertIn("Received critique from Langflow 'results.COMPONENT.message.text' structure.", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_successful_critique_nested_results_text_response(self, mock_post):
        """Test successful critique with {"outputs": [{"results": {"comp": {"text": "..."}}}]} structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "outputs": [{
                "results": {
                    "critique_component_123": {"text": "Results direct text critique."}
                }
            }]
        }
        mock_post.return_value = mock_response
        result = mcp_langflow_critique_server.run_tool("code")
        self.assertEqual(result, "Results direct text critique.")
        self.assertIn("Received critique from Langflow 'results.COMPONENT.text' structure.", captured_stderr.getvalue())


    @patch('mcp_langflow_critique_server.requests.post')
    def test_successful_critique_fallback_message_text_response(self, mock_post):
        """Test successful critique with {"outputs": [{"message": {"text": "..."}}]} fallback structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "outputs": [{
                "message": {"text": "Fallback message critique."}
            }]
        }
        mock_post.return_value = mock_response
        result = mcp_langflow_critique_server.run_tool("code")
        self.assertEqual(result, "Fallback message critique.")
        self.assertIn("Received critique from Langflow 'outputs[0].message.text' structure.", captured_stderr.getvalue())


    @patch('mcp_langflow_critique_server.requests.post')
    def test_langflow_api_http_error(self, mock_post):
        """Test handling of an HTTP error from Langflow API."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error", response=mock_response)
        mock_response.text = "Internal Server Error" # For error detail
        mock_post.return_value = mock_response

        result_str = mcp_langflow_critique_server.run_tool("some code")
        result_json = json.loads(result_str)
        self.assertIn("error", result_json)
        self.assertIn("Failed to connect to Langflow API", result_json["error"])
        self.assertIn("Server Error", result_json["error"])
        self.assertIn("Internal Server Error", result_json["error"]) # Detail check
        self.assertIn("Error calling Langflow API", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_network_error(self, mock_post):
        """Test handling of a network error (e.g., ConnectionError)."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result_str = mcp_langflow_critique_server.run_tool("some code")
        result_json = json.loads(result_str)
        self.assertIn("error", result_json)
        self.assertIn("Failed to connect to Langflow API", result_json["error"])
        self.assertIn("Connection failed", result_json["error"])
        self.assertIn("Error calling Langflow API: Connection failed", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_timeout_error(self, mock_post):
        """Test handling of a timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result_str = mcp_langflow_critique_server.run_tool("some code")
        result_json = json.loads(result_str)
        self.assertIn("error", result_json)
        self.assertIn("Langflow API request timed out", result_json["error"])
        self.assertIn("Request timed out", result_json["error"])
        self.assertIn("Error calling Langflow API: Timeout - Request timed out", captured_stderr.getvalue())


    @patch('mcp_langflow_critique_server.requests.post')
    def test_malformed_json_response(self, mock_post):
        """Test handling of a malformed JSON response from Langflow API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_response.text = "This is not JSON" # For logging
        mock_post.return_value = mock_response

        result_str = mcp_langflow_critique_server.run_tool("some code")
        result_json = json.loads(result_str)
        self.assertIn("error", result_json)
        self.assertIn("Invalid JSON response from Langflow API", result_json["error"])
        self.assertIn("Error decoding JSON response from Langflow API", captured_stderr.getvalue())
        self.assertIn("Response text: This is not JSON", captured_stderr.getvalue())

    @patch('mcp_langflow_critique_server.requests.post')
    def test_missing_critique_key_in_response(self, mock_post):
        """Test handling when 'critique' key (or known nested structure) is missing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "This is a valid JSON but no critique."}
        mock_post.return_value = mock_response

        result_str = mcp_langflow_critique_server.run_tool("some code")
        result_json = json.loads(result_str)
        self.assertIn("error", result_json)
        self.assertIn("'critique' field (or known nested structure) not found", result_json["error"])
        self.assertIn("Error: 'critique' field (or known nested structure) not found", captured_stderr.getvalue())
        self.assertIn("Full response: {'message': 'This is a valid JSON but no critique.'}", captured_stderr.getvalue())

    @patch.dict(os.environ, {"LANGFLOW_CRITIQUE_API_URL": "http://custom.test.url/api"})
    @patch('mcp_langflow_critique_server.requests.post')
    def test_custom_api_url_from_env_variable(self, mock_post):
        """Test that a custom API URL is used when LANGFLOW_CRITIQUE_API_URL is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"critique": "Critique from custom URL."}
        mock_post.return_value = mock_response

        code_to_critique = "def custom_url_test(): pass"
        result_str = mcp_langflow_critique_server.run_tool(code_to_critique)

        self.assertEqual(result_str, "Critique from custom URL.")
        mock_post.assert_called_once_with(
            "http://custom.test.url/api",
            json={"code": code_to_critique},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        self.assertIn("Attempting to critique code using Langflow API: http://custom.test.url/api", captured_stderr.getvalue())

    def test_main_function_tool_spec(self):
        """Test main function with --tool_spec argument."""
        sys.argv = ["mcp_langflow_critique_server.py", "--tool_spec"]
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 0)
            self.assertIn('"name": "critique_code"', mock_stdout.getvalue())

    @patch('mcp_langflow_critique_server.run_tool')
    def test_main_function_successful_run(self, mock_run_tool):
        """Test main function with a successful tool invocation."""
        expected_critique = "This is a great piece of code!"
        mock_run_tool.return_value = expected_critique
        
        tool_invocation_json = json.dumps({
            "tool_name": "critique_code",
            "arguments": {"code_to_critique": "print('hello')"}
        })
        sys.argv = ["mcp_langflow_critique_server.py", tool_invocation_json]

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            mcp_langflow_critique_server.main()
            result = json.loads(mock_stdout.getvalue())
            self.assertEqual(result, {"result": expected_critique})
        mock_run_tool.assert_called_once_with("print('hello')")

    @patch('mcp_langflow_critique_server.run_tool')
    def test_main_function_run_tool_returns_error_json(self, mock_run_tool):
        """Test main function when run_tool itself returns a JSON error string."""
        error_payload = {"error": "Something bad happened in run_tool"}
        mock_run_tool.return_value = json.dumps(error_payload)
        
        tool_invocation_json = json.dumps({
            "tool_name": "critique_code",
            "arguments": {"code_to_critique": "print('hello')"}
        })
        sys.argv = ["mcp_langflow_critique_server.py", tool_invocation_json]

        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            mcp_langflow_critique_server.main()
            result = json.loads(mock_stdout.getvalue())
            self.assertEqual(result, error_payload) # Should print the error JSON directly
        mock_run_tool.assert_called_once_with("print('hello')")


    def test_main_function_invalid_json_arg(self):
        """Test main function with invalid JSON argument."""
        sys.argv = ["mcp_langflow_critique_server.py", "{not_json"]
        with patch('sys.stdout', new_callable=io.StringIO): # Suppress print to stdout
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Invalid JSON argument", captured_stderr.getvalue())

    def test_main_function_missing_args(self):
        """Test main function with missing arguments."""
        sys.argv = ["mcp_langflow_critique_server.py"]
        with patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Expected one argument", captured_stderr.getvalue())

    def test_main_function_wrong_tool_name(self):
        """Test main function with incorrect tool name in JSON."""
        tool_invocation_json = json.dumps({
            "tool_name": "wrong_tool",
            "arguments": {"code_to_critique": "code"}
        })
        sys.argv = ["mcp_langflow_critique_server.py", tool_invocation_json]
        with patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Unknown tool_name 'wrong_tool'", captured_stderr.getvalue())

    def test_main_function_missing_code_to_critique(self):
        """Test main function with missing 'code_to_critique' in arguments."""
        tool_invocation_json = json.dumps({
            "tool_name": "critique_code",
            "arguments": {} # Missing code_to_critique
        })
        sys.argv = ["mcp_langflow_critique_server.py", tool_invocation_json]
        with patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Missing 'code_to_critique' in tool arguments.", captured_stderr.getvalue())
    
    def test_main_function_code_to_critique_not_string(self):
        """Test main function with 'code_to_critique' not being a string."""
        tool_invocation_json = json.dumps({
            "tool_name": "critique_code",
            "arguments": {"code_to_critique": 123} # Not a string
        })
        sys.argv = ["mcp_langflow_critique_server.py", tool_invocation_json]
        with patch('sys.stdout', new_callable=io.StringIO): # Suppress print to stdout
            with self.assertRaises(SystemExit) as cm:
                mcp_langflow_critique_server.main()
            self.assertEqual(cm.exception.code, 1) # Exit code 1 for error
        self.assertIn("Error: 'code_to_critique' argument must be a string.", captured_stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
