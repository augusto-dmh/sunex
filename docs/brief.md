# Sunex — product brief

**Date:** 2026-09-30 · **Owner:** Augusto · **Status:** v1, revisited at the end of every phase
**Sources:** the author's research notes (market, compliance, agent runtime) and a recorded decision
interview; the public reasoning lives in [`docs/adr/`](adr/) and [`docs/tdd/`](tdd/).
Format: vision paragraph + product values + press release and internal FAQ (Amazon PR/FAQ) +
no-gos and appetite (Shape Up).

## Vision (one paragraph, does not change per phase)

An HR team opens Sunex and every person's employment history is there as a sequence of dated
facts: when each change takes effect, when it was recorded, why it happened and who approved it.
Férias are requested, checked against the CLT and approved in the same place, and the payroll
system receives clean, signed lifecycle events instead of spreadsheets. Leaders see their people
through the same rules as everyone else, and AI agents work beside them as accountable users:
each one has an owner, acts within a scope, asks a human before it changes anything, and leaves a
record of every action.

## Five product values (tie-breakers for every decision)

1. **A fact has a date and a reason.** No employment change exists without an effective date,
   a recorded date and a reason. Corrections are new facts, never silent edits.
2. **One door for everyone.** Humans, in-app agents and external assistants pass through the same
   policy function. An agent never sees or does what its sponsor could not.
3. **The source, not the transmitter.** Sunex is the best-structured source of the facts payroll
   needs. It never calculates payroll and never talks to eSocial.
4. **Brazil first, legible everywhere.** CLT and eSocial rules are encoded where they apply; the
   code, ADRs and docs read clearly to an engineer who has never heard of them.
5. **Depth over breadth.** One module done to the standard of the best vendors beats five done
   halfway. To add a module, finish the previous one.

## Press release (written as if v1 had shipped)

**Sunex: people management for Brazilian companies, with AI agents you can audit**

Sunex is an open-source people-management application for companies with one or several CNPJs.
It keeps each employee's record as a dated history, so HR can answer "what was true on this date,
and when did we learn it" in one query. Admissions are checked for eSocial completeness before
the start date, and changes go out to the payroll system as signed events and CSV files.

Férias requests follow the CLT: the acquisition period, the split into up to three periods with
the 14-day and 5-day minimums, abono pecuniário and the reduction by absences are enforced when
the request is made, not discovered at payroll closing. Afastamentos track the 15-day threshold.

Two AI agents ship with v1. One answers policy and balance questions with citations. The other
drafts férias requests that a person reviews and a manager approves. Both act as registered users
with an owner and a scope, and every tool call they make is logged next to the change it caused.
The same tools are available to Claude or ChatGPT through an MCP server, under the same rules.

"I wanted an HR system where the history is trustworthy and the AI is accountable," says the
author. "Sunex is what I would want to maintain."

## Internal FAQ

**Three reasons this could fail**

1. **The bitemporal core swallows the 12 weeks.** Mitigation: bitemporality only on employment
   versions ([ADR-0005](adr/0005-bitemporal-employment-versions.md)); everything else is effective-dated plus audit log. If the core passes
   week 5, the second agent moves to v1.1.
2. **CLT rules are encoded wrongly and the demo is legally misleading.** Mitigation: every rule
   cites its article, has a table-driven test, and the UI labels balances as calculated by Sunex,
   with payroll as the system of record. Primary texts are checked before each rule ships.
3. **Scope creep from the "almost infinite" domain.** Mitigation: the no-gos below, one module
   at a time, appetite with a circuit breaker.

**Why not build on an existing open-source HRMS?** None is in modern Laravel; the best data
models (Frappe HR, Odoo `hr.version`) are in Python and serve as references only.

**Why Laravel AI and not Agno?** The agent identity, policy and audit design has to live in
Laravel anyway; a Python sidecar would duplicate it. [ADR-0008](adr/0008-agent-runtime-laravel-ai-and-mcp.md) records the
reasoning and the conditions that would reverse it.

**Who uses it?** A demo company with seeded data, reviewers of the author's work, and anyone who
self-hosts it under AGPL-3.0.

## Global no-gos (all phases)

- No payroll calculation, no eSocial XML, no eSocial transmission.
- No SaaS sign-up or tenant isolation; multi-company inside one installation only.
- No agent action that changes data without a human approval in v1.
- No AI feature that reads data its sponsor cannot read.
- No recruiting/ATS, time clock or banco de horas.
- No code, schema or text from any employer's system; ideas only.

## Phases

| Phase | Content | Observable success |
|---|---|---|
| v1 (12 weeks) | Effective-dated record (bitemporal employment), org and positions, movements with approvals, férias and afastamentos, eSocial readiness and signed events, agent registry + MCP, Q&A agent and férias-drafting agent | A reviewer clones the repo, runs one command, and follows a férias request from agent draft to manager approval to signed event, with the audit trail visible |
| Module 2 | Performance: dyad-scoped 1:1s, check-ins, PDI, then eNPS; meeting-transcript intake agent | A 1:1 transcript becomes action items in the right 1:1 without anyone outside the pair reading it |
| Module 3 | Finance: people cost, headcount plan vs actual, cost centres, GL CSV | Monthly cost per cost centre matches a hand calculation for the demo company |
| Later | Rest of the Brazil pack (experiência, aviso prévio, desligamento, LGPD toolset, NR-1), deploy to a VPS | — |

## Appetite

**v1: 12 weeks of spare hours** [user, 2026-09-30]. If v1 runs over, its scope is cut, not the
deadline: first the férias-drafting agent moves to v1.1, then the MCP server.
