import unittest
import os
from cpp_runner import run_cpp_code # Assuming cpp_runner.py is in the same directory or PYTHONPATH

# A global check for Docker availability might be useful,
# but for now, tests will fail individually if Docker is not present.
# It is assumed Docker is installed and the user running tests has permissions.

class TestCppRunner(unittest.TestCase):

    def _run_successful_execution(self, compiler_name):
        cpp_code = f"""
        #include <iostream>
        int main() {{
            // The following output helps verify which compiler was used,
            // though the 'compiler_used' field in the result is the primary check.
            #if defined(__clang__)
                std::cout << "Hello from Clang, C++ World!" << std::endl;
            #elif defined(__GNUC__)
                std::cout << "Hello from GCC, C++ World!" << std::endl;
            #else
                std::cout << "Hello from Unknown Compiler, C++ World!" << std::endl;
            #endif
            return 0;
        }}
        """
        expected_output_fragment = "Clang" if compiler_name == "clang++" else "GCC"
        
        result = run_cpp_code(cpp_code, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: STDERR:\n{result['compilation_stderr']}\nSTDOUT:\n{result['compilation_stdout']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed for {compiler_name}: STDERR:\n{result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertIn(expected_output_fragment, result['execution_stdout'])
        self.assertEqual(result['execution_stderr'], "")

    def test_successful_execution_gpp(self):
        self._run_successful_execution("g++")

    def test_successful_execution_clangpp(self):
        self._run_successful_execution("clang++")

    def _run_stdin_handling(self, compiler_name):
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
        stdin_data = f"C++ Developer via {compiler_name}"
        result = run_cpp_code(cpp_code, stdin_data=stdin_data, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed for {compiler_name}: {result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertEqual(result['execution_stdout'], f"Hello, {stdin_data}!\n")

    def test_stdin_handling_gpp(self):
        self._run_stdin_handling("g++")

    def test_stdin_handling_clangpp(self):
        self._run_stdin_handling("clang++")

    def _run_compilation_error(self, compiler_name):
        cpp_code = """
        #include <iostream>
        int main() {
            std::cout << "Syntax Error Here" << std::end; // Error: std::end instead of std::endl
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertNotEqual(result['compilation_exit_code'], 0, f"Compilation should have failed for {compiler_name} but exit code was 0.")
        self.assertFalse(result['timed_out_compilation'])
        # Both g++ and clang++ should report "error:" for this.
        self.assertIn("error:", result['compilation_stderr'].lower(), f"Compiler error message not found in compilation_stderr for {compiler_name}.")
        # Check for specific error related to 'std::end' if consistent, otherwise generic 'error:' is fine.
        # For example, clang says "no member named 'end' in namespace 'std'", g++ says "'end' is not a member of 'std'"
        self.assertIn("end", result['compilation_stderr'].lower())
        self.assertIn("std", result['compilation_stderr'].lower())

        self.assertIsNone(result['execution_stdout'])
        self.assertIsNone(result['execution_stderr'])
        self.assertIsNone(result['execution_exit_code'])
        self.assertFalse(result['timed_out_execution'])

    def test_compilation_error_gpp(self):
        self._run_compilation_error("g++")

    def test_compilation_error_clangpp(self):
        self._run_compilation_error("clang++")

    def _run_runtime_error_segmentation_fault(self, compiler_name):
        cpp_code = """
        #include <iostream>
        int main() {
            int *p = nullptr;
            *p = 42; // Segmentation fault
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertNotEqual(result['execution_exit_code'], 0, f"Execution should have failed for {compiler_name} due to runtime error.")
        self.assertFalse(result['timed_out_execution'])

    def test_runtime_error_segmentation_fault_gpp(self):
        self._run_runtime_error_segmentation_fault("g++")

    def test_runtime_error_segmentation_fault_clangpp(self):
        self._run_runtime_error_segmentation_fault("clang++")
        
    def _run_runtime_error_throw_exception(self, compiler_name):
        cpp_code = """
        #include <iostream>
        #include <stdexcept> // Required for std::runtime_error
        int main() {
            throw std::runtime_error("Test runtime error from C++");
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertNotEqual(result['execution_exit_code'], 0, f"Execution should have failed for {compiler_name} due to thrown exception.")
        self.assertFalse(result['timed_out_execution'])
        self.assertIn("terminate called after throwing an instance of 'std::runtime_error'", result['execution_stderr'], f"Expected C++ runtime error message not found in stderr for {compiler_name}.")
        self.assertIn("Test runtime error from C++", result['execution_stderr'], f"Specific exception message not found in stderr for {compiler_name}.")

    def test_runtime_error_throw_exception_gpp(self):
        self._run_runtime_error_throw_exception("g++")

    def test_runtime_error_throw_exception_clangpp(self):
        self._run_runtime_error_throw_exception("clang++")

    def test_execution_timeout(self): # Using default compiler (g++) for this
        cpp_code = """
        #include <iostream>
        int main() {
            while(true) { /* Infinite loop */ }
            std::cout << "This will not print." << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, exec_timeout=1, compiler="g++") # Explicitly g++
        self.assertEqual(result['compiler_used'], "g++")
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertTrue(result['timed_out_execution'])
        self.assertEqual(result['execution_exit_code'], -1)
        self.assertIn("Execution timed out after 1 seconds.", result['execution_stderr'])

    def test_compilation_timeout(self): # Using default compiler (g++) for this
        # This code is valid but we use a very short timeout.
        # The apt-get update/install in the Docker command might influence this.
        cpp_code = """
        #include <iostream>
        int main() { std::cout << "Hello!" << std::endl; return 0; }
        """
        # Setting timeout to 2s. apt-get install can take >1s if image layers not cached.
        # This test is more about the timeout mechanism than precise timing of C++ compilation itself.
        result = run_cpp_code(cpp_code, compile_timeout=2, compiler="g++") # Explicitly g++
        
        self.assertEqual(result['compiler_used'], "g++")
        if result['timed_out_compilation']:
            self.assertTrue(result['timed_out_compilation'])
            self.assertEqual(result['compilation_exit_code'], -1)
            self.assertIn(f"Compilation timed out after {2} seconds.", result['compilation_stderr'])
        else:
            print("\nWarning: Compilation timeout test did not time out compilation. "
                  "The compile_timeout (2s) might be too generous if Docker image layers were cached "
                  "and system is fast. The test primarily checks the timeout path logic.")
            self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed unexpectedly: {result['compilation_stderr']}")

    def _run_empty_code_string(self, compiler_name):
        cpp_code = ""
        result = run_cpp_code(cpp_code, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertNotEqual(result['compilation_exit_code'], 0, f"Compilation of empty string should fail for {compiler_name}.")
        self.assertFalse(result['timed_out_compilation'])
        # Error messages for no input can vary.
        # g++: "g CXX: fatal error: no input files"
        # clang++: "clang: error: no input files"
        # So, check for "no input files" generally.
        self.assertIn("no input files", result['compilation_stderr'].lower(), f"Expected 'no input files' error not found for {compiler_name}: {result['compilation_stderr']}")

    def test_empty_code_string_gpp(self):
        self._run_empty_code_string("g++")

    def test_empty_code_string_clangpp(self):
        self._run_empty_code_string("clang++")

    def _run_no_stdin_provided_graceful(self, compiler_name):
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
        result = run_cpp_code(cpp_code, stdin_data=None, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        self.assertEqual(result['execution_exit_code'], 0, msg=f"Execution failed for {compiler_name}: {result['execution_stderr']}")
        self.assertFalse(result['timed_out_execution'])
        self.assertEqual(result['execution_stdout'], "No input received.\n")

    def test_no_stdin_provided_graceful_gpp(self):
        self._run_no_stdin_provided_graceful("g++")

    def test_no_stdin_provided_graceful_clangpp(self):
        self._run_no_stdin_provided_graceful("clang++")

    def _run_no_stdin_provided_expecting_input(self, compiler_name):
        cpp_code = """
        #include <iostream>
        #include <string>
        int main() {
            std::string name;
            std::cin >> name; 
            if (std::cin.fail() && name.empty()) {
                return 1; // Indicate failure
            }
            std::cout << "Name: " << name << std::endl;
            return 0;
        }
        """
        result = run_cpp_code(cpp_code, stdin_data=None, exec_timeout=2, compiler=compiler_name)
        
        self.assertEqual(result['compiler_used'], compiler_name)
        self.assertEqual(result['compilation_exit_code'], 0, msg=f"Compilation failed for {compiler_name}: {result['compilation_stderr']}")
        self.assertFalse(result['timed_out_compilation'])
        
        if result['timed_out_execution']:
            self.fail(f"Execution timed out unexpectedly for {compiler_name}. Stderr: {result['execution_stderr']}")

        self.assertNotEqual(result['execution_exit_code'], 0, f"Execution should have a non-zero exit code for {compiler_name} if input was expected but not given.")
        self.assertEqual(result['execution_stdout'], "")

    def test_no_stdin_provided_expecting_input_gpp(self):
        self._run_no_stdin_provided_expecting_input("g++")

    def test_no_stdin_provided_expecting_input_clangpp(self):
        self._run_no_stdin_provided_expecting_input("clang++")

    def test_invalid_compiler_choice(self):
        cpp_code = "#include <iostream>\nint main() { std::cout << \"test\"; return 0; }"
        invalid_compiler = "nonexistent_compiler"
        result = run_cpp_code(cpp_code, compiler=invalid_compiler)
        
        self.assertEqual(result['compiler_used'], "none")
        self.assertEqual(result['compilation_exit_code'], -100) # Special code for invalid compiler
        self.assertIn(f"Unsupported compiler: '{invalid_compiler}'", result['compilation_stderr'])
        self.assertIsNone(result['execution_stdout'])
        self.assertIsNone(result['execution_stderr'])
        self.assertIsNone(result['execution_exit_code'])
        self.assertFalse(result['timed_out_compilation'])
        self.assertFalse(result['timed_out_execution'])

if __name__ == '__main__':
    print("Running cpp_runner tests...")
    print("IMPORTANT: Docker must be installed, running, and the user must have permissions to use it.")
    # Updated to reflect the change in cpp_runner.py for DOCKER_IMAGE
    print(f"These tests will use the Docker image specified in cpp_runner.py (currently: ubuntu:22.04).")
    print("If tests fail, check Docker installation and image availability (e.g., `docker pull ubuntu:22.04`).")
    unittest.main()
```
