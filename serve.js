const http = require('http');
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname);
const s = http.createServer((req, res) => {
  const fp = path.join(ROOT, req.url === '/' ? 'autotest-ui.html' : req.url);
  fs.readFile(fp, (e, d) => {
    if (e) { res.writeHead(404); res.end('Not found'); }
    else { res.writeHead(200, { 'Content-Type': 'text/html;charset=utf-8' }); res.end(d); }
  });
});
s.listen(5500, () => console.log('Server running at http://localhost:5500'));
