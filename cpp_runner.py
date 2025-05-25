import subprocess
import tempfile
import os
import shutil # For robust directory deletion
from typing import Union, Dict, Any
from datetime import datetime
import traceback

# Use ubuntu:22.04 as the Docker image
DOCKER_IMAGE = "ubuntu:22.04"

def run_cpp_code(cpp_code: str, stdin_data: Union[str, None] = None, compile_timeout: int = 10, exec_timeout: int = 5, compiler: str = "g++") -> Dict[str, Any]:
    """
    Compiles and runs C++ code in a sandboxed environment using Docker,
    with a choice of compiler (g++ or clang++).

    Args:
        cpp_code: A string containing the C++ code to compile and run.
        stdin_data: Optional string data to be passed to the C++ program's standard input.
        compile_timeout: Timeout in seconds for the compilation phase.
        exec_timeout: Timeout in seconds for the execution phase.
        compiler: The C++ compiler to use. Supported values are "g++" (default) and "clang++".

    Returns:
        A dictionary containing the results of the compilation and execution.
        Structure:
        {
            "compilation_stdout": str,
            "compilation_stderr": str,
            "compilation_exit_code": int | None, # None if Docker command itself fails, -100 for invalid compiler
            "timed_out_compilation": bool,
            "execution_stdout": str | None,
            "execution_stderr": str | None,
            "execution_exit_code": int | None, # None if execution skipped or Docker command fails
            "timed_out_execution": bool,
            "compiler_used": str # "g++", "clang++", or "none"
        }
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering run_cpp_code with cpp_code='{cpp_code[:100]}...', stdin_data='{stdin_data}', compile_timeout={compile_timeout}, exec_timeout={exec_timeout}, compiler='{compiler}'")
    results: Dict[str, Any] = {
        "compilation_stdout": "",
        "compilation_stderr": "",
        "compilation_exit_code": None,
        "timed_out_compilation": False,
        "execution_stdout": None,
        "execution_stderr": None,
        "execution_exit_code": None,
        "timed_out_execution": False,
        "compiler_used": "none", # Default to "none"
    }

    # 1. Compiler Validation
    if compiler not in ["g++", "clang++"]:
        results["compilation_stderr"] = f"Unsupported compiler: '{compiler}'. Supported compilers are 'g++' and 'clang++'."
        results["compilation_exit_code"] = -100 # Special exit code for invalid compiler
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_cpp_code (compiler validation failed) with results: {results}")
        return results
    
    results["compiler_used"] = compiler
    compiler_exe = "clang++" if compiler == "clang++" else "g++"
    print(f"DEBUG: [%{datetime.now().isoformat()}] Compiler set to: {compiler_exe}")

    temp_dir = None
    try:
        # 1. Setup Temporary Directory
        temp_dir = tempfile.mkdtemp()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Created temporary directory: {temp_dir}")
        cpp_filepath = os.path.join(temp_dir, "temp_code.cpp")
        executable_filepath = os.path.join(temp_dir, "temp_exec") # Relative path for inside container

        # 2. Setup Temporary Directory (moved after compiler validation)
        # This is a duplicate of the above temp_dir creation. Removing it.
        # temp_dir = tempfile.mkdtemp() 
        # cpp_filepath = os.path.join(temp_dir, "temp_code.cpp")
        # executable_filepath = os.path.join(temp_dir, "temp_exec")

        # 3. Write C++ Code
        with open(cpp_filepath, "w") as f:
            f.write(cpp_code)
        print(f"DEBUG: [%{datetime.now().isoformat()}] C++ code written to {cpp_filepath}")

        # 4. Compilation Phase
        # Shell command to install compilers and then compile
        # apt-get update and install are silenced with > /dev/null 2>&1
        docker_shell_command = (
            f"apt-get update > /dev/null 2>&1 && apt-get install -y g++ clang > /dev/null 2>&1; "
            f"{compiler_exe} -std=c++17 -O2 temp_code.cpp -o temp_exec"
        )
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker shell command for compilation: {docker_shell_command}")
        
        compile_command = [
            "docker", "run", "--rm", "--network=none", # Added --network=none
            "-v", f"{os.path.abspath(temp_dir)}:/sandbox",
            "-w", "/sandbox",
            DOCKER_IMAGE,
            "sh", "-c", docker_shell_command # Run the combined command in a shell
        ]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Full Docker compile command: {' '.join(compile_command)}")

        try:
            print(f"DEBUG: [%{datetime.now().isoformat()}] Attempting to run Docker compile command. Timeout: {compile_timeout}s")
            compile_process = subprocess.run(
                compile_command,
                timeout=compile_timeout,
                capture_output=True,
                text=True
            )
            results["compilation_stdout"] = compile_process.stdout
            results["compilation_stderr"] = compile_process.stderr
            results["compilation_exit_code"] = compile_process.returncode
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker compile process completed. Return code: {compile_process.returncode}")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker compile stdout (first 500 chars): {compile_process.stdout[:500]}")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker compile stderr (first 500 chars): {compile_process.stderr[:500]}")
        except subprocess.TimeoutExpired:
            results["timed_out_compilation"] = True
            results["compilation_stderr"] = f"Compilation timed out after {compile_timeout} seconds."
            results["compilation_exit_code"] = -1 # Indicate timeout
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker compile command timed out. Error: {results['compilation_stderr']}")
        except FileNotFoundError: # Docker not found
            results["compilation_stderr"] = "Error: Docker command not found. Please ensure Docker is installed and in PATH."
            results["compilation_exit_code"] = -1 # Indicate Docker error
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker command not found during compilation. Error: {results['compilation_stderr']}")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_cpp_code (Docker not found during compile) with results: {results}")
            return results # Cannot proceed
        except Exception as e: # Other potential errors running Docker
            formatted_traceback = traceback.format_exc()
            print(f"DEBUG: [%{datetime.now().isoformat()}] An unexpected exception occurred during Docker compilation command: {e}\nTraceback:\n{formatted_traceback}")
            results["compilation_stderr"] = f"{type(e).__name__} - {str(e)}"
            results["compilation_exit_code"] = -1 # Indicate Docker error
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_cpp_code (Docker exception during compile) with results: {results}")
            return results # Cannot proceed


        if results["compilation_exit_code"] != 0 or results["timed_out_compilation"]:
            # Compilation failed or timed out, skip execution
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_cpp_code (compilation failed or timed out) with results: {results}")
            return results

        # 5. Execution Phase (if compilation succeeded)
        # Docker command: docker run --rm --network=none -i -v /host/temp_dir:/sandbox -w /sandbox <image> ./temp_exec
        execute_command = [
            "docker", "run", "--rm", "--network=none", "-i", # Added --network=none
            "-v", f"{os.path.abspath(temp_dir)}:/sandbox",
            "-w", "/sandbox",
            DOCKER_IMAGE, # The same image already has the runtime environment
            "./temp_exec"
        ]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Full Docker execute command: {' '.join(execute_command)}")

        input_bytes = stdin_data.encode('utf-8') if stdin_data is not None else None

        try:
            print(f"DEBUG: [%{datetime.now().isoformat()}] Attempting to run Docker execute command. Timeout: {exec_timeout}s")
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
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker execute process completed. Return code: {execute_process.returncode}")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker execute stdout (first 500 chars): {execute_process.stdout[:500]}")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker execute stderr (first 500 chars): {execute_process.stderr[:500]}")
        except subprocess.TimeoutExpired:
            results["timed_out_execution"] = True
            results["execution_stderr"] = f"Execution timed out after {exec_timeout} seconds."
            results["execution_exit_code"] = -1 # Indicate timeout
            print(f"DEBUG: [%{datetime.now().isoformat()}] Docker execute command timed out. Error: {results['execution_stderr']}")
        except FileNotFoundError: # Should not happen if compilation Docker command worked
            results["execution_stderr"] = "Error: Docker command not found for execution (unexpected)."
            results["execution_exit_code"] = -1
        except Exception as e: # Other potential errors running Docker
            formatted_traceback = traceback.format_exc()
            print(f"DEBUG: [%{datetime.now().isoformat()}] An unexpected exception occurred during Docker execution command: {e}\nTraceback:\n{formatted_traceback}")
            results["execution_stderr"] = f"{type(e).__name__} - {str(e)}"
            results["execution_exit_code"] = -1

        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_cpp_code with results: {results}")
        return results

    finally:
        # 6. Cleanup
        if temp_dir and os.path.exists(temp_dir):
            print(f"DEBUG: [%{datetime.now().isoformat()}] Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    print(f"DEBUG: [%{datetime.now().isoformat()}] Starting cpp_runner.py example usage...")
    # Example Usage:

    # 1. Simple Hello World (default g++)
    hello_world_code = """
    #include <iostream>
    int main() {
        std::cout << "Hello, C++ World from Docker!" << std::endl;
        return 0;
    }
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Hello World (g++) ---")
    hello_results_gpp = run_cpp_code(hello_world_code, compiler="g++")
    print(f"Compiler Used: {hello_results_gpp['compiler_used']}")
    print(f"Compilation Exit Code: {hello_results_gpp['compilation_exit_code']}")
    print(f"Compilation STDERR:\n{hello_results_gpp['compilation_stderr']}")
    if hello_results_gpp['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{hello_results_gpp['execution_stdout']}")
    print("-" * 30)

    # 1b. Simple Hello World (clang++)
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Hello World (clang++) ---")
    hello_results_clang = run_cpp_code(hello_world_code, compiler="clang++")
    print(f"Compiler Used: {hello_results_clang['compiler_used']}")
    print(f"Compilation Exit Code: {hello_results_clang['compilation_exit_code']}")
    print(f"Compilation STDERR:\n{hello_results_clang['compilation_stderr']}")
    if hello_results_clang['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{hello_results_clang['execution_stdout']}")
    print("-" * 30)

    # 1c. Invalid Compiler
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running with Invalid Compiler ---")
    invalid_compiler_results = run_cpp_code(hello_world_code, compiler="invalid_compiler")
    print(f"Compiler Used: {invalid_compiler_results['compiler_used']}") # Should be 'none'
    print(f"Compilation Exit Code: {invalid_compiler_results['compilation_exit_code']}") # Should be -100
    print(f"Compilation STDERR:\n{invalid_compiler_results['compilation_stderr']}") # Should show error message
    print("-" * 30)


    # 2. Code with STDIN and STDOUT (using clang++)
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
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running STDIN/STDOUT Example (clang++) ---")
    stdin_results_clang = run_cpp_code(stdin_code, stdin_data="Tester Clang", compiler="clang++")
    print(f"Compiler Used: {stdin_results_clang['compiler_used']}")
    print(f"Compilation Exit Code: {stdin_results_clang['compilation_exit_code']}")
    if stdin_results_clang['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{stdin_results_clang['execution_stdout']}") # Includes the prompt
    print("-" * 30)

    # 3. Compilation Error (using g++)
    compile_error_code = """
    #include <iostream>
    int main() {
        std::cout << "This will not compile" << std::end; // Error: std::end instead of std::endl
        return 0;
    }
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Compilation Error Example (g++) ---")
    compile_error_results_gpp = run_cpp_code(compile_error_code, compiler="g++")
    print(f"Compiler Used: {compile_error_results_gpp['compiler_used']}")
    print(f"Compilation STDERR:\n{compile_error_results_gpp['compilation_stderr']}") # Should show g++ error
    print(f"Compilation Exit Code: {compile_error_results_gpp['compilation_exit_code']}") # Should be non-zero
    print("-" * 30)

    # 4. Execution Timeout (default g++)
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
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Execution Timeout Example (g++) ---")
    exec_timeout_results = run_cpp_code(exec_timeout_code, exec_timeout=2)
    print(f"Compiler Used: {exec_timeout_results['compiler_used']}")
    print(f"Compilation Exit Code: {exec_timeout_results['compilation_exit_code']}")
    if exec_timeout_results['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{exec_timeout_results['execution_stdout']}")
        print(f"Execution STDERR:\n{exec_timeout_results['execution_stderr']}")
        print(f"Execution Exit Code: {exec_timeout_results['execution_exit_code']}")
        print(f"Execution Timed Out: {exec_timeout_results['timed_out_execution']}") # Should be True
    print("-" * 30)

    # 5. Compilation Timeout (using clang++, requires a very fast system or slow image pull to reliably trigger)
    # The apt-get update/install part of the command might make this harder to hit unless Docker caches layers.
    # For this example, let's assume a very small timeout.
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Compilation Timeout Example (clang++) ---")
    # Note: The 'apt-get update && apt-get install' can take time.
    # If this times out, it might be before actual C++ compilation.
    compile_timeout_results_clang = run_cpp_code(hello_world_code, compile_timeout=1, compiler="clang++") # Very small timeout
    print(f"Compiler Used: {compile_timeout_results_clang['compiler_used']}")
    print(f"Compilation STDERR:\n{compile_timeout_results_clang['compilation_stderr']}")
    print(f"Compilation Exit Code: {compile_timeout_results_clang['compilation_exit_code']}")
    print(f"Compilation Timed Out: {compile_timeout_results_clang['timed_out_compilation']}") # Should be True if timeout is effective
    print("-" * 30)

    # 6. Code with runtime error (using g++)
    runtime_error_code = """
    #include <iostream>
    int main() {
        int* ptr = nullptr;
        *ptr = 10; // Dereferencing null pointer
        std::cout << "This won't be printed." << std::endl;
        return 0;
    }
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running Runtime Error Example (g++) ---")
    runtime_error_results_gpp = run_cpp_code(runtime_error_code, compiler="g++")
    print(f"Compiler Used: {runtime_error_results_gpp['compiler_used']}")
    print(f"Compilation Exit Code: {runtime_error_results_gpp['compilation_exit_code']}")
    if runtime_error_results_gpp['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{runtime_error_results_gpp['execution_stdout']}")
        print(f"Execution STDERR:\n{runtime_error_results_gpp['execution_stderr']}") # May or may not have stderr
        print(f"Execution Exit Code: {runtime_error_results_gpp['execution_exit_code']}") # Should be non-zero
    print("-" * 30)

    # 7. No input provided to code expecting input (using clang++)
    print(f"DEBUG: [%{datetime.now().isoformat()}] --- Running No Input For Code Expecting Input (clang++) ---")
    no_input_results_clang = run_cpp_code(stdin_code, stdin_data=None, exec_timeout=2, compiler="clang++")
    print(f"Compiler Used: {no_input_results_clang['compiler_used']}")
    print(f"Compilation Exit Code: {no_input_results_clang['compilation_exit_code']}")
    if no_input_results_clang['execution_stdout'] is not None:
        print(f"Execution STDOUT:\n{no_input_results_clang['execution_stdout']}")
        print(f"Execution STDERR:\n{no_input_results_clang['execution_stderr']}")
        print(f"Execution Exit Code: {no_input_results_clang['execution_exit_code']}")
        print(f"Execution Timed Out: {no_input_results_clang['timed_out_execution']}")
    print("-" * 30)

    # 8. Docker not found test (manual)
    # This remains a manual test scenario for the developer.
    # print("--- Testing Docker Not Found (Manual Test) ---")
    # print("If Docker is not installed or not in PATH, this test should indicate an error.")
    # print("Expected: compilation_stderr contains 'Docker command not found', compilation_exit_code is -1.")
    # print("-" * 30)
    print(f"DEBUG: [%{datetime.now().isoformat()}] Finished cpp_runner.py example usage.")
```
