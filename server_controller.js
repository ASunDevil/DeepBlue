const child_process = require('child_process');
const path = require('path');

function startServer(projectPath) {
    return new Promise((resolve, reject) => {
        const serverProcess = child_process.spawn('node', ['app.js'], {
            cwd: projectPath,
            // detached: false, // This is the default, explicitly stating for clarity
        });

        let stdoutData = '';
        let stderrData = '';
        let resolved = false;

        serverProcess.stdout.on('data', (data) => {
            if (resolved) return;
            stdoutData += data.toString();
            // Example message: "Server is running on http://localhost:3000"
            const match = stdoutData.match(/Server is running on http:\/\/localhost:(\d+)/);
            if (match && match[1]) {
                resolved = true;
                const port = parseInt(match[1], 10);
                // Clear listeners as we've succeeded or failed
                serverProcess.stdout.removeAllListeners();
                serverProcess.stderr.removeAllListeners();
                serverProcess.removeAllListeners('error');
                serverProcess.removeAllListeners('exit');
                resolve({ process: serverProcess, port: port });
            }
        });

        serverProcess.stderr.on('data', (data) => {
            if (resolved) return;
            stderrData += data.toString();
            // Reject if significant error occurs before server is ready
            // This is a simple check; more sophisticated error parsing might be needed
            if (stderrData.toLowerCase().includes('error')) {
                resolved = true;
                // Clear listeners
                serverProcess.stdout.removeAllListeners();
                serverProcess.stderr.removeAllListeners();
                serverProcess.removeAllListeners('error');
                serverProcess.removeAllListeners('exit');
                reject(new Error(`Server failed to start. Stderr: ${stderrData.trim()}`));
            }
        });

        serverProcess.on('error', (err) => {
            if (resolved) return;
            resolved = true;
            // Clear listeners
            serverProcess.stdout.removeAllListeners();
            serverProcess.stderr.removeAllListeners();
            serverProcess.removeAllListeners('error');
            serverProcess.removeAllListeners('exit');
            reject(new Error(`Failed to start server process: ${err.message}`));
        });

        serverProcess.on('exit', (code, signal) => {
            if (resolved) return; // Already resolved (e.g. successful start) or rejected
            resolved = true;
            // Clear listeners
            serverProcess.stdout.removeAllListeners();
            serverProcess.stderr.removeAllListeners();
            serverProcess.removeAllListeners('error');
            serverProcess.removeAllListeners('exit');
            reject(new Error(`Server process exited prematurely with code ${code} and signal ${signal}. Stderr: ${stderrData.trim()}. Stdout: ${stdoutData.trim()}`));
        });
    });
}

function stopServer(serverProcess) {
    return new Promise((resolve, reject) => {
        if (!serverProcess || !serverProcess.pid || serverProcess.killed || !serverProcess.connected) {
            resolve('Server process was not running or already stopped.');
            return;
        }

        if (!serverProcess || !serverProcess.pid || serverProcess.killed || !serverProcess.connected) {
            console.log('[stopServer] Process already stopped or invalid.');
            resolve('Server process was not running or already stopped.');
            return;
        }

        console.log(`[stopServer] Attempting to stop process ${serverProcess.pid}`);
        let resolved = false;
        const stopTimeout = 3000; // Reduced to 3 seconds

        // Define clearAllTimeouts function
        const clearAllTimeouts = () => {
            if (timeoutId) clearTimeout(timeoutId);
            if (serverProcess._sigtermTimeoutId) clearTimeout(serverProcess._sigtermTimeoutId);
        };
        
        const timeoutId = setTimeout(() => {
            if (resolved) return;
            console.warn(`[stopServer] Process ${serverProcess.pid} did not exit after ${stopTimeout}ms with SIGINT. Attempting SIGTERM.`);
            serverProcess.kill('SIGTERM'); // Attempt more forceful termination
            
            serverProcess._sigtermTimeoutId = setTimeout(() => {
                if (resolved) return;
                resolved = true;
                console.error(`[stopServer] Process ${serverProcess.pid} did not exit after SIGTERM. It might need to be killed manually (SIGKILL).`);
                serverProcess.removeAllListeners(); // Clean up all listeners
                reject(new Error(`Failed to stop server process ${serverProcess.pid} even with SIGTERM.`));
            }, stopTimeout); // Another 5 seconds for SIGTERM
        }, stopTimeout);

        serverProcess.on('exit', (code, signal) => {
            if (resolved) return;
            resolved = true;
            console.log(`[stopServer] Process ${serverProcess.pid} exited (code ${code}, signal ${signal}).`);
            clearAllTimeouts();
            serverProcess.removeAllListeners(); // Clean up all listeners
            resolve(`Server process ${serverProcess.pid} stopped (code ${code}, signal ${signal}).`);
        });
        
        serverProcess.on('error', (err) => { // Should not happen often with kill
            if (resolved) return;
            resolved = true;
            console.error(`[stopServer] Error event on process ${serverProcess.pid}: ${err.message}`);
            clearAllTimeouts();
            serverProcess.removeAllListeners();
            reject(new Error(`Error while trying to stop server process ${serverProcess.pid}: ${err.message}`));
        });

        try {
            console.log(`[stopServer] Sending SIGINT to process ${serverProcess.pid}.`);
            const killed = serverProcess.kill('SIGINT');
            if (!killed) { 
                 if (resolved) return;
                 resolved = true;
                 console.log(`[stopServer] SIGINT failed, process ${serverProcess.pid} likely already dead.`);
                 clearAllTimeouts();
                 serverProcess.removeAllListeners();
                 resolve('Process was already stopped or could not be signaled (SIGINT failed).');
            } else {
                console.log(`[stopServer] SIGINT sent successfully to ${serverProcess.pid}.`);
            }
        } catch (e) {
             if (resolved) return;
             resolved = true;
             console.error(`[stopServer] Exception while sending SIGINT to process ${serverProcess.pid}: ${e.message}`);
             clearAllTimeouts();
             serverProcess.removeAllListeners();
             reject(new Error(`Exception while sending SIGINT to server process ${serverProcess.pid}: ${e.message}`));
        }
    });
}

module.exports = {
    startServer,
    stopServer
};
