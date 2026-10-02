---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0006: One policy function with roles, reach as of a date, and field groups

## Context and Problem Statement

People data is read and changed by very different actors: an HR analyst for one company of the
group, a manager for their team, an employee for themselves, an in-app agent acting for one of
them, and an external assistant (Claude, ChatGPT) connected over MCP. "Can this actor see this
person?" depends on relationships that change over time (who reports to whom, which org unit a
person is in), and "which fields can they see?" differs by role: a manager sees the team's
positions but not their CPF or diagnosis-adjacent absence details.

How does Sunex decide access so that every actor, human or agent, gets the same answer for the
same question, including questions about the past and the future?

## Decision Drivers

- The brief's second product value: one door for everyone; an agent never sees or does what its
  sponsor could not.
- Relationships are effective-dated: a future-dated transfer must not give the new manager access
  before its effective date, and "who could see this person on date D" must be answerable.
- Sensitive fields must never leave the server for an actor who may not see them, whether the
  output is an Inertia prop, a CSV or a tool result read by a model.
- Multi-company installations ([ADR-0011](0011-multi-company-single-installation.md)): grants are
  scoped to companies.
- Testability: the whole decision table should be a dataset, not scattered `if`s.

## Considered Options

1. `spatie/laravel-permission` RBAC plus ad-hoc policy code per model.
2. An external ABAC/ReBAC engine (OPA, or an OpenFGA/Zanzibar-style relationship store).
3. **In-app capabilities, reach evaluated as of a date, and field groups, behind one policy
   function.**
4. Role-name checks in controllers and components.

## Decision Outcome

Chosen option: **3**, because neither the package nor an external engine models reach as of a date
over Sunex's own bitemporal versions, and a single function in the application is the only way to
make humans, in-app agents and MCP clients pass through the same door.

The design:

- `Shared\Access\Authorizer::decide(Principal $principal, Capability $capability, Subject $subject,
  CarbonImmutable $asOf): Decision`, where `Decision` is `{allowed, reason, visibleFieldGroups}`.
  `asOf` defaults to today.
- `Capability` is a PHP enum (`employees.view`, `movements.request`, `movements.approve`,
  `absence.request`, `absence.approve`, `esocial.export`, `webhooks.manage`, `agents.manage`…).
- Roles grant capabilities. Role assignments are small Sunex-owned tables, **company-scoped and
  effective-dated** (`valid_period daterange`), so access granted for a project ends on its date.
- Each grant carries a **reach**: `self`, `direct_reports`, `manager_chain`, `org_unit` (subtree),
  `company`, `all_companies`. Reach is evaluated as of `asOf` from current-belief employment
  versions ([ADR-0005](0005-bitemporal-employment-versions.md)) and the org tree as of that date.
  A future-dated transfer gives the new manager reach on its effective date, not on approval.
- `Shared` declares the `ReachResolver` interface; People implements it (manager chain by a
  recursive query over versions valid on the date, org-unit subtree through Organization's
  `OrgTree`). Shared never depends on People.
- Each grant lists **field groups**: `basic`, `contact`, `personal`, `identifiers`,
  `compensation`, `absence_details`. One server-side serializer applies `visibleFieldGroups` to
  every output: Inertia props, exports and the agent tool gateway. Masked fields are absent, not
  hidden by the frontend.
- Laravel policies are thin and delegate to the `Authorizer`. Agents and MCP clients reach the
  same function through the tool gateway, where an agent's rights are its scopes intersected with
  the rights of the human it acts for ([ADR-0007](0007-agents-as-principals-one-toolset.md)).

### Consequences

- Good, because there is one place to read, test and audit access rules; a decision matrix
  (role × reach × relationship × date → allow/deny, fields) is a Pest dataset.
- Good, because agents inherit permissions by construction instead of by convention: the gateway
  cannot call anything but `decide`.
- Good, because reach follows the HR record: promotions, transfers and terminations change access
  on their effective date without anyone editing a group.
- Good, because masking at the serializer means a frontend bug cannot leak a CPF or a salary.
- Bad, because Sunex owns its authorization code instead of reusing a popular package; role
  administration screens are built in-house.
- Bad, because reach queries are recursive and date-dependent; they need request-level caching of
  the reachable set and indexes on current-belief versions.
