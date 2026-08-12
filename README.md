# Jalod Server API

A Flask-based REST API server for managing member data, contributions, welfare events, and treasury for a family social group, with JWT authentication and automatic API documentation via Swagger/OpenAPI.

## Project Overview

**Jalod Server** is a Python Flask application that powers the backend for the Jalod mobile app. It provides:

- **Member management** — create, read, update, delete members; birthday listing; each member has a login account.
- **Authentication** — JWT-based signup/login with role-based access (`user` / `admin`).
- **Contributions** — per-member contribution records (amount, date, payment type: `boma`, `mpesa`, `cash`, `bank`), scoped so each member can only manage their own records.
- **Welfare** — group events/expenses, plus a combined monthly view of events and member birthdays.
- **Treasury** — table and admin-only endpoint exist; data serving is a stub for now.

API documentation is auto-generated with flask-smorest and served via Swagger UI.

> **Note for mobile-app developers:** a separate, mobile-focused reference lives in `MOBILE_APP_README.md` (not tracked in git). This file is the general project README.

---

## Project Structure

```
jalod-server/
├── src/
│   ├── app.py                    # Flask app entry point, config, blueprints, error handlers
│   ├── db.py                     # SQLAlchemy instance, URL normalization, startup schema fixes
│   ├── logging_config.py         # Structured (JSON/console) logging with request correlation IDs
│   ├── models/
│   │   ├── member.py             # Member entity (incl. password hash + role)
│   │   ├── contribution.py       # Contribution records
│   │   ├── treasury.py           # Treasury balances
│   │   └── welfare.py            # Welfare events
│   ├── resources/                # flask-smorest blueprints (API endpoints)
│   │   ├── auth.py               # Signup / login (JWT)
│   │   ├── members.py            # Member CRUD, birthdays, own contributions
│   │   ├── contributions.py      # Contribution CRUD (ownership-scoped)
│   │   ├── treasury.py           # Treasury (admin-only)
│   │   └── welfare.py            # Welfare CRUD + monthly view
│   ├── schemas/                  # Marshmallow request/response schemas
│   └── jalod_api/                # Package marker
├── migrations/                   # Alembic migrations
│   ├── env.py
│   └── versions/0001_initial_schema.py
├── scripts/
│   └── init_db.py                # Applies pending migrations
├── tests/                        # pytest test suite
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml                # Project metadata + dependencies (Rye)
├── requirements.txt
├── .env / .flaskenv              # Environment config (never commit .env)
└── README.md
```

---

## Technology Stack

### Core Framework

- **Flask** (3.0.3+): lightweight web framework
- **Flask-Smorest** (0.x): REST API framework with automatic OpenAPI/Swagger docs and input validation via marshmallow
- **Flask-SQLAlchemy** (3.1.1+): ORM integration
- **Flask-JWT-Extended** (4.6.0+): JWT authentication + role claims
- **Flask-Marshmallow / Marshmallow-SQLAlchemy**: request/response (de)serialization

### Database

- **SQLAlchemy** (2.0.34+): ORM toolkit
- **Neon Hosted PostgreSQL** (primary): connection string from environment variables
- **SQLite** (local fallback): used automatically when no `DATABASE_URL` is set (and by tests)

### Database Connection Strategy

On startup the app reads `DATABASE_URL`, then `NEON_DATABASE_URL`, then `POSTGRES_URL`. Neon-style `postgres://` URLs are normalized to a SQLAlchemy-compatible form (`postgresql+psycopg2://`), `sslmode=require` is ensured, and unsupported Neon query params (e.g. `channelbinding`) are stripped. If no URL is set, the app falls back to `sqlite:///jalod.db`.

### Development & Deployment

- Python 3.12
- Docker (slim Python image), Docker Compose for local dev
- Rye package manager (`pyproject.toml`) / pip (`requirements.txt`)
- python-dotenv for environment loading
- Alembic for schema migrations
- pytest for tests

---

## Quickstart

### Option A: Docker Compose (recommended for local dev)

```bash
docker-compose up
# App runs at http://localhost:5000
```

### Option B: Docker

```bash
docker build -t jalod-api .
docker run -p 5000:5000 jalod-api
```

