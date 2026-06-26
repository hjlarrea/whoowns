from __future__ import annotations

import os
from collections.abc import Iterable
from contextlib import asynccontextmanager, contextmanager
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .domain import (
    ErrorResponse,
    OrphanedServiceResponse,
    OwnershipAssign,
    Resource,
    ResourceCreate,
    ResolveResponse,
    Service,
    ServiceCreate,
    ServiceLookupResponse,
    ServiceOwnership,
    Team,
    TeamCreate,
)
from .db import SessionLocal, init_db
from .store import ConflictError, NotFoundError, OwnershipStore


def configured_api_keys() -> set[str]:
    raw_keys = os.getenv("WHOOWNS_API_KEYS", "dev-api-key")
    return {key.strip() for key in raw_keys.split(",") if key.strip()}


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if x_api_key not in configured_api_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid X-API-Key header required",
        )


SessionFactory = Callable[[], Session]


def create_app(
    session_factory: SessionFactory = SessionLocal,
    initialize_database: bool = True,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if initialize_database:
            init_db()
        yield

    app = FastAPI(
        title="WhoOwns",
        version="0.1.0",
        description="Lightweight ownership resolution service.",
        lifespan=lifespan,
        redoc_url=None,
    )
    app.state.session_factory = session_factory

    @contextmanager
    def session_context():
        session = app.state.session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_store():
        with session_context() as session:
            yield OwnershipStore(session)

    @app.exception_handler(ConflictError)
    async def conflict_handler(_, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/teams",
        response_model=Team,
        status_code=status.HTTP_201_CREATED,
        responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
        tags=["teams"],
    )
    def create_team(
        payload: TeamCreate,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Team:
        return store.create_team(payload)

    @app.get(
        "/teams",
        response_model=list[Team],
        responses={401: {"model": ErrorResponse}},
        tags=["teams"],
    )
    def list_teams(
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Iterable[Team]:
        return store.list_teams()

    @app.get(
        "/teams/{team_ref}",
        response_model=Team,
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["teams"],
    )
    def get_team(
        team_ref: str,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Team:
        return store.get_team(team_ref)

    @app.get(
        "/teams/{team_ref}/services",
        response_model=list[Service],
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["teams"],
    )
    def list_team_services(
        team_ref: str,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Iterable[Service]:
        return store.list_services_for_team(team_ref)

    @app.post(
        "/services",
        response_model=Service,
        status_code=status.HTTP_201_CREATED,
        responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
        tags=["services"],
    )
    def create_service(
        payload: ServiceCreate,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Service:
        return store.create_service(payload)

    @app.get(
        "/services",
        response_model=list[Service],
        responses={401: {"model": ErrorResponse}},
        tags=["services"],
    )
    def list_services(
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Iterable[Service]:
        return store.list_services()

    @app.post(
        "/services/{service_ref}/ownership",
        response_model=ServiceOwnership,
        status_code=status.HTTP_201_CREATED,
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["services"],
    )
    def assign_ownership(
        service_ref: str,
        payload: OwnershipAssign,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> ServiceOwnership:
        return store.assign_ownership(
            service_ref=service_ref,
            team_ref=payload.team,
            confidence=payload.confidence,
            status=payload.status,
        )

    @app.get(
        "/services/{service_ref}",
        response_model=ServiceLookupResponse,
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["services"],
    )
    def get_service(
        service_ref: str,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> ServiceLookupResponse:
        return store.lookup_service(service_ref)

    @app.post(
        "/resources",
        response_model=Resource,
        status_code=status.HTTP_201_CREATED,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
        },
        tags=["resources"],
    )
    def create_resource(
        payload: ResourceCreate,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Resource:
        return store.create_resource(payload)

    @app.get(
        "/resources",
        response_model=list[Resource],
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["resources"],
    )
    def list_resources(
        service: str | None = Query(default=None, min_length=1),
        resource: str | None = Query(default=None, min_length=1),
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Iterable[Resource]:
        return store.list_resources(service_ref=service, resource_ref=resource)

    @app.get(
        "/resources/{resource_ref}",
        response_model=Resource,
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["resources"],
    )
    def get_resource(
        resource_ref: str,
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Resource:
        return store.get_resource(resource_ref)

    @app.get(
        "/resolve",
        response_model=ResolveResponse,
        responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
        tags=["resolution"],
    )
    def resolve_resource(
        resource: str = Query(min_length=1),
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> ResolveResponse:
        return store.resolve(resource)

    @app.get(
        "/orphaned",
        response_model=list[OrphanedServiceResponse],
        responses={401: {"model": ErrorResponse}},
        tags=["services"],
    )
    def list_orphaned(
        _: None = Depends(require_api_key),
        store: OwnershipStore = Depends(get_store),
    ) -> Iterable[OrphanedServiceResponse]:
        return [
            OrphanedServiceResponse(service=service.name)
            for service in store.orphaned_services()
        ]

    return app


app = create_app()