- Neutral, because Laravel 13's `#[Authorize]` attributes and `Gate` still work: they call the
  policies, which call the `Authorizer`.

### Confirmation

- A policy matrix test runs every default role against self, direct report, indirect report,
  another org unit, another company, with dates before and after a future-dated transfer.
- Feature tests assert that Inertia props and CSV rows for a manager do not contain `cpf`,
  `salary_amount` or absence motive details, as keys, not only as values.
- An architecture test forbids `Gate::allows`-style role-name checks and `->hasRole()` outside
  `Shared\Access`, and requires every policy to call the `Authorizer`.
- A parity test runs the same read through a human request, an in-app agent tool and the MCP
  server and expects the same decision and the same visible fields.

## Pros and Cons of the Options

### 1. spatie/laravel-permission plus ad-hoc policies

- Good, because it is the de-facto Laravel package (v8.0.0 in 2026) and community guidance says to
  "check capabilities rather than role names, and put ownership and tenancy in Policies".
- Bad, because its model has no reach and no effective dates; reach and history would live in
  policy code anyway, so the package would hold only the least interesting part.
- Bad, because field-level masking is out of its scope.

### 2. External ABAC/ReBAC engine

- Good, because relationship-based engines express manager chains and org trees natively and
  scale to many services.
- Bad, because relationships would have to be mirrored from bitemporal versions into another store
  and kept in sync per date; a missed sync is a silent leak.
- Bad, because it adds a second runtime to deploy and test for a single-application monolith.

### 3. Capabilities, reach as of a date, field groups (chosen)

- Good, because it mirrors what the leading HR products document: Rippling's profile of scope ×
  access × actions with permissions that "adjust automatically with org changes", HiBob's people
  scope × category/field access.
- Bad, because it is code Sunex must maintain and test thoroughly.

### 4. Role-name checks in controllers

- Good, because it is fast to write.
- Bad, because rules scatter across controllers, agents bypass them, and no test can show the full
  table.

## More Information

Sources:

- Rippling permission profiles and Supergroups
  ([permissions page](https://www.rippling.com/platform/permissions)); relationship-based role
  permissions that adjust with org changes
  ([Rippling platform blog](https://www.rippling.com/blog/introducing-rippling-platform)).
- HiBob people scope and category/field-level access, with sensitive fields requiring both view
  and edit ([HiBob categories and permissions](https://apidocs.hibob.com/docs/categories-and-permissions));
  HiBob's payroll hub enforces permissions at display time because "if we miss a permission change
  event, we still enforce it" ([HiBob Engineering](https://medium.com/hibob-engineering/event-driven-reports-in-payroll-hub-7491cf2dad0f)).
- BambooHR's AI connector: "Every request runs as you, against the same permissions BambooHR
  applies when you're signed in" ([BambooHR and AI](https://documentation.bamboohr.com/docs/bamboohr-and-ai));
  Ask BambooHR routes every question through the permission engine
  ([press release](https://www.bamboohr.com/about-bamboohr/press-release/ask-bamboohr)).
- Workday's single security model adapting to org changes
  ([Organization Management datasheet](https://www.workday.com/content/dam/web/en-us/documents/datasheets/organization-management-in-workday-datasheet-en-us.pdf)).
- Laravel 13 RBAC guidance ([qadrlabs](https://qadrlabs.com/post/laravel-13-role-based-access-control-with-spatie-permission-and-middleware-attributes))
  and [spatie/laravel-permission 8.0.0](https://github.com/spatie/laravel-permission/releases/tag/8.0.0).

Related: [ADR-0004](0004-domain-namespaces-with-architecture-tests.md),
[ADR-0005](0005-bitemporal-employment-versions.md),
[ADR-0007](0007-agents-as-principals-one-toolset.md),
[ADR-0011](0011-multi-company-single-installation.md). Detailed design: TDD-0001, permission model.

Conditions that would reverse it: Sunex splits into several services that all need the same
relationship graph (an external ReBAC engine becomes cheaper than mirroring code), or reach
evaluation cannot be made fast enough for list screens with caching and indexes, in which case a
materialized reach table refreshed on version writes supersedes the on-the-fly resolver.
