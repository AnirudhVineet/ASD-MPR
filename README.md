# Campus Clubs — College Club Management

A web app for running college clubs: students register, browse and join clubs, RSVP to events and
read announcements; club admins manage members, events and announcements; site admins manage clubs.

**Stack:** Flask · SQLAlchemy · PostgreSQL · Gunicorn · Docker Compose · Prometheus · Grafana ·
GitHub Actions. Work is tracked in Jira project **AM** (ASD MPR).

## Features

| Role | Can do |
| --- | --- |
| Visitor | Browse the club directory (search + category filter), view clubs and upcoming events |
| Student | Register/log in, join/leave clubs, RSVP to events of clubs they belong to, see a dashboard of their clubs, events and announcements |
| Club admin | Edit their club, manage members (promote/demote/remove), create/edit/delete events, see attendee lists, post announcements |
| Site admin | Everything above for every club, plus create and delete clubs |

RSVPs are blocked for non-members, past events and events at capacity.

## Quick start (Docker Compose)

```bash
cp .env.example .env        # then edit the secrets
docker compose up -d --build
docker compose exec web flask create-admin --email you@college.edu --name "Your Name"
```

| Service | URL |
| --- | --- |
| Web app | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (login from `GRAFANA_ADMIN_*` in `.env`) |

Grafana opens on the provisioned **Club Manager** dashboard. Stop with `docker compose down`
(add `-v` to also delete the database and metrics volumes).

## Local development (without Docker)

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt      # Windows: .venv\Scripts\pip
flask --app wsgi run --debug                       # uses SQLite (instance/clubs.db)
flask --app wsgi create-admin --email you@college.edu
ruff check . && pytest
```

Configuration comes from environment variables: `SECRET_KEY` and `DATABASE_URL`
(default `sqlite:///clubs.db`). Tables are created on startup.

## Monitoring

The app exposes Prometheus metrics at `/metrics`:

- `http_requests_total{method,endpoint,status}` and `http_request_duration_seconds` — labelled by
  URL rule (e.g. `/clubs/<int:club_id>`) to keep cardinality bounded
- `clubapp_users`, `clubapp_clubs`, `clubapp_memberships`, `clubapp_upcoming_events`,
  `clubapp_event_rsvps`, `clubapp_announcements` — read from the database at scrape time
- `clubapp_logins_total{result}`, `clubapp_registrations_total`,
  `clubapp_membership_changes_total{action}`, `clubapp_rsvps_total{action}`

Prometheus alert rules (`monitoring/prometheus/alerts.yml`): app down, 5xx ratio above 5%,
p95 latency above 1s. Alerts are visible at http://localhost:9090/alerts (no Alertmanager is
configured, so they are not routed anywhere).

Gunicorn runs one worker with 8 threads so in-process counters stay consistent; scale by running
more containers.

## CI/CD (GitHub Actions)

`.github/workflows/ci-cd.yml` runs on every push and pull request to `main`:

1. **Lint & test** — `ruff` and `pytest`
2. **Validate config** — `promtool check config` (includes alert rules), dashboard JSON,
   `docker compose config`
3. **Smoke test** — boots the full Compose stack, checks the app, runs `create-admin` against
   PostgreSQL, confirms Prometheus scrapes the app and Grafana loaded the dashboard
4. **Publish** (pushes to `main` only) — builds and pushes
   `ghcr.io/<owner>/club-manager:latest` and `:sha-<short>` to GitHub Container Registry

## Jira workflow

Every branch, commit and PR references a Jira key from project **AM** so the GitHub for Jira
integration links it to the issue:

```bash
git checkout -b AM-14-event-reminders
git commit -m "AM-14 Add event reminder emails"
```

Use several keys when a commit spans issues (`AM-9 AM-10 ...`).

## Project layout

```
app/                Flask application (blueprints: main, auth, clubs, events, metrics)
  templates/        Jinja templates
  static/           CSS
tests/              pytest suite
monitoring/         Prometheus config + alerts, Grafana provisioning + dashboard
Dockerfile, docker-compose.yml, .github/workflows/ci-cd.yml
```
