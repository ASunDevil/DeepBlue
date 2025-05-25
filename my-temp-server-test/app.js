
const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse URL-encoded bodies
app.use(express.urlencoded({ extended: false }));

// Set view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Simple route
app.get('/', (req, res) => {
  res.render('index', { title: 'Home Page' });
});

// Route for the form
app.get('/form', (req, res) => {
  res.render('form-test', { title: 'Test Form' });
});

// Route to handle form submission
app.post('/submit-form', (req, res) => {
  const data = req.body.data; // 'data' is the name of the input field in the form
  res.render('form-success', { title: 'Form Submission Successful', submittedData: data });
});

app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
  