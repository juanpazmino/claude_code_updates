// © 2026 Juan Pazmino B — local harness that emulates Vercel Functions to test the chatbot.
// Usage: node dev/server.mjs   (reads ANTHROPIC_API_KEY from the repo's .env)
// Dev only — never deployed (see .vercelignore).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');

// Load the project's .env (same file the Python pipeline reads via
// python-dotenv). Never printed — see CLAUDE.md sensitive-file rules.
const envFile = path.join(root, '.env');
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
  }
} else {
  console.error('Missing .env at repo root (needs ANTHROPIC_API_KEY=...)');
  process.exit(1);
}

const chat = (await import('../api/chat.js')).default;

http.createServer(async (req, res) => {
  // Emulate Vercel's JSON body parsing and res.status/res.json helpers
  let raw = '';
  for await (const chunk of req) raw += chunk;
  try { req.body = raw ? JSON.parse(raw) : {}; } catch { req.body = {}; }
  res.status = c => { res.statusCode = c; return res; };
  res.json = o => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(o)); return res; };

  if (req.url === '/api/chat') return chat(req, res);

  // Static: serve public/ so the widget can be tested on the same origin
  const MIME = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
                 '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
  let urlPath = decodeURIComponent(req.url.split('?')[0]);
  if (urlPath === '/') urlPath = '/index.html';
  const file = path.resolve(root, 'public', '.' + urlPath);
  if (file.startsWith(path.join(root, 'public')) && fs.existsSync(file) && fs.statSync(file).isFile()) {
    res.setHeader('Content-Type', MIME[path.extname(file)] || 'application/octet-stream');
    res.setHeader('Cache-Control', 'no-store');
    return res.end(fs.readFileSync(file));
  }
  res.status(404).end();
}).listen(3000, () => console.log('chatbot dev server → http://localhost:3000'));
