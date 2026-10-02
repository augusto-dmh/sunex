---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0005: Make employment versions bitemporal, and only them

## Context and Problem Statement

An employment changes over time: position, org unit, manager, establishment, salary, weekly hours,
cost centre. Two different questions are asked about that history. "What was true on 15 February?"
is answered by the **effective date** of each change. "What did we believe on 25 February, when
payroll ran and the S-2206 left for eSocial?" is answered by the **recorded date**, because HR
often learns about a change weeks after it took effect, and corrects mistakes after other systems
have acted on them. Labour disputes and eSocial rectifications ask the second question.

How should Sunex store employment history so that both questions have exactly one answer, without
paying that cost on every table?

## Decision Drivers

- The brief's first product value: a fact has a date and a reason; corrections are new facts,
  never silent edits.
- Payroll and eSocial act on the values Sunex publishes; a later correction must not erase what
  was believed when they acted.
- The guarantee should hold in the database, not only in application code.
- The 12-week appetite: the bitemporal core is the first listed risk in the brief's internal FAQ.
- Queries for screens ("the team as of today") must stay simple and indexable.

## Considered Options

1. Current state plus an audit log.
2. Effective-dated only (uni-temporal versions), as in Odoo 19 `hr.version` or Frappe's dated
   submittable documents.
3. **Bitemporal on employment versions only**; every other entity effective-dated plus the audit
   log.
4. Bitemporal everywhere, or event sourcing (`spatie/laravel-event-sourcing`).

## Decision Outcome

Chosen option: **3, bitemporal on employment versions only**, because it is the one place where
actions are taken on values that are later corrected, which is exactly the condition under which
Fowler says bitemporality pays for itself. Everything else (org units, positions, role
assignments, absences) is effective-dated with a `daterange` and covered by the audit log.

The design:

- Table `employment_versions`: `employment_id`; `valid_period daterange` (inclusive dates in the
  domain, stored half-open `[start, end + 1)`, open upper bound for "until further notice");
  `recorded_period tstzrange` (`[recorded_at, closed_at)`, open upper bound = current belief);
  a full attribute snapshot (`position_id`, `org_unit_id`, `manager_employment_id`,
  `establishment_id`, `cbo_code`, `salary_amount numeric(12,2)`, `salary_unit`, `weekly_hours`,
  `schedule_description`, `cost_centre_code`, `contract_type`); `reason_code` and `reason_note`;
  the source reference (the movement that produced it); `recorded_by` (principal type and id);
  `supersedes_version_id` for corrections.
- Constraint, with `btree_gist`:
  `EXCLUDE USING gist (employment_id WITH =, valid_period WITH &&, recorded_period WITH &&)`.
  No two rows of one employment overlap in both times, so an as-of query cannot return two rows.
- Append-only trigger: `DELETE` is rejected; `UPDATE` is allowed only to close an open
  `recorded_period`, once, and may not touch any other column.
- Writes: a command captures `recordedAt` once from an injected clock, locks the employment row
  (`SELECT … FOR UPDATE`), and asks a pure `TimelinePlanner` for `{rows to close, rows to insert}`
  for a **change**, a **correction** or a **rescission**. All closes and inserts share the same
  `recordedAt`, so recorded ranges abut exactly. Inserting a change before future-dated versions
  propagates the changed attributes forward only into later versions whose value still equals the
  value being replaced; deliberate later changes are kept.
- As-of read: `valid_period @> :date AND recorded_period @> :knownAt`; "known now" is the common
  case and gets a partial index on `upper_inf(recorded_period)`.

### Consequences

- Good, because "what was true on D, as known at T" is one indexed query with one row per
  employment, guaranteed by the database.
- Good, because a correction keeps the old belief: the S-2206 that payroll sent can be explained
  from the row it was built from.
- Good, because the planner is pure: change, correction, rescission and forward propagation are
  unit-tested with tables of timelines, without a database.