The Docker image runs `python scripts/init_db.py` before starting, so migrations are applied automatically.

### Option C: Direct Python (requires Python 3.12+)

```bash
pip install -r requirements.txt
# set DATABASE_URL (or omit for SQLite) and JWT_SECRET_KEY
flask run
# App runs at http://localhost:5000
```

### Useful URLs

- Welcome: `http://localhost:5000`
- Swagger UI: `http://localhost:5000/swagger-ui`
- OpenAPI spec: served at the root prefix (see Swagger UI)

---

## Configuration (`.env`)

Create a `.env` in the project root:

```env
DATABASE_URL=postgres://USER:PASSWORD@HOST.neon.tech:5432/DB_NAME?sslmode=require
JWT_SECRET_KEY=your-jwt-secret-key
FLASK_APP=src/app.py
FLASK_ENV=development
DEBUG=True

# Optional logging
LOG_LEVEL=INFO            # INFO | DEBUG | WARNING | ERROR
LOG_FORMAT=console        # console | json
LOG_FILE=logs/app.log     # optional file output
```

Notes:

- Do not commit `.env` to source control.
- `DATABASE_URL` may be omitted for SQLite-based local development.
- `JWT_SECRET_KEY` is required in production (a dev default is used otherwise).

---

## Neon PostgreSQL Setup

