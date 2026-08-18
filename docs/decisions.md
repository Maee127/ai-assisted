# Architecture Decision Log

This document records architecture decisions established during Milestone 2.

## ADR-001 — Use a `src` package layout

**Status:** Accepted

The application package is installed from:

```text
src/lead_pipeline/
```

This prevents accidental imports from the repository root and supports normal editable and production installation.

## ADR-002 — Keep the domain independent

**Status:** Accepted

The domain layer must not depend on:

* Flask or FastAPI.
* Meta APIs.
* SQLite or PostgreSQL.
* Background-job frameworks.
* Queue implementations.
* Deployment platforms.

Domain rules must remain testable without infrastructure.

## ADR-003 — Use stable platform identifiers

**Status:** Accepted

The domain uses stable identifiers for identity and idempotency:

* `ClientId` identifies the isolated client boundary.
* `InstagramUserId` identifies an Instagram user or account.
* `InstagramEventId` identifies an interaction and acts as its idempotency key.
* `InstagramMediaId` identifies a post or reel.

A username is optional display metadata and must not define identity because it may change.

## ADR-004 — Scope records to one client

**Status:** Accepted

Every user-related record must include `ClientId`.

Data belonging to the same Instagram user across different clients must remain isolated.

The system must not join, enrich, expose, modify, or erase data across client boundaries.

## ADR-005 — Store only authorized minimal interaction data

**Status:** Accepted

`InstagramInteraction` contains only the information required for identity, traceability, classification, processing, and retention.

The complete webhook payload is not part of the domain model.

Meta-specific payload structures belong to ingestion adapters and must not leak into domain entities.

## ADR-006 — Separate sales, customer care, and uncertainty

**Status:** Accepted

The system uses separate domain records for different business outcomes:

* Sales interests belong to `LeadProfile`.
* Complaints and product problems belong to `CustomerCareCase`.
* Items unresolved after stronger-model evaluation belong to `UnresolvedRecord`.

Customer-care information must not be stored inside a sales-lead profile.

An unresolved record must not be promoted into validated lead or customer-care storage.

## ADR-007 — Preserve immutable domain records

**Status:** Accepted

Domain models are immutable dataclasses.

Updates produce new domain objects rather than mutating existing objects.

This supports:

* Evidence preservation.
* Safer processing.
* Predictable tests.
* Clear state history.
* Reduced accidental modification.

For example, adding an interest to a lead profile returns a new `LeadProfile`.

## ADR-008 — Preserve explainable classification output

**Status:** Accepted

`ClassificationResult` must preserve:

* Classification label.
* Confidence.
* Reason.
* Model name.
* Model version.
* Prompt version when applicable.

The permitted top-level classifications are:

* `SALES_LEAD`
* `CUSTOMER_CARE`
* `IRRELEVANT`
* `SPAM`
* `UNCERTAIN`

The domain does not depend on a specific classifier provider.

## ADR-009 — Preserve interest evidence

**Status:** Accepted

`InterestEvidence` must preserve:

* Interest name.
* Explicit or inferred interest type.
* Confidence.
* Stable source event ID.
* Model name.
* Model version.
* Prompt version when applicable.
* Catalogue evidence when applicable.

Low-confidence unresolved interests must remain outside confirmed lead profiles.

## ADR-010 — Keep one evolving lead profile per client-scoped user

**Status:** Accepted

`LeadProfile` represents one stable Instagram user within one client boundary.

Multiple relevant interactions may add interests to the same profile while preserving prior evidence.

The same Instagram user interacting with two clients produces two independent profiles.

## ADR-011 — Keep customer-care cases separate

**Status:** Accepted

`CustomerCareCase` represents complaints, dissatisfaction, product problems, or support needs.

A customer-care case and a lead profile may reference the same client-scoped user, but they remain separate records.

This prevents complaints from being misrepresented as sales opportunities.

## ADR-012 — Preserve unresolved results

**Status:** Accepted

`UnresolvedRecord` represents an item that remains uncertain after stronger-model evaluation.

It preserves both:

* The primary-model result.
* The stronger-model result.

The system must not force unresolved items into a final classification.

## ADR-013 — Scope erasure by client and stable user ID

**Status:** Accepted

`ErasureRequest` is scoped by:

* `ClientId`
* `InstagramUserId`

It preserves:

* Request timestamp.
* Verification timestamp.
* Optional completion timestamp.

An erasure operation for one client must not expose, modify, or delete another client’s records.

