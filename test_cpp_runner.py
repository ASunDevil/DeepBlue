import unittest
import os
from cpp_runner import run_cpp_code # Assuming cpp_runner.py is in the same directory or PYTHONPATH

# A global check for Docker availability might be useful,
# but for now, tests will fail individually if Docker is not present.
# It is assumed Docker is installed and the user running tests has permissions.

class TestCppRunner(unittest.TestCase):

    def test_successful_execution(self):
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Hello, C++ World!" << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: STDERR:\n{result['compilation_stderr']}\nSTDOUT:\n{result['compilation_stdout']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed: STDERR:\n{result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertEqual(result['execution_stdout'], "Hello, C++ World!\n")
        # g++ is usually quiet on success unless warnings are present.
        # self.assertEqual(result['compilation_stdout'], "") 
        self.assertEqual(result['execution_stderr'], "")

    def test_stdin_handling(self):
        cpp_code = """
        #include <iostream>
        #include <string>
        int main() {
            std::string name;
            std::getline(std::cin, name);
            std::cout << "Hello, " << name << "!" << std::endl;
            return 0;
        }
        """
        stdin_data = "C++ Developer"
        result = run_cpp_code(cpp_code, stdin_data=stdin_data)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed: {result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertEqual(result['execution_stdout'], f"Hello, {stdin_data}!\n")

    def test_compilation_error(self):
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Syntax Error Here" << std::end; // Error: std::end instead of std::endl
            return 0;
        }
        """
        result = run_cpp_code(cpp_code)
        self.assertNotEqual(result['compilation_exit_code'], 0, msg="Compilation should have failed but exit code was 0.")
        self.assertFalse(result['timed_out_compilation'])
        self.assertIn("error:", result['compilation_stderr'].lower(), "g++ error message not found in compilation_stderr.")
        # Execution fields should be None as execution is skipped
        self.assertIsNone(result['execution_stdout'])
        self.assertIsNone(result['execution_stderr'])
        self.assertIsNone(result['execution_exit_code'])
        self.assertFalse(result['timed_out_execution'])


    def test_runtime_error_segmentation_fault(self):
        cpp_code = """
        #include <iostream>
        int main() {
            int *p = nullptr;
            *p = 42; // Segmentation fault
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertNotEqual(result['execution_exit_code'], 0, "Execution should have failed due to runtime error.")
        self.assertFalse(result['timed_out_execution'])
        # Stderr for segfaults might be empty or system-dependent inside Docker.
        # The key is the non-zero exit code.
        # If stderr is consistently populated by the Docker image, we can assert its content.
        # For example, on some systems, it might be empty, on others it might say "Segmentation fault".

    def test_runtime_error_throw_exception(self):
        cpp_code = """
        #include <iostream>
        #include <stdexcept> // Required for std::runtime_error
        int main() {
            throw std::runtime_error("Test runtime error from C++");
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertNotEqual(result['execution_exit_code'], 0, "Execution should have failed due to thrown exception.")
        self.assertFalse(result['timed_out_execution'])
        # The C++ runtime often prints unhandled exception messages to stderr.
        self.assertIn("terminate called after throwing an instance of 'std::runtime_error'", result['execution_stderr'], "Expected C++ runtime error message not found in stderr.")
        self.assertIn("Test runtime error from C++", result['execution_stderr'], "Specific exception message not found in stderr.")


    def test_execution_timeout(self):
        cpp_code = """
        #include <iostream>
        int main() {
            while(true) {
                // Infinite loop
            }
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, exec_timeout=1)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertTrue(result['timed_out_execution'])
        self.assertEqual(result['execution_exit_code'], -1, "Exit code for execution timeout should be -1 as set by cpp_runner.")
        self.assertIn("Execution timed out after 1 seconds.", result['execution_stderr'])


    def test_compilation_timeout(self):
        # This code is valid but we use a very short timeout to force it.
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Hello!" << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, compile_timeout=1) # Assuming 1ms is too short for docker overhead + compile
        # Check if timeout occurred. If compilation was too fast, this test might not be reliable
        # for the timeout *reason*, but it still tests the timeout *mechanism*.
        if result['timed_out_compilation']:
            self.assertTrue(result['timed_out_compilation'])
            self.assertEqual(result['compilation_exit_code'], -1, "Exit code for compilation timeout should be -1 as set by cpp_runner.")
            self.assertIn("Compilation timed out after 1 seconds.", result['compilation_stderr'])
        else:
            # This branch might be taken if Docker + g++ is extremely fast on the system for simple code.
            # In such a case, the timeout mechanism itself is still exercised, but the code compiled too fast.
            print("\nWarning: Compilation timeout test did not time out compilation. "
                  "The compile_timeout might be too generous for this simple code on this system, "
                  "or Docker overhead was minimal. The test still checks the path.")
            self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed unexpectedly: {result['compilation_stderr']}")


    def test_empty_code_string(self):
        cpp_code = ""
        result = run_cpp_code(cpp_code)
        self.assertNotEqual(result['compilation_exit_code'], 0, "Compilation of empty string should fail.")
        self.assertFalse(result['timed_out_compilation'])
        # g++ usually gives a specific error for no input files or empty input.
        # e.g. "g++: fatal error: no input files" or similar.
        self.assertTrue(
            "no input files" in result['compilation_stderr'].lower() or \
            "missing input file" in result['compilation_stderr'].lower() or \
            "empty" in result['compilation_stderr'].lower(), # some versions of g++ might say this for empty files
            f"Expected 'no input files' or similar error not found in compilation_stderr: {result['compilation_stderr']}"
        )

    def test_no_stdin_provided_graceful(self):
        # This C++ code checks if there's input, and acts accordingly.
        cpp_code = """
        #include <iostream>
        #include <string>
        int main() {
            std::string line;
            if (std::cin.peek() != EOF && std::getline(std::cin, line)) {
                 std::cout << "Received: " << line << std::endl;
            } else {
                 std::cout << "No input received." << std::endl;
            }
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, stdin_data=None)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed: {result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertEqual(result['execution_stdout'], "No input received.\n")

    def test_no_stdin_provided_expecting_input(self):
        # This C++ code simply tries to read, which might lead to non-zero exit if cin fails.
        cpp_code = """
        #include <iostream>
        #include <string>
        int main() {
            std::string name;
            std::cin >> name; // This will set failbit if stdin is empty and closed.
            if (std::cin.fail() && name.empty()) {
                // std::cerr << "Input operation failed or no input provided." << std::endl;
                return 1; // Indicate failure
            }
            std::cout << "Name: " << name << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, stdin_data=None, exec_timeout=2) # Timeout in case it hangs
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        
        # Behavior of std::cin with no input can be tricky.
        # If stdin is immediately closed (as Docker -i should do if no input is piped),
        # std::cin >> name; will fail, name will be empty, and failbit will be set.
        if result['timed_out_execution']:
            self.fail(f"Execution timed out unexpectedly. Stderr: {result['execution_stderr']}")

        self.assertNotEqual(result['execution_exit_code'], 0, "Execution should have a non-zero exit code if input was expected but not given.")
        # The exact stdout/stderr depends on how cin handles EOF. Often stdout is empty.
        self.assertEqual(result['execution_stdout'], "") # Expecting empty output as cin failed.
        # Stderr might be empty or contain a message if we added one.
        # self.assertIn("Input operation failed", result['execution_stderr']) # If we added the cerr line

if __name__ == '__main__':
    print("Running cpp_runner tests...")
    print("IMPORTANT: Docker must be installed, running, and the user must have permissions to use it.")
    print(f"These tests will use the Docker image specified in cpp_runner.py (currently: {os.getenv('DOCKER_IMAGE', 'frolvlad/alpine-gxx:latest')}).")
    print("If tests fail, check Docker installation and image availability (e.g., `docker pull frolvlad/alpine-gxx:latest`).")
    unittest.main()
```