1. Create an account at [neon.tech](https://neon.tech) and a project (e.g. `jalod-server`).
2. Copy the connection string from the project dashboard (usually `postgres://USER:PASSWORD@HOST.neon.tech:5432/DB_NAME?...`).
3. Set it as `DATABASE_URL` in `.env`. Keep `sslmode=require`; the app normalizes/strips the rest.
4. Restart the backend after changing `.env`.

Verify connectivity with:

1. `GET /` — app is running
2. `GET /members` (with a bearer token) — reads work
3. `POST /auth/signup` — writes reach Neon

Common connection failures: wrong credentials, missing `sslmode=require`, stale container not rebuilt after `.env` changes.

---

## Database Migrations & Initialization

Migrations live in `migrations/` (Alembic). The migration environment resolves the database URL exactly like the app (`DATABASE_URL` → `NEON_DATABASE_URL` → `POSTGRES_URL`, with Neon normalization).

Apply pending migrations (schema only, no seed data):

```bash
python scripts/init_db.py        # equivalent to: alembic upgrade head
```

Working with migrations:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic current                  # show current revision
alembic history                  # list applied revisions
alembic downgrade -1             # revert last migration
```

The baseline migration (`0001_initial_schema.py`) creates `Members`, `Contributions`, `Treasury`, and `Welfare`. It is tolerant of databases that already contain these tables. Additionally, `db.py` runs small startup "schema fixes" (`ensure_member_auth_columns`) that add auth/contribution columns to an older `Members` table if missing.

---

## Architecture

The app follows an MVC-style layout:

1. **Models** (`src/models/`) — SQLAlchemy ORM classes for `Members`, `Contributions`, `Treasury`, `Welfare`. Business helpers live on the model (e.g. `memberModel.set_password` / `check_password` / `is_admin`).
2. **Resources** (`src/resources/`) — flask-smorest blueprints defining endpoints, auth decorators, and error handling per operation.
3. **Schemas** (`src/schemas/`) — Marshmallow schemas for request validation and response serialization (including `SQLAlchemyAutoSchema`-based schemas).
4. **Database layer** (`src/db.py`) — central SQLAlchemy instance, URL normalization, connection pool options, startup schema fixes.
5. **Application entry** (`src/app.py`) — config, JWT manager, blueprint registration, request-ID middleware, global error handlers.
6. **Logging** (`src/logging_config.py`) — console or JSON structured logging with a per-request correlation ID (also echoed as the `X-Request-ID` response header).

### Authentication

- JWT issued on signup/login via flask-jwt-extended.
- Default access-token lifetime is **15 minutes**; there is no refresh endpoint — clients re-authenticate on expiry.
- Token identity is the member id; claims include `name` and `role`.
- Roles: `user` (default) and `admin`. Treasury access requires `admin`.

### Error Handling

Error bodies vary by source; clients should rely on the HTTP status code:

- Application errors (flask-smorest `abort`) → `{"error": "<message>", "status_code": <code>}`
- JWT failures → `{"msg": "..."}` (401/422)
- Schema validation via `blp.arguments` → `422`
- Global handlers catch `HTTPException`, marshmallow `ValidationError`, `SQLAlchemyError`, and unexpected exceptions (500s).

---

## Database Schema

### Members (`Members`)

| Column                   | Type            | Constraints | Notes |
| ------------------------ | --------------- | ----------- | ----- |
| `id`                     | Integer         | PK          | |
| `name`                   | String(40)      | Unique, Not Null | Used for login |
| `email_address`          | String(40)      | Unique, Not Null | |
| `phone_number`           | Integer         | Not Null    | 32-bit int |
| `birthday`               | DateTime        | Nullable    | |
| `age_group`              | String(20)      | Nullable    | |
| `total_contributions`    | Numeric(10,2)   | Nullable    | |
| `contributions_predated` | DateTime        | Nullable    | |
| `password_hash`          | String(255)     | Not Null    | Hashed, never serialized |
| `contributions_tier`     | Numeric(10,2)   | Nullable    | Not serialized |
| `contributions_debt`     | Numeric(10,2)   | Nullable    | Not serialized |
| `loans_debt`             | Numeric(10,2)   | Nullable    | Not serialized |
| `contributions_dated_at` | DateTime        | Nullable    | Not serialized |
| `role`                   | String(10)      | Not Null    | `user` / `admin` |

Relationships: one-to-many with `Contributions` (delete-orphan cascade).

### Contributions (`Contributions`)

| Column | Type             | Constraints | Notes |
| ------ | ---------------- | ----------- | ----- |
| `id`   | Integer          | PK          | |
| `member_id` | Integer     | FK → Members.id, Not Null | |
| `amount` | Numeric(12,2)  | Not Null    | Serialized as string |
| `date`  | DateTime         | Not Null    | |
| `type`  | Enum(`boma`,`mpesa`,`cash`,`bank`) | Not Null | Serialized as `contribution_type` |

### Welfare (`Welfare`)

| Column | Type             | Constraints | Notes |
| ------ | ---------------- | ----------- | ----- |
| `id`   | Integer          | PK          | Used in item URLs |
| `event_id` | Integer       | Not Null    | Separate business id, set on create |
| `event_name` | String(100) | Not Null    | |
| `date`  | DateTime         | Not Null    | |
| `description` | Text        | Nullable    | |
| `amount_spent` | Numeric(12,2) | Nullable | |
| `status` | Enum(`Done`,`Not Completed`) | Not Null | |

### Treasury (`Treasury`)

| Column | Type             | Constraints |
| ------ | ---------------- | ----------- |
| `id`   | Integer          | PK |
| `current_balance`, `money_in_this_year`, `money_out_this_year`, `boma_yangu`, `market_fund`, `government_bonds`, `cryptocurrency` | Numeric(12,2) | Nullable |
| `current_balance_date` | DateTime | Nullable |

---

## API Endpoints

All endpoints return JSON and live at the **root path (no `/api/` prefix)**. Date/times are ISO-8601 strings; money values serialize as strings (e.g. `"250.00"`).

### Auth

#### `POST /auth/signup` — create a member account (public)
Request: `{ "name", "email_address", "phone_number", "password" }`
Response `201`: `{ "message", "access_token", "member": { id, name, email_address, phone_number, role } }`
Errors: `409` name/email already exists; `422` validation.

#### `POST /auth/login` — log in by name (public)
Request: `{ "name", "password" }`
Response `200`: same shape as signup.
Errors: `401` invalid credentials.

### Members

#### `GET /members` — list all members (🔒 auth)
Response `200`: array of member objects (id, name, email_address, phone_number, birthday, age_group, total_contributions, contributions_predated, role).

#### `POST /members` — register a member (public)
Request: `{ "name", "email_address", "phone_number", "birthday"? }`
Response `201`: member object.

#### `GET /members/{member_id}` — get one member (public)
Response `200` / `404`.

#### `PUT /members/{member_id}` — update a member (public, partial)
Response `200` / `404`.

#### `DELETE /members/{member_id}` — delete a member (🔒 auth)
Response `204` / `404`. Cascade-deletes contributions.

#### `GET /members/birthdays` — all birthdays ascending (🔒 auth)
Response `200`: `[{ id, name, birthday }]` (only members with a birthday).

#### `GET /members/me/contributions` — authenticated member's contributions, trailing 12 months (🔒 auth)
Response `200`: array of contribution objects ascending by date.

### Contributions (all 🔒 auth, ownership-scoped)

Access to another member's contribution returns `404`.

#### `POST /contributions` — record a contribution
Request: `{ "amount": "250.00", "date": "2026-07-10T00:00:00", "contribution_type": "mpesa" }` (`contribution_type` ∈ `boma|mpesa|cash|bank`)
Response `201`: `{ id, member_id, amount, date, contribution_type }`.

#### `GET /contributions/{id}` — get one of my contributions
`200` / `404`.

#### `PUT /contributions/{id}` — update one of my contributions (partial)
`200` / `404`.

#### `DELETE /contributions/{id}` — delete one of my contributions
`204` / `404`.

### Welfare

#### `GET /welfare` — list all events (public)
Response `200`: array of welfare objects ascending by date.

#### `POST /welfare` — create an event (🔒 auth)
Request: `{ "event_id", "event_name", "date", "description"?, "amount_spent"?, "status" }` (`status` ∈ `Done|Not Completed`)
Response `201`.

#### `GET /welfare/{id}` — get one event (public)
`200` / `404`. Note: `{id}` is the primary key.

#### `PUT /welfare/{id}` — update an event (🔒 auth, partial)
`200` / `404`.

#### `DELETE /welfare/{id}` — delete an event (🔒 auth)
`204` / `404`.

#### `GET /welfare/month/{year}/{month}` — events + birthdays for a month (public)
`month` 1–12 (else `400`). Response `200`: `{ "events": [...], "birthdays": [...] }`.

### Treasury

#### `GET /treasury` — get treasury data (🔒 auth + admin)
Non-admin → `403`. **Stub:** currently returns `200 []`.

### Root

#### `GET /` — welcome
Returns plain text `Welcome to the Jalod Server App!`

---

## Logging

Logging is configured centrally (`src/logging_config.py`):

- Console output by default; set `LOG_FORMAT=json` for structured JSON (log-aggregator friendly).
- `LOG_LEVEL` controls verbosity; `LOG_FILE` enables a rotating file handler (10 MB × 5).
- Every request gets a correlation ID: logs include `[request_id]` and responses carry the `X-Request-ID` header.

---

## Testing

Run the pytest suite:

```bash
pytest
```

Tests cover the full CRUD flows, auth requirements, ownership enforcement, and validation for members, contributions, welfare, birthdays, and treasury. The test client uses SQLite in a temp directory (see `tests/conftest.py`).

---

## Dependencies

Defined in both `requirements.txt` (pip) and `pyproject.toml` (Rye):

- `flask` (3.0.3+)
- `flask-smorest`
- `flask-sqlalchemy` (3.1.1+)
- `flask-jwt-extended` (4.6.0+)
- `flask-marshmallow`, `marshmallow-sqlalchemy`
- `sqlalchemy` (2.0.34+)
- `psycopg2-binary` (PostgreSQL driver)
- `alembic` (migrations)
- `python-dotenv` (1.0.1+)

---

## Known Limitations & Next Steps

- **Treasury** endpoint exists but returns no data (stub) — needs implementation.
- **No pagination** on list endpoints (`GET /members`, `GET /welfare` return full tables).
- **No refresh tokens** — access tokens expire after 15 minutes and clients must re-authenticate.
- **No CORS** configuration (relevant if a web client is added).
- **Phone numbers** stored as 32-bit integers; very long numbers may overflow.
- **No admin-management endpoints** — the `admin` role is set directly in the database.
- **No structured per-resource authorization beyond `admin`** for treasury and JWT ownership checks for contributions.
- Candidate next features: treasury implementation, pagination/filtering, refresh tokens, CORS, admin user management, more tests.