## ADR-014 — Require timezone-aware timestamps

**Status:** Accepted

Domain timestamps must be timezone-aware.

This avoids ambiguity in:

* Event ordering.
* Processing history.
* Retention calculations.
* Erasure auditing.
* Cross-system data exchange.

Naïve timestamps are rejected by domain validation.

## ADR-015 — Enforce processing transitions in the domain

**Status:** Accepted

The processing lifecycle includes:

* `RECEIVED`
* `QUEUED`
* `PROCESSING`
* `COMPLETED`
* `RETRYABLE_FAILURE`
* `PERMANENT_FAILURE`

Permitted transitions are defined in the domain layer.

Invalid transitions raise `InvalidStatusTransitionError`.

`COMPLETED` and `PERMANENT_FAILURE` are terminal states in the current model.

## ADR-016 — Use domain-specific exceptions

**Status:** Accepted

Domain-rule violations use exceptions derived from `DomainError`.

The first specific exception is:

* `InvalidStatusTransitionError`

Infrastructure-specific errors must be translated at adapter boundaries rather than leaking database, HTTP, queue, or Meta API exceptions into the domain.

## ADR-017 — Depend on repository protocols

**Status:** Accepted

Application use cases depend on abstract repository protocols.

The initial protocol is:

* `InteractionRepository`

It defines operations to:

* Add an interaction.
* Retrieve an interaction by stable event ID.

Concrete SQLite and PostgreSQL adapters will be introduced later without changing domain or application logic.

## ADR-018 — Keep application orchestration independent of infrastructure

**Status:** Accepted

The application layer coordinates use cases and depends on:

* Domain models.
* Domain rules.
* Abstract interfaces.

It must not depend directly on:

* Flask or FastAPI routes.
* Meta webhook payloads.
* SQLite or PostgreSQL connections.
* Queue implementation details.
* Deployment-platform configuration.

The initial application use case is:

* `IngestInteraction`

## ADR-019 — Keep Meta-specific logic in ingestion adapters

**Status:** Accepted

Future Meta webhook adapters may handle:

* Signature verification.
* Payload-size limits.
* Payload schema validation.
* Authorized account validation.
* Event extraction.
* Mapping Meta data into domain models.
* Retryable and non-retryable transport responses.

Meta payload structures must not become domain dependencies.

The webhook adapter defaults to a 1 MiB request-body limit. Deployments may
override this through validated configuration. Oversized bodies are rejected
before JSON parsing and must not be logged or retained.

Comment extraction requires Meta's stable Instagram-scoped commenter ID and
never substitutes username as identity. If a verified live payload omits that
ID, an authorized API enrichment step must supply it before domain mapping.

A comment-level source timestamp is preferred when supplied. Otherwise, the
adapter uses Meta's webhook notification time from the containing entry.

Webhook request processing follows this order: enforce the byte limit, verify
the signature against the exact raw body, parse JSON, validate the authorized
account, extract minimized interactions, and then call the application use case.
All interactions are extracted before persistence begins so a malformed batch
cannot create partial durable state.

## ADR-020 — Keep processing providers replaceable

**Status:** Accepted

Future classifiers, stronger models, language detectors, interest extractors, and catalogue retrievers should be accessed through provider-independent interfaces.

The domain stores their outputs and versions but does not depend on a specific vendor or SDK.

## ADR-021 — Keep privacy operations isolated

**Status:** Accepted

Retention, erasure, and anonymization behavior belongs to the privacy and persistence layers.

Privacy operations must use stable identifiers and explicit client boundaries.

They must not rely on usernames.

## ADR-022 — Keep operational data privacy-safe

**Status:** Accepted

Operational logs and errors must avoid unnecessary personal data.

They must not normally contain:

* Complete webhook payloads.
* Comment text.
* Usernames.
* Sensitive catalogue or profile evidence.
* Erased personal data.

Future observability adapters should use correlation IDs and safe structured metadata.

## ADR-023 — Defer infrastructure implementation

**Status:** Accepted

Milestone 2 establishes architecture and contracts only.

The following remain deferred to later milestones:

* PostgreSQL repositories.
* SQLite development adapters.
* Database migrations.
* Transaction handling.
* Meta webhook hardening.
* Background workers.
* Queue adapters.
* Classification providers.
* RAG and catalogue retrieval.
* Retention jobs.
* Erasure execution.
* API endpoints.
* Dashboard functionality.
* Production deployment.
