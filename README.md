# Jalod Server API

A Flask-based REST API server for managing member data with automatic API documentation via Swagger/OpenAPI.

## Project Overview

**Jalod Server** is a Python Flask application designed to manage member information for an organization. The API provides endpoints to retrieve member records from a database, with automatic API documentation generated through flask-smorest and Swagger UI.

### Current Stage

This is a **minimum viable product (MVP)** with core infrastructure and basic member management functionality implemented. The foundation is solid and ready for feature expansion.

---

## Project Structure

```
jalod-server/
├── src/
│   ├── app.py                    # Flask application entry point and configuration
│   ├── db.py                     # SQLAlchemy database instance + URL normalization
│   ├── models/
│   │   ├── member.py             # SQLAlchemy ORM model for Member entity
│   │   ├── contribution.py       # SQLAlchemy ORM model for contributions
│   │   ├── treasury.py           # SQLAlchemy ORM model for treasury
│   │   └── welfare.py            # SQLAlchemy ORM model for welfare
│   ├── resources/                # Flask-smorest API blueprints
│   └── schemas/                  # Marshmallow request/response schemas
├── migrations/
│   ├── env.py                    # Alembic environment (wired to app models)
│   ├── script.py.mako            # Migration script template
│   └── versions/
│       └── 0001_initial_schema.py # Baseline schema migration
├── scripts/
│   └── init_db.py                # Database initialization script
├── alembic.ini                   # Alembic configuration
├── Dockerfile                    # Docker container configuration for Python 3.12
├── docker-compose.yml            # Docker Compose configuration for local development
├── pyproject.toml                # Project metadata and dependencies (Rye-based)
├── requirements.txt              # Python package dependencies (pip format)
└── README.md                     # This file
```

---

## Technology Stack

### Core Framework

- **Flask** (3.0.3+): Lightweight web framework for building the REST API
- **Flask-Smorest** (0.x): Extension for building REST APIs with automatic OpenAPI/Swagger documentation
- **Flask-SQLAlchemy** (3.1.1+): ORM integration layer for database operations

### Database

- **SQLAlchemy** (2.0.34+): Python SQL toolkit and Object-Relational Mapping (ORM)
- **Neon Hosted PostgreSQL**: The backend is configured to connect to a Neon-managed Postgres database through environment variables

### Database Connection Strategy

The application now expects a PostgreSQL connection string from the environment. During startup, the backend reads `DATABASE_URL`, `NEON_DATABASE_URL`, or `POSTGRES_URL`, normalizes Neon-style URLs, and connects the Flask-SQLAlchemy layer to Postgres.

If no database URL is provided, the app can fall back to SQLite for local-only development, but the intended setup is Neon Postgres.

### Development & Deployment

- **Python** 3.12.5
- **Docker** with slim Python image for containerization
- **Rye** package manager (specified in pyproject.toml)
- **python-dotenv** (1.0.1+): Environment variable management

---

## Neon PostgreSQL Setup

This project is designed to run against a Neon hosted PostgreSQL database. The steps below describe how to create the Neon account, provision the database, and connect it to the backend.

### 1. Create a Neon Account

