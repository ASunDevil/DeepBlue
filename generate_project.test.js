const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('Running tests for generate_project.js...\n');

const testProjectName = 'test-project-auto';
const projectPath = path.join(__dirname, testProjectName);

// Helper function for cleanup
function cleanup() {
  console.log('\nCleaning up...');
  if (fs.existsSync(projectPath)) {
    // Node.js < 14.14.0 needs recursive fs.rmdirSync or external lib
    // For simplicity with built-in modules, we'll use rm -rf via execSync
    // This is less safe than fs.rm(Sync) with recursive option, but works for this controlled test.
    try {
      if (process.platform === "win32") {
        execSync(`rmdir /s /q "${projectPath}"`);
      } else {
        execSync(`rm -rf "${projectPath}"`);
      }
      console.log(`  ✓ Deleted project directory ${projectPath}`);
    } catch (error) {
      console.error(`  ! Error deleting project directory ${projectPath}: ${error.message}`);
      console.error('  ! Manual cleanup might be required.');
    }
  } else {
    console.log('  ✓ Project directory does not exist, no cleanup needed for it.');
  }
}

// Run tests
try {
  console.log(`Test Case 1: Project generation for '${testProjectName}'`);

  // Initial cleanup in case of previous failed run
  cleanup();

  // 1. Run the project generator script
  try {
    const output = execSync(`node generate_project.js ${testProjectName}`, { encoding: 'utf-8' });
    console.log(`  ✓ Script execution successful: ${output.trim()}`);
    assert.ok(output.includes(`Project ${testProjectName} created successfully!`), 'Script success message not found.');
  } catch (error) {
    console.error(`  ! Error executing generate_project.js: ${error.message}`);
    console.error(`  Stderr: ${error.stderr?.toString()}`);
    console.error(`  Stdout: ${error.stdout?.toString()}`);
    assert.fail(`Failed to execute generate_project.js: ${error.message}`);
  }

  // 2. Verify project directory creation
  assert.ok(fs.existsSync(projectPath), `  ✗ Project directory '${projectPath}' was not created.`);
  console.log(`  ✓ Project directory '${projectPath}' exists.`);

  // 3. Verify key files and subdirectories
  const expectedPaths = [
    'app.js',
    'package.json',
    path.join('views', 'index.ejs'),
    path.join('public', 'css', 'style.css'),
    path.join('public', 'js', 'main.js'),
  ];

  console.log('  Verifying structure:');
  for (const p of expectedPaths) {
    const fullPath = path.join(projectPath, p);
    assert.ok(fs.existsSync(fullPath), `    ✗ Expected path '${p}' not found in project.`);
    console.log(`    ✓ Found: ${p}`);
  }

  // 4. Check package.json content
  console.log('  Verifying package.json:');
  const packageJsonPath = path.join(projectPath, 'package.json');
  const packageJsonContent = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));

  assert.strictEqual(packageJsonContent.name, testProjectName, `    ✗ package.json: name is incorrect. Expected '${testProjectName}', got '${packageJsonContent.name}'`);
  console.log(`    ✓ Name: ${packageJsonContent.name}`);
  assert.ok(packageJsonContent.dependencies && packageJsonContent.dependencies.express, '    ✗ package.json: missing express dependency.');
  console.log(`    ✓ Dependency: express version ${packageJsonContent.dependencies.express}`);
  assert.ok(packageJsonContent.dependencies && packageJsonContent.dependencies.ejs, '    ✗ package.json: missing ejs dependency.');
  console.log(`    ✓ Dependency: ejs version ${packageJsonContent.dependencies.ejs}`);

  // 5. Check app.js content
  console.log('  Verifying app.js:');
  const appJsPath = path.join(projectPath, 'app.js');
  const appJsContent = fs.readFileSync(appJsPath, 'utf-8');

  assert.ok(appJsContent.includes("const express = require('express');"), "    ✗ app.js: missing `require('express')`.");
  console.log("    ✓ Contains: require('express')");
  assert.ok(appJsContent.includes("app.set('view engine', 'ejs');"), "    ✗ app.js: missing `app.set('view engine', 'ejs')`.");
  console.log("    ✓ Contains: app.set('view engine', 'ejs')");
  assert.ok(appJsContent.includes("app.get('/', (req, res) => {"), "    ✗ app.js: missing default route `app.get('/', ...)`.");
  console.log("    ✓ Contains: default route app.get('/')");


  console.log('\nTest Case 1 Passed.\n');
  console.log('All generate_project.js tests passed successfully!');

} catch (e) {
  console.error('\nA test failed unexpectedly:', e);
  // Log additional details if it's a test assertion error from execSync
  if (e.stdout) console.error("Stdout from failed command:", e.stdout.toString());
  if (e.stderr) console.error("Stderr from failed command:", e.stderr.toString());
} finally {
  // Cleanup after tests
  cleanup();
}
