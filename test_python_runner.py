import unittest
from unittest.mock import patch, MagicMock, call
import subprocess # To reference subprocess.CompletedProcess and TimeoutExpired

# Assuming python_runner.py is in the same directory or accessible via PYTHONPATH
from python_runner import run_python_code 

class TestPythonRunner(unittest.TestCase):

    def assertDockerCommand(self, mock_execute, expected_partial_command, call_index=-1):
        """Helper to assert that a docker command was called."""
        self.assertTrue(mock_execute.call_count > 0, "Expected _execute_command to be called.")
        actual_command_args = mock_execute.call_args_list[call_index][0][0] # First arg of the specific call
        # Check if expected_partial_command is a sublist of actual_command_args
        # This allows checking for key parts of the command without matching the full unique tag.
        is_sublist = False
        if len(actual_command_args) >= len(expected_partial_command):
            for i in range(len(actual_command_args) - len(expected_partial_command) + 1):
                if actual_command_args[i:i+len(expected_partial_command)] == expected_partial_command:
                    is_sublist = True
                    break
        self.assertTrue(is_sublist, 
                        f"Expected command {{expected_partial_command}} not found as sublist in actual command {{actual_command_args}}")

    @patch('python_runner._execute_command')
    def test_simple_python_code_success(self, mock_execute_command):
        print("\nRunning: test_simple_python_code_success")
        # Mock docker build: success
        mock_build_process = MagicMock(spec=subprocess.CompletedProcess)
        mock_build_process.returncode = 0
        mock_build_process.stdout = "Successfully built image"
        mock_build_process.stderr = ""
        
        # Mock docker run: success
        mock_run_process = MagicMock(spec=subprocess.CompletedProcess)
        mock_run_process.returncode = 0
        mock_run_process.stdout = "Hello from Python!"
        mock_run_process.stderr = ""
        
        # Mock docker rmi: success
        mock_rmi_process = MagicMock(spec=subprocess.CompletedProcess)
        mock_rmi_process.returncode = 0

        mock_execute_command.side_effect = [
            (mock_build_process, False), # (result, timed_out)
            (mock_run_process, False),
            (mock_rmi_process, False) 
        ]

        code = "print('Hello from Python!')"
        result = run_python_code(code, timeout=10)

        self.assertEqual(result['stdout'], "Hello from Python!")
        self.assertEqual(result['stderr'], "")
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['timed_out'])
        self.assertIsNone(result['error'])
        
        self.assertEqual(mock_execute_command.call_count, 3)
        self.assertDockerCommand(mock_execute_command, ["docker", "build"], call_index=0)
        self.assertDockerCommand(mock_execute_command, ["docker", "run", "--rm"], call_index=1)
        self.assertDockerCommand(mock_execute_command, ["docker", "rmi", "-f"], call_index=2)

    @patch('python_runner._execute_command')
    def test_python_code_with_requirements_success(self, mock_execute_command):
        print("\nRunning: test_python_code_with_requirements_success")
        mock_build_process = MagicMock(returncode=0, stdout="Built", stderr="")
        mock_run_process = MagicMock(returncode=0, stdout="requests version: 2.25.1", stderr="")
        mock_rmi_process = MagicMock(returncode=0)

        mock_execute_command.side_effect = [
            (mock_build_process, False),
            (mock_run_process, False),
            (mock_rmi_process, False)
        ]

        code = "import requests; print(f'requests version: {requests.__version__}')"
        requirements = ["requests==2.25.1"]
        result = run_python_code(code, requirements=requirements, timeout=20)

        self.assertEqual(result['stdout'], "requests version: 2.25.1")
        self.assertEqual(result['exit_code'], 0)
        self.assertIsNone(result['error'])
        self.assertEqual(mock_execute_command.call_count, 3)
        # Further checks on Dockerfile content could be done by also mocking open/write if needed

    @patch('python_runner._execute_command')
    def test_python_code_runtime_error(self, mock_execute_command):
        print("\nRunning: test_python_code_runtime_error")
        mock_build_process = MagicMock(returncode=0, stdout="Built", stderr="")
        # Simulate stderr output and non-zero exit code from docker run
        mock_run_process = MagicMock(returncode=1, stdout="", stderr="Traceback...\nValueError: Test error")
        mock_rmi_process = MagicMock(returncode=0)

        mock_execute_command.side_effect = [
            (mock_build_process, False),
            (mock_run_process, False),
            (mock_rmi_process, False)
        ]
        
        code = "raise ValueError('Test error')"
        result = run_python_code(code, timeout=10)

        self.assertEqual(result['stdout'], "")
        self.assertIn("ValueError: Test error", result['stderr'])
        self.assertEqual(result['exit_code'], 1)
        self.assertFalse(result['timed_out'])
        self.assertIsNone(result['error'])

    @patch('python_runner._execute_command')
    def test_execution_timeout(self, mock_execute_command):
        print("\nRunning: test_execution_timeout")
        mock_build_process = MagicMock(returncode=0, stdout="Built", stderr="")
        # Simulate timeout for docker run
        # _execute_command returns (CompletedProcess_like_object, True) for timeout
        mock_run_process_timeout_stdout = "Partial output before timeout"
        mock_run_process_timeout_stderr = "Looping..." # Some stderr that might have occurred
        mock_run_process_timeout_obj = MagicMock(spec=subprocess.CompletedProcess)
        mock_run_process_timeout_obj.returncode = -1 # Or specific code like 137
        mock_run_process_timeout_obj.stdout = mock_run_process_timeout_stdout
        mock_run_process_timeout_obj.stderr = mock_run_process_timeout_stderr
        
        mock_rmi_process = MagicMock(returncode=0)

        mock_execute_command.side_effect = [
            (mock_build_process, False),
            (mock_run_process_timeout_obj, True), # Docker run times out
            (mock_rmi_process, False)
        ]

        code = "import time; time.sleep(5)"
        result = run_python_code(code, timeout=1) # Script sleeps 5s, runner timeout 1s

        self.assertTrue(result['timed_out'])
        self.assertEqual(result['stdout'], mock_run_process_timeout_stdout)
        self.assertIn("Execution timed out after 1 seconds.", result['stderr'])
        # Exit code for timeout can be platform/Docker dependent, often 137 or -1 if killed by SIGKILL
        # self.assertNotEqual(result['exit_code'], 0) # Check it's non-zero or specific timeout code
        self.assertIsNone(result['error'])

    @patch('python_runner._execute_command')
    def test_docker_build_fails(self, mock_execute_command):
        print("\nRunning: test_docker_build_fails")
        # Simulate Docker build failure
        mock_build_process_fail = MagicMock(spec=subprocess.CompletedProcess)
        mock_build_process_fail.returncode = 1
        mock_build_process_fail.stdout = "Some build stdout info"
        mock_build_process_fail.stderr = "Error: Docker build command failed..."
        
        mock_execute_command.side_effect = [
            (mock_build_process_fail, False) # Build fails, no run or rmi should be called after this
        ]

        result = run_python_code("print('hello')", timeout=10)

        self.assertIsNotNone(result['error'])
        self.assertIn("Docker image build failed", result['error'])
        self.assertIn("Error: Docker build command failed...", result['stderr'])
        self.assertNotEqual(result['exit_code'], 0) # Should be build's exit code
        self.assertFalse(result['timed_out'])
        
        # Only docker build should have been attempted
        self.assertEqual(mock_execute_command.call_count, 1)
        self.assertDockerCommand(mock_execute_command, ["docker", "build"], call_index=0)


    @patch('python_runner._execute_command')
    def test_docker_command_not_found(self, mock_execute_command):
        print("\nRunning: test_docker_command_not_found")
        # Simulate FileNotFoundError for the first docker command (build)
        mock_build_fnf_obj = MagicMock(spec=subprocess.CompletedProcess)
        mock_build_fnf_obj.returncode = -1 # Custom code for internal tracking perhaps
        mock_build_fnf_obj.stdout = ""
        mock_build_fnf_obj.stderr = "Command not found: docker" # As per _execute_command
        
        mock_execute_command.side_effect = [
             (mock_build_fnf_obj, False) # Simulate FileNotFoundError from _execute_command
        ]

        result = run_python_code("print('hello')", timeout=10)

        self.assertIsNotNone(result['error'])
        # The error is now caught by the build failure check primarily
        self.assertIn("Docker image build failed", result['error']) 
        self.assertIn("Command not found: docker", result['stderr'])
        self.assertFalse(result['timed_out'])
        self.assertEqual(mock_execute_command.call_count, 1)

    @patch('python_runner.tempfile.mkdtemp')
    @patch('python_runner._execute_command')
    def test_temp_dir_creation_fails(self, mock_execute_command, mock_mkdtemp):
        print("\nRunning: test_temp_dir_creation_fails")
        mock_mkdtemp.side_effect = OSError("Permission denied")

        result = run_python_code("print('hello')", timeout=10)

        self.assertIsNotNone(result['error'])
        self.assertIn("Error during setup or Docker preparation: Permission denied", result['error'])
        self.assertEqual(mock_execute_command.call_count, 0) # Docker shouldn't be called

    # TODO: Add tests for build timeout
    # TODO: Add tests for Docker rmi failure (should be warning, not affect primary result)

if __name__ == '__main__':
    unittest.main()
