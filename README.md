# Blink Ultimate — implementation starter

## What is included
- `frontend/index.html`: polished mobile-first Blink interface, local IndexedDB video library, link-format check for TeraBox, and a Blink logo animation preview.
- `backend/worker.js`: Cloudflare Worker API scaffold with health route and public metadata read route.
- `backend/schema.sql`: starter D1 schema.
- `backend/wrangler.toml.example`: deployment example.

## Important honesty note
This is a starter implementation, NOT a production-ready deployed service.
- Login/registration is a UI preview only; no real user authentication is included.
- Video storage currently uses this browser's IndexedDB only; it is not cloud storage or a backup.
- The TeraBox URL check only validates the URL format. It does not list folders or download video files. Real folder selection/import needs an authorized, technically supported TeraBox integration or a supported import flow.
- Cloudflare R2/D1 are not configured by this package. The 20 GB+ target is not active yet.
- The Worker intentionally has no unauthenticated upload or account-write routes.

## Try the frontend
Open `frontend/index.html` in a modern browser. If browser `file://` restrictions interfere, serve the frontend over a local development server. Browser storage may be cleared/evicted and has device-specific limits.

## Roadmap to production
1. Create Cloudflare account and configure Workers, D1, and R2.
2. Configure a real auth provider or implement a security-reviewed auth system with hashed passwords, secure sessions, CSRF protections where relevant, rate limiting, account recovery, and authorization checks.
3. Add short-lived signed upload/download URLs and multipart/resumable uploads for large files.
4. Implement TeraBox integration only through a permitted and reliable method; test direct-video and folder links, expired links, access permissions, and large-file failures.
5. Add server-side file validation, quotas, deduplication strategy, retries, abuse reporting, moderation, delete/export flows, and monitoring.
6. Test refresh persistence, device-to-device access, upload interruptions, permission boundaries, and deletion behavior before public launch.

## Never
- Put Cloudflare API tokens or storage secrets in frontend JavaScript or a public GitHub repository.
- Call local IndexedDB "cloud backup".
- Mark an upload as online until the server confirms that the object is stored and verified.
- Ask users to paste passwords or session cookies into a third-party importer.
