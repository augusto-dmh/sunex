---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted: research notes on the 2026 Laravel stack
informed:
---

# ADR-0003: Build the UI with Inertia 3, Vue 3 and TypeScript

## Context and Problem Statement

Sunex's screens are mostly forms and tables (employees, movements, approvals, férias requests),
plus a few that are genuinely interactive: an employment timeline with "effective on" and "as
known at" pickers, an org chart as of a date, and an agent chat with streaming and a confirmation
step. The application is a portfolio piece read by Laravel and general full-stack reviewers.

Which frontend approach gives a maintainable, typed UI without a second backend contract?

## Decision Drivers

- One application and one authorization path: data reaches the browser only after the policy
  function has masked it ([ADR-0006](0006-permission-model-roles-reach-field-groups.md)).
- Type safety from route to component, so a renamed route or prop fails the build.
- Interactive screens (timeline, chat with streaming) must be comfortable to build.
- Craft signal for reviewers, on a stack the author already masters.
- Accept the cost of building admin screens by hand only if the gains above are real.

## Considered Options

- Inertia 3 + Vue 3 + TypeScript, from the official Vue starter kit (chosen)
- Livewire 4 + Filament 5
- A separate SPA consuming a JSON API

## Decision Outcome

Chosen option: "Inertia 3 + Vue 3 + TypeScript", because it keeps server-side routing,
controllers and policies (one authorization path, no public JSON API to secure for the UI) while
giving component-level frontend engineering with types.

Concretely:

- The scaffold is the official Laravel 13 Vue starter kit: Inertia 3, Vue 3, TypeScript,
  Tailwind 4, shadcn-style components and Fortify for authentication.
- **Wayfinder** generates typed functions for routes and controller actions; components never
  hard-code URLs.
- Inertia props are built by serializers that apply field-group masking; a masked attribute is
  absent from the props JSON, not hidden by the component.
- Inertia 3's built-in HTTP client, `useHttp` and optimistic updates are used where they fit
  ([Inertia 3.0.0](https://laravel-news.com/inertia-3-0-0)).
- User-visible copy goes through translation keys
  ([ADR-0012](0012-english-ui-copy-behind-translation-keys.md)).

### Consequences

- Good, because there is no public API for the UI to design, version and secure; the only
  external surfaces are the MCP server and the signed webhooks, each with its own ADR.
- Good, because TypeScript plus Wayfinder turn route and prop mismatches into build errors.
- Good, because the timeline and the agent chat are ordinary Vue components.
- Bad, because there is no Filament-style resource generator: every list, form and filter is
  written by hand. Mitigation: a small set of shared table and form components built early, and
  scope discipline on admin screens.
- Bad, because two languages (PHP and TypeScript) and two toolchains (Composer and Node) must be
  kept green in CI.
- Neutral, because Boost ships Inertia and Vue guidelines and skills, so agent tooling is equal
  between the options ([Boost docs](https://laravel.com/docs/13.x/boost)).

### Confirmation

- `vue-tsc --noEmit` runs in `composer test` and CI; a type error fails the build.
- Feature tests assert on Inertia props (including the absence of masked fields).
- Pest browser tests cover the v1 golden path (férias request from draft to approval).

## Pros and Cons of the Options

### Inertia 3 + Vue 3 + TypeScript

- Good, because server-driven routing and policies stay in Laravel.
- Good, because "if the developers on your project think in components", Inertia 3 is the
  recommended choice ([hafiz.dev, 2026-04-03](https://hafiz.dev/blog/livewire-4-vs-inertia-3-laravel-frontend-2026)).
- Good, because reviewers know Inertia's reference app, Ping CRM
  ([inertiajs/pingcrm](https://github.com/inertiajs/pingcrm)); an HR app that goes beyond it
  (effective dating, approvals, masking) reads as more than a demo.
- Bad, because admin CRUD is written by hand.

### Livewire 4 + Filament 5

- Good, because "Pick Livewire 4 if you're building an admin panel … form-heavy and data-driven,
  especially if Filament is in the stack" ([hafiz.dev](https://hafiz.dev/blog/livewire-4-vs-inertia-3-laravel-frontend-2026));
  Filament would produce CRUD screens fastest, and the official Filament demo even has an HR
  module ([filamentphp/demo](https://github.com/filamentphp/demo)).
- Bad, because Filament's resource abstractions sit between the policy function and the rendered
  fields; masking and as-of-date reach would have to be threaded through Filament's own
  authorization hooks on every resource.
- Bad, because the bespoke screens (bitemporal timeline, streaming agent chat) fit poorly in a
  panel framework, and a Filament demo is less distinctive as a portfolio signal.
- Neutral, because Filament 5 has "no functional changes … beyond Livewire v4 support"
  ([Laravel News](https://laravel-news.com/filament-5)).

### Separate SPA + JSON API

- Good, because the API would be reusable by other clients.
- Bad, because it doubles the contract (API resources plus client types), needs token or cookie
  auth for the browser, and creates a public API to version before anyone needs one.
- Bad, because external integrations are already served by MCP and webhooks.

## More Information

- Related: [ADR-0002](0002-laravel-13-php-84-postgresql.md) (stack),
  [ADR-0006](0006-permission-model-roles-reach-field-groups.md) (masking before props),
  [ADR-0012](0012-english-ui-copy-behind-translation-keys.md) (translation keys).
- Revisit if: a mobile client or a third-party integration needs a general REST API (then add
  versioned API resources alongside Inertia, not instead of it); or admin CRUD consumes so much of
  the appetite that an internal-only Filament panel for configuration screens becomes cheaper.
