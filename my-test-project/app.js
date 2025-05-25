
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
  console.log(`Server is running on http://localhost:${port}`);
});
  