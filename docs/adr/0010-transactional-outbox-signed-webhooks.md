---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0010: Deliver lifecycle events through a transactional outbox with HMAC-signed webhooks

## Context and Problem Statement

Payroll systems need Sunex's lifecycle facts (admission, contract change, absence, termination) as
they happen, and HR teams need the same facts as files ([ADR-0009](0009-no-payroll-no-esocial-transmission.md)).
Two failure modes must be impossible: an event is announced for a change that rolled back, and a
committed change is never announced. Receivers must also be able to prove that a request came from
Sunex and was not replayed.

The decision covers how events leave the database (dispatch mechanism) and how a receiver verifies
them (signing scheme).

## Decision Drivers

- Atomicity: the event exists if and only if the domain change committed.
- At-least-once delivery with idempotent consumers, because networks fail.
- Verifiable origin and replay protection for each request.
- One source for webhooks and CSV exports, so they never disagree.
- Conventions receivers already know from HR vendors.
- No new infrastructure: PostgreSQL and Laravel queues only.

## Considered Options

Dispatch:

1. Dispatch queued jobs or events directly after commit.
2. Transactional outbox table plus a relay.
3. Event sourcing, using the event store as the outbound log.
4. A third-party Laravel outbox package.

Signing:

- a. No signature.
- b. A shared static token in a header.
- c. HMAC over the body only.
- d. HMAC-SHA256 over a timestamp and the raw body.
- e. Asymmetric signatures (receiver verifies with a public key).

## Decision Outcome

Chosen: **option 2 with signing scheme d**; e stays a future option.

**Outbox.** Each context records integration events through `Shared\Integration\Outbox` inside the
same transaction as its domain change. `outbox_messages` holds:

| Column | Meaning |
|---|---|
| `id` (ULID) | The event id; stable across retries and exports |
| `company_id` | Employer the fact belongs to; subscriptions are company-scoped |
| `aggregate_type`, `aggregate_id`, `sequence` | For example `employment` + id; `sequence` increases per aggregate so consumers can detect gaps |
| `event_type`, `schema_version` | For example `employment.changed`, `1` |
| `effective_date`, `occurred_at` | When the fact applies; when Sunex recorded it |
| `payload` (jsonb) | The versioned event body |
| `relayed_at` | Set by the relay once deliveries were created |

**Relay.** A queued job claims unrelayed rows with `FOR UPDATE SKIP LOCKED`, creates one
`webhook_deliveries` row per matching active subscription, and marks the message relayed. Several
workers can run without double-claiming.

**Delivery.** A delivery job POSTs the JSON body with these headers:

```
Sunex-Event-Id: 01JABC...            (outbox id)
Sunex-Event-Type: employment.changed
Sunex-Signature: t=1791000000,v1=5257a869e7...
```

where `v1 = hex(HMAC-SHA256(secret, "<t>.<raw body>"))`, computed at every attempt over the stored
body (the event id does not change). Receivers should reject a `t` more than five minutes away from
their clock in either direction and deduplicate by event id. Delivery is at least once and ordering
is not guaranteed; `sequence` lets a receiver detect a gap and fetch the missing event. Failures
retry with exponential backoff for about three days; then the subscription is disabled and its
administrators are notified. Secrets are encrypted at rest; a routine rotation keeps the old secret
valid for a seven-day grace period during which both signatures are sent (`v1=new,v1=old`), and a
rotation after a leak drops the old secret at once.

**Egress.** The URL comes from a company-scoped administrator, not from the operator of the host,
so it is untrusted: the host is resolved and vetted at save and at every delivery (no loopback,
private, link-local, CGNAT, multicast or unique-local addresses), the connection goes to the vetted
address, redirects are not followed, only port 443 is allowed, and administrators see the status
code and a short sanitized excerpt of the response, never the raw body.

**CSV.** Exports shaped like S-2200, S-2206, S-2230 and S-2299 are built from the same outbox
messages, so a file and a webhook for the same fact carry the same values and the same event id.

**Retention.** Relayed messages and their deliveries are pruned after a configurable retention
window; exports needed beyond it are generated before pruning.

### Consequences

- Good, because a rollback discards the event with the change, and a commit guarantees the event:
  the dual-write problem disappears.
- Good, because receivers verify origin and freshness with a standard construction they already
  implement for other HR vendors.
