from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from .db import SessionLocal, engine, init_db
from .domain import ResourceCreate, ServiceCreate, TeamCreate
from .models import Base
from .store import ConflictError, OwnershipStore


SEED_TEAMS = [
    {
        "name": "Payments Platform",
        "incident_management_team": "payments-oncall",
    },
    {
        "name": "Infrastructure",
        "incident_management_team": "infra-oncall",
    },
    {
        "name": "Developer Experience",
        "incident_management_team": "devex-oncall",
    },
]

SEED_SERVICES = [
    {
        "name": "payments-api",
        "description": "Processes payment authorization and capture requests.",
    },
    {
        "name": "checkout",
        "description": "Owns customer checkout orchestration.",
    },
    {
        "name": "internal-developer-portal",
        "description": "Internal tooling entrypoint for engineering teams.",
    },
    {
        "name": "legacy-api",
        "description": "Example service intentionally left orphaned.",
    },
]

SEED_OWNERSHIPS = [
    {
        "service": "payments-api",
        "team": "payments-platform",
        "confidence": 100,
    },
    {
        "service": "checkout",
        "team": "payments-platform",
        "confidence": 100,
    },
    {
        "service": "internal-developer-portal",
        "team": "developer-experience",
        "confidence": 90,
    },
]

SEED_RESOURCES = [
    {
        "type": "repository",
        "name": "payments-api",
        "service": "payments-api",
        "metadata": {"provider": "github", "organization": "acme"},
    },
    {
        "type": "kubernetes_namespace",
        "name": "payments",
        "service": "payments-api",
        "metadata": {"cluster": "prod-us-east-1"},
    },
    {
        "type": "jira_project",
        "name": "PAY",
        "service": "payments-api",
    },
    {
        "type": "repository",
        "name": "checkout",
        "service": "checkout",
        "metadata": {"provider": "github", "organization": "acme"},
    },
    {
        "type": "kubernetes_namespace",
        "name": "checkout-prod",
        "service": "checkout",
        "metadata": {"cluster": "prod-us-east-1"},
    },
    {
        "type": "repository",
        "name": "internal-developer-portal",
        "service": "internal-developer-portal",
        "metadata": {"provider": "github", "organization": "acme"},
    },
]


def seed_database(session: Session) -> dict[str, int]:
    store = OwnershipStore(session)
    created = {"teams": 0, "services": 0, "ownerships": 0, "resources": 0}

    for team in SEED_TEAMS:
        try:
            store.create_team(TeamCreate(**team))
            created["teams"] += 1
        except ConflictError:
            pass

    for service in SEED_SERVICES:
        try:
            store.create_service(ServiceCreate(**service))
            created["services"] += 1
        except ConflictError:
            pass

    for ownership in SEED_OWNERSHIPS:
        current = store.current_ownership(
            store.get_service_record(ownership["service"]).id
        )
        team = store.get_team_record(ownership["team"])
        if current and current.team_id == team.id:
            continue
        store.assign_ownership(
            service_ref=ownership["service"],
            team_ref=ownership["team"],
            confidence=ownership["confidence"],
        )
        created["ownerships"] += 1

    for resource in SEED_RESOURCES:
        try:
            store.create_resource(ResourceCreate(**resource))
            created["resources"] += 1
        except ConflictError:
            pass

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the WhoOwns development database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before loading seed data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.reset:
        Base.metadata.drop_all(bind=engine)
    init_db()
    with SessionLocal() as session:
        created = seed_database(session)
    print(
        "Seeded database: "
        f"{created['teams']} teams, "
        f"{created['services']} services, "
        f"{created['ownerships']} ownerships, "
        f"{created['resources']} resources created."
    )


if __name__ == "__main__":
    main()
