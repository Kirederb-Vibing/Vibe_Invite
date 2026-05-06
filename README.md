# Vibe Invite

A self-hosted invitation and RSVP service for private events. Guests receive a personal link and respond without creating an account. Supports households, polls, comment threads, PWA, and automatic reminders.

---

## Features

- **Events** — create with date, venue, description, and optional cover image
- **Themes** — birthday, wedding, Christmas, Easter, summer party, and more
- **Invitations** — solo or household (multiple members under one invitation)
- **RSVP flow** — yes / no / maybe, individual responses per household member
- **Deadline** — automatic conversion of "maybe" to "no" when the deadline passes
- **Reminders** — automatic reminder emails to maybe-guests N days before the event
- **Comment thread** — guests can post comments on the event page
- **Poll** — attach a vote with multiple options to any event
- **Guest book / contacts** — reusable household and contact lists
- **Cancellation** — mark an event as cancelled and notify all guests by email
- **Auto-archiving** — events are automatically archived the day after they take place
- **PWA** — installable as an app on mobile and tablet
- **Security** — HSTS, secure cookies, CSRF protection, comment rate limiting

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 6 (Python 3.12) |
| Database | PostgreSQL 16 |
| Task queue | Django-Q2 (daily reminders and auto-archiving) |
| Web server | Gunicorn |
| Containers | Docker + Docker Compose |
| Proxy | Caddy (bundled) or any external proxy |

---

## Ports

| Service | Port | Notes |
|---------|------|-------|
| `vibe_invite_web` | 8000 | Always exposed to the host — point your proxy here |
| `caddy` | 80 / 443 | Only when using the `caddy` profile |
| `vibe_invite_db` | 5432 | PostgreSQL — internal only, never exposed to the host |

---

## Setup guide

