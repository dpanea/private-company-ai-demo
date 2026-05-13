# Caddy reverse proxy

The demo app binds to `127.0.0.1:8000`. Caddy terminates HTTPS on the host and proxies public traffic to that local port.

## Rate-limit module

The `rate_limit` directive in `Caddyfile.example` requires `github.com/mholt/caddy-ratelimit`. Build Caddy with `xcaddy`:

```bash
xcaddy build --with github.com/mholt/caddy-ratelimit
```

The official Caddy docs recommend `xcaddy build --with ...` for custom plugin builds, and the rate-limit module documents the same command for this plugin.

## Install outline

1. Point `demo.danielpanea.com` at the Hetzner VPS.
2. Install Caddy or replace the packaged binary with the custom `xcaddy` build.
3. Copy `Caddyfile.example` into the active Caddy config path and adjust the domain if needed.
4. Run the app with `docker compose up -d --build`.
5. Reload Caddy and confirm `/api/health` returns `{"ok":"true"}` over HTTPS.

Only ports 80 and 443 should be internet-facing. Keep SSH/admin access behind Tailscale.
