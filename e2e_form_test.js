const fs = require('fs').promises;
const path = require('path');
const { execSync, spawnSync } = require('child_process'); // Using spawnSync for better error handling
const assert = require('assert');

const { startServer, stopServer } = require('./server_controller');
const { testSimpleForm } = require('./browser_interactor');

const generateProjectScript = path.resolve(__dirname, 'generate_project.js');

(async () => {
    const timestamp = Date.now();
    const projectName = `e2e-test-project-${timestamp}`;
    const projectPath = path.resolve(__dirname, projectName);
    const testValue = `test-data-${timestamp}`;
    let serverInfo; // To store { process, port }

    console.log('--- Starting E2E Form Test ---');
    console.log(`Project Name: ${projectName}`);
    console.log(`Project Path: ${projectPath}`);
    console.log(`Test Value: ${testValue}`);

    try {
        // 1. Generate Project
        console.log(`[E2E] Generating project: ${projectName} at ${projectPath}...`);
        // Using spawnSync for better control over stdio and error reporting
        const genProcess = spawnSync('node', [generateProjectScript, projectName], {
            stdio: 'inherit', // Show output from generate_project.js
            encoding: 'utf-8'
        });
        if (genProcess.status !== 0) {
            throw new Error(`Project generation failed with status ${genProcess.status}. Stderr: ${genProcess.stderr}`);
        }
        console.log('[E2E] Project generation script completed.');

        // Verify project directory exists
        try {
            await fs.access(projectPath);
            console.log('[E2E] Project directory verified.');
        } catch (e) {
            throw new Error(`Project directory ${projectPath} not found after generation.`);
        }
        
        // CRITICAL STEP: Install dependencies in the generated project
        // This is likely to fail or cause issues in the sandbox environment
        console.log(`[E2E] Installing dependencies for ${projectName}... (This may fail in sandbox)`);
        const npmInstallProcess = spawnSync('npm', ['install'], {
            cwd: projectPath,
            stdio: 'inherit',
            encoding: 'utf-8'
        });
        if (npmInstallProcess.status !== 0) {
            // Log error but attempt to continue, as server_controller might still work if dependencies were cached/pre-installed
            // or if the script is run outside the sandbox where npm install works.
            console.warn(`[E2E] npm install failed with status ${npmInstallProcess.status}. Stderr: ${npmInstallProcess.stderr}. Proceeding with caution.`);
        } else {
            console.log('[E2E] npm install completed successfully.');
        }


        // 2. Start Server
        console.log('[E2E] Starting server...');
        serverInfo = await startServer(projectPath);
        console.log(`[E2E] Server started. PID: ${serverInfo.process.pid}, Port: ${serverInfo.port}`);

        // 3. Test Form Submission
        const pageUrl = `http://localhost:${serverInfo.port}/form`;
        console.log(`[E2E] Testing form at: ${pageUrl}`);
        
        const formOptions = {
            pageUrl,
            inputFields: [{ selector: '#dataInput', value: testValue }], // Matches form-test.ejs
            submitSelector: 'button[type="submit"]', // Matches form-test.ejs
            // successIndicator: { textOnPage: `You submitted: ${testValue}` }, // This can be tricky with textContent.
            successIndicator: { elementSelector: '#submittedData' }, // Check for the element's presence first
            resultSelector: '#submittedData', // ID of the strong tag in form-success.ejs
            waitForNavigationTimeout: 10000, // Increased timeout for browser
            launchOptions: { headless: true } // Explicitly ensure headless
        };
        
        const result = await testSimpleForm(formOptions);

        console.log('[E2E] Browser interaction result:', JSON.stringify(result, null, 2));
        
        assert.strictEqual(result.success, true, `Browser interaction failed: ${result.error}`);
        
        // Playwright's textContent includes all text within the element, including children.
        // The strong tag is #submittedData, its text content is what we want.
        // Minimal-test-app's form-success.ejs has: <p>You submitted: <strong id="submittedData"><%= submittedData %></strong></p>
        // So, result.retrievedText should be exactly testValue.
        assert.strictEqual(result.retrievedText, testValue, `Expected submitted data text to be '${testValue}', but got '${result.retrievedText}'`);
        console.log('[E2E] E2E form test assertions passed!');

    } catch (error) {
        console.error('[E2E] Test failed:', error);
        process.exitCode = 1; // Indicate failure
    } finally {
        // 4. Cleanup
        if (serverInfo && serverInfo.process && !serverInfo.process.killed) {
            console.log('[E2E] Stopping server...');
            try {
                await stopServer(serverInfo.process);
                console.log('[E2E] Server stopped.');
            } catch (stopError) {
                console.error('[E2E] Failed to stop server:', stopError);
                 if (process.exitCode !== 1) process.exitCode = 1; // Indicate failure if not already set
            }
        } else {
             console.log('[E2E] Server not started or already stopped, skipping server stop.');
        }

        console.log(`[E2E] Cleaning up project directory: ${projectPath}...`);
        try {
            await fs.rm(projectPath, { recursive: true, force: true });
            console.log('[E2E] Project directory cleaned up.');
        } catch (cleanupError) {
            console.error('[E2E] Failed to clean up project directory:', cleanupError);
             if (process.exitCode !== 1) process.exitCode = 1;
        }
        console.log('--- E2E Form Test Completed ---');
        if (process.exitCode === 1) {
            console.log("Exiting with error code 1.");
        }
    }
})();
