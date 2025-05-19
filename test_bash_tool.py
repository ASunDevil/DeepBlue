import unittest
import os
import tempfile
import shutil
from bash_tool import run_bash_command

class TestRunBashCommand(unittest.TestCase):

    def test_basic_command_stdout(self):
        """Test a simple command and verify stdout."""
        result = run_bash_command("echo 'hello world'")
        self.assertEqual(result["stdout"], "hello world\n")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])

    def test_basic_command_stderr(self):
        """Test a command that produces output to stderr."""
        # Use bash -c to ensure redirection is handled by a shell
        result = run_bash_command("bash -c \"echo 'error message' >&2\"")
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "error message\n")
        self.assertEqual(result["exit_code"], 0) # The bash command itself succeeds
        self.assertFalse(result["timed_out"])

    def test_successful_exit_code(self):
        """Test a command that exits successfully (exit code 0)."""
        result = run_bash_command("true") # 'true' command always exits with 0
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "")
        self.assertFalse(result["timed_out"])

    def test_nonzero_exit_code(self):
        """Test a command that exits with a non-zero exit code."""
        result = run_bash_command("false") # 'false' command always exits with 1
        self.assertNotEqual(result["exit_code"], 0)
        # Specific exit code for 'false' can vary, but it's usually 1
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "")
        self.assertFalse(result["timed_out"])

    def test_command_within_timeout(self):
        """Test a command that completes well within the timeout."""
        result = run_bash_command("sleep 0.1", timeout=5)
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])

    def test_command_exceeds_timeout(self):
        """Test a command that sleeps longer than the timeout value."""
        result = run_bash_command("sleep 5", timeout=1)
        self.assertTrue(result["timed_out"])
        self.assertIn("timed out", result["stderr"].lower())
        # Exit code for timeout is set to -1 in the tool
        self.assertEqual(result["exit_code"], -1)

    def test_working_directory(self):
        """Test a command that depends on the working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy file in the temporary directory
            with open(os.path.join(tmpdir, "test_file.txt"), "w") as f:
                f.write("test content")

            result_ls = run_bash_command("ls", working_directory=tmpdir)
            self.assertEqual(result_ls["exit_code"], 0)
            self.assertIn("test_file.txt", result_ls["stdout"])

            result_pwd = run_bash_command("pwd", working_directory=tmpdir)
            self.assertEqual(result_pwd["exit_code"], 0)
            # Resolve symbolic links for comparison, as pwd might return a symlinked path
            self.assertEqual(os.path.realpath(result_pwd["stdout"].strip()), os.path.realpath(tmpdir))


    def test_non_existent_command(self):
        """Test a non-existent command."""
        command = "non_existent_command_abc123_xyz"
        result = run_bash_command(command)
        self.assertNotEqual(result["exit_code"], 0)
        # Exit code for command not found is set to -1 in the tool, after FileNotFoundError
        self.assertEqual(result["exit_code"], -1)
        self.assertIn(f"Error: Command or executable not found: {command}", result["stderr"])
        self.assertFalse(result["timed_out"])

    def test_empty_command_string(self):
        """Test behavior with an empty command string."""
        result = run_bash_command("")
        # shlex.split('') returns [], which is now handled explicitly.
        self.assertEqual(result["exit_code"], -1)
        self.assertEqual(result["stderr"], "Error: Empty command provided.")
        self.assertEqual(result["stdout"], "")
        self.assertFalse(result["timed_out"])

    def test_command_with_semicolon(self):
        """Test a command with a semicolon."""
        # shlex.split should handle this by treating 'echo "hello;' and 'world"' as separate arguments if not quoted properly.
        # If we want to execute two commands, we'd typically pass them as "bash -c 'echo hello; echo world'"
        # The current tool is designed to run *a* command, not a shell script directly unless invoked via "bash -c"
        # Let's test `echo "hello; world"` which should print the literal string.
        result = run_bash_command('echo "hello; world"')
        self.assertEqual(result["stdout"], "hello; world\n")
        self.assertEqual(result["exit_code"], 0)

    def test_command_with_quotes_and_spaces(self):
        """Test a command with quotes and spaces."""
        # shlex.split handles quotes well.
        result = run_bash_command('echo \'hello "world"\'') # echo 'hello "world"'
        self.assertEqual(result["stdout"], 'hello "world"\n')
        self.assertEqual(result["exit_code"], 0)

    def test_command_as_list(self):
        """Test when the command is passed as a list of arguments."""
        result = run_bash_command(["echo", "hello", "list"])
        self.assertEqual(result["stdout"], "hello list\n")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["timed_out"])

if __name__ == "__main__":
    unittest.main()
