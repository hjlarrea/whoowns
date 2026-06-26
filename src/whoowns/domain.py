from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class OwnershipStatus(StrEnum):
    OWNED = "OWNED"
    ORPHANED = "ORPHANED"
    DEPRECATED = "DEPRECATED"


class ServiceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class ResourceType(StrEnum):
    repository = "repository"
    kubernetes_namespace = "kubernetes_namespace"
    jira_project = "jira_project"


class Team(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    slug: str
    incident_management_team: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Service(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    status: ServiceStatus = ServiceStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceOwnership(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    service_id: str
    team_id: str | None = None
    status: OwnershipStatus = OwnershipStatus.OWNED
    confidence: int = Field(ge=0, le=100)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Resource(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ResourceType
    name: str
    service_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime | None = None


class TeamCreate(BaseModel):
    name: str = Field(min_length=1)
    incident_management_team: str | None = None


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    status: ServiceStatus = ServiceStatus.ACTIVE


class OwnershipAssign(BaseModel):
    team: str = Field(min_length=1)
    confidence: int = Field(default=100, ge=0, le=100)
    status: OwnershipStatus = OwnershipStatus.OWNED


class ResourceCreate(BaseModel):
    type: ResourceType
    name: str = Field(min_length=1)
    service: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceSummary(BaseModel):
    type: ResourceType
    name: str


class ResolveResponse(BaseModel):
    resource: str
    service: str
    owner: str | None
    incident_management_team: str | None
    confidence: int | None
    status: OwnershipStatus


class ServiceLookupResponse(BaseModel):
    service: str
    owner: str | None
    incident_management_team: str | None
    resources: list[ResourceSummary]


class OrphanedServiceResponse(BaseModel):
    service: str


class ErrorResponse(BaseModel):
    detail: str

