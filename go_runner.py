import subprocess
import tempfile
import os
import shutil
import uuid

# Default resource limits for Docker execution
DEFAULT_CPU_LIMIT = "1.0"  # Number of CPUs
DEFAULT_MEMORY_LIMIT = "256m"  # Amount of memory
DEFAULT_GO_IMAGE = "golang:1.21-alpine" # Default Go image for Docker

def _execute_command_for_go(command_args, timeout_seconds=None, cwd=None, capture_output=True, text=True, **kwargs):
    # Helper to run a subprocess command, similar to the one in python_runner.
    # Returns a tuple: (CompletedProcess object, timed_out_boolean)
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
        return process, False 
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            args=command_args, 
            returncode=-1, # Custom indicator for timeout
            stdout=e.stdout.decode(errors='ignore') if e.stdout else "", 
            stderr=e.stderr.decode(errors='ignore') if e.stderr else "Execution timed out."
        ), True
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(
            args=command_args,
            returncode=-1, 
            stdout="",
            stderr=f"Command not found: {e.filename}"
        ), False
    except Exception as e: 
        return subprocess.CompletedProcess(
            args=command_args,
            returncode=-1,
            stdout="",
            stderr=f"An unexpected error occurred running command: {str(e)}"
        ), False

def run_go_code(code: str, timeout: int = 60, 
                go_image: str = DEFAULT_GO_IMAGE,
                cpu_limit: str = DEFAULT_CPU_LIMIT, 
                memory_limit: str = DEFAULT_MEMORY_LIMIT):
    """
    Runs Go code in a sandboxed Docker environment.

    Args:
        code: The Go code to execute.
        timeout: Maximum execution time in seconds.
        go_image: The base Docker image to use for Go execution.
        cpu_limit: Docker CPU limit (e.g., "1.0" for 1 CPU).
        memory_limit: Docker memory limit (e.g., "256m").

    Returns:
        A dictionary containing:
            'stdout': Standard output from the code execution.
            'stderr': Standard error from the code execution.
            'exit_code': Exit code of the script. 0 for success.
            'timed_out': Boolean, True if execution timed out.
            'error': A high-level error message if setup or Docker interaction failed.
    """
    result = {
        "stdout": "", "stderr": "", "exit_code": -1, 
        "timed_out": False, "error": None 
    }
    
    exec_id = str(uuid.uuid4())
    temp_dir = None
    docker_image_tag = f"go-exec-{exec_id}"
    image_built = False

    try:
        temp_dir = tempfile.mkdtemp(prefix=f"gorunner_{exec_id}_")
        
        main_go_path = os.path.join(temp_dir, "main.go")
        with open(main_go_path, "w", encoding="utf-8") as f:
            f.write(code)

        # For simplicity, this initial version does not explicitly handle 'go.mod' or external packages.
        # It assumes single-file Go programs or programs where dependencies are fetched by Go commands (e.g. go run .)
        # A more advanced version might need to parse imports and run 'go get'.
        
        dockerfile_content = f"""
FROM {go_image}
WORKDIR /app
COPY main.go .
# Attempt to fetch dependencies if any are specified in the code via go.mod implicitly or explicitly
# For single file, 'go run' handles some cases. For complex projects, go.mod would be needed.
# This RUN command might fail if main.go has unresolvable imports and no go.mod,
# but it's a common pattern for simple Go Dockerfiles.
# RUN go mod init tempmod && go mod tidy 
# Or, if assuming simple scripts, just build/run directly.
# Let's try building first, then running the binary. This is generally safer.
RUN go build -o /app/main main.go
CMD ["/app/main"]
"""
        with open(os.path.join(temp_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        # 1. Build the Docker image
        build_command = ["docker", "build", "-t", docker_image_tag, "-f", os.path.join(temp_dir, "Dockerfile"), temp_dir]
        print(f"Building Go Docker image {docker_image_tag} with command: {' '.join(build_command)}")
        
        build_process_result, build_timed_out = _execute_command_for_go(build_command, timeout_seconds=300) # Build timeout

        if build_timed_out:
            result['error'] = "Docker image build for Go timed out."
            result['stderr'] = build_process_result.stderr
            result['timed_out'] = True
            return result
        
        if build_process_result.returncode != 0:
            result['error'] = "Docker image build for Go failed."
            result['stderr'] = f"Build STDOUT:\n{build_process_result.stdout}\n\nBuild STDERR:\n{build_process_result.stderr}"
            result['exit_code'] = build_process_result.returncode
            return result
        
        image_built = True
        print(f"Go Docker image {docker_image_tag} built successfully.")

        # 2. Run the Docker container
        run_command = [
            "docker", "run", "--rm", "--network=none",
            f"--cpus={cpu_limit}", f"--memory={memory_limit}",
            docker_image_tag
        ]
        print(f"Running Go Docker container with command: {' '.join(run_command)} (timeout: {timeout}s)")
        
        run_process_result, run_timed_out = _execute_command_for_go(run_command, timeout_seconds=timeout)

        result['timed_out'] = run_timed_out
        result['stdout'] = run_process_result.stdout
        result['stderr'] = run_process_result.stderr
        result['exit_code'] = run_process_result.returncode
        
        if run_timed_out:
            result['stderr'] = (str(result['stderr']) + f"\nExecution timed out after {timeout} seconds.").lstrip()
            if result['exit_code'] == 0 or result['exit_code'] == -1: result['exit_code'] = 137 

    except Exception as e:
        result['error'] = f"An unexpected error occurred in run_go_code: {str(e)}"
        if not result['stderr']: 
            result['stderr'] = str(e)
    finally:
        if image_built:
            print(f"Attempting to remove Go Docker image {docker_image_tag}...")
            rmi_command = ["docker", "rmi", "-f", docker_image_tag]
            rmi_result, _ = _execute_command_for_go(rmi_command, timeout_seconds=30)
            if rmi_result.returncode != 0:
                print(f"Warning: Failed to remove Go Docker image {docker_image_tag}. STDERR: {rmi_result.stderr}")
            else:
                print(f"Successfully removed Go Docker image {docker_image_tag}.")
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to remove temporary directory {temp_dir}: {str(e)}")
    return result

if __name__ == '__main__':
    print("--- Example Go 1: Simple print ---")
    go_code_1 = """
package main
import "fmt"
func main() {
    fmt.Println("Hello from Go runner!")
    fmt.Println("This is a Go test.")
}
"""
    output_go_1 = run_go_code(go_code_1)
    print(f"Output Go 1: {output_go_1}\n")

    print("--- Example Go 2: Code with an error (compilation error) ---")
    go_code_2 = """
package main
import "fmt"
func main() {
    fmt.Println("Hello without semicolon") // Deliberate syntax error for Go if it expects one or type mismatch
    var x int = "hello" // Type mismatch error
    fmt.Println(x)
}
"""
    output_go_2 = run_go_code(go_code_2)
    print(f"Output Go 2: {output_go_2}\n")

    print("--- Example Go 3: Timeout test ---")
    go_code_3 = """
package main
import (
    "fmt"
    "time"
)
func main() {
    time.Sleep(5 * time.Second)
    fmt.Println("Slept for 5s in Go")
}
"""
    output_go_3 = run_go_code(go_code_3, timeout=2)
    print(f"Output Go 3: {output_go_3}\n")
    
    print("--- Example Go 4: Runtime panic ---")
    go_code_4 = """
package main
import "fmt"
func main() {
    fmt.Println("Starting...")
    panic("This is a deliberate panic!")
}
"""
    output_go_4 = run_go_code(go_code_4)
    print(f"Output Go 4: {output_go_4}\n")
