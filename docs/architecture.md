# Application Architecture

## Purpose

This document defines the target architecture established during Milestone 2.

The architecture separates domain rules, application orchestration, persistence, external APIs, ingestion, processing, privacy, and observability.

## Package structure

```text
src/
└── lead_pipeline/
    ├── api/
    ├── application/
    ├── domain/
    ├── ingestion/
    ├── observability/
    ├── persistence/
    ├── privacy/
    └── processing/
```

## Dependency direction

Dependencies must point inward toward the domain and application layers.

```text
API / ingestion / persistence adapters
                |
                v
        Application layer
                |
                v
           Domain layer
```

The domain layer must not depend on Flask, FastAPI, Meta APIs, SQLite, PostgreSQL, queue systems, or deployment frameworks.

The application layer may depend on domain models and abstract interfaces, but it must not depend on concrete infrastructure implementations.

Infrastructure adapters may depend on the application and domain layers.

## Domain layer

The domain layer contains the project’s core business concepts and rules.

It currently includes:

* Stable client identifiers.
* Stable Instagram user identifiers.
* Stable Instagram event identifiers.
* Stable Instagram media identifiers.
* Authorized Instagram interaction records.
* Classification results.
* Beauty-related interest evidence.
* Client-scoped lead profiles.
* Customer-care cases.
* Unresolved classification records.
* Verified erasure requests.
* Processing statuses.
* Permitted processing-status transitions.
* Domain-specific exceptions.

Domain models are immutable.

Changes to domain state should produce new domain objects rather than modifying existing objects in place.

## Application layer

The application layer coordinates business use cases.

It may depend on:

* Domain models.
* Domain rules.
* Abstract repository interfaces.
* Abstract service interfaces.

It must not depend directly on:

* Flask or FastAPI routes.
* Meta webhook payload structures.
* SQLite connections.
* PostgreSQL connections.
* Queue implementation details.
* Deployment-platform configuration.

The initial application use case is:

* `IngestInteraction`

`IngestInteraction` receives a validated `InstagramInteraction` domain object and persists it through the `InteractionRepository` interface.

## Persistence boundary

The persistence layer defines interfaces required by the application.

The initial persistence interface is:

* `InteractionRepository`

It provides operations to:

* Add an Instagram interaction.
* Retrieve an interaction by its stable Instagram event ID.

Concrete SQLite or PostgreSQL implementations must satisfy this interface without changing domain or application logic.

Database schema design, migrations, transactions, indexes, and concrete repository adapters belong to later milestones.

## Client isolation

Every user-related domain record must include a `ClientId`.

The same Instagram user interacting with two different clients must produce two independent client-scoped records.

Data must not be joined, enriched, exposed, or erased across client boundaries.

Client isolation applies to:

* Interactions.
* Lead profiles.
* Interest evidence.
* Customer-care cases.
* Unresolved records.
* Erasure operations.
* Catalogue evidence.
* Future processing results.

## Identity and idempotency

Stable Instagram platform identifiers define identity.

* `InstagramUserId` identifies an Instagram user.
* `InstagramEventId` identifies an interaction and acts as its idempotency key.
* `InstagramMediaId` identifies a post or reel.
* `ClientId` identifies the isolated client boundary.

Usernames are optional display metadata.

A username must not define identity because it may change.

Two events with different Instagram event IDs must remain distinct even when their usernames, media IDs, and text are identical.

## Interaction boundary

`InstagramInteraction` represents the minimum authorized event data required by the domain.

It includes:

* Stable event ID.
* Client ID.
* Stable Instagram user ID.
* Instagram media ID.
* Source type.
* Interaction text.
* Source timestamp.
* Collection timestamp.
* Processing status.
* Optional username.

The complete webhook payload is not part of the domain model.

Webhook verification, payload parsing, and Meta-specific validation belong to ingestion adapters.

## Classification boundary

`ClassificationResult` represents an explainable and versioned classification output.

It preserves:

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

Classification-provider implementation details must remain outside the domain.

## Interest evidence

`InterestEvidence` represents one beauty- or skincare-related interest.

It preserves:

* Interest name.
* Explicit or inferred interest type.
* Confidence.
* Source event ID.
* Model name.
* Model version.
* Prompt version when applicable.
* Catalogue evidence when applicable.

Low-confidence unresolved interests must not be added to a confirmed lead profile.

## Lead profile boundary

`LeadProfile` represents one evolving sales-lead profile for one stable Instagram user inside one client boundary.

A lead profile may accumulate multiple interests while preserving previous evidence.

