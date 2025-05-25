const assert = require('assert');
const { parseRouteText } = require('./route_parser.js'); // Assuming route_parser.js is in the same directory

console.log('Running tests for route_parser.js...\n');

// Test Suite: Valid Inputs
console.log('Testing valid inputs...');

// Test Case 1: GET request
const getRouteDesc = "CREATE GET ROUTE FOR /test-get THAT RENDERS EJS VIEW test-get-view AND PASSES TITLE VARIABLE 'Test GET Page'";
const expectedGetCode = `
app.get('/test-get', (req, res) => {
  res.render('test-get-view', { title: 'Test GET Page' });
});`.trim();
assert.strictEqual(parseRouteText(getRouteDesc), expectedGetCode, 'Test Case 1 Failed: GET route');
console.log('  ✓ GET route generated correctly');

// Test Case 2: POST request
const postRouteDesc = "CREATE POST ROUTE FOR /submit-form THAT RENDERS EJS VIEW form-success AND PASSES TITLE VARIABLE 'Form Submitted'";
const expectedPostCode = `
app.post('/submit-form', (req, res) => {
  res.render('form-success', { title: 'Form Submitted' });
});`.trim();
assert.strictEqual(parseRouteText(postRouteDesc), expectedPostCode, 'Test Case 2 Failed: POST route');
console.log('  ✓ POST route generated correctly');

// Test Case 3: PUT request
const putRouteDesc = "CREATE PUT ROUTE FOR /update/item/123 THAT RENDERS EJS VIEW item-updated-put AND PASSES TITLE VARIABLE 'Item Updated via PUT'";
const expectedPutCode = `
app.put('/update/item/123', (req, res) => {
  res.render('item-updated-put', { title: 'Item Updated via PUT' });
});`.trim();
assert.strictEqual(parseRouteText(putRouteDesc), expectedPutCode, 'Test Case 3 Failed: PUT route');
console.log('  ✓ PUT route generated correctly');

// Test Case 4: DELETE request
const deleteRouteDesc = "CREATE DELETE ROUTE FOR /delete/item/456 THAT RENDERS EJS VIEW item-deleted-info AND PASSES TITLE VARIABLE 'Item Deletion Info'";
const expectedDeleteCode = `
app.delete('/delete/item/456', (req, res) => {
  res.render('item-deleted-info', { title: 'Item Deletion Info' });
});`.trim();
assert.strictEqual(parseRouteText(deleteRouteDesc), expectedDeleteCode, 'Test Case 4 Failed: DELETE route');
console.log('  ✓ DELETE route generated correctly');

// Test Case 5: Input with varied spacing
const variedSpacingDesc = "CREATE   GET   ROUTE   FOR   /spaced-route    THAT   RENDERS   EJS   VIEW   spaced-view   AND   PASSES   TITLE   VARIABLE   'Spaced Out'";
const expectedSpacedCode = `
app.get('/spaced-route', (req, res) => {
  res.render('spaced-view', { title: 'Spaced Out' });
});`.trim();
assert.strictEqual(parseRouteText(variedSpacingDesc), expectedSpacedCode, 'Test Case 5 Failed: Varied spacing');
console.log('  ✓ Varied spacing handled correctly');
console.log('All valid input tests passed.\n');

// Test Suite: Invalid Inputs
console.log('Testing invalid inputs...');

// Test Case 6: Invalid HTTP method (FETCH)
const invalidMethodDesc = "CREATE FETCH ROUTE FOR /fetch-data THAT RENDERS EJS VIEW fetch-view AND PASSES TITLE VARIABLE 'Fetch Data'";
const expectedErrorInvalidMethod = "Error: Invalid route description format."; // As per current implementation
assert.strictEqual(parseRouteText(invalidMethodDesc), expectedErrorInvalidMethod, 'Test Case 6 Failed: Invalid HTTP method');
console.log('  ✓ Invalid HTTP method (FETCH) handled correctly');

// Test Case 7: Malformed input string (missing parts)
const malformedDesc = "CREATE GET ROUTE FOR /incomplete";
const expectedErrorMalformed = "Error: Invalid route description format.";
assert.strictEqual(parseRouteText(malformedDesc), expectedErrorMalformed, 'Test Case 7 Failed: Malformed input string');
console.log('  ✓ Malformed input string handled correctly');

// Test Case 8: Malformed input string (wrong keywords)
const wrongKeywordsDesc = "BUILD GET PATH FOR /keywords THAT SHOWS EJS TEMPLATE keywords-view WITH TITLE 'Keywords Test'";
assert.strictEqual(parseRouteText(wrongKeywordsDesc), expectedErrorMalformed, 'Test Case 8 Failed: Wrong keywords in input');
console.log('  ✓ Malformed input string (wrong keywords) handled correctly');

// Test Case 9: Path with special characters not in \w-
const specialCharPathDesc = "CREATE GET ROUTE FOR /path/to/* THAT RENDERS EJS VIEW special-view AND PASSES TITLE VARIABLE 'Special Path'";
// The regex [/\w-]+ for path will not match '*'
assert.strictEqual(parseRouteText(specialCharPathDesc), expectedErrorMalformed, 'Test Case 9 Failed: Path with special characters');
console.log('  ✓ Path with special characters (not in [\\w-]) handled correctly');

console.log('All invalid input tests passed.\n');

console.log('All route_parser.js tests passed successfully!');

// To make parseRouteText available for require, route_parser.js should export it.
// Add this to the end of route_parser.js:
// module.exports = { parseRouteText };
// If it's not already there.
// The previous subtask for route_parser.js did not explicitly add it, so I will do that now.
