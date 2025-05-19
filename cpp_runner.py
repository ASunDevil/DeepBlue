import subprocess
import tempfile
import os
import shutil # For robust directory deletion
from typing import Union, Dict, Any # For type hinting

# Define a default Docker image
# Using frolvlad/alpine-gxx for a smaller footprint than gcc:latest
# Ensure this image is available or use a common one like gcc:latest
DOCKER_IMAGE = "frolvlad/alpine-gxx:latest"
# DOCKER_IMAGE = "gcc:latest" # Alternative if the alpine image is problematic

def run_cpp_code(cpp_code: str, stdin_data: Union[str, None] = None, compile_timeout: int = 10, exec_timeout: int = 5) -> Dict[str, Any]:
    """
    Compiles and runs C++ code in a sandboxed environment using Docker.

    Args:
        cpp_code: A string containing the C++ code to compile and run.
        stdin_data: Optional string data to be passed to the C++ program's standard input.
        compile_timeout: Timeout in seconds for the compilation phase.
        exec_timeout: Timeout in seconds for the execution phase.

    Returns:
        A dictionary containing the results of the compilation and execution.
        Structure:
        {
            "compilation_stdout": str,
            "compilation_stderr": str,
            "compilation_exit_code": int | None, # None if Docker command itself fails
            "timed_out_compilation": bool,
            "execution_stdout": str | None,
            "execution_stderr": str | None,
            "execution_exit_code": int | None, # None if execution skipped or Docker command fails
            "timed_out_execution": bool
        }
    """
    results: Dict[str, Any] = {
        "compilation_stdout": "",
        "compilation_stderr": "",
        "compilation_exit_code": None,
        "timed_out_compilation": False,
        "execution_stdout": None,
        "execution_stderr": None,
        "execution_exit_code": None,
        "timed_out_execution": False,
    }

    temp_dir = None
    try:
        # 1. Setup Temporary Directory
        temp_dir = tempfile.mkdtemp()
        cpp_filepath = os.path.join(temp_dir, "temp_code.cpp")
        executable_filepath = os.path.join(temp_dir, "temp_exec") # Relative path for inside container

        # 2. Write C++ Code
        with open(cpp_filepath, "w") as f:
            f.write(cpp_code)

        # 3. Compilation Phase
        # Docker command: docker run --rm -v /host/temp_dir:/sandbox -w /sandbox <image> g++ ...
        compile_command = [
            "docker", "run", "--rm",
            "-v", f"{os.path.abspath(temp_dir)}:/sandbox",
            "-w", "/sandbox",
            DOCKER_IMAGE,
            "g++", "-std=c++17", "-O2", "temp_code.cpp", "-o", "temp_exec"
        ]

        try:
            compile_process = subprocess.run(
                compile_command,
                timeout=compile_timeout,
                capture_output=True,
                text=True
            )
            results["compilation_stdout"] = compile_process.stdout
            results["compilation_stderr"] = compile_process.stderr
            results["compilation_exit_code"] = compile_process.returncode
        except subprocess.TimeoutExpired:
            results["timed_out_compilation"] = True
            results["compilation_stderr"] = f"Compilation timed out after {compile_timeout} seconds."
            results["compilation_exit_code"] = -1 # Indicate timeout
        except FileNotFoundError: # Docker not found
            results["compilation_stderr"] = "Error: Docker command not found. Please ensure Docker is installed and in PATH."
            results["compilation_exit_code"] = -1 # Indicate Docker error
            return results # Cannot proceed
        except Exception as e: # Other potential errors running Docker
            results["compilation_stderr"] = f"Error during Docker compilation command: {str(e)}"
            results["compilation_exit_code"] = -1 # Indicate Docker error
            return results # Cannot proceed


        if results["compilation_exit_code"] != 0 or results["timed_out_compilation"]:
            # Compilation failed or timed out, skip execution
            return results

        # 4. Execution Phase (if compilation succeeded)
        # Docker command: docker run --rm -i -v /host/temp_dir:/sandbox -w /sandbox <image> ./temp_exec
        execute_command = [
            "docker", "run", "--rm", "-i", # -i for interactive to pass stdin
            "-v", f"{os.path.abspath(temp_dir)}:/sandbox",
            "-w", "/sandbox",
            DOCKER_IMAGE, # Can use the same image, or a smaller runtime if available and compatible
            "./temp_exec"
        ]

        input_bytes = stdin_data.encode('utf-8') if stdin_data is not None else None

        try:
            execute_process = subprocess.run(
                execute_command,
                input=input_bytes,
                timeout=exec_timeout,
                capture_output=True,
                text=True # Decodes stdout/stderr as UTF-8 by default
            )
            results["execution_stdout"] = execute_process.stdout
            results["execution_stderr"] = execute_process.stderr
            results["execution_exit_code"] = execute_process.returncode
        except subprocess.TimeoutExpired:
            results["timed_out_execution"] = True
            results["execution_stderr"] = f"Execution timed out after {exec_timeout} seconds."
            results["execution_exit_code"] = -1 # Indicate timeout
        except FileNotFoundError: # Should not happen if compilation Docker command worked
            results["execution_stderr"] = "Error: Docker command not found for execution (unexpected)."
            results["execution_exit_code"] = -1
        except Exception as e: # Other potential errors running Docker
            results["execution_stderr"] = f"Error during Docker execution command: {str(e)}"
            results["execution_exit_code"] = -1

        return results

    finally:
        # 5. Cleanup
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    # Example Usage:

    # 1. Simple Hello World
    hello_world_code = """
    #include <iostream>
    int main() {
        std::cout << "Hello, C++ World from Docker!" << std::endl;
        return 0;
    }
    """
    print("--- Running Hello World ---")
    hello_results = run_cpp_code(hello_world_code)
    print(f"Compilation STDOUT:\n{hello_results['compilation_stdout']}")
    print(f"Compilation STDERR:\n{hello_results['compilation_stderr']}")
    print(f"Compilation Exit Code: {hello_results['compilation_exit_code']}")
    print(f"Compilation Timed Out: {hello_results['timed_out_compilation']}")
    if hello_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{hello_results['execution_stdout']}")
        print(f"Execution STDERR:\n{hello_results['execution_stderr']}")
        print(f"Execution Exit Code: {hello_results['execution_exit_code']}")
        print(f"Execution Timed Out: {hello_results['timed_out_execution']}")
    print("-" * 30)

    # 2. Code with STDIN and STDOUT
    stdin_code = """
    #include <iostream>
    #include <string>
    int main() {
        std::string name;
        std::cout << "Enter your name: "; // Prompt to stdout
        std::cin >> name;
        std::cout << "Hello, " << name << "!" << std::endl;
        return 0;
    }
    """
    print("--- Running STDIN/STDOUT Example ---")
    stdin_results = run_cpp_code(stdin_code, stdin_data="Tester")
    print(f"Compilation STDOUT:\n{stdin_results['compilation_stdout']}")
    print(f"Compilation STDERR:\n{stdin_results['compilation_stderr']}")
    print(f"Compilation Exit Code: {stdin_results['compilation_exit_code']}")
    if stdin_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{stdin_results['execution_stdout']}") # Includes the prompt
        print(f"Execution STDERR:\n{stdin_results['execution_stderr']}")
        print(f"Execution Exit Code: {stdin_results['execution_exit_code']}")
    print("-" * 30)

    # 3. Compilation Error
    compile_error_code = """
    #include <iostream>
    int main() {
        std::cout << "This will not compile" << std::end; // Error: std::end instead of std::endl
        return 0;
    }
    """
    print("--- Running Compilation Error Example ---")
    compile_error_results = run_cpp_code(compile_error_code)
    print(f"Compilation STDOUT:\n{compile_error_results['compilation_stdout']}")
    print(f"Compilation STDERR:\n{compile_error_results['compilation_stderr']}") # Should show g++ error
    print(f"Compilation Exit Code: {compile_error_results['compilation_exit_code']}") # Should be non-zero
    print("-" * 30)

    # 4. Execution Timeout
    exec_timeout_code = """
    #include <iostream>
    #include <unistd.h> // For sleep
    int main() {
        std::cout << "Starting sleep..." << std::endl;
        sleep(10); // Sleep for 10 seconds
        std::cout << "Sleep finished." << std::endl;
        return 0;
    }
    """
    print("--- Running Execution Timeout Example ---")
    exec_timeout_results = run_cpp_code(exec_timeout_code, exec_timeout=2)
    print(f"Compilation Exit Code: {exec_timeout_results['compilation_exit_code']}")
    if exec_timeout_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{exec_timeout_results['execution_stdout']}")
        print(f"Execution STDERR:\n{exec_timeout_results['execution_stderr']}")
        print(f"Execution Exit Code: {exec_timeout_results['execution_exit_code']}")
        print(f"Execution Timed Out: {exec_timeout_results['timed_out_execution']}") # Should be True
    print("-" * 30)

    # 5. Compilation Timeout (less common to hit with simple code, but good for testing)
    # This code itself is fine, but we'll set a very low compile timeout.
    print("--- Running Compilation Timeout Example ---")
    compile_timeout_results = run_cpp_code(hello_world_code, compile_timeout=0.001) # Very small timeout
    print(f"Compilation STDERR:\n{compile_timeout_results['compilation_stderr']}")
    print(f"Compilation Exit Code: {compile_timeout_results['compilation_exit_code']}")
    print(f"Compilation Timed Out: {compile_timeout_results['timed_out_compilation']}") # Should be True
    print("-" * 30)

    # 6. Code with runtime error
    runtime_error_code = """
    #include <iostream>
    int main() {
        int* ptr = nullptr;
        *ptr = 10; // Dereferencing null pointer
        std::cout << "This won't be printed." << std::endl;
        return 0;
    }
    """
    print("--- Running Runtime Error Example ---")
    runtime_error_results = run_cpp_code(runtime_error_code)
    print(f"Compilation Exit Code: {runtime_error_results['compilation_exit_code']}")
    if runtime_error_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{runtime_error_results['execution_stdout']}")
        print(f"Execution STDERR:\n{runtime_error_results['execution_stderr']}") # May or may not have stderr
        print(f"Execution Exit Code: {runtime_error_results['execution_exit_code']}") # Should be non-zero
    print("-" * 30)

    # 7. No input provided to code expecting input (can lead to non-zero exit or hang if not handled in C++)
    # The C++ code used for stdin_code will wait for input. If none is given through stdin_data,
    # it might exit if cin fails, or hang if not well-written (though Docker's -i should close stdin).
    print("--- Running No Input For Code Expecting Input ---")
    no_input_results = run_cpp_code(stdin_code, stdin_data=None, exec_timeout=2) # Use timeout in case it hangs
    print(f"Compilation Exit Code: {no_input_results['compilation_exit_code']}")
    if no_input_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{no_input_results['execution_stdout']}")
        print(f"Execution STDERR:\n{no_input_results['execution_stderr']}")
        print(f"Execution Exit Code: {no_input_results['execution_exit_code']}")
        print(f"Execution Timed Out: {no_input_results['timed_out_execution']}")
    print("-" * 30)

    # 8. Check if Docker is not installed (manual test by developer)
    # To test this, you'd need to run this script in an environment where 'docker' command is not available.
    # The script should gracefully handle this by setting compilation_stderr and compilation_exit_code.
    # print("--- Testing Docker Not Found (Manual Test) ---")
    # print("If Docker is not installed or not in PATH, this test should indicate an error.")
    # print("Manually disable Docker or alter PATH to test this scenario.")
    # print("Expected: compilation_stderr contains 'Docker command not found', compilation_exit_code is -1.")
    # print("-" * 30)

```
