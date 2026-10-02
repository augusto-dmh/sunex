---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted: research notes on the 2026 Laravel stack and open-source HR systems
informed:
---

# ADR-0002: Build on Laravel 13, PHP 8.4 and PostgreSQL 17 with pgvector

## Context and Problem Statement

Sunex needs a backend framework, a PHP version and a database before any feature can be built.
The product's core is a dated employment history whose rows must never overlap, a permission model
evaluated as of a date, an approval workflow, a transactional outbox, and two AI agents that use
retrieval over company policies. The author's strongest stack is Laravel, and the project is a
portfolio piece that Laravel and international reviewers will read.

Which framework version, PHP version and database give that design its strongest guarantees with
current, supported packages?

## Decision Drivers

- The database must be able to forbid overlapping effective-dated rows by itself, not only in
  application code (product value "a fact has a date and a reason").
- Vector search for the policy Q&A agent, without a second datastore.
- Every first-party and Spatie package the design relies on should be on its current major.
- Long support window: v1 takes 12 weeks and must not start on a framework in security-only mode.
- One runtime, one CI pipeline, one deploy for a solo maintainer.

## Considered Options

- Laravel 13 + PHP 8.4 + PostgreSQL 17 with pgvector and btree_gist (chosen)
- Laravel 13 + PHP 8.3
- Laravel 12
- Laravel with MySQL 8
- Symfony + Doctrine
- Python (Django, or Frappe HR as a base)

## Decision Outcome

Chosen option: "Laravel 13 + PHP 8.4 + PostgreSQL 17 with pgvector and btree_gist", because it is
the only combination where every package in the design is on its current major, and PostgreSQL is
the only candidate database that enforces non-overlapping ranges natively and serves vector search.

- **Laravel 13** (released 2026-03-17, bug fixes until Q3 2027, security fixes until 2028-03-17)
  ships the first-party AI SDK and native vector queries (`whereVectorSimilarTo`), and Laravel 12
  is already in security-fix-only mode ([Laravel 13 release notes](https://laravel.com/docs/13.x/releases)).
- **PHP 8.4**: Pest 5 requires `^8.4` ([Packagist](https://packagist.org/packages/pestphp/pest)),
  as do `spatie/laravel-activitylog` 5 ([Packagist](https://packagist.org/packages/spatie/laravel-activitylog))
  and `spatie/laravel-model-states` 2.14 ([Packagist](https://packagist.org/packages/spatie/laravel-model-states)).
  On PHP 8.3 the project would start on Pest 4 and activitylog 4.
- **PostgreSQL 17** with two extensions:
  - `btree_gist`, so an exclusion constraint can combine equality on `employment_id` with overlap
    (`&&`) on `daterange` / `tstzrange` columns. This is what makes "no two employment versions
    overlap in both valid and recorded time" a database guarantee
    ([ADR-0005](0005-bitemporal-employment-versions.md)), and the same mechanism forbids
    overlapping absence periods.
  - `pgvector`, for embeddings of policy documents; Laravel 13's vector column, index and
    `whereVectorSimilarTo` target PostgreSQL + pgvector
    ([AI SDK docs](https://laravel.com/docs/13.x/ai-sdk)).
- Local development uses the Docker image `pgvector/pgvector:pg17` on host port **54329**, so it
  does not clash with other PostgreSQL instances on the same machine. Tests always run on
  PostgreSQL, never SQLite.
- **Deploy is deliberately deferred.** No live environment exists until v1 is close; then a small
  VPS. The deploy pipeline will get its own ADR at that point.

### Consequences

- Good, because overlapping employment versions and absence periods are rejected by the database
  even if application code has a bug or two requests race.
- Good, because relational data, history, the outbox and embeddings live in one transactional
  store: an audit row, a domain write and an outbox message commit or roll back together.
- Good, because Laravel's queues, scheduler, policies, Fortify, Passport and the AI and MCP
  packages are first-party and versioned together.
- Bad, because range types and exclusion constraints have no schema-builder support in Laravel;
  migrations use raw DDL and Eloquent needs custom casts for ranges. This is contained in
  `Shared\Time` and covered by tests.
- Bad, because the project is tied to PostgreSQL; MySQL users cannot self-host it.
- Neutral, because the installer scaffold's `composer.json` still declares `php: ^8.3`; tightening
  it to `^8.4` belongs to the quality-tooling work that owns the composer files.

### Confirmation

- CI runs the suite against `pgvector/pgvector:pg17`; a test asserts that the `vector` and
  `btree_gist` extensions are installed.
- Database-constraint tests insert overlapping rows and expect the exclusion violation.
- Composer platform constraints (once tightened) refuse to install on PHP below 8.4.

## Pros and Cons of the Options

### Laravel 13 + PHP 8.4 + PostgreSQL 17

- Good, because every package is current and the framework has the longest support window.
- Good, because the database itself enforces the temporal invariants.
- Bad, because raw DDL for ranges and constraints must be maintained by hand.

### Laravel 13 + PHP 8.3

- Good, because more hosts ship PHP 8.3.
- Bad, because Pest 5, activitylog 5 and model-states' current line need PHP 8.4; the project would
  start one major behind on its test framework.

### Laravel 12

- Good, because it is a known quantity.
- Bad, because it has been security-fix-only since 2026-08-13 and lacks Laravel 13's AI SDK
  integration and vector queries ([release notes](https://laravel.com/docs/13.x/releases)).

### Laravel with MySQL 8

- Good, because MySQL is common on shared hosting.
- Bad, because it has no range types and no exclusion constraints, so non-overlap would rest on
  application locks only; and no pgvector, so vector search would need another store.

### Symfony + Doctrine

- Good, because Doctrine has a mature mapping layer; OrangeHRM shows a plugin-per-domain HR app
  on Symfony ([OrangeHRM plugins](https://github.com/orangehrm/orangehrm/tree/main/src/plugins)).
- Bad, because OrangeHRM itself is still on Symfony 5.4 and Doctrine ORM 2 in 2026
  ([composer.json](https://github.com/orangehrm/orangehrm/blob/main/src/composer.json)), and
  Symfony has no first-party AI SDK or MCP server equivalent.
- Bad, because it is not the author's strongest stack, which costs speed inside a fixed appetite.

### Python: Django, or Frappe HR as a base

- Good, because Frappe HR and Odoo 19 have the best open-source HR data models
  ([frappe/hrms](https://github.com/frappe/hrms),
  [Odoo `hr.version`](https://github.com/odoo/odoo/blob/master/addons/hr/models/hr_version.py)).
- Bad, because Frappe HR requires ERPNext and its framework's conventions; building on it means
  inheriting a platform, not designing one.
- Bad, because no modern Laravel HR reference exists, which is exactly the gap a Laravel
  implementation fills; those models serve as reading material only.

## More Information

- Related: [ADR-0003](0003-inertia-vue-typescript-frontend.md) (frontend),
  [ADR-0005](0005-bitemporal-employment-versions.md) (why ranges and exclusion constraints),
  [ADR-0008](0008-agent-runtime-laravel-ai-and-mcp.md) (AI SDK and MCP),
  [ADR-0011](0011-multi-company-single-installation.md) (one database for several employers).
- Revisit if: a target self-hosting audience requires MySQL; Laravel 14 ships during v1 with a
  feature the design needs; or pgvector cannot meet retrieval quality, which would justify a
  dedicated vector store behind the same retrieval port.
