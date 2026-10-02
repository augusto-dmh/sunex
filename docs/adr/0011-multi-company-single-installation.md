---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0011: Several companies as data in one installation, no SaaS tenancy

## Context and Problem Statement

Brazilian employers are often groups: a holding and several operating companies, each with its own
CNPJ, its own establishments and its own employees, sometimes sharing people (a manager employed
by one company who leads a team in another, or a person transferred between companies of the
group). eSocial identifies the employer by its CNPJ and each establishment by a full CNPJ; the
worker by CPF; and the employment by a matrícula unique within the employer.

Should Sunex isolate each company as a tenant, or hold several companies as data in one
installation?

## Decision Drivers

- The product serves companies "with one or several CNPJs" (brief, press release).
- The brief's no-go: no SaaS sign-up and no tenant isolation in any phase.
- A person is one person across the group; their CPF must not be duplicated per company.
- Company scoping must be enforced, not remembered: a query that forgets the company filter is a
  data leak.
- The demo must show company scoping (two companies, one HR team per company, one group HR).

## Considered Options

1. One installation per company.
2. `stancl/tenancy` in single-database mode (a `tenant_id` scope on every model).
3. Database (or schema) per tenant.
4. **Multi-company as data in one installation**, scoped by the policy function.

## Decision Outcome

Chosen option: **4, multi-company as data**, because a company group is one organisation with
shared people and shared HR staff, not a set of strangers that must be isolated from each other.

The design:

- `companies` holds the employer (legal name, CNPJ root); `establishments` hold the full CNPJ of
  each eSocial establishment and belong to a company.
- Every company-owned row carries `company_id` (org units, positions, employments, movements,
  absences, webhook subscriptions, policy documents).
- `persons` are global and identified by CPF. A person may hold employments in several companies;
  matrícula is unique per company. A person is reached only through an employment the principal
  reaches, and person fields are shown under that employment's grant. The admission form's CPF
  check answers only whether the person already exists, pre-fills nothing from an employment the
  principal does not reach, and is audited.
- Access is decided by the `company` and `all_companies` reaches of the policy function
  ([ADR-0006](0006-permission-model-roles-reach-field-groups.md)); role assignments are
  company-scoped.
- CNPJ is stored as text and validated by a value object that accepts both the numeric format and
  the alphanumeric format announced by the Receita Federal for new registrations from 2026
  (**to verify** against the primary normative text before the identifier row ships).

### Consequences

- Good, because group-level HR, transfers between companies and shared managers are ordinary
  queries, with no cross-tenant plumbing.
- Good, because one deploy, one database and one migration path keep operations as simple as the
  appetite allows.
- Good, because company scoping goes through the same function as every other access rule, so it
  is tested in the same decision matrix.
- Bad, because isolation is logical, not physical: a missing filter would expose another company's
  data. As the multi-tenancy guide warns, "one vulnerability can expose every tenant
  simultaneously". The mitigations are the policy function, list queries that start from the
  principal's reachable set, and tests below.
- Bad, because Sunex is not a hosted multi-customer product; turning it into one later needs a new
  decision.
- Neutral, because each self-hosted installation already isolates one customer from another.

### Confirmation

- Every company-owned table has a non-null `company_id` with a foreign key; a schema test lists
  tables without it and compares them to an allow-list (global tables such as `persons`).
- A feature test seeds two companies and, for each list screen, export and agent tool, asserts that
  an HR analyst of company A never receives a row of company B, including the person data of
  someone employed by both.
- An architecture test forbids raw `DB::table()` queries on company-owned tables outside
  `app/Http/Queries` and the owning context.
- Value-object tests cover valid and invalid CNPJ check digits in both formats.

## Pros and Cons of the Options

### 1. One installation per company

- Good, because isolation is total and trivially correct.
- Bad, because a group runs several copies, a person transferred between companies becomes two
  unrelated records, and group HR has no single view.

### 2. stancl/tenancy single-database mode

- Good, because it is "the most maintained multi-tenant package for Laravel" (v3.10.1 supports
  Laravel 13) and applies the scope automatically.
- Bad, because tenancy assumes tenants do not share data; shared persons and cross-company
  managers fight the global scope.
- Bad, because it adds tenant identification and bootstrapping that a self-hosted single
  organisation does not need.

### 3. Database or schema per tenant

- Good, because isolation is physical and per-tenant backup is easy.
- Bad, because cross-company queries (group headcount, transfers) need cross-database work, and
  migrations multiply. It is the enterprise tier of SaaS tenancy, which the brief rules out.

### 4. Multi-company as data (chosen)

- Good, because it matches how employers and eSocial see a group: one employer per CNPJ root,
  establishments per full CNPJ, one worker per CPF. Personio also models legal entities as
  first-class resources inside one account.
- Bad, because correctness depends on consistent scoping, enforced by tests rather than by the
  database topology.

## More Information

Sources:

- [`stancl/tenancy` on Packagist](https://packagist.org/packages/stancl/tenancy) and its
  [documentation](https://tenancyforlaravel.com/docs/v3/introduction/) (single- and multi-database
  modes).
- [Multi-tenant SaaS in Laravel guide](https://kokil.com.np/blog/building-multi-tenant-saas-applications-in-laravel)
  (shared vs schema vs database tenancy; "One vulnerability can expose every tenant
  simultaneously").
- eSocial identification: S-1000 (employer) and S-1005 (establishments) in the table family
  ([event table 2026](https://rolmyjuncontabilidade.com.br/financas/obrigacoes-trabalhistas/eventos-esocial/));
  S-2200 requires CPF, matrícula and establishment
  ([Senior, leiaute S-2200](https://documentacao.senior.com.br/gestao-de-pessoas-hcm/esocial/leiautes/nao-periodicos/s-2200.htm));
  CPF is the sole worker key and matrícula must match across events
  ([TecnoSpeed](https://atendimento.tecnospeed.com.br/hc/pt-br/articles/27165521606551-S-2200-Cadastramento-Inicial-do-V%C3%ADnculo-e-Admiss%C3%A3o-Ingresso-de-Trabalhador)).
- Personio exposes legal entities, org units and cost centres as first-class API resources
  ([developer.personio.de/llms.txt](https://developer.personio.de/llms.txt)).

Related: [ADR-0005](0005-bitemporal-employment-versions.md) (an employment belongs to one
company), [ADR-0006](0006-permission-model-roles-reach-field-groups.md) (company reach). Detailed
design: TDD-0001, Organization and data-model conventions.

Conditions that would reverse it: Sunex is offered as a hosted service to unrelated customers, which
needs tenant isolation and its own ADR (stancl/tenancy single-database mode first, as the guide
recommends); or a regulated customer requires physical separation between companies of the same
group.