- Good, because webhooks and CSV share one source of truth and one event id.
- Good, because it uses only Postgres and the existing queue.
- Bad, because delivery latency equals the relay interval plus queue latency (seconds, not
  milliseconds); acceptable for payroll.
- Bad, because the outbox, relay, retries, disabling and rotation are code we own and must test.
- Neutral, because receivers must be idempotent; this is documented with a verification snippet.

### Confirmation

- Feature tests: a domain change that rolls back leaves no outbox row; a committed change leaves
  exactly one; two concurrent relays never create duplicate deliveries.
- A signature test vector (fixed secret, timestamp and body → expected hex) is shared by the
  delivery code and the receiver documentation.
- Delivery tests with `Http::fake`: retries with backoff and a fresh `t` on each attempt,
  disabling after the retry window, both signatures during a routine rotation and one after an
  immediate rotation, refusal of every blocked address range and of a redirect to a private
  address.
- The verification snippet rejects a `t` five minutes in the future as well as in the past.
- Export test: the CSV row for an event equals the webhook payload for the same event id.

## Pros and Cons of the Options

### 1. Dispatch after commit

- Good, because it is built into Laravel (`afterCommit`) and needs no table.
- Bad, because a crash between commit and dispatch loses the event silently, and a queue outage
  loses it too; there is no record to replay or export from.

### 2. Transactional outbox and relay (chosen)

- Good, because the event is stored atomically with the change and can be replayed, audited and
  exported.
- Bad, because it adds a table, a relay job and pruning.

### 3. Event sourcing as the outbound log

- Good, because events are the source of truth by construction.
- Bad, because it changes the persistence model of the whole application; Sunex already chose
  bitemporal tables for employment history ([ADR-0005](0005-bitemporal-employment-versions.md)),
  and internal domain events should not become a public contract.

### 4. A third-party outbox package

- Good, because someone else maintains it.
- Bad, because the Laravel outbox packages found are tiny and unproven ("not yet proven at scale"),
  so the dependency risk exceeds the amount of code saved.

### Signing a–e

- a and b: no integrity protection; a leaked static token is valid forever and does not bind the
  body.
- c: integrity, but a captured request can be replayed indefinitely.
- d (chosen): integrity and replay protection with a timestamp; the scheme used by Personio and
  BambooHR, and close to Deel's.
- e: better key distribution (no shared secret), but rare among HR vendors and more work for every
  receiver; reconsider if subscribers ask for it.

## More Information

Sources (read 2026-09-30):

- HiBob rebuilt its payroll hub on change events with the transactional outbox, idempotent
  processing, partitioning by employee id, dead-letter queues and backoff —
  [HiBob Engineering, 2025-09-18](https://medium.com/hibob-engineering/event-driven-reports-in-payroll-hub-7491cf2dad0f).
- Personio: HMAC-SHA256 over timestamp and body, retries over three days, secret rotation with a
  seven-day grace — [Personio webhooks](https://developer.personio.de/reference/webhooks).
- Deel: HMAC-SHA256 signature, ten retries with backoff up to 16 hours, then the subscription is
  disabled — [Deel webhook event types](https://developer.deel.com/docs/webhook-event-types).
- BambooHR: HMAC-SHA256 signature with a timestamp, fixed retry schedule, HTTPS only —
  [BambooHR webhooks](https://documentation.bamboohr.com/docs/webhooks).
- Gusto: ordering not guaranteed, handlers must be idempotent —
  [Gusto webhooks](https://docs.gusto.com/app-integrations/docs/webhooks).
- Laravel outbox packages: [Dnakitare/laravel-outbox](https://github.com/Dnakitare/laravel-outbox),
  [PHPOutbox](https://github.com/sumantasam1990/PHPOutbox),
  [webrek/laravel-outbox](https://packagist.org/packages/webrek/laravel-outbox).

Related: [ADR-0009](0009-no-payroll-no-esocial-transmission.md) (what is sent),
[ADR-0011](0011-multi-company-single-installation.md) (company-scoped subscriptions),
[TDD-0001](../tdd/0001-v1-architecture.md) (event catalogue and payloads).

**What would reverse or amend this decision:** a message broker becoming part of the platform
(the outbox would then feed the broker instead of HTTP directly); subscribers requiring asymmetric
signatures (add scheme e alongside d); event volumes where the polling relay's latency matters
(switch the relay to `LISTEN/NOTIFY` wake-ups, keeping the table).
