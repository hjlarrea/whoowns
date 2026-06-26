from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .domain import (
    OwnershipStatus,
    Resource,
    ResourceCreate,
    ResourceSummary,
    ResolveResponse,
    Service,
    ServiceCreate,
    ServiceLookupResponse,
    ServiceOwnership,
    Team,
    TeamCreate,
)
from .models import (
    ResourceRecord,
    ServiceOwnershipRecord,
    ServiceRecord,
    TeamRecord,
)


class ConflictError(ValueError):
    pass


class NotFoundError(ValueError):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "team"


def team_from_record(record: TeamRecord) -> Team:
    return Team.model_validate(record, from_attributes=True)


def service_from_record(record: ServiceRecord) -> Service:
    return Service.model_validate(record, from_attributes=True)


def ownership_from_record(record: ServiceOwnershipRecord) -> ServiceOwnership:
    return ServiceOwnership.model_validate(record, from_attributes=True)


def resource_from_record(record: ResourceRecord) -> Resource:
    return Resource(
        id=record.id,
        type=record.type,
        name=record.name,
        service_id=record.service_id,
        metadata=record.metadata_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_seen_at=record.last_seen_at,
    )


class OwnershipStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_team(self, payload: TeamCreate) -> Team:
        slug = slugify(payload.name)
        existing = self.session.scalar(select(TeamRecord).where(TeamRecord.slug == slug))
        if existing:
            raise ConflictError(f"team already exists: {slug}")
        record = TeamRecord(
            name=payload.name,
            slug=slug,
            incident_management_team=payload.incident_management_team,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return team_from_record(record)

    def create_service(self, payload: ServiceCreate) -> Service:
        existing = self.session.scalar(
            select(ServiceRecord).where(ServiceRecord.name == payload.name)
        )
        if existing:
            raise ConflictError(f"service already exists: {payload.name}")
        record = ServiceRecord(
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return service_from_record(record)

    def assign_ownership(
        self,
        service_ref: str,
        team_ref: str,
        confidence: int,
        status: OwnershipStatus = OwnershipStatus.OWNED,
    ) -> ServiceOwnership:
        service = self.get_service_record(service_ref)
        team = self.get_team_record(team_ref)
        now = datetime.now(UTC)
        current_records = self.session.scalars(
            select(ServiceOwnershipRecord).where(
                ServiceOwnershipRecord.service_id == service.id,
                ServiceOwnershipRecord.valid_until.is_(None),
            )
        ).all()
        for record in current_records:
            record.valid_until = now
        ownership = ServiceOwnershipRecord(
            service_id=service.id,
            team_id=team.id,
            status=status,
            confidence=confidence,
            valid_from=now,
            created_at=now,
        )
        self.session.add(ownership)
        self.session.commit()
        self.session.refresh(ownership)
        return ownership_from_record(ownership)

    def create_resource(self, payload: ResourceCreate) -> Resource:
        existing = self.session.scalar(
            select(ResourceRecord).where(ResourceRecord.name == payload.name)
        )
        if existing:
            raise ConflictError(f"resource already exists: {payload.name}")
        service = self.get_service_record(payload.service)
        now = datetime.now(UTC)
        record = ResourceRecord(
            type=payload.type,
            name=payload.name,
            service_id=service.id,
            metadata_json=payload.metadata,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return resource_from_record(record)

    def list_teams(self) -> list[Team]:
        records = self.session.scalars(select(TeamRecord).order_by(TeamRecord.name)).all()
        return [team_from_record(record) for record in records]

    def get_team(self, ref: str) -> Team:
        return team_from_record(self.get_team_record(ref))

    def list_services(self) -> list[Service]:
        records = self.session.scalars(select(ServiceRecord).order_by(ServiceRecord.name)).all()
        return [service_from_record(record) for record in records]

    def list_services_for_team(self, team_ref: str) -> list[Service]:
        team = self.get_team_record(team_ref)
        records = self.session.scalars(
            select(ServiceRecord)
            .join(
                ServiceOwnershipRecord,
                ServiceOwnershipRecord.service_id == ServiceRecord.id,
            )
            .where(
                ServiceOwnershipRecord.team_id == team.id,
                ServiceOwnershipRecord.valid_until.is_(None),
                ServiceOwnershipRecord.status == OwnershipStatus.OWNED,
            )
            .order_by(ServiceRecord.name)
        ).all()
        return [service_from_record(record) for record in records]

    def list_resources(
        self,
        service_ref: str | None = None,
        resource_ref: str | None = None,
    ) -> list[Resource]:
        query = select(ResourceRecord)
        if service_ref is not None:
            service = self.get_service_record(service_ref)
            query = query.where(ResourceRecord.service_id == service.id)
        if resource_ref is not None:
            query = query.where(
                (ResourceRecord.name == resource_ref) | (ResourceRecord.id == resource_ref)
            )
        records = self.session.scalars(query.order_by(ResourceRecord.name)).all()
        return [resource_from_record(record) for record in records]

    def get_resource(self, ref: str) -> Resource:
        record = self.session.scalar(
            select(ResourceRecord).where((ResourceRecord.name == ref) | (ResourceRecord.id == ref))
        )
        if not record:
            raise NotFoundError(f"resource not found: {ref}")
        return resource_from_record(record)

    def get_team_record(self, ref: str) -> TeamRecord:
        team_id = ref
        slug = slugify(ref)
        record = self.session.scalar(
            select(TeamRecord).where((TeamRecord.slug == slug) | (TeamRecord.id == team_id))
        )
        if not record:
            raise NotFoundError(f"team not found: {ref}")
        return record

    def get_service_record(self, ref: str) -> ServiceRecord:
        record = self.session.scalar(
            select(ServiceRecord).where((ServiceRecord.name == ref) | (ServiceRecord.id == ref))
        )
        if not record:
            raise NotFoundError(f"service not found: {ref}")
        return record

    def current_ownership(self, service_id: str) -> ServiceOwnershipRecord | None:
        return self.session.scalar(
            select(ServiceOwnershipRecord)
            .where(
                ServiceOwnershipRecord.service_id == service_id,
                ServiceOwnershipRecord.valid_until.is_(None),
            )
            .order_by(ServiceOwnershipRecord.valid_from.desc())
            .limit(1)
        )

    def resolve(self, resource_name: str) -> ResolveResponse:
        resource = self.session.scalar(
            select(ResourceRecord).where(ResourceRecord.name == resource_name)
        )
        if resource:
            service = self.get_service_record(resource.service_id)
        else:
            service = self.get_service_record(resource_name)
        ownership = self.current_ownership(service.id)
        team = self.session.get(TeamRecord, ownership.team_id) if ownership and ownership.team_id else None
        return ResolveResponse(
            resource=resource_name,
            service=service.name,
            owner=team.name if team else None,
            incident_management_team=team.incident_management_team if team else None,
            confidence=ownership.confidence if ownership else None,
            status=ownership.status if ownership else OwnershipStatus.ORPHANED,
        )

    def lookup_service(self, service_ref: str) -> ServiceLookupResponse:
        service = self.get_service_record(service_ref)
        ownership = self.current_ownership(service.id)
        team = self.session.get(TeamRecord, ownership.team_id) if ownership and ownership.team_id else None
        resources = [
            ResourceSummary(type=record.type, name=record.name)
            for record in self.session.scalars(
                select(ResourceRecord).where(ResourceRecord.service_id == service.id)
            )
        ]
        return ServiceLookupResponse(
            service=service.name,
            owner=team.name if team else None,
            incident_management_team=team.incident_management_team if team else None,
            resources=sorted(resources, key=lambda resource: (resource.type, resource.name)),
        )

    def orphaned_services(self) -> list[Service]:
        services = self.session.scalars(select(ServiceRecord)).all()
        orphaned: list[Service] = []
        for service in services:
            ownership = self.current_ownership(service.id)
            if not ownership or ownership.status != OwnershipStatus.OWNED:
                orphaned.append(service_from_record(service))
        return sorted(orphaned, key=lambda service: service.name)