You need:
- A Linux server with [Docker](https://docs.docker.com/engine/install/) installed
- A domain name pointing to your server
- An SMTP account for sending emails (e.g. Mailgun, Brevo, Simply, Gmail SMTP)

**Step 1 — Clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/vibe-invite vibe-invite
cd vibe-invite
```

**Step 2 — Create your configuration file**

```bash
cp .env.example .env
```

**Step 3 — Fill in `.env`**

| Variable | What to set |
|----------|------------|
| `SECRET_KEY` | A long random string — generate with the command below |
| `DB_PASSWORD` | Any strong password for the database |
| `ALLOWED_HOSTS` | Your domain, e.g. `events.example.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://events.example.com` |
| `SITE_URL` | `https://events.example.com` |
| `EMAIL_HOST` | Your SMTP server hostname |
| `EMAIL_HOST_USER` | Your SMTP username |
| `EMAIL_HOST_PASSWORD` | Your SMTP password |
| `DEFAULT_FROM_EMAIL` | The "From" address guests will see |

Generate a secret key:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Step 4 — Start the app**

Choose the option that matches your setup:

---

### Option A — Caddy (recommended, auto-SSL)

Caddy is bundled and handles HTTPS automatically. Use this if you have no existing reverse proxy.

Add to `.env`:
```env
DOMAIN=events.example.com
ACME_EMAIL=your@email.com
```

```bash
make start-caddy
```

---

### Option B — External proxy (Nginx Proxy Manager, Traefik, Caddy standalone, Pangolin…)

The app listens on port `8000`. Point your proxy at `http://<server-ip>:8000`.

```bash
make start
```

**Nginx Proxy Manager** — add a Proxy Host: domain → `http://<server-ip>:8000`, enable SSL.

**Traefik** — point a router at `http://<server-ip>:8000`, or add labels via `docker-compose.override.yml`:
```yaml
# docker-compose.override.yml
services:
  vibe_invite_web:
    networks: [default, traefik_net]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.events.rule=Host(`events.example.com`)"
      - "traefik.http.routers.events.entrypoints=websecure"
      - "traefik.http.routers.events.tls.certresolver=letsencrypt"
      - "traefik.http.services.events.loadbalancer.server.port=8000"
networks:
  traefik_net:
    external: true
    name: traefik
```

**Pangolin** — if newt already runs as a system service, just point its target at `http://localhost:8000`. If you want newt bundled in this stack instead:
```bash
# Add PANGOLIN_ENDPOINT, PANGOLIN_SITE_ID, PANGOLIN_SITE_SECRET to .env, then:
make start-pangolin
```

---

**Step 5 — Create your first admin user**

```bash
make createsuperuser
```

---

## Useful commands

```bash
make help              # List all available commands

make start             # Start (external proxy, port 8000)
make start-caddy       # Start with built-in Caddy (auto-SSL)
make start-pangolin    # Start with Pangolin newt agent bundled

make stop              # Stop everything
make logs              # Follow live logs
make update            # Pull latest code and restart
make shell             # Open a Django shell
make migrate           # Run database migrations
make createsuperuser   # Create an admin user
make backup-db         # Dump database to a local .sql file
```

---

## Environment variables reference

See [`.env.example`](.env.example) for the full list with comments.

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Always | Long random Django secret key |
| `DEBUG` | Always | `False` in production |
| `ALLOWED_HOSTS` | Always | Your domain (comma-separated) |
| `CSRF_TRUSTED_ORIGINS` | Always | `https://your-domain` |
| `SITE_URL` | Always | Full URL (used in emails and links) |
| `DB_PASSWORD` | Always | PostgreSQL password |
| `EMAIL_HOST` | Always | SMTP server hostname |
| `EMAIL_HOST_USER` | Always | SMTP username |
| `EMAIL_HOST_PASSWORD` | Always | SMTP password |
| `DEFAULT_FROM_EMAIL` | Always | Sender address shown to guests |
| `ADMIN_EMAIL` | Always | Receives admin/approval notifications |
| `DOMAIN` | Caddy | Your domain (e.g. `events.example.com`) |
| `ACME_EMAIL` | Caddy | Email for Let's Encrypt certificate notifications |
| `PANGOLIN_ENDPOINT` | Pangolin (bundled) | URL of your Pangolin server |
| `PANGOLIN_SITE_ID` | Pangolin (bundled) | Site ID from Pangolin dashboard |
| `PANGOLIN_SITE_SECRET` | Pangolin (bundled) | Site secret from Pangolin dashboard |

---

## Automatic background tasks

The `vibe_invite_worker` container runs Django-Q and handles:

| Task | Schedule | Description |
|------|----------|-------------|
| `send_maaske_reminders` | Daily | Sends reminders to "maybe" guests; converts to "no" when deadline passes |
| `auto_arkiver_events` | Daily | Automatically archives events the day after they take place |

Schedules are created automatically on first `migrate` — no manual setup required.

---

## User management

New users can request access via the login page. The admin receives an email with approve/reject links.

Create the first admin user:
```bash
make createsuperuser
```

The Django admin panel is available at `/admin/`.

---

## Updates

```bash
make update
```

This pulls the latest code, rebuilds the image, and restarts — migrations run automatically on startup.

---

## Storage — custom host paths

By default all data lives in Docker-managed named volumes. If you want data to land in a specific directory on the host (e.g. for easier backups or a dedicated disk), create a `docker-compose.override.yml` in the project root.

**Example — store everything under `/data/vibe-invite`:**

```yaml
# docker-compose.override.yml
services:
  vibe_invite_db:
    volumes:
      - /data/vibe-invite/db:/var/lib/postgresql/data

  vibe_invite_web:
    volumes:
      - /data/vibe-invite/media:/app/media
      - /data/vibe-invite/staticfiles:/app/staticfiles
      - /data/vibe-invite/logs:/app/logs

volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vibe-invite/db
  media:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vibe-invite/media
  staticfiles:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vibe-invite/staticfiles
  logs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vibe-invite/logs
```

Create the directories before starting:

```bash
mkdir -p /data/vibe-invite/{db,media,staticfiles,logs}
```

`docker-compose.override.yml` is merged automatically — no changes to the existing compose files are needed.

> **Media files only on S3?**  
> If you set `USE_S3=True` in `.env`, uploaded images go directly to your S3 bucket and the `media` volume/directory is unused. See [`.env.example`](.env.example) for the full S3 configuration.

---

## Backup and restore

```bash
# Backup database to a local file
make backup-db

# Restore from backup
cat backup_20260506_120000.sql | docker compose exec -T vibe_invite_db psql -U vibe_invite vibe_invite

# Backup uploaded images and media
docker cp $(docker compose ps -q vibe_invite_web):/app/media ./media_backup
```
