---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted: research notes on modular monoliths in Laravel
informed:
---

# ADR-0004: Split the code into domain namespaces enforced by Pest architecture tests

## Context and Problem Statement

An HR domain is "almost infinite": employment history, organization, movements, absences, agents,
and later performance and people cost. Laravel's default layout (`app/Models`, `app/Http`,
`app/Actions`) groups code by technical kind, so after a few months every model can reach every
other one and the rules about who may change an employment version stop being visible. Sunex is
also built by several agents in parallel worktrees; without visible boundaries, two pull requests
reach into the same internals and conflict.

How do we make the boundaries between parts of the domain explicit and enforced, without the
ceremony of a package per module?

## Decision Drivers

- Boundaries must be **checked by CI**, not by convention alone.
- Low ceremony: no Composer path repositories, per-module service providers or custom directory
  conventions that fight Laravel's generators.
- Data ownership: each part of the domain owns its tables and exposes a small public surface.
- Parallel delivery: rows in different contexts should touch different directories.
- The structure must be justified, because "don't use modular monolith for simple apps and
  small teams" is sound default advice
  ([Hamasaki, Laracon India 2025](https://speakerdeck.com/avosalmon/modularizing-inertia-laracon-india-2025)).

## Considered Options

- Laravel's default flat layout
- `nwidart/laravel-modules`
- `internachi/modular`
- Plain namespaces under `app/Domain/<Context>` enforced by Pest architecture tests (chosen)
- Deptrac in addition to the architecture tests

## Decision Outcome

Chosen option: "plain namespaces under `app/Domain/<Context>` enforced by Pest architecture tests",
because it gives the boundary checks of a modular monolith with no packaging ceremony: the code is
still one Composer package under the `App\` PSR-4 root, and the rules live in ordinary tests.

The contexts and their rules are defined in [ARCHITECTURE.md](../../ARCHITECTURE.md):

| Context | May depend on |
|---|---|
| Shared | the framework only |
| Organization | Shared |
| People | Organization, Shared |
| Movements | People, Organization, Shared |
| Absence | People, Organization, Shared |
| Agents | Absence, Movements, People, Organization, Shared |

1. A context uses another only through that context's `Contracts` and `Events` namespaces;
   models, actions and internal classes stay private.
2. Dependencies point down the table; no cycles. `Shared` depends on nothing in `app/Domain`.
   When a lower context needs a higher one, it declares an interface that the higher context
   implements (the `ReachResolver` declared in Shared is implemented by People).
3. Each context owns its tables. Foreign keys across contexts are allowed for integrity;
   Eloquent relationships across contexts are not.
4. Screens that combine data from several contexts read through query classes in
   `app/Http/Queries` (read-only query builder); writes go through the owning context's actions.
5. Controllers, MCP tools and jobs stay thin: build input, call one action or contract, shape
   output.

Each context has the same internal layout: `Actions/`, `Contracts/`, `Data/`, `Events/`,
`Models/`, `Policies/` and, where needed, `Rules/` for pure rule code with no I/O.

### Consequences

- Good, because a forbidden import fails CI with a message naming the rule, in the same suite
  developers already run.
- Good, because the namespaces map to roadmap rows, so parallel worktrees rarely touch the same
  files.
- Good, because artisan generators keep working (with a namespace argument), unlike layouts with
  their own conventions.
- Bad, because cross-context reads through contracts cost DTO mapping and sometimes an extra
  query; list screens use `app/Http/Queries` to avoid N+1 patterns.
- Bad, because Pest's `toUse` checks are namespace-based: they catch imports, not runtime
  coupling through strings (for example a table name in raw SQL). Review covers the rest.
- Neutral, because the contexts are not deployable units; extracting one later would still need
  work, by design.

### Confirmation

- `tests/Arch/` holds one architecture test per rule above, for example
  `arch()->expect('App\Domain\Shared')->not->toUse('App\Domain\People')` and checks that only a
  context's own namespace uses its `Models`.
- The arch tests run in `composer test` and CI; a pull request cannot merge with them red.

## Pros and Cons of the Options

### Laravel's default flat layout

- Good, because every Laravel developer knows it and Boost's guidelines assume it.
- Bad, because nothing stops any class using any model; boundaries live only in reviewers' heads.

### `nwidart/laravel-modules`

- Good, because it is popular (6k+ stars) and supports Laravel 13
  ([Packagist](https://packagist.org/packages/nwidart/laravel-modules)).
- Bad, because it brings its own directory layout and module lifecycle; it "better suits CMS
  projects requiring dynamic third-party module support"
  ([InterNACHI/modular](https://github.com/InterNACHI/modular)), which Sunex is not.

### `internachi/modular`

- Good, because it follows Laravel conventions, with each module a Composer path package under
  `app-modules/` ([InterNACHI/modular](https://github.com/InterNACHI/modular)).
- Bad, because a package per context adds service providers, composer wiring and autoload
  indirection for boundaries that a test can enforce directly.

### Plain namespaces + Pest architecture tests

- Good, because the modular-monolith guidance is followed in substance: organise by business
  context, keep modules out of each other's internals, pass data objects, use events, and use
  "Pest architectural tests to block unauthorized imports"
  ([Guimarães, Laracon EU 2024](https://speakerdeck.com/mateusjatenee/unveiling-the-modular-monolith-laracon-eu-2024);
  [Sevalla](https://sevalla.com/blog/building-modular-systems-laravel/)).
- Good, because Pest architecture tests have been built into the test runner since Pest 3
  ([Redberry](https://redberry.international/introducing-laravel-pest-3-new-features-updates/)).
- Bad, because the discipline (DTOs at the boundary, no cross-context relations) is partly a
  convention backed by review.

### Deptrac in addition

- Good, because it models the full dependency graph and catches more indirect cases.
- Bad, because it is a second tool with its own configuration that duplicates the arch tests for a
  six-context codebase. Rejected for now; reconsider if arch tests miss a real violation.

## More Information

- Related: [ADR-0005](0005-bitemporal-employment-versions.md) (People owns employment versions),
  [ADR-0006](0006-permission-model-roles-reach-field-groups.md) (the Authorizer in Shared and the
  ReachResolver implemented by People), [ADR-0007](0007-agents-as-principals-one-toolset.md)
  (Agents as the outermost context).
- Spatie's "Laravel Beyond CRUD" describes the same actions-and-data-objects style inside domains
  ([laravel-beyond-crud.com](https://laravel-beyond-crud.com/)).
- Revisit if: a context needs to ship or deploy independently; the arch tests prove unable to
  express a boundary that matters; or module 2 or 3 makes the dependency table cyclic.
