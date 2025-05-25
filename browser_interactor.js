const playwright = require('playwright');

async function testSimpleForm(options) {
    const defaultOptions = {
        browserType: 'chromium',
        launchOptions: { headless: true },
        waitForNavigationTimeout: 5000,
        formSelector: null, // Default to no specific form selector
        resultSelector: null,
    };
    const config = { ...defaultOptions, ...options };

    if (!config.pageUrl || !config.inputFields || !config.submitSelector || !config.successIndicator) {
        return { success: false, error: "Missing required options: pageUrl, inputFields, submitSelector, or successIndicator." };
    }
    if (!['chromium', 'firefox', 'webkit'].includes(config.browserType)) {
        return { success: false, error: `Invalid browserType: ${config.browserType}. Must be 'chromium', 'firefox', or 'webkit'.` };
    }
    if (typeof config.successIndicator !== 'object' || (!config.successIndicator.textOnPage && !config.successIndicator.elementSelector)) {
        return { success: false, error: "Invalid successIndicator: Must be an object with 'textOnPage' or 'elementSelector'." };
    }


    let browser;
    try {
        // 1. Launch the specified browser
        console.log(`[testSimpleForm] Launching ${config.browserType} browser...`);
        browser = await playwright[config.browserType].launch(config.launchOptions);
        const context = await browser.newContext();
        const page = await context.newPage();
        console.log(`[testSimpleForm] Browser launched, new page created.`);

        // 3. Navigate to pageUrl
        console.log(`[testSimpleForm] Navigating to ${config.pageUrl}...`);
        try {
            await page.goto(config.pageUrl, { waitUntil: 'domcontentloaded', timeout: config.waitForNavigationTimeout });
        } catch (e) {
            return { success: false, error: `Failed to navigate to ${config.pageUrl}: ${e.message}` };
        }
        console.log(`[testSimpleForm] Navigation successful.`);

        // Determine form context for selectors
        const formHandle = config.formSelector ? await page.$(config.formSelector) : page;
        if (config.formSelector && !formHandle) {
             return { success: false, error: `Form with selector "${config.formSelector}" not found.` };
        }
        const scope = config.formSelector ? formHandle : page;


        // 4. Fill input fields
        console.log(`[testSimpleForm] Filling input fields...`);
        for (const field of config.inputFields) {
            try {
                const fieldElement = await scope.$(field.selector);
                if (!fieldElement) {
                    throw new Error(`Input field with selector "${field.selector}" not found ${config.formSelector ? 'within form "'+config.formSelector+'"' : ''}.`);
                }
                await fieldElement.fill(field.value);
                console.log(`[testSimpleForm]   ✓ Filled "${field.selector}" with "${field.value}"`);
            } catch (e) {
                return { success: false, error: `Error filling input field "${field.selector}": ${e.message}` };
            }
        }

        // 5. Click submit button
        console.log(`[testSimpleForm] Clicking submit button "${config.submitSelector}"...`);
        const submitButton = await scope.$(config.submitSelector);
        if (!submitButton) {
            return { success: false, error: `Submit button with selector "${config.submitSelector}" not found ${config.formSelector ? 'within form "'+config.formSelector+'"' : ''}.` };
        }

        // Using Promise.all to handle navigation that might start upon click
        // This is a common pattern: click and waitForNavigation
        try {
            await Promise.all([
                page.waitForNavigation({ timeout: config.waitForNavigationTimeout, waitUntil: 'domcontentloaded' }),
                submitButton.click(),
            ]);
            console.log(`[testSimpleForm] Submit button clicked and navigation completed.`);
        } catch (e) {
            // If waitForNavigation fails, it might be a single-page app that updates DOM instead.
            // We'll proceed to success check, as that's the ultimate arbiter.
            console.warn(`[testSimpleForm] Navigation after submit click failed or timed out: ${e.message}. Will proceed to success check.`);
        }
        

        // 7. Verify success
        console.log(`[testSimpleForm] Verifying success...`);
        let successConfirmed = false;
        if (config.successIndicator.textOnPage) {
            try {
                // Playwright's page.textContent('body') can be used, or a more specific selector if needed
                // For simplicity, using a locator that checks for the text.
                const textLocator = page.locator(`text=${config.successIndicator.textOnPage}`);
                await textLocator.waitFor({ timeout: config.waitForNavigationTimeout }); // Wait for text to appear
                if (await textLocator.count() > 0) { // Check if any element contains this text
                    successConfirmed = true;
                    console.log(`[testSimpleForm]   ✓ Success confirmed by text: "${config.successIndicator.textOnPage}"`);
                } else {
                     console.log(`[testSimpleForm]   ✗ Success text "${config.successIndicator.textOnPage}" not found.`);
                }
            } catch (e) {
                 console.log(`[testSimpleForm]   ✗ Error waiting for success text "${config.successIndicator.textOnPage}": ${e.message}`);
            }
        } else if (config.successIndicator.elementSelector) {
            try {
                await page.waitForSelector(config.successIndicator.elementSelector, { timeout: config.waitForNavigationTimeout });
                successConfirmed = true;
                console.log(`[testSimpleForm]   ✓ Success confirmed by element: "${config.successIndicator.elementSelector}"`);
            } catch (e) {
                console.log(`[testSimpleForm]   ✗ Success element "${config.successIndicator.elementSelector}" not found or timed out: ${e.message}`);
            }
        }

        if (!successConfirmed) {
            return { success: false, error: "Success indicator not found after submission." };
        }

        // 8. Retrieve result text if selector provided
        let retrievedText = null;
        if (config.resultSelector) {
            try {
                retrievedText = await page.textContent(config.resultSelector);
                console.log(`[testSimpleForm]   ✓ Retrieved text from "${config.resultSelector}": "${retrievedText}"`);
            } catch (e) {
                // Not a fatal error if result selector fails, but good to note.
                console.warn(`[testSimpleForm] Could not retrieve text using resultSelector "${config.resultSelector}": ${e.message}`);
            }
        }

        // 9. Close browser (done in finally)
        return { success: true, retrievedText: retrievedText, message: "Form submitted and success confirmed." };

    } catch (error) {
        console.error(`[testSimpleForm] An unexpected error occurred: ${error.message}`, error.stack);
        return { success: false, error: `An unexpected error occurred: ${error.message}` };
    } finally {
        if (browser) {
            console.log(`[testSimpleForm] Closing browser...`);
            await browser.close();
            console.log(`[testSimpleForm] Browser closed.`);
        }
    }
}

module.exports = {
    testSimpleForm
};
