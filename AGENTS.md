# Repository Guidelines

## Project Structure & Module Organization

This repository contains product documentation and an initial FastAPI MVP for WhoOwns, a lightweight ownership resolution service. The main source of truth for product behavior is `docs/PRD.md`, which defines the product vision, domain model, MVP scope, and API direction.

Application code lives outside the docs root:

- `src/whoowns/` for FastAPI routes, domain models, and in-memory storage.
- `tests/` for pytest coverage.
- `docs/` for product, architecture, and API documentation.
- `assets/` for diagrams or supporting images.

## Project Status

The project has an initial FastAPI MVP backed by PostgreSQL through SQLAlchemy. Production authentication storage and migrations are not implemented yet.

## Build, Test, and Development Commands

- `make install` to create `.venv` and install dependencies from `requirements.txt`.
- `make db` to start PostgreSQL for local development.
- `make docker-up` to start the API and PostgreSQL through Docker Compose.
- `make test` to run the pytest suite.
- `make dev` to start the local FastAPI service with generated OpenAPI docs.

## Languages and Frameworks

Build the application in Python using FastAPI. Write tests with pytest. Document the HTTP API through OpenAPI generated from the FastAPI application where possible.

## Coding Style & Naming Conventions

Keep Markdown concise, structured, and easy to scan. Use sentence-case headings unless the document already uses another style. Prefer fenced code blocks with language tags, for example `json` or `text`.

For code, use clear domain names from the PRD: `Team`, `Service`, `ServiceOwnership`, and `Resource`. Use lowercase, hyphenated file names for documentation, such as `api-design.md`.

## Testing Guidelines

Use pytest for automated tests once code is added. Include tests with each implementation change and place them under `tests/` or the language-specific standard test location. Name tests after behavior, such as `test_resolves_repository_owner` or `test_marks_service_orphaned`.

## Commit & Pull Request Guidelines

This repository has no commit history yet, so no existing commit convention can be inferred. Use short, imperative commit messages, for example `Add ownership API draft`.

Pull requests should include a brief summary, the reason for the change, any validation performed, and links to related issues or decisions. Include screenshots only when changing visual documentation or generated diagrams.

## Agent-Specific Instructions

Before modifying files in this repository, check whether the working directory is a git repository and ask whether a new branch should be created. Do not overwrite an existing `AGENTS.md`.