- Good, because the cost is confined to one table that one context (People) owns.
- Bad, because writes are more complex than an `UPDATE`: every change closes and re-inserts rows,
  and the propagation rule must be explained to users ("a retroactive raise also updates the
  future-dated transfer, unless that transfer changed the salary itself").
- Bad, because Laravel's schema builder has no range types or exclusion constraints; migrations
  use raw DDL and a custom cast maps ranges to a `DateRange` value object.
- Bad, because the recorded time comes from the application clock: a skewed server clock could
  produce overlapping recorded ranges. That fails safe: the constraint rejects the transaction.
- Neutral, because other entities answer only "what was true on D"; "what did we believe" for them
  comes from the audit log, which is enough while no external system acts on them.

### Confirmation

- Feature tests on PostgreSQL insert overlapping rows and expect the exclusion constraint to fail;
  attempt a `DELETE` and an `UPDATE` of an attribute and expect the trigger to fail.
- Table-driven unit tests for `TimelinePlanner` cover change in the middle, change before a
  future-dated version (with and without propagation), correction of a past version, rescission
  of a future change, and two changes on the same day.
- An as-of test travels in time: record, correct, then query at a `knownAt` before and after the
  correction and expect the old and the new belief.
- An architecture test forbids `update()` and `delete()` calls on `EmploymentVersion` outside the
  writer.

## Pros and Cons of the Options

### 1. Current state plus audit log

- Good, because it is the Laravel default and the cheapest to build.
- Bad, because future-dated changes have nowhere to live until their date arrives.
- Bad, because "what was true on D" must be reconstructed by replaying the log, and nothing in the
  database prevents contradictory history.

### 2. Effective-dated only

- Good, because it answers "what was true on D" and supports future-dated changes; Odoo 19 merged
  employee and contract into one dated `hr.version` row, and Frappe makes every change a dated,
  submittable document with `amended_from`.
- Good, because an exclusion constraint on `valid_period` alone keeps versions from overlapping.
- Bad, because a correction overwrites the row payroll acted on; the previous belief survives only
  in the audit log, outside the constraint and outside as-of queries.

### 3. Bitemporal on employment versions only (chosen)

- Good, because it gives both answers where they matter and keeps the rest simple.
- Bad, because it adds write complexity and raw DDL to the core of v1.

### 4. Bitemporal everywhere, or event sourcing

- Good, because every entity could answer both questions; event sourcing gives a complete log by
  construction.
- Bad, because hand-rolled bitemporality "needs separate history tables, triggers, and explicit
  time columns across every entity" (JUXT), multiplying the cost the brief names as the first
  risk.
- Bad, because event sourcing moves the system of record into projections; Fowler notes it is
  conceptually simpler, but it changes how every context is written and tested, for a benefit only
  employment history needs.

## More Information

Sources:

- Martin Fowler, [Bitemporal History](https://martinfowler.com/articles/bitemporal-history.html)
  (2021): actual time vs record time, the payroll example, and the rule that bitemporality is worth
  it only when actions depended on values later corrected.
- Martin Fowler, [Temporal Object](https://martinfowler.com/eaaDev/TemporalObject.html).
- Workday: effective date vs entry date, "the same worker can return different data depending on
  the date parameters" ([unified.to integration guide](https://unified.to/blog/workday_api_integration_what_to_know_before_you_build));
  effective-dated snapshots copied from the previous snapshot
  ([Workday admin guide](https://doc.workday.com/admin-guide/en-us/manage-workday/tenant-configuration/custom-objects-and-labels/dan1370796495420.html)).
- Odoo 19 [`hr_version.py`](https://github.com/odoo/odoo/blob/master/addons/hr/models/hr_version.py)
  (effective-dated version rows) and Frappe HR
  [`employee_promotion.json`](https://github.com/frappe/hrms/blob/develop/hrms/hr/doctype/employee_promotion/employee_promotion.json)
  (a promotion is a dated document, not an in-place edit).
- SAP SuccessFactors requires an event and event reason for every job and compensation change
  ([SAP Learning](https://learning.sap.com/courses/sap-successfactors-employee-central-core-administration/managing-events-and-event-reasons)),
  which is why each version carries a `reason_code`.
- [JUXT: bitemporality, more than a design pattern](https://www.juxt.pro/blog/bitemporality-more-than-a-design-pattern/)
  and [Marley Spoon on dev.to](https://dev.to/marleyspoon/bitemporality-or-how-to-change-the-past-3k4f)
  ("transaction time is immutable and can be only increased").
- [`spatie/laravel-event-sourcing`](https://packagist.org/packages/spatie/laravel-event-sourcing),
  the option considered for event sourcing.

Related: [ADR-0002](0002-laravel-13-php-84-postgresql.md) (PostgreSQL range types),
[ADR-0006](0006-permission-model-roles-reach-field-groups.md) (reach is evaluated from current-belief
versions), [ADR-0010](0010-transactional-outbox-signed-webhooks.md) (each recorded version emits an
outbox message). Detailed design: TDD-0001, People and bitemporal employment.

Conditions that would reverse or extend it: another entity starts feeding an external system that
acts on its values (for example cost centres for a GL export), which would make that entity
bitemporal too; or the write complexity proves unmanageable by the end of the People phase, in
which case versions fall back to option 2 with corrections kept in the audit log, recorded in a
superseding ADR.
