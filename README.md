# WhoOwns

WhoOwns is a lightweight ownership resolution service that answers one question:

> Given a repository, namespace, Jira project, or service, who owns it?

The MVP is a FastAPI application with in-memory storage. It supports manual registration of teams, services, ownership assignments, and resources, then resolves owners from resource or service names.

## Setup

Use pyenv and the project virtual environment.

```sh
pyenv install --skip-existing
make install
```

The repository pins Python in `.python-version` and installs dependencies from `requirements.txt` into `.venv`.

## Database

WhoOwns uses PostgreSQL for development and runtime storage.

Start only the database for local app development:

```sh
make db
```

The local default connection string is:

```text
postgresql+psycopg://whoowns:whoowns@localhost:5432/whoowns
```

Override it with `DATABASE_URL` when needed.

Load development seed data:

```sh
make seed
```

When running the full Docker Compose stack, seed through the API container:

```sh
make docker-seed
```

Reset all tables before loading seed data:

```sh
.venv/bin/python -m whoowns.seed --reset
```

## Run locally

```sh
make dev
```

The API is available at `http://127.0.0.1:8000`. FastAPI serves generated OpenAPI docs at `/docs`.

Mutating endpoints require an API key:

```text
X-API-Key: dev-api-key
```

Override the accepted keys with a comma-separated environment variable:

```sh
WHOOWNS_API_KEYS=local-key,ci-key make dev
```

## Run with Docker Compose

```sh
make docker-up
```

This starts both PostgreSQL and the API. The API is available at `http://127.0.0.1:8000`.

Stop the stack:

```sh
make docker-down
```

## Test

```sh
make test
```

## Example workflow

```sh
curl -X POST http://127.0.0.1:8000/teams \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -d '{"name":"Payments Platform","incident_management_team":"payments-oncall"}'

curl -X POST http://127.0.0.1:8000/services \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -d '{"name":"payments-api"}'

curl -X POST http://127.0.0.1:8000/services/payments-api/ownership \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -d '{"team":"payments-platform","confidence":100}'

curl -X POST http://127.0.0.1:8000/resources \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -d '{"type":"kubernetes_namespace","name":"payments","service":"payments-api"}'

curl 'http://127.0.0.1:8000/resolve?resource=payments' \
  -H 'X-API-Key: dev-api-key'
```

## API

- `POST /teams`
- `GET /teams`
- `GET /teams/{team}`
- `GET /teams/{team}/services`
- `POST /services`
- `GET /services`
- `POST /services/{service}/ownership`
- `GET /services/{service}`
- `POST /resources`
- `GET /resources`
- `GET /resources?service={service}`
- `GET /resources?resource={resource}`
- `GET /resources/{resource}`
- `GET /resolve?resource={name}`
- `GET /orphaned`
- `GET /health`
