const { startServer, stopServer } = require('./server_controller.js');
const { testSimpleForm } = require('./browser_interactor.js');
const path = require('path');

const serverProjectPath = path.resolve('./minimal-test-app');

async function runTest() {
    let serverInfo;
    console.log('--- Starting Test: browser_interactor.js ---');

    try {
        // 1. Start the minimal web server
        console.log(`[TestScript] Attempting to start server in ${serverProjectPath}...`);
        serverInfo = await startServer(serverProjectPath);
        console.log(`[TestScript] Server started. PID: ${serverInfo.process.pid}, Port: ${serverInfo.port}`);

        // 2. Define options for testSimpleForm
        const formOptions = {
            browserType: 'chromium', // Keep as default for now
            launchOptions: { headless: true },
            pageUrl: `http://localhost:${serverInfo.port}/test-form`,
            // formSelector: '#mainForm', // The form in minimal-test-app has id "mainForm"
            inputFields: [
                { selector: '#data', value: 'Automated Test Data' },
                { selector: '#user', value: 'BrowserBot' }
            ],
            submitSelector: '#submitBtn',
            waitForNavigationTimeout: 7000, // Slightly longer for browser interactions
            successIndicator: {
                // textOnPage: 'Submission Successful' 
                elementSelector: '#resultData' // Check for the presence of result area
            },
            resultSelector: '#resultData' // Retrieve text from this element
        };

        console.log('[TestScript] Options for testSimpleForm:', JSON.stringify(formOptions, null, 2));

        // 3. Call testSimpleForm
        console.log('[TestScript] Calling testSimpleForm...');
        const formResult = await testSimpleForm(formOptions);

        console.log('[TestScript] testSimpleForm result:', formResult);

        if (!formResult.success) {
            console.error('[TestScript] testSimpleForm reported failure:', formResult.error);
            // Potentially throw an error to indicate test failure if needed for CI
        } else {
            console.log('[TestScript] testSimpleForm reported success. Retrieved text:', formResult.retrievedText);
            // Add assertions here if needed, e.g.,
            // assert.strictEqual(formResult.retrievedText, "Submitted Data: Automated Test Data");
        }

    } catch (error) {
        console.error('[TestScript] An error occurred:', error);
        // process.exitCode = 1; // Indicate test failure
    } finally {
        // 4. Stop the server
        if (serverInfo && serverInfo.process && !serverInfo.process.killed) {
            console.log('[TestScript] Attempting to stop server...');
            try {
                const stopResult = await stopServer(serverInfo.process);
                console.log(`[TestScript] Server stop result: ${stopResult}`);
            } catch (stopError) {
                console.error('[TestScript] Failed to stop server:', stopError);
            }
        } else {
            console.log('[TestScript] Server process info not available or already stopped.');
        }
        console.log('--- Test Completed: browser_interactor.js ---');
    }
}

runTest();