1. Go to [https://neon.tech](https://neon.tech).
2. Sign up with your email, GitHub, or Google account.
3. Verify your account if Neon prompts you to do so.
4. After login, you will land in the Neon console where projects and databases are managed.

### 2. Create a Neon Project and Database

1. In the Neon console, create a new project.
2. Choose a project name that matches this backend, for example `jalod-server`.
3. Select the preferred region closest to your application or development environment.
4. Neon creates the first Postgres database automatically inside the project.
5. Open the project dashboard and locate the connection details or connection string.

### 3. Copy the Database Connection String

Neon provides a PostgreSQL connection URL in the project dashboard. It usually looks similar to this:

```text
postgres://USER:PASSWORD@HOST.neon.tech:5432/DB_NAME?sslmode=require&channelbinding=require
```

For this backend:

- You can paste the Neon URL into `.env` as `DATABASE_URL`.
- The application already normalizes `postgres://` to a SQLAlchemy-friendly form.
- The backend also strips unsupported Neon query parameters such as `channelbinding`.
- Keep `sslmode=require` in the URL because Neon requires SSL.

### 4. Add the Connection String to `.env`

Create or update the `.env` file in the project root with the following values:

```env
DATABASE_URL=postgres://USER:PASSWORD@HOST.neon.tech:5432/DB_NAME?sslmode=require
JWT_SECRET_KEY=your-jwt-secret-key
FLASK_APP=src/app.py
FLASK_ENV=development
DEBUG=True
```

Recommended notes:

- Do not commit `.env` to source control.
- Use the exact connection string Neon gives you, then let the app normalize it.
- If you rotate your Neon password or recreate the database, update `DATABASE_URL` immediately.

### 5. Restart the Backend After Updating `.env`

The container or local Flask process must be restarted after changing the environment file.

For Docker:

```bash
docker build -t jalod-api .
docker run -p 5000:5000 jalod-api
```

If you are reusing an existing container, stop and remove it first before running a new one.

### 6. What Happens on Startup

When the app starts with a Neon connection:

- Flask loads environment variables from `.env`.
- SQLAlchemy connects to the Neon Postgres database.
- For a production deployment, run `python scripts/init_db.py` (or `alembic upgrade head`) to create/upgrade the schema before starting the app. The Docker image does this automatically on container start.
- As a development convenience, the app still creates tables with `db.create_all()` on startup if they do not exist yet.
- Existing databases get schema adjustments for newer member columns used by authentication and contributions.

### 7. Verify the Connection

After the app starts, confirm the database is working by checking:

1. `GET /` to confirm the Flask app is running.
2. `GET /members` to verify member reads work.
3. `POST /auth/signup` to confirm inserts are reaching Neon.

If you see database errors, the most common causes are:

- incorrect username or password in the Neon URL
- a missing `sslmode=require`
- a stale container that was not rebuilt after editing `.env`
- the wrong database URL still being used by the container

---

## Database Migrations & Initialization

The database schema is managed with **Alembic** migrations. Migrations live in
`migrations/` and are configured via `alembic.ini`. The migration environment
resolves the database URL exactly like the application does (`DATABASE_URL`,
then `NEON_DATABASE_URL`, then `POSTGRES_URL`, with Neon URL normalization), so
it works with the production `.env` connection string.

### Initializing the Schema

Run the initialization script to apply all pending migrations (schema only, no
seed data):

```bash
python scripts/init_db.py
```

This is equivalent to running:

```bash
alembic upgrade head
```

The baseline migration (`0001_initial_schema.py`) creates the `Members`,
`Contributions`, `Treasury`, and `Welfare` tables. It is tolerant of databases
that already contain these tables (e.g. created earlier by `db.create_all()` on
startup), so it can be applied to both fresh and existing databases.

### Working with Migrations

After changing a model in `src/models/`, generate a new migration and apply it:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Other useful commands:

```bash
alembic current          # show the current revision
alembic history          # list applied revisions
alembic downgrade -1     # revert the last migration
```

> Note: Alembic must be installed (it is part of `requirements.txt` /
> `pyproject.toml`). Run `pip install -r requirements.txt` or `rye sync` first.

---

## Architecture & Design

### Application Structure (MVC Pattern)

1. **Models** (`src/models/member.py`)
   - Defines database schema using SQLAlchemy ORM
   - Currently includes only the `memberModel` class
   - All business logic is embedded in the model

2. **Resources/Controllers** (`src/resources/member.py`)
   - Flask-Smorest Blueprints that define API endpoints
   - Handle HTTP requests and return JSON responses
   - Two endpoints implemented for member operations

3. **Database Layer** (`src/db.py`)
   - Centralized SQLAlchemy instance for database connection management
   - Used by models and resources for database operations

4. **Application Entry Point** (`src/app.py`)
   - Flask app initialization and configuration
   - API configuration with Swagger UI settings
   - Blueprint registration
   - Default welcome route

### API Documentation

- **OpenAPI Version**: 3.0.3
- **Swagger UI**: Available at `/swagger-ui`
- **CDN-hosted Swagger UI**: Uses jsdelivr CDN for UI assets
- All endpoints are auto-documented based on decorators

---

## Database Schema

### Member Model (`memberModel`)

**Table Name**: `Members`

| Column                   | Type          | Constraints      | Description                                        |
| ------------------------ | ------------- | ---------------- | -------------------------------------------------- |
| `id`                     | Integer       | Primary Key      | Unique identifier for each member                  |
| `name`                   | String(40)    | Unique, Not Null | Member's full name                                 |
| `email_address`          | String(40)    | Unique, Not Null | Member's email address                             |
| `phone_number`           | Integer       | Nullable         | Member's phone number                              |
| `birthday`               | DateTime      | Nullable         | Member's date of birth                             |
| `age_group`              | String(20)    | Not Null         | Age group classification (e.g., "18-25", "26-35")  |
| `total_contributions`    | Numeric(10,2) | Nullable         | Sum of all contributions (supports decimal values) |
| `contributions_predated` | DateTime      | Nullable         | Date when contributions started/were predated      |

**Notes**:

- `name` and `email_address` are unique constraints (prevents duplicates)
- `age_group` is a required field for all members
- Contribution-related fields support historical tracking

---

## API Endpoints

All endpoints are prefixed with `/api/` (configured through flask-smorest) and return JSON responses.

### 1. Get All Members

- **Endpoint**: `GET /api/members`
- **Description**: Retrieves a list of all members in the database
- **Response**: 200 OK
- **Returns**: Array of member objects with fields: `id`, `name`, `email_address`, `phone_number`, `birthday`, `age_group`
- **Implementation**: Queries all records from the Members table, excludes `total_contributions` and `contributions_predated` from response

### 2. Get Member by ID

- **Endpoint**: `GET /api/members/<int:member_id>`
- **Description**: Retrieves a single member by their ID
- **Parameters**: `member_id` (URL path parameter, integer)
- **Response Success**: 200 OK with member object
- **Response Error**: 404 Not Found if member doesn't exist
- **Returns**: Single member object with fields: `id`, `name`, `email_address`, `phone_number`, `birthday`, `age_group`
- **Error Handling**: Uses flask-smorest `abort()` for 404 responses

### Root Endpoint

- **Endpoint**: `GET /`
- **Description**: Welcome message from the application
- **Returns**: "Welcome to the Jalod Server App!"

---

## Current Configuration

### Flask Configuration (`app.py`)

```python
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['API_TITLE'] = 'Jalod Server API'
app.config['API_VERSION'] = 'v1'
app.config['OPENAPI_VERSION'] = '3.0.3'
app.config['OPENAPI_URL_PREFIX'] = '/'
app.config['OPENAPI_SWAGGER_UI_PATH'] = '/swagger-ui'
app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
```

### Environment

- Uses `python-dotenv` for loading `.env` files
- The backend reads `DATABASE_URL`, `NEON_DATABASE_URL`, or `POSTGRES_URL`
- Flask debug mode is enabled in development
- JWT auth uses `JWT_SECRET_KEY` from the environment

---

## Deployment & Execution

### Docker Setup

**Dockerfile Configuration**:

- Base image: `python:3.12.5-slim`
- Working directory: `/app`
- Exposes port: `5000`
- Installs dependencies from `requirements.txt`
- Command: `flask run --host 0.0.0.0` (binds to all interfaces)

**Docker Compose**:

- Service name: `api`
- Port mapping: `5000:5000`
- Volume mount: `.:/app` (enables hot-reload during development)
- Build context: Current directory

### Running Locally

1. **Clone the repository**

   ```bash
   git clone https://github.com/loicemeyo/jalod-server.git
   cd jalod-server
   ```

2. **Option A: Using Docker Compose** (Recommended)

   ```bash
   docker-compose up
   # Application runs at http://localhost:5000
   ```

3. **Option B: Using Docker**

   ```bash
   docker build -t jalod-api .
   docker run -p 5000:5000 jalod-api
   # Application runs at http://localhost:5000
   ```

4. **Option C: Direct Python** (requires Python 3.12+)
   ```bash
   pip install -r requirements.txt
   export FLASK_APP=src/app.py
   flask run
   # Application runs at http://localhost:5000
   ```

### Testing the API

- **Welcome endpoint**: http://localhost:5000
- **Swagger UI**: http://localhost:5000/swagger-ui
- **Get all members**: http://localhost:5000/api/members
- **Get member by ID**: http://localhost:5000/api/members/1

---

## Known Limitations & Missing Features

### Current Limitations

1. **No POST/PUT/DELETE endpoints**: Only read-only (GET) operations are implemented
2. **No authentication/authorization**: No user authentication or permission system
3. **No input validation**: Request payloads are not validated (relevant for future POST/PUT endpoints)
4. **No error handling**: Limited error messaging beyond 404 responses
5. **No pagination**: All members endpoint returns entire dataset without limits
6. **Database not configured**: No database is currently initialized; would need migration setup (Alembic or similar)
7. **No tests**: No unit tests or integration tests implemented
8. **No logging**: No structured logging system in place
9. **No CORS configuration**: Not configured for cross-origin requests
10. **No data persistence**: Docker container doesn't persist database data between runs

### Ready for Implementation (Building Blocks Exist)

- **Create member** (POST /members) - Add a new member to the database
- **Update member** (PUT /members/{id}) - Modify existing member information
- **Delete member** (DELETE /members/{id}) - Remove a member from the database
- **Search/Filter members** - Add query parameters for filtering by name, age_group, email, etc.
- **Batch operations** - Create or update multiple members at once
- **Advanced error handling** - Custom error responses with validation messages
- **Request/response validation** - Using flask-smorest schemas
- **Pagination** - Implement limit/offset or cursor-based pagination
- **Sorting** - Add sorting capabilities to member list endpoint
- **Rate limiting** - Protect endpoints from abuse

---

## Dependencies

All dependencies are specified in both `requirements.txt` (pip) and `pyproject.toml` (Rye):

- `flask` (3.0.3+) - Web framework
- `flask-smorest` (0.x) - REST API framework with OpenAPI/Swagger
- `python-dotenv` (1.0.1+) - Environment variable loading
- `sqlalchemy` (2.0.34+) - SQL toolkit and ORM
- `flask-sqlalchemy` (3.1.1+) - SQLAlchemy Flask integration

---

## Development Notes for Future LLM Prompts

When requesting new features or code generation, provide context with:

1. **The feature you want to add** and how it fits into the current architecture
2. **The endpoint specification** if it's a new API endpoint (method, path, request/response format)
3. **Database changes** if needed (new fields, new models)
4. **Reference to this README** for context on the existing structure

### Example Prompts That Work Well

- "Add a POST endpoint to create new members, following the existing Member model schema and flask-smorest patterns"
- "Implement member search functionality using query parameters (name, age_group, email)"
- "Add request validation using flask-smorest schemas for member creation"
- "Create database migrations using Alembic for the existing memberModel"
- "Add pagination to the GET /members endpoint with limit and offset parameters"

---

## Next Steps

1. **Database initialization**: Set up PostgreSQL/MySQL connection and create schema
2. **Data persistence**: Add database migrations and initialization scripts
3. **CRUD operations**: Implement POST, PUT, DELETE endpoints for members
4. **Input validation**: Add request/response schema validation
5. **Testing**: Create unit and integration tests
6. **Authentication**: Add JWT or session-based authentication
7. **Logging & monitoring**: Implement structured logging and error tracking

---

## Repository Info

- **Repository**: loicemeyo/jalod-server
- **Current Branch**: main
- **Default Branch**: main
- **License**: See LICENSE file
