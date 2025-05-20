import unittest
from unittest.mock import patch, MagicMock, call
import subprocess # To reference subprocess.CompletedProcess

# Assuming go_runner.py is in the same directory or accessible via PYTHONPATH
from go_runner import run_go_code 

class TestGoRunner(unittest.TestCase):

    def assertDockerCommand(self, mock_execute, expected_partial_command, call_index=-1):
        """Helper to assert that a docker command was called (similar to test_python_runner)."""
        self.assertTrue(mock_execute.call_count > 0, "Expected _execute_command_for_go to be called.")
        actual_command_args = mock_execute.call_args_list[call_index][0][0]
        is_sublist = False
        if len(actual_command_args) >= len(expected_partial_command):
            for i in range(len(actual_command_args) - len(expected_partial_command) + 1):
                if actual_command_args[i:i+len(expected_partial_command)] == expected_partial_command:
                    is_sublist = True
                    break
        self.assertTrue(is_sublist, 
                        f"Expected command {expected_partial_command} not found as sublist in actual command {actual_command_args}")

    @patch('go_runner._execute_command_for_go')
    def test_simple_go_code_success(self, mock_execute_command_for_go):
        print("\nRunning: test_simple_go_code_success (Go Runner)")
        mock_build_process = MagicMock(spec=subprocess.CompletedProcess, returncode=0, stdout="Successfully built Go image", stderr="")
        mock_run_process = MagicMock(spec=subprocess.CompletedProcess, returncode=0, stdout="Hello from Go!", stderr="")
        mock_rmi_process = MagicMock(spec=subprocess.CompletedProcess, returncode=0)

        mock_execute_command_for_go.side_effect = [
            (mock_build_process, False), # (result, timed_out)
            (mock_run_process, False),
            (mock_rmi_process, False) 
        ]

        go_code = """
package main
import "fmt"
func main() { fmt.Println("Hello from Go!") }
"""
        result = run_go_code(go_code, timeout=10)

        self.assertEqual(result['stdout'], "Hello from Go!")
        self.assertEqual(result['stderr'], "")
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['timed_out'])
        self.assertIsNone(result['error'])
        
        self.assertEqual(mock_execute_command_for_go.call_count, 3)
        self.assertDockerCommand(mock_execute_command_for_go, ["docker", "build"], call_index=0)
        self.assertDockerCommand(mock_execute_command_for_go, ["docker", "run", "--rm"], call_index=1)
        self.assertDockerCommand(mock_execute_command_for_go, ["docker", "rmi", "-f"], call_index=2)

    @patch('go_runner._execute_command_for_go')
    def test_go_code_runtime_error_panic(self, mock_execute_command_for_go):
        print("\nRunning: test_go_code_runtime_error_panic")
        mock_build_process = MagicMock(returncode=0, stdout="Built Go", stderr="")
        # Go panics often print to stderr and result in a non-zero exit code (e.g., 2 for panic)
        mock_run_process = MagicMock(returncode=2, stdout="", stderr="panic: test panic\n...stacktrace...")
        mock_rmi_process = MagicMock(returncode=0)

        mock_execute_command_for_go.side_effect = [
            (mock_build_process, False),
            (mock_run_process, False),
            (mock_rmi_process, False)
        ]
        
        go_code = "package main\nfunc main() { panic(\"test panic\") }"
        result = run_go_code(go_code, timeout=10)

        self.assertEqual(result['stdout'], "")
        self.assertIn("panic: test panic", result['stderr'])
        self.assertEqual(result['exit_code'], 2) # Common exit code for Go panics
        self.assertFalse(result['timed_out'])
        self.assertIsNone(result['error'])

    @patch('go_runner._execute_command_for_go')
    def test_go_execution_timeout(self, mock_execute_command_for_go):
        print("\nRunning: test_go_execution_timeout")
        mock_build_process = MagicMock(returncode=0, stdout="Built Go", stderr="")
        mock_run_timeout_stdout = "Partial output before Go timeout"
        mock_run_timeout_stderr = "Some Go stderr before timeout"
        mock_run_process_timeout_obj = MagicMock(spec=subprocess.CompletedProcess, 
                                                 returncode=-1, # Or 137
                                                 stdout=mock_run_timeout_stdout, 
                                                 stderr=mock_run_timeout_stderr)
        mock_rmi_process = MagicMock(returncode=0)

        mock_execute_command_for_go.side_effect = [
            (mock_build_process, False),
            (mock_run_process_timeout_obj, True), # Docker run times out
            (mock_rmi_process, False)
        ]

        go_code = "package main\nimport \"time\"; func main() { time.Sleep(5 * time.Second) }"
        result = run_go_code(go_code, timeout=1) 

        self.assertTrue(result['timed_out'])
        self.assertEqual(result['stdout'], mock_run_timeout_stdout)
        self.assertIn("Execution timed out after 1 seconds.", result['stderr'])
        self.assertIsNone(result['error'])

    @patch('go_runner._execute_command_for_go')
    def test_go_docker_build_fails(self, mock_execute_command_for_go):
        print("\nRunning: test_go_docker_build_fails")
        mock_build_fail_stdout = "Go build stdout..."
        mock_build_fail_stderr = "Error: Go Docker build command failed (e.g. compilation error)"
        mock_build_process_fail = MagicMock(spec=subprocess.CompletedProcess, 
                                            returncode=1, 
                                            stdout=mock_build_fail_stdout, 
                                            stderr=mock_build_fail_stderr)
        
        mock_execute_command_for_go.side_effect = [
            (mock_build_process_fail, False) 
        ]

        result = run_go_code("package main\nfunc main() { var x int = \"string\" }", timeout=10) # Compilation error

        self.assertIsNotNone(result['error'])
        self.assertIn("Docker image build for Go failed", result['error'])
        self.assertIn(mock_build_fail_stderr, result['stderr'])
        self.assertEqual(result['exit_code'], 1)
        self.assertFalse(result['timed_out'])
        self.assertEqual(mock_execute_command_for_go.call_count, 1)
        self.assertDockerCommand(mock_execute_command_for_go, ["docker", "build"], call_index=0)

    @patch('go_runner._execute_command_for_go')
    def test_go_docker_command_not_found(self, mock_execute_command_for_go):
        print("\nRunning: test_go_docker_command_not_found")
        mock_build_fnf_stderr = "Command not found: docker"
        mock_build_fnf_obj = MagicMock(spec=subprocess.CompletedProcess,
                                       returncode=-1,
                                       stdout="",
                                       stderr=mock_build_fnf_stderr)
        
        mock_execute_command_for_go.side_effect = [
             (mock_build_fnf_obj, False)
        ]

        result = run_go_code("package main", timeout=10)

        self.assertIsNotNone(result['error'])
        self.assertIn("Docker image build for Go failed", result['error']) 
        self.assertIn(mock_build_fnf_stderr, result['stderr'])
        self.assertFalse(result['timed_out'])
        self.assertEqual(mock_execute_command_for_go.call_count, 1)

if __name__ == '__main__':
    unittest.main()
