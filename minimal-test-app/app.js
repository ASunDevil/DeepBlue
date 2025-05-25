const http = require('http');
const port = process.env.PORT || 3000; // Allow environment variable to override port
const querystring = require('querystring');

const server = http.createServer((req, res) => {
    if (req.url === '/' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Hello from Minimal Test App!\n');
    } else if (req.url === '/test-form' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'html' });
        res.end(`
            <!DOCTYPE html>
            <html>
            <head><title>Test Form Page</title></head>
            <body>
                <h1>Simple Test Form</h1>
                <form action="/form-submitted" method="POST" id="mainForm">
                    <label for="data">Data:</label>
                    <input type="text" id="data" name="data" value="testData123">
                    <br>
                    <label for="user">User:</label>
                    <input type="text" id="user" name="user" value="testUser">
                    <br>
                    <button type="submit" id="submitBtn">Submit Form</button>
                </form>
            </body>
            </html>
        `);
    } else if (req.url === '/form-submitted' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            const params = querystring.parse(body);
            res.writeHead(200, { 'Content-Type': 'html' });
            res.end(`
                <!DOCTYPE html>
                <html>
                <head><title>Submission Success</title></head>
                <body>
                    <h1>Submission Successful</h1>
                    <p>Thank you for submitting.</p>
                    <div id="resultData">Submitted Data: ${params.data}</div>
                    <div id="resultUser">Submitted User: ${params.user}</div>
                </body>
                </html>
            `);
        });
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
    }
});

server.listen(port, () => {
  // Output the exact message format expected by server_controller.js
  console.log(\`Server is running on http://localhost:\${port}\`);
});

// Handle SIGINT for graceful shutdown
process.on('SIGINT', () => {
  console.log('minimal-test-app: SIGINT signal received. Exiting.');
  process.exit(0);
});

process.on('SIGTERM', () =>
  console.log('minimal-test-app: SIGTERM signal received. Exiting.');
  process.exit(0);
});