Adding an interest returns a new profile rather than mutating the existing profile.

Customer-care information must not be stored inside `LeadProfile`.

## Customer-care boundary

`CustomerCareCase` represents a complaint, dissatisfaction, product problem, or support need.

Customer-care cases remain separate from sales-lead profiles.

A lead profile and a customer-care case may reference the same client-scoped Instagram user, but they must remain distinct records.

## Uncertainty boundary

`UnresolvedRecord` represents an item that remains uncertain after stronger-model evaluation.

It preserves:

* Client ID.
* User ID.
* Source event ID.
* Primary-model result.
* Stronger-model result.
* Creation timestamp.

An unresolved record must not enter:

* Validated lead storage.
* Confirmed lead profiles.
* Customer-care storage.

The system must not force an uncertain item into a final category.

## Erasure boundary

`ErasureRequest` represents a verified request to erase or anonymize user-related data within one client boundary.

It is scoped by:

* `ClientId`
* `InstagramUserId`

It preserves:

* Request timestamp.
* Verification timestamp.
* Optional completion timestamp.

An erasure operation for one client must not expose, modify, or delete records belonging to another client.

Concrete erasure execution belongs to the privacy and persistence adapters in a later milestone.

## Processing statuses

The processing lifecycle currently includes:

* `RECEIVED`
* `QUEUED`
* `PROCESSING`
* `COMPLETED`
* `RETRYABLE_FAILURE`
* `PERMANENT_FAILURE`

Permitted transitions are enforced in the domain layer.

Invalid transitions raise `InvalidStatusTransitionError`.

Completed and permanently failed records are terminal in the current transition model.

## Error handling

Domain-rule violations use domain-specific exceptions.

Infrastructure errors, HTTP errors, database errors, Meta API errors, and queue errors must be translated at adapter boundaries.

Sensitive event data, usernames, comment text, and complete payloads must not be included unnecessarily in operational error messages or logs.

## API layer

The API package will contain future HTTP routes and transport adapters.

Its responsibilities may include:

* Receiving requests.
* Validating transport-level input.
* Mapping transport data to application commands.
* Calling application use cases.
* Mapping results to HTTP responses.

Business rules must not be implemented directly inside routes.

## Ingestion layer

The ingestion package will contain future Meta webhook and event adapters.

Its responsibilities may include:

* Signature verification.
* Payload-size enforcement.
* Payload schema validation.
* Authorized account validation.
* Event extraction.
* Mapping Meta data into domain models.
* Safe handling of invalid or retryable events.

Meta-specific payload structures must not leak into the domain layer.

## Processing layer

The processing package will contain future deterministic and model-based processing components.

Its responsibilities may include:

* Text normalization.
* Language detection.
* Spam detection.
* Classification.
* Stronger-model escalation.
* Interest extraction.
* Catalogue grounding.
* Processing-version management.

Processing providers should be accessed through provider-independent interfaces.

## Privacy layer

The privacy package will contain future privacy operations.

Its responsibilities may include:

* Retention enforcement.
* Verified erasure execution.
* Anonymization.
* Privacy-safe audit records.
* Client-boundary enforcement.

Privacy rules must operate through stable identifiers and must not rely on usernames.

## Observability layer

The observability package will contain future operational diagnostics.

Its responsibilities may include:

* Structured logging.
* Metrics.
* Correlation IDs.
* Processing-duration measurements.
* Failure monitoring.
* Privacy-safe health diagnostics.

Operational logs must not contain unnecessary personal data or complete webhook payloads.

## Future adapters

Later milestones may add:

* Flask or FastAPI routes.
* Meta webhook adapters.
* PostgreSQL repositories.
* SQLite development repositories.
* Database migrations.
* Background workers.
* Queue adapters.
* Classification providers.
* Stronger-model providers.
* Catalogue retrieval adapters.
* Retention jobs.
* Erasure jobs.
* Monitoring and health checks.

These adapters must depend on the established domain and application boundaries.

They must not move infrastructure-specific behavior into the domain layer.

## Milestone 2 completion boundary

Milestone 2 establishes:

* The installable `src` package structure.
* Domain entities and value objects.
* Processing-state rules.
* Domain exceptions.
* Repository protocols.
* An initial application use case.
* Architecture documentation.
* Architecture decision records.
* Automated domain and architecture tests.

Milestone 2 does not implement:

* Production database adapters.
* Database migrations.
* Meta webhook hardening.
* Background workers.
* Classification providers.
* RAG.
* Retention jobs.
* Erasure execution.
* API endpoints.
* Dashboard functionality.
* Production deployment.
