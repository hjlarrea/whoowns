from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from whoowns.api import create_app
from whoowns.models import Base
from whoowns.seed import seed_database


API_KEY_HEADERS = {"X-API-Key": "dev-api-key"}


def client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return TestClient(
        create_app(
            session_factory=session_factory,
            initialize_database=False,
        )
    )


def test_seed_database_loads_sample_data_idempotently() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        first_result = seed_database(session)
        second_result = seed_database(session)

    test_client = TestClient(
        create_app(
            session_factory=session_factory,
            initialize_database=False,
        )
    )
    resolved = test_client.get(
        "/resolve",
        params={"resource": "payments"},
        headers=API_KEY_HEADERS,
    )
    orphaned = test_client.get("/orphaned", headers=API_KEY_HEADERS)

    assert first_result == {
        "teams": 3,
        "services": 4,
        "ownerships": 3,
        "resources": 6,
    }
    assert second_result == {
        "teams": 0,
        "services": 0,
        "ownerships": 0,
        "resources": 0,
    }
    assert resolved.status_code == 200
    assert resolved.json()["owner"] == "Payments Platform"
    assert orphaned.status_code == 200
    assert orphaned.json() == [{"service": "legacy-api"}]


def register_payments(client: TestClient) -> None:
    assert client.post(
        "/teams",
        json={
            "name": "Payments Platform",
            "incident_management_team": "payments-oncall",
        },
        headers=API_KEY_HEADERS,
    ).status_code == 201
    assert client.post(
        "/services",
        json={"name": "payments-api"},
        headers=API_KEY_HEADERS,
    ).status_code == 201
    assert client.post(
        "/services/payments-api/ownership",
        json={"team": "payments-platform", "confidence": 100},
        headers=API_KEY_HEADERS,
    ).status_code == 201
    for payload in [
        {"type": "repository", "name": "payments-api", "service": "payments-api"},
        {"type": "kubernetes_namespace", "name": "payments", "service": "payments-api"},
        {"type": "jira_project", "name": "PAY", "service": "payments-api"},
    ]:
        assert (
            client.post("/resources", json=payload, headers=API_KEY_HEADERS).status_code
            == 201
        )


def test_resolves_registered_resource_owner() -> None:
    test_client = client()
    register_payments(test_client)

    response = test_client.get(
        "/resolve",
        params={"resource": "payments"},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "resource": "payments",
        "service": "payments-api",
        "owner": "Payments Platform",
        "incident_management_team": "payments-oncall",
        "confidence": 100,
        "status": "OWNED",
    }


def test_resolves_service_name_without_resource_record() -> None:
    test_client = client()
    register_payments(test_client)

    response = test_client.get(
        "/resolve",
        params={"resource": "payments-api"},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["owner"] == "Payments Platform"
    assert response.json()["service"] == "payments-api"


def test_service_lookup_returns_owner_and_resources() -> None:
    test_client = client()
    register_payments(test_client)

    response = test_client.get("/services/payments-api", headers=API_KEY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "service": "payments-api",
        "owner": "Payments Platform",
        "incident_management_team": "payments-oncall",
        "resources": [
            {"type": "jira_project", "name": "PAY"},
            {"type": "kubernetes_namespace", "name": "payments"},
            {"type": "repository", "name": "payments-api"},
        ],
    }


def test_lists_and_fetches_teams() -> None:
    test_client = client()
    register_payments(test_client)

    list_response = test_client.get("/teams", headers=API_KEY_HEADERS)
    detail_response = test_client.get("/teams/payments-platform", headers=API_KEY_HEADERS)

    assert list_response.status_code == 200
    assert [team["slug"] for team in list_response.json()] == ["payments-platform"]
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Payments Platform"


def test_lists_services_and_services_for_team() -> None:
    test_client = client()
    register_payments(test_client)
    assert test_client.post(
        "/services",
        json={"name": "legacy-api"},
        headers=API_KEY_HEADERS,
    ).status_code == 201

    list_response = test_client.get("/services", headers=API_KEY_HEADERS)
    team_services_response = test_client.get(
        "/teams/payments-platform/services",
        headers=API_KEY_HEADERS,
    )

    assert list_response.status_code == 200
    assert [service["name"] for service in list_response.json()] == [
        "legacy-api",
        "payments-api",
    ]
    assert team_services_response.status_code == 200
    assert [service["name"] for service in team_services_response.json()] == [
        "payments-api",
    ]


def test_lists_and_fetches_resources() -> None:
    test_client = client()
    register_payments(test_client)

    list_response = test_client.get("/resources", headers=API_KEY_HEADERS)
    service_response = test_client.get(
        "/resources",
        params={"service": "payments-api"},
        headers=API_KEY_HEADERS,
    )
    resource_query_response = test_client.get(
        "/resources",
        params={"resource": "payments"},
        headers=API_KEY_HEADERS,
    )
    resource_detail_response = test_client.get(
        "/resources/payments",
        headers=API_KEY_HEADERS,
    )

    assert list_response.status_code == 200
    assert [resource["name"] for resource in list_response.json()] == [
        "PAY",
        "payments",
        "payments-api",
    ]
    assert service_response.status_code == 200
    assert [resource["name"] for resource in service_response.json()] == [
        "PAY",
        "payments",
        "payments-api",
    ]
    assert resource_query_response.status_code == 200
    assert [resource["name"] for resource in resource_query_response.json()] == ["payments"]
    assert resource_detail_response.status_code == 200
    assert resource_detail_response.json()["name"] == "payments"


def test_lists_orphaned_services() -> None:
    test_client = client()
    register_payments(test_client)
    assert test_client.post(
        "/services",
        json={"name": "legacy-api"},
        headers=API_KEY_HEADERS,
    ).status_code == 201

    response = test_client.get("/orphaned", headers=API_KEY_HEADERS)

    assert response.status_code == 200
    assert response.json() == [{"service": "legacy-api"}]


def test_reassignment_preserves_history_and_uses_current_owner() -> None:
    test_client = client()
    register_payments(test_client)
    assert test_client.post(
        "/teams",
        json={
            "name": "Platform Operations",
            "incident_management_team": "platform-oncall",
        },
        headers=API_KEY_HEADERS,
    ).status_code == 201

    response = test_client.post(
        "/services/payments-api/ownership",
        json={"team": "platform-operations", "confidence": 90},
        headers=API_KEY_HEADERS,
    )

    assert response.status_code == 201
    assert response.json()["valid_until"] is None
    resolved = test_client.get(
        "/resolve",
        params={"resource": "payments"},
        headers=API_KEY_HEADERS,
    ).json()
    assert resolved["owner"] == "Platform Operations"
    assert resolved["confidence"] == 90


def test_mutating_requests_require_api_key() -> None:
    response = client().post("/teams", json={"name": "Payments Platform"})

    assert response.status_code == 401
    assert response.json() == {"detail": "valid X-API-Key header required"}


def test_resolution_requires_api_key() -> None:
    response = client().get("/resolve", params={"resource": "payments"})

    assert response.status_code == 401
    assert response.json() == {"detail": "valid X-API-Key header required"}


def test_redoc_is_disabled_but_openapi_and_swagger_remain_available() -> None:
    test_client = client()

    assert test_client.get("/redoc").status_code == 404
    assert test_client.get("/openapi.json").status_code == 200
    assert test_client.get("/docs").status_code == 200
