const http = require('http');
const fs = require('fs');
const url = require('url');
const { Pool } = require('pg');

const pool = new Pool({
    user: 'app_user',
    password: 'app_password',
    host: 'localhost',
    database: 'breach_lab',
    port: 5432,
});

const server = http.createServer(async (req, res) => {
    // Allows both terminal tools and browsers to communicate
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    const parsedUrl = url.parse(req.url, true);

    // PATHWAY 1: If you go to http://localhost:3000/ it serves the website input form!
    if (parsedUrl.pathname === '/' || parsedUrl.pathname === '/index.html') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(fs.readFileSync('index.html'));
    } 
    
    // PATHWAY 2: The raw data bridge used by your inputs and terminal curls
    else if (parsedUrl.pathname === '/search') {
        const usernameInput = parsedUrl.query.username || '';
        
        const dangerousQuery = `SELECT username, email FROM users WHERE username = '${usernameInput}'`;
        console.log(`\n[SERVER] Executing SQL: ${dangerousQuery}`);

        try {
            const dbResult = await pool.query(dangerousQuery);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(dbResult.rows));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end(`DB Error: ${err.message}`);
        }
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

server.listen(3000, () => {
    console.log('Server is running! Webpage at http://localhost:3000');
});
