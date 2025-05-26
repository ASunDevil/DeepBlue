import subprocess
import tempfile
import os
import shutil
import uuid
import time # For a brief sleep if needed for cleanup
from datetime import datetime
import traceback

# Default resource limits for Docker execution
DEFAULT_CPU_LIMIT = "1.0"  # Number of CPUs
DEFAULT_MEMORY_LIMIT = "256m"  # Amount of memory
DEFAULT_PYTHON_IMAGE = "python:3.10-slim" # Default Python image for Docker

def _execute_command(command_args, timeout_seconds=None, cwd=None, capture_output=True, text=True, **kwargs):
    # Helper to run a subprocess command.
    # Returns a tuple: (CompletedProcess object, timed_out_boolean)
    print(f"DEBUG: [%{datetime.now().isoformat()}] _execute_command called with command_args={command_args}, timeout_seconds={timeout_seconds}, cwd={cwd}")
    try:
        process = subprocess.run(
            command_args,
            timeout=timeout_seconds,
            cwd=cwd,
            capture_output=capture_output,
            text=text,
            check=False, 
            **kwargs
        )
        print(f"DEBUG: [%{datetime.now().isoformat()}] _execute_command completed successfully. Return code: {process.returncode}")
        return process, False 
    except subprocess.TimeoutExpired as e:
        print(f"DEBUG: [%{datetime.now().isoformat()}] _execute_command timed out for command: {command_args}")
        return subprocess.CompletedProcess(
            args=command_args, 
            returncode=-1, 
            stdout=e.stdout.decode(errors='ignore') if e.stdout else "", 
            stderr=e.stderr.decode(errors='ignore') if e.stderr else "Execution timed out."
        ), True
    except FileNotFoundError as e:
        print(f"DEBUG: [%{datetime.now().isoformat()}] _execute_command FileNotFoundError: {e.filename} for command: {command_args}")
        return subprocess.CompletedProcess(
            args=command_args,
            returncode=-1, 
            stdout="",
            stderr=f"Command not found: {e.filename}" # Corrected f-string
        ), False
    except Exception as e: 
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] _execute_command encountered an exception for command {command_args}: {e}\nTraceback:\n{formatted_traceback}")
        return subprocess.CompletedProcess(
            args=command_args,
            returncode=-1,
            stdout="",
            stderr=f"An unexpected error occurred running command: {str(e)}" # Corrected f-string
        ), False


