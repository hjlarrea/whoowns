# PRD: WhoOwns

## Overview

WhoOwns is a lightweight ownership resolution service that answers a single question:

> Who owns this?

The system allows organizations to register services, associate them with teams, and map organizational resources to those services.

Unlike developer portals, CMDBs, or service catalogs, WhoOwns focuses exclusively on ownership resolution and ownership visibility.

The product is intentionally small.

---

# Problem Statement

Engineering organizations consistently struggle to answer ownership questions.

Examples:

- Who owns this repository?
- Who owns this Kubernetes namespace?
- Which team should receive this incident?
- Which Jira project belongs to which team?
- Is this resource still owned by anyone?

Most organizations attempt to solve this through:

- Confluence pages
- Wikis
- Spreadsheets
- Backstage catalogs
- Tribal knowledge

These solutions often fail because they require continuous maintenance and are difficult to consume during operational events.

The problem is not documentation.

The problem is ownership resolution.

---

# Product Vision

Provide a simple API capable of resolving ownership for any registered engineering resource.

Example:

Input:

```text
payments-api
```

Output:

```text
Payments Platform
```

The product should be simple enough that engineers can immediately understand how to use it and simple enough that teams can keep it updated.

---

# Goals

## Primary Goals

- Resolve ownership for engineering resources.
- Maintain a single source of truth for service ownership.
- Support manual registration through APIs.
- Track ownership history.
- Identify orphaned services.
- Support future automation and discovery.

## Non-Goals

- Developer portal
- Service catalog
- Documentation platform
- CMDB
- Architecture modeling
- Dependency graphs
- Incident management
- Asset inventory

---

# Core Concepts

## Team

A team responsible for one or more services.

Example:

```text
Payments Platform
Infrastructure
Developer Experience
```

Teams may change over time.

### Team Properties

```text
id
name
slug
incident_management_team
created_at
updated_at
```

Example:

```json
{
  "name": "Payments Platform",
  "incident_management_team": "payments-oncall"
}
```

The incident management team allows ownership resolution to integrate with alerting and incident workflows without coupling to a specific tool.

---

## Service

The stable ownership boundary.

Services are the primary object owned by teams.

Examples:

```text
payments-api
checkout
user-profile
```

### Service Properties

```text
id
name
description
status
created_at
updated_at
```

---

## Service Ownership

Ownership is assigned at the service level.

Resources inherit ownership through their associated service.

### Properties

```text
id
service_id
team_id
status
confidence
valid_from
valid_until
```

### Status

```text
OWNED
ORPHANED
DEPRECATED
```

### Confidence

```text
100 = manually assigned
90  = imported
70  = inferred
```

Ownership history is preserved by creating new ownership records rather than overwriting existing ones.

---

## Resource

A resource is any object associated with a service.

Resources do not belong directly to teams.

Resources belong to services.

Services belong to teams.

### MVP Resource Types

```text
repository
kubernetes_namespace
jira_project
```

### Resource Properties

```text
id
type
name
service_id
metadata
created_at
updated_at
last_seen_at
```

Examples:

Repository:

```json
{
  "type": "repository",
  "name": "payments-api"
}
```

Kubernetes Namespace:

```json
{
  "type": "kubernetes_namespace",
  "name": "payments"
}
```

Jira Project:

```json
{
  "type": "jira_project",
  "name": "PAY"
}
```

### Metadata

Additional system-specific information is stored in metadata.

Example:

```json
{
  "provider": "github",
  "organization": "acme"
}
```

Metadata is not required for ownership resolution.

The primary lookup mechanism is the resource name.

---

# Data Model

## teams

```text
id
name
slug
incident_management_team
created_at
updated_at
```

## services

```text
id
name
description
status
created_at
updated_at
```

## service_ownerships

```text
id
service_id
team_id
status
confidence
valid_from
valid_until
created_at
```

## resources

```text
id
type
name
service_id
metadata
created_at
updated_at
last_seen_at
```

---

# API

## Teams

### Create Team

```http
POST /teams
```

Request:

```json
{
  "name": "Payments Platform",
  "incident_management_team": "payments-oncall"
}
```

---

## Services

### Create Service

```http
POST /services
```

Request:

```json
{
  "name": "payments-api"
}
```

### Assign Ownership

```http
POST /services/{id}/ownership
```

Request:

```json
{
  "team": "payments-platform",
  "confidence": 100
}
```

---

## Resources

### Create Resource

```http
POST /resources
```

Repository:

```json
{
  "type": "repository",
  "name": "payments-api",
  "service": "payments-api"
}
```

Namespace:

```json
{
  "type": "kubernetes_namespace",
  "name": "payments",
  "service": "payments-api"
}
```

Jira Project:

```json
{
  "type": "jira_project",
  "name": "PAY",
  "service": "payments-api"
}
```

---

# Ownership Resolution

The ownership resolution endpoint is the primary product capability.

### Resolve Resource

```http
GET /resolve?resource=payments-api
```

Response:

```json
{
  "resource": "payments-api",
  "service": "payments-api",
  "owner": "Payments Platform",
  "incident_management_team": "payments-oncall",
  "confidence": 100
}
```

---

# Service Lookup

### Get Service

```http
GET /services/payments-api
```

Response:

```json
{
  "service": "payments-api",
  "owner": "Payments Platform",
  "incident_management_team": "payments-oncall",
  "resources": [
    {
      "type": "repository",
      "name": "payments-api"
    },
    {
      "type": "kubernetes_namespace",
      "name": "payments"
    },
    {
      "type": "jira_project",
      "name": "PAY"
    }
  ]
}
```

---

# Orphaned Services

### List Orphaned Services

```http
GET /orphaned
```

Response:

```json
[
  {
    "service": "legacy-api"
  }
]
```

---

# Example Workflow

## Register a New Service

Create team:

```json
{
  "name": "Payments Platform",
  "incident_management_team": "payments-oncall"
}
```

Create service:

```json
{
  "name": "payments-api"
}
```

Assign ownership:

```text
payments-api -> Payments Platform
```

Register repository:

```json
{
  "type": "repository",
  "name": "payments-api",
  "service": "payments-api"
}
```

Register namespace:

```json
{
  "type": "kubernetes_namespace",
  "name": "payments",
  "service": "payments-api"
}
```

Register Jira project:

```json
{
  "type": "jira_project",
  "name": "PAY",
  "service": "payments-api"
}
```

---

## Incident Example

An alert references the namespace:

```text
payments
```

The incident system queries:

```http
GET /resolve?resource=payments
```

Response:

```json
{
  "service": "payments-api",
  "owner": "Payments Platform",
  "incident_management_team": "payments-oncall"
}
```

The incident can immediately be routed to the correct team.

---

# Authentication

## MVP

```text
API Keys
```

Each client receives an API key for authentication.

## Future

```text
OAuth2
OIDC
SAML
```

---

# Future Enhancements

## Discovery

Automatic registration from:

- GitHub
- GitLab
- Kubernetes
- Jira

## Search

```http
GET /search?q=payments
```

Used to discover resources and services.

## Additional Resource Types

Potential future additions:

```text
dashboard
runbook
database
bucket
kafka_topic
dns_record
alert
```

---

# Success Metrics

## Product Metrics

Ownership lookup success rate:

```text
> 95%
```

Median lookup latency:

```text
< 100ms
```

## Organizational Metrics

- Percentage of services with owners
- Number of orphaned services
- Time to identify ownership during incidents
- Reduction in ownership-related support requests

---

# Guiding Principle

WhoOwns exists to answer one question:

> Given a repository, namespace, Jira project, or service, who owns it?

Everything else is secondary.
