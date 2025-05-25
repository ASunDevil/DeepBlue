function parseRouteText(routeDescription) {
  const regex = /CREATE\s+(GET|POST|PUT|DELETE)\s+ROUTE\s+FOR\s+([/\w-]+)\s+THAT\s+RENDERS\s+EJS\s+VIEW\s+([\w-]+)\s+AND\s+PASSES\s+TITLE\s+VARIABLE\s+'([^']*)'/i;
  const match = routeDescription.match(regex);

  if (!match) {
    return "Error: Invalid route description format.";
  }

  const httpMethod = match[1].toLowerCase();
  const path = match[2];
  const viewName = match[3];
  const titleValue = match[4];

  // Validate HTTP method (already partially done by regex, but good for explicit check)
  const validMethods = ['get', 'post', 'put', 'delete'];
  if (!validMethods.includes(httpMethod)) {
    return `Error: Unsupported HTTP method "${httpMethod}". Supported methods are GET, POST, PUT, DELETE.`;
  }

  const routeCode = `
app.${httpMethod}('${path}', (req, res) => {
  res.render('${viewName}', { title: '${titleValue}' });
});
  `;

  return routeCode.trim();
}

/*
// Example Usages:

const route1Description = "CREATE GET ROUTE FOR /products THAT RENDERS EJS VIEW product-list AND PASSES TITLE VARIABLE 'Product List Page'";
const route1Code = parseRouteText(route1Description);
console.log(route1Code);
// Expected Output:
// app.get('/products', (req, res) => {
//   res.render('product-list', { title: 'Product List Page' });
// });

const route2Description = "CREATE POST ROUTE FOR /submit-data THAT RENDERS EJS VIEW submission-success AND PASSES TITLE VARIABLE 'Data Submitted'";
const route2Code = parseRouteText(route2Description);
console.log(route2Code);
// Expected Output:
// app.post('/submit-data', (req, res) => {
//   res.render('submission-success', { title: 'Data Submitted' });
// });

const route3Description = "CREATE PUT ROUTE FOR /update-item/123 THAT RENDERS EJS VIEW item-updated AND PASSES TITLE VARIABLE 'Item Updated Successfully'";
const route3Code = parseRouteText(route3Description);
console.log(route3Code);
// Expected Output:
// app.put('/update-item/123', (req, res) => {
//   res.render('item-updated', { title: 'Item Updated Successfully' });
// });

const route4Description = "CREATE DELETE ROUTE FOR /item/456 THAT RENDERS EJS VIEW item-deleted AND PASSES TITLE VARIABLE 'Item Deleted'";
const route4Code = parseRouteText(route4Description);
console.log(route4Code);
// Expected Output:
// app.delete('/item/456', (req, res) => {
//   res.render('item-deleted', { title: 'Item Deleted' });
// });

const invalidRouteDescription = "CREATE INVALID ROUTE FOR /test";
const invalidRouteCode = parseRouteText(invalidRouteDescription);
console.log(invalidRouteCode); // Expected: Error: Invalid route description format.

const unsupportedMethodDescription = "CREATE PATCH ROUTE FOR /test THAT RENDERS EJS VIEW test-view AND PASSES TITLE VARIABLE 'Test Title'";
const unsupportedMethodCode = parseRouteText(unsupportedMethodDescription);
console.log(unsupportedMethodCode); // Expected: Error: Invalid route description format. (or a more specific error if we refine the regex/logic for method validation)

*/

module.exports = { parseRouteText };
