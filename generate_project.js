const fs = require('fs');
const path = require('path');

function createProject(projectName) {
  // Create project directory
  fs.mkdirSync(projectName);

  // Create package.json
  const packageJsonContent = {
    name: projectName,
    version: '1.0.0',
    description: '',
    main: 'app.js',
    scripts: {
      start: 'node app.js',
      test: 'echo "Error: no test specified" && exit 1',
    },
    keywords: [],
    author: '',
    license: 'ISC',
    dependencies: {
      express: '^4.17.1',
      ejs: '^3.1.6',
    },
  };
  fs.writeFileSync(
    path.join(projectName, 'package.json'),
    JSON.stringify(packageJsonContent, null, 2)
  );

  // Create app.js
  const appJsContent = `
const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Set view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Simple route
app.get('/', (req, res) => {
  res.render('index', { title: 'Home Page' });
});

app.listen(port, () => {
  console.log(\`Server is running on http://localhost:\${port}\`);
});
  `;
  fs.writeFileSync(path.join(projectName, 'app.js'), appJsContent);

  // Create views directory and index.ejs
  fs.mkdirSync(path.join(projectName, 'views'));
  const indexEjsContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><%= title %></title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <h1><%= title %></h1>
    <p>Welcome to the generated Express application!</p>
    <script src="/js/main.js"></script>
</body>
</html>
  `;
  fs.writeFileSync(path.join(projectName, 'views', 'index.ejs'), indexEjsContent);

  // Create public directory
  fs.mkdirSync(path.join(projectName, 'public'));

  // Create public/css directory and style.css
  fs.mkdirSync(path.join(projectName, 'public', 'css'));
  const styleCssContent = `
body {
  font-family: sans-serif;
}
  `;
  fs.writeFileSync(path.join(projectName, 'public', 'css', 'style.css'), styleCssContent);

  // Create public/js directory and main.js
  fs.mkdirSync(path.join(projectName, 'public', 'js'));
  const mainJsContent = `
console.log('Main script loaded');
  `;
  fs.writeFileSync(path.join(projectName, 'public', 'js', 'main.js'), mainJsContent);

  console.log('Project ' + projectName + ' created successfully!');
}

// Get project name from command line arguments
const projectName = process.argv[2];

if (!projectName) {
  console.error('Please provide a project name.');
  process.exit(1);
}

createProject(projectName);
