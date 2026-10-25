const http = require('http');
// Bounded contract fixture; non-personal choice values only.
http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/attributes/get_attribute_values') {
    res.writeHead(501); return res.end('Outside this contract fixture');
  }
  const body = req.body;
  if (!body?.request_header?.request_id || !body.request_body?.request_payload ||
      body.request_body.pagination_request?.page_size !== 1000) {
    res.writeHead(400); return res.end('Expected native MDS envelope and pagination');
  }
  const rows = body.request_body.pagination_request.current_page === 1 ? [
    { attribute_id: 'GENDER', value_id: 10, value_code: 'MALE', value_display: 'Male' },
    { attribute_id: 'LIVESTOCK_BREED', value_id: 42, value_code: 'LOCAL', value_display: 'Local' },
  ] : [];
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ response_header: { response_status: 'SUCCESS' },
    response_body: { response_payload: { attribute_values: rows, total: 2 } } }));
}).listen(process.env.PORT);
