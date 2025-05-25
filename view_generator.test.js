const assert = require('assert');
const fs = require('fs');
const path = require('path');
const generateEjsView = require('./view_generator.js'); // Assumes view_generator.js is in the same directory

console.log('Running tests for view_generator.js...\n');

const testViewName = 'test-view-for-generator';
const viewsDir = 'views';
const testFilePath = path.join(viewsDir, `${testViewName}.ejs`);

// Helper function for cleanup
function cleanup() {
  console.log('\nCleaning up...');
  if (fs.existsSync(testFilePath)) {
    fs.unlinkSync(testFilePath);
    console.log(`  ✓ Deleted ${testFilePath}`);
  }
  // Only delete viewsDir if it's empty and was likely created by this test
  if (fs.existsSync(viewsDir) && fs.readdirSync(viewsDir).length === 0) {
    try {
      fs.rmdirSync(viewsDir);
      console.log(`  ✓ Deleted directory ${viewsDir}`);
    } catch (err) {
      // It's possible another process/test created files there, so don't error out hard
      console.warn(`  ! Could not delete ${viewsDir}. It might not be empty or permissions issue.`);
    }
  } else if (fs.existsSync(viewsDir) && fs.readdirSync(viewsDir).length > 0) {
      console.log(`  ! Directory ${viewsDir} is not empty. Skipping deletion.`);
  }
}

// Run tests
try {
  console.log('Test Case 1: Successful view generation and content verification');

  // Initial cleanup in case of previous failed run
  cleanup(); 

  const result = generateEjsView(testViewName, 'Test Page Title'); // headingText is not directly used in h1/title

  // 1. Verify success message (optional, but good to check)
  assert.ok(result.startsWith('Successfully created'), `Test Case 1 Failed: Expected success message, got: ${result}`);
  console.log('  ✓ Success message received');

  // 2. Verify 'views' directory exists
  assert.ok(fs.existsSync(viewsDir), `Test Case 1 Failed: Directory '${viewsDir}' was not created.`);
  console.log(`  ✓ Directory '${viewsDir}' exists`);

  // 3. Verify the <viewName>.ejs file was created
  assert.ok(fs.existsSync(testFilePath), `Test Case 1 Failed: File '${testFilePath}' was not created.`);
  console.log(`  ✓ File '${testFilePath}' was created`);

  // 4. Read and verify file content
  const fileContent = fs.readFileSync(testFilePath, 'utf-8');
  assert.ok(fileContent.includes('<title><%= title %></title>'), 'Test Case 1 Failed: File content missing <title><%= title %></title>');
  console.log('  ✓ File content includes correct title tag');

  assert.ok(fileContent.includes('<h1><%= title %></h1>'), 'Test Case 1 Failed: File content missing <h1><%= title %></h1>');
  console.log('  ✓ File content includes correct h1 tag');
  
  const expectedPContent = `<p>This is the page for ${testViewName}. Additional content related to '<%= title %>' can go here.</p>`;
  assert.ok(fileContent.includes(expectedPContent), `Test Case 1 Failed: File content missing expected paragraph. Expected: "${expectedPContent}"`);
  console.log('  ✓ File content includes correct paragraph content');

  console.log('Test Case 1 Passed.\n');

  // Test Case 2: Idempotency (running again should still work, overwriting the file)
  console.log('Test Case 2: Idempotent view generation');
  const secondResult = generateEjsView(testViewName, 'Another Test Title');
  assert.ok(secondResult.startsWith('Successfully created'), `Test Case 2 Failed: Expected success message on overwrite, got: ${secondResult}`);
  assert.ok(fs.existsSync(testFilePath), `Test Case 2 Failed: File '${testFilePath}' should still exist after overwrite.`);
  console.log('  ✓ View generation is idempotent');
  console.log('Test Case 2 Passed.\n');


  console.log('All view_generator.js tests passed successfully!');

} catch (e) {
  console.error('A test failed unexpectedly:', e);
} finally {
  // Cleanup after tests
  cleanup();
}

// Note: view_generator.js already exports the function, so no changes needed there.
// module.exports = generateEjsView; // This is in view_generator.js
// fs.mkdirSync(path.join(projectName, 'views')); in generate_project.js also creates views.
// The cleanup in this test tries to be careful.
// If 'views' dir was created by generate_project.js test and contains other files, it won't be deleted here.
// This is fine as generate_project.test.js should handle its own full cleanup.
