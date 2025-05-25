const fs = require('fs');
const path = require('path');

function generateEjsView(viewName, headingText) {
  const viewsDir = 'views';
  const filePath = path.join(viewsDir, `${viewName}.ejs`);

  // Ensure the 'views' directory exists
  if (!fs.existsSync(viewsDir)) {
    try {
      fs.mkdirSync(viewsDir);
    } catch (err) {
      return `Error creating directory ${viewsDir}: ${err.message}`;
    }
  }

  // Construct EJS content
  // headingText is not directly used as per instruction to use <%= title %> for h1
  const ejsContent = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><%= title %></title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <h1><%= title %></h1>
    <p>This is the page for ${viewName}. Additional content related to '<%= title %>' can go here.</p>
    <script src="/js/main.js"></script>
</body>
</html>
`;

  try {
    fs.writeFileSync(filePath, ejsContent);
    return `Successfully created ${filePath}`;
  } catch (err) {
    return `Error writing file ${filePath}: ${err.message}`;
  }
}

// Simple test case
if (require.main === module) {
  const testViewName = 'sample-view';
  const testHeadingText = 'Sample Page Title'; // This text isn't directly in h1 or title tag
  
  const result = generateEjsView(testViewName, testHeadingText);
  console.log(result);

  // Test case for existing directory
  const anotherViewName = 'another-sample';
  const anotherResult = generateEjsView(anotherViewName, "Another Page");
  console.log(anotherResult);

  // Verify file creation (optional, for manual check or further automated test steps)
  // if (result.startsWith("Successfully created")) {
  //   const createdFilePath = path.join('views', `${testViewName}.ejs`);
  //   try {
  //     const content = fs.readFileSync(createdFilePath, 'utf-8');
  //     console.log(\`\nContent of ${createdFilePath}:\n\${content}\`);
  //   } catch (e) {
  //     console.error(\`Error reading created file: \${e.message}\`);
  //   }
  // }
}

module.exports = generateEjsView; // Export for potential use in other modules
