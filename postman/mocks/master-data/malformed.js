const http = require('http');
http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/attributes/get_attribute_values') {
    res.writeHead(501); return res.end('Outside this contract fixture');
  }
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end('{not-json');
}).listen(process.env.PORT);