def run_python_code(code: str, requirements: list[str] = None, timeout: int = 60, 
                    python_image: str = DEFAULT_PYTHON_IMAGE,
                    cpu_limit: str = DEFAULT_CPU_LIMIT, 
                    memory_limit: str = DEFAULT_MEMORY_LIMIT):
    """
    Runs Python code in a sandboxed Docker environment.

    Args:
        code: The Python code to execute.
        requirements: A list of pip package requirements (e.g., ["requests", "numpy==1.21.0"]).
        timeout: Maximum execution time in seconds.
        python_image: The base Docker image to use for Python execution.
        cpu_limit: Docker CPU limit (e.g., "1.0" for 1 CPU).
        memory_limit: Docker memory limit (e.g., "256m").

    Returns:
        A dictionary containing:
            'stdout': Standard output from the code execution.
            'stderr': Standard error from the code execution.
            'exit_code': Exit code of the script. 0 for success.
            'timed_out': Boolean, True if execution timed out.
            'error': A high-level error message if setup or Docker interaction failed before code execution.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering run_python_code with code='{code[:100]}...', requirements={requirements}, timeout={timeout}, python_image='{python_image}', cpu_limit='{cpu_limit}', memory_limit='{memory_limit}'")
    result = {
        "stdout": "", "stderr": "", "exit_code": -1, 
        "timed_out": False, "error": None 
    }
    
    exec_id = str(uuid.uuid4())
    temp_dir = None
    docker_image_tag = f"python-exec-{exec_id}" # Corrected f-string
    image_built = False

    try:
        temp_dir = tempfile.mkdtemp(prefix=f"pyrunner_{exec_id}_") # Corrected f-string
        print(f"DEBUG: [%{datetime.now().isoformat()}] Created temporary directory: {temp_dir}")
        
        with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(code)
        print(f"DEBUG: [%{datetime.now().isoformat()}] Python code written to {os.path.join(temp_dir, 'main.py')}")

        dockerfile_parts = [f"FROM {python_image}", "WORKDIR /app", "COPY main.py ."] # Corrected f-string
        if requirements:
            with open(os.path.join(temp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(requirements))
            print(f"DEBUG: [%{datetime.now().isoformat()}] requirements.txt written to {os.path.join(temp_dir, 'requirements.txt')}")
            dockerfile_parts.extend(["COPY requirements.txt .", "RUN pip install --no-cache-dir -r requirements.txt"])
        dockerfile_parts.append('CMD ["python", "-u", "main.py"]')
        
        dockerfile_content_for_log = "\n".join(dockerfile_parts)
        print(f"DEBUG: [%{datetime.now().isoformat()}] Dockerfile content:\n{dockerfile_content_for_log}")

        with open(os.path.join(temp_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write("\n".join(dockerfile_parts))
        print(f"DEBUG: [%{datetime.now().isoformat()}] Dockerfile written to {os.path.join(temp_dir, 'Dockerfile')}")

        build_command = ["docker", "build", "-t", docker_image_tag, "-f", os.path.join(temp_dir, "Dockerfile"), temp_dir]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Building Docker image {docker_image_tag} with command: {' '.join(build_command)}")
        
        build_process_result, build_timed_out = _execute_command(build_command, timeout_seconds=300) 

        if build_timed_out:
            result['error'] = "Docker image build timed out."
            result['stderr'] = build_process_result.stderr
            result['timed_out'] = True
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_python_code (build timeout) with result: {result}")
            return result
        
        if build_process_result.returncode != 0:
            result['error'] = "Docker image build failed."
            result['stderr'] = f"Build STDOUT:\n{build_process_result.stdout}\n\nBuild STDERR:\n{build_process_result.stderr}" # Corrected f-string
            result['exit_code'] = build_process_result.returncode
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting run_python_code (build failed) with result: {result}")
            return result
        
        image_built = True
        print(f"DEBUG: [%{datetime.now().isoformat()}] Docker image {docker_image_tag} built successfully.")

        run_command = [
            "docker", "run", "--rm", "--network=none",
            f"--cpus={cpu_limit}", f"--memory={memory_limit}", # Corrected f-strings
            docker_image_tag
        ]
        print(f"DEBUG: [%{datetime.now().isoformat()}] Running Docker container with command: {' '.join(run_command)} (timeout: {timeout}s)")
        
        run_process_result, run_timed_out = _execute_command(run_command, timeout_seconds=timeout)

        result['timed_out'] = run_timed_out
        result['stdout'] = run_process_result.stdout
        result['stderr'] = run_process_result.stderr
        result['exit_code'] = run_process_result.returncode
        
        if run_timed_out:
            result['stderr'] = (str(result['stderr']) + f"\nExecution timed out after {timeout} seconds.").lstrip() # Corrected f-string
            # Ensure exit_code reflects timeout if not already set by _execute_command's timeout path
            if result['exit_code'] == 0 or result['exit_code'] == -1 : result['exit_code'] = 137 # common for timeout/killed

    except Exception as e:
        result['error'] = f"An unexpected error occurred in run_python_code: {str(e)}" # Corrected f-string
        if not result['stderr']: 
            result['stderr'] = str(e)
    finally:
        if image_built:
            print(f"Attempting to remove Docker image {docker_image_tag}...") # Corrected f-string
            rmi_command = ["docker", "rmi", "-f", docker_image_tag]
            # Give a bit of time for the container to be fully released before image removal
            time.sleep(1) # Brief pause
            rmi_result, _ = _execute_command(rmi_command, timeout_seconds=30) # Use a short timeout
            if rmi_result.returncode != 0:
                print(f"Warning: Failed to remove Docker image {docker_image_tag}. STDERR: {rmi_result.stderr}") # Corrected f-string
            else:
                print(f"Successfully removed Docker image {docker_image_tag}.") # Corrected f-string
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to remove temporary directory {temp_dir}: {str(e)}") # Corrected f-string

    print(f"DEBUG: run_python_code returning: {result}")
    return result

# Keep the __main__ example usage block as it was for testing
if __name__ == '__main__':
    print("DEBUG: Starting python_runner.py example usage...")
    print("--- Example 1: Simple print ---")
    example_code_1 = "print('Hello from Python runner!')\nprint('This is a test.')"
    output_1 = run_python_code(example_code_1)
    print(f"Output 1: {output_1}\n") # Corrected f-string

    print("--- Example 2: With requirements (requests) ---")
    example_code_2 = "import requests; print(f'Requests version: {requests.__version__}')" # Corrected f-string
    example_reqs_2 = ["requests==2.25.1"] 
    output_2 = run_python_code(example_code_2, requirements=example_reqs_2)
    print(f"Output 2: {output_2}\n") # Corrected f-string
    
    print("--- Example 3: Code with an error ---")
    example_code_3 = "print('Start')\nraise ValueError('This is a test error')\nprint('End')"
    output_3 = run_python_code(example_code_3)
    print(f"Output 3: {output_3}\n") # Corrected f-string

    print("--- Example 4: Timeout test ---")
    example_code_4 = "import time; time.sleep(5); print('Slept for 5s')"
    output_4 = run_python_code(example_code_4, timeout=2)
    print(f"Output 4: {output_4}\n") # Corrected f-string

    print("--- Example 5: Docker command not found (Manual Test: rename docker temporarily) ---")
    # This test is more for manual verification by temporarily making 'docker' unavailable in PATH
    # output_5 = run_python_code("print('Testing docker not found')")
    # print(f"Output 5 (Docker not found): {output_5}\n")

    print("--- Example 6: Using a different python image ---")
    example_code_6 = "import sys; print(sys.version)"
    output_6 = run_python_code(example_code_6, python_image="python:3.8-slim")
    print(f"Output 6 (Python 3.8): {output_6}\n")

    print("--- Example 7: Unicode test ---")
    example_code_7 = "print('你好世界 😊')" # Hello World in Chinese + emoji
    output_7 = run_python_code(example_code_7)
    print(f"Output 7 (Unicode): {output_7}\n")
