# ADR 001 — Clean Architecture

**Date:** 2026-07-05  
**Status:** Accepted  
**Deciders:** landai-systems engineering

---

## Context

VERIDA needs to be maintainable, testable, and evolvable.  
The initial team is small; onboarding must be fast.  
We expect to swap infrastructure components (e.g. switch from heuristic attestation to ML) without disrupting business logic.

---

## Decision

We adopt **Clean Architecture** (Robert C. Martin) with the following layer structure:

```
domain/          ← entities, value objects — no external deps
application/     ← use cases, port interfaces (Protocols), command/query handlers
infrastructure/  ← concrete adapters: DB, cache, email, 3rd party APIs
api/             ← FastAPI routers, request/response schemas
```

**Dependency rule:** Source code dependencies point inward only.  
`api` may import from `application` and `infrastructure`.  
`application` may import from `domain` only.  
`domain` imports nothing from outside the standard library.

**Port / Adapter pattern:**
- Application layer defines `Protocol` interfaces (ports).
- Infrastructure layer provides concrete implementations (adapters).
- Adapters are injected via FastAPI's `Depends()` at the router level.

---

## Consequences

### Positive

- Domain and application layers are testable with zero infrastructure setup.
- Swapping an adapter (e.g. replacing heuristic checker with ML) requires no changes in application or domain.
- New developers can understand business rules by reading `domain/` and `application/` only.
- `mypy --strict` on `domain/` and `application/` enforces type safety where it matters most.

### Negative

- More files and indirection than a simple CRUD pattern.
- Requires discipline to avoid leaking framework types into the domain.
- Slightly more boilerplate for simple CRUD operations.

### Neutral

- The project starts with `make check` enforcing the architecture via mypy's strict mode on inner layers.
- ADRs are required before adding framework imports to `domain/` or `application/`.

---

## Alternatives considered

| Alternative | Reason rejected |
|-------------|----------------|
| Django MTV | Heavy ORM coupling; harder to test domain without DB |
| Flat module structure | Doesn't scale; mixing concerns from day one |
| Hexagonal (Ports & Adapters only, no layers) | Equivalent in spirit; Clean Architecture has better naming conventions for onboarding |

---

## References

- Robert C. Martin — *Clean Architecture* (2017)
- [FastAPI Bigger Applications guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
