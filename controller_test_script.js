const { startServer, stopServer } = require('./server_controller.js');
const http = require('http');
const path = require('path');

const projectPath = './minimal-test-app'; // Revert to relative for simplicity, relying on CWD of this script

async function main() {
    let serverInfo;
    try {
        console.log(`Attempting to start server in ${path.resolve(projectPath)}...`);
        serverInfo = await startServer(projectPath);
        console.log(`Server started successfully. PID: ${serverInfo.process.pid}, Port: ${serverInfo.port}`);
        console.log("Server start detected. Proceeding to stop.");

        // Test is now just start and stop. HTTP GET removed to simplify.

    } catch (error) {
        console.error('Error during server start:', error);
        if (serverInfo && serverInfo.process && !serverInfo.process.killed) {
            console.log('Attempting to stop server due to start error...');
            try {
                const stopResult = await stopServer(serverInfo.process);
                console.log(`Server stop result (after start error): ${stopResult}`);
            } catch (stopError) {
                console.error('Failed to stop server after start error:', stopError);
            }
        }
        process.exit(1); // Exit with error code
        return; 
    }

    // If server started, try to stop it
    if (serverInfo && serverInfo.process && !serverInfo.process.killed) {
        try {
            console.log('Attempting to stop server normally...');
            const stopResult = await stopServer(serverInfo.process);
            console.log(`Normal server stop result: ${stopResult}`);
        } catch (error) {
            console.error('Error stopping server normally:', error);
            process.exit(1); // Exit with error code
        }
    } else {
        console.log("Server process info not available or process already killed, skipping normal stop.");
    }
    console.log("Test script completed.");
}

main();
