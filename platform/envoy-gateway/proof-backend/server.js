// L3 proof backend — dependency-free HTTP server with a deterministic body.
//
// Why Node instead of busybox httpd: the local `alpine:latest` build ships a
// busybox WITHOUT the `httpd` applet (verified: `busybox --list | grep -x httpd`
// returned nothing and no /bin|/usr/sbin/httpd exists), so the busybox approach
// crash-looped with `exec: "httpd": executable file not found in $PATH`.
// `node:22-alpine` is already present locally, is arm64, and needs no pull.
const http = require('node:http');

const PORT = process.env.PORT || 8080;
const MARKER = 'LOCAL-ENVOY-GATEWAY-OK\n';

const server = http.createServer((req, res) => {
  // Logged so the Envoy -> backend hop is visible as evidence in pod logs.
  console.log(`${new Date().toISOString()} ${req.method} ${req.url} peer=${req.socket.remoteAddress}`);
  res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
  res.end(req.url.startsWith('/proof') ? `${MARKER}path=/proof\n` : MARKER);
});

server.listen(PORT, '0.0.0.0', () => console.log(`listening on ${PORT}`));
